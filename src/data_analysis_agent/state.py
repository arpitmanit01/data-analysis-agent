"""LangGraph shared state definition.

The state is threaded through every node in the graph. LangGraph merges partial
dict updates returned by each node into this typed structure.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    """Mutable state passed between graph nodes."""

    # --- Inputs -----------------------------------------------------------
    csv_path: str
    user_query: str
    # User-supplied answers to earlier clarifying questions (optional).
    clarifications: str

    # --- Data context -----------------------------------------------------
    profile: str  # human-readable CSV profile injected into prompts

    # --- Working memory ---------------------------------------------------
    plan: str
    generated_code: str
    execution_output: str
    execution_error: str
    attempts: int  # code-gen/execute/critique loop counter

    # --- Control flow -----------------------------------------------------
    next_action: str  # clarify | analyze | finish
    needs_user_input: bool
    pending_questions: list[str]

    # --- Outputs ----------------------------------------------------------
    insights: dict[str, Any]
    final_response: str

    # --- Observability (append-only trace) --------------------------------
    trace: Annotated[list[dict], operator.add]
