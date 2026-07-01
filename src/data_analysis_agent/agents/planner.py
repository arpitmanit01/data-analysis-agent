"""Planner agent: decides the next action (clarify / analyze / finish)."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import enforce_token_budget, invoke_structured
from ..prompts import PLANNER_SYSTEM, build_context_block
from ..schemas import PlannerDecision
from ..state import AgentState


def planner_node(state: AgentState) -> dict:
    """Route the workflow based on current state."""
    attempts = state.get("attempts", 0)
    clarifications = state.get("clarifications", "")

    # Deterministic guard-rails around the LLM decision to avoid loops.
    if attempts >= 3:
        decision = PlannerDecision(
            next_action="finish",
            reasoning="Reached maximum analysis attempts; finishing.",
        )
    else:
        context = build_context_block(
            state.get("profile", ""), state["user_query"], clarifications
        )
        prior = state.get("execution_output", "")
        if prior:
            context += f"\n\n=== LATEST ANALYSIS OUTPUT ===\n{prior}"
        context = enforce_token_budget(context)

        decision = invoke_structured(
            [SystemMessage(content=PLANNER_SYSTEM), HumanMessage(content=context)],
            PlannerDecision,
        )
        # Never clarify twice.
        if decision.next_action == "clarify" and clarifications:
            decision.next_action = "analyze"

    return {
        "next_action": decision.next_action,
        "trace": [
            {
                "step": "planner",
                "phase": "plan",
                "detail": f"next_action={decision.next_action}",
                "data": {"reasoning": decision.reasoning, "attempts": attempts},
            }
        ],
    }
