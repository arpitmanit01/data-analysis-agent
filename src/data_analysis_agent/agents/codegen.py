"""CodeGen agent: writes analysis code, executes it, and self-critiques.

Implements the act -> observe portion of the loop plus self-reflection: after
executing, a critic judges sufficiency and may request another attempt.
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import enforce_token_budget, invoke_structured
from ..prompts import (
    CODEGEN_FEWSHOT,
    CODEGEN_SYSTEM,
    CRITIC_SYSTEM,
    build_context_block,
)
from ..schemas import Critique, GeneratedCode
from ..state import AgentState
from ..tools.code_exec import execute_code
from ..tools.csv_tools import load_csv


@lru_cache(maxsize=8)
def _cached_df(csv_path: str) -> pd.DataFrame:
    return load_csv(csv_path)


def codegen_node(state: AgentState) -> dict:
    """Generate + execute analysis code, then self-critique the result."""
    attempts = state.get("attempts", 0) + 1
    context = build_context_block(
        state.get("profile", ""),
        state["user_query"],
        state.get("clarifications", ""),
    )

    # Feed back the previous failure so the model can fix it.
    prev_error = state.get("execution_error", "")
    prev_code = state.get("generated_code", "")
    if prev_error:
        context += (
            f"\n\n=== PREVIOUS ATTEMPT (failed) ===\nCODE:\n{prev_code}\n\n"
            f"ERROR:\n{prev_error}\nFix the specific problem."
        )

    gen = invoke_structured(
        [
            SystemMessage(content=CODEGEN_SYSTEM + "\n\n" + CODEGEN_FEWSHOT),
            HumanMessage(content=enforce_token_budget(context)),
        ],
        GeneratedCode,
    )

    df = _cached_df(state["csv_path"])
    exec_result = execute_code(gen.code, df)
    observation = exec_result.as_observation()

    # Self-reflection: is this good enough, or should we retry?
    critique = _critique(state, gen.code, observation)
    should_retry = (not critique.is_sufficient) and attempts < 3

    return {
        "attempts": attempts,
        "plan": gen.plan,
        "generated_code": gen.code,
        "execution_output": observation if exec_result.ok else "",
        "execution_error": "" if exec_result.ok else exec_result.error,
        "next_action": "retry" if should_retry else "synthesize",
        "trace": [
            {
                "step": "codegen",
                "phase": "act",
                "detail": f"attempt {attempts}: generated and executed code",
                "data": {"plan": gen.plan, "code": gen.code},
            },
            {
                "step": "executor",
                "phase": "observe",
                "detail": "ok" if exec_result.ok else "error",
                "data": {"observation": observation},
            },
            {
                "step": "critic",
                "phase": "reason",
                "detail": f"sufficient={critique.is_sufficient}, retry={should_retry}",
                "data": {"issues": critique.issues, "suggestion": critique.suggestion},
            },
        ],
    }


def _critique(state: AgentState, code: str, observation: str) -> Critique:
    context = (
        f"USER QUESTION:\n{state['user_query']}\n\n"
        f"EXECUTED CODE:\n{code}\n\n"
        f"OBSERVED OUTPUT:\n{observation}"
    )
    return invoke_structured(
        [
            SystemMessage(content=CRITIC_SYSTEM),
            HumanMessage(content=enforce_token_budget(context)),
        ],
        Critique,
    )
