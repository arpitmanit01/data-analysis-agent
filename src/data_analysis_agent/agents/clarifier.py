"""Clarifier agent: asks targeted clarifying questions when needed."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import enforce_token_budget, invoke_structured
from ..prompts import CLARIFIER_SYSTEM, build_context_block
from ..schemas import ClarifyingQuestions
from ..state import AgentState


def clarifier_node(state: AgentState) -> dict:
    """Generate clarifying questions and pause for user input."""
    context = build_context_block(
        state.get("profile", ""),
        state["user_query"],
        state.get("clarifications", ""),
    )
    result = invoke_structured(
        [
            SystemMessage(content=CLARIFIER_SYSTEM),
            HumanMessage(content=enforce_token_budget(context)),
        ],
        ClarifyingQuestions,
    )

    questions = result.questions or []
    return {
        "pending_questions": questions,
        "needs_user_input": bool(questions),
        "trace": [
            {
                "step": "clarifier",
                "phase": "act",
                "detail": f"generated {len(questions)} clarifying question(s)",
                "data": {"questions": questions, "rationale": result.rationale},
            }
        ],
    }
