"""High-level agent runner used by the CLI and the Streamlit UI.

Wraps graph construction, memory, streaming, and the clarify -> resume cycle
behind a small API so front-ends stay thin.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

from .graph import build_graph
from .memory import build_checkpointer
from .state import AgentState


class DataAnalysisAgent:
    """Stateful agent bound to a persistent memory checkpointer."""

    def __init__(self, *, use_memory: bool = True) -> None:
        self._checkpointer = build_checkpointer() if use_memory else None
        self._graph = build_graph(self._checkpointer)

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def new_thread_id() -> str:
        return uuid.uuid4().hex[:12]

    def _config(self, thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}}

    # -- execution ---------------------------------------------------------
    def run(
        self,
        csv_path: str,
        query: str,
        *,
        thread_id: str | None = None,
        clarifications: str = "",
    ) -> dict[str, Any]:
        """Run the agent to completion and return the final state."""
        thread_id = thread_id or self.new_thread_id()
        inputs: AgentState = {"csv_path": csv_path, "user_query": query}
        if clarifications:
            inputs["clarifications"] = clarifications
        final = self._graph.invoke(inputs, self._config(thread_id))
        final["thread_id"] = thread_id
        return final

    def stream(
        self,
        csv_path: str,
        query: str,
        *,
        thread_id: str | None = None,
        clarifications: str = "",
    ) -> Iterator[tuple[str, dict]]:
        """Yield (node_name, node_output) tuples as the graph executes."""
        thread_id = thread_id or self.new_thread_id()
        inputs: AgentState = {"csv_path": csv_path, "user_query": query}
        if clarifications:
            inputs["clarifications"] = clarifications
        for chunk in self._graph.stream(
            inputs, self._config(thread_id), stream_mode="updates"
        ):
            for node_name, node_output in chunk.items():
                yield node_name, node_output

    def resume_with_answers(
        self, csv_path: str, query: str, answers: str, thread_id: str
    ) -> dict[str, Any]:
        """Resume a clarified run on the same thread with the user's answers."""
        return self.run(
            csv_path, query, thread_id=thread_id, clarifications=answers
        )
