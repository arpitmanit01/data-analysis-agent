"""Pydantic models for structured LLM outputs.

Using JSON/structured output keeps agent hand-offs typed and parseable instead
of relying on brittle free-text parsing.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PlannerDecision(BaseModel):
    """The planner's routing decision for the next step."""

    next_action: Literal["clarify", "analyze", "finish"] = Field(
        description="Which step to take next: ask a clarifying question, run an "
        "analysis, or finish and summarize."
    )
    reasoning: str = Field(
        description="Brief chain-of-thought justification for the decision."
    )


class ClarifyingQuestions(BaseModel):
    """Clarifying questions the agent needs answered before analyzing."""

    questions: list[str] = Field(
        default_factory=list,
        description="1-3 targeted clarifying questions. Empty if none needed.",
    )
    rationale: str = Field(
        description="Why these questions matter for the requested analysis."
    )


class GeneratedCode(BaseModel):
    """A block of analysis code plus its intent."""

    plan: str = Field(description="Short step-by-step plan the code implements.")
    code: str = Field(
        description="Executable Python. The DataFrame is preloaded as `df`. "
        "Print results and assign a final summary string to `result`."
    )
    expected_output: str = Field(
        description="What the code is expected to produce, for self-check."
    )


class InsightSummary(BaseModel):
    """Final insights distilled from executed analysis."""

    insights: list[str] = Field(
        description="Concrete, data-grounded findings (3-6 bullet points)."
    )
    caveats: list[str] = Field(
        default_factory=list,
        description="Limitations, assumptions, or data-quality caveats.",
    )
    summary: str = Field(description="One-paragraph plain-language summary.")


class Critique(BaseModel):
    """Self-critique of an analysis result (self-reflection technique)."""

    is_sufficient: bool = Field(
        description="True if the result adequately answers the user's question."
    )
    issues: list[str] = Field(
        default_factory=list,
        description="Problems found (errors, wrong approach, missing angles).",
    )
    suggestion: str = Field(
        default="",
        description="If insufficient, how the next attempt should improve.",
    )
