"""Insight agent: synthesizes final insights from executed analysis output."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import enforce_token_budget, invoke_structured
from ..prompts import INSIGHT_SYSTEM
from ..schemas import InsightSummary
from ..state import AgentState


def _render(summary: InsightSummary) -> str:
    lines = ["## Insights"]
    lines += [f"- {i}" for i in summary.insights]
    if summary.caveats:
        lines.append("\n## Caveats")
        lines += [f"- {c}" for c in summary.caveats]
    lines.append("\n## Summary")
    lines.append(summary.summary)
    return "\n".join(lines)


def insight_node(state: AgentState) -> dict:
    """Produce the final, user-facing insight summary."""
    output = state.get("execution_output", "")
    error = state.get("execution_error", "")

    if not output and error:
        # Graceful fallback: no successful analysis to summarize.
        summary = InsightSummary(
            insights=["The analysis could not be completed successfully."],
            caveats=[f"Last error: {error}"],
            summary=(
                "The agent was unable to produce a reliable answer after "
                "multiple attempts. Consider rephrasing the question or "
                "checking the dataset."
            ),
        )
    else:
        context = (
            f"USER QUESTION:\n{state['user_query']}\n\n"
            f"ANALYSIS OUTPUT:\n{output}"
        )
        summary = invoke_structured(
            [
                SystemMessage(content=INSIGHT_SYSTEM),
                HumanMessage(content=enforce_token_budget(context)),
            ],
            InsightSummary,
        )

    rendered = _render(summary)
    return {
        "insights": json.loads(summary.model_dump_json()),
        "final_response": rendered,
        "next_action": "done",
        # Clear any stale clarify flags so a resumed run reports correctly.
        "needs_user_input": False,
        "pending_questions": [],
        "trace": [
            {
                "step": "insight",
                "phase": "respond",
                "detail": f"synthesized {len(summary.insights)} insight(s)",
                "data": {"summary": summary.summary},
            }
        ],
    }
