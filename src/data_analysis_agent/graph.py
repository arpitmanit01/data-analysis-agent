"""LangGraph orchestration: wires specialist agents into the agent loop.

Flow (reason -> plan -> act -> observe -> respond):

    profiler -> planner --clarify--> clarifier -> (interrupt / END)
                       \--analyze--> codegen --retry--> codegen
                       |                    \--synthesize--> insight -> END
                       \--finish---> insight -> END
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .agents.clarifier import clarifier_node
from .agents.codegen import codegen_node
from .agents.insight import insight_node
from .agents.planner import planner_node
from .state import AgentState
from .tools.csv_tools import load_and_profile


def profiler_node(state: AgentState) -> dict:
    """Load + profile the CSV once at the start of a run (tool call)."""
    if state.get("profile"):
        return {}
    _, profile = load_and_profile(state["csv_path"])
    return {
        "profile": profile,
        "attempts": state.get("attempts", 0),
        "trace": [
            {
                "step": "profiler",
                "phase": "observe",
                "detail": "loaded and profiled CSV",
                "data": {"profile_preview": profile[:400]},
            }
        ],
    }


def _route_after_planner(state: AgentState) -> str:
    action = state.get("next_action", "analyze")
    if action == "clarify":
        return "clarifier"
    if action == "finish":
        return "insight"
    return "codegen"


def _route_after_codegen(state: AgentState) -> str:
    return "codegen" if state.get("next_action") == "retry" else "insight"


def build_graph(checkpointer=None):
    """Construct and compile the agent graph."""
    graph = StateGraph(AgentState)

    graph.add_node("profiler", profiler_node)
    graph.add_node("planner", planner_node)
    graph.add_node("clarifier", clarifier_node)
    graph.add_node("codegen", codegen_node)
    graph.add_node("insight", insight_node)

    graph.add_edge(START, "profiler")
    graph.add_edge("profiler", "planner")
    graph.add_conditional_edges(
        "planner",
        _route_after_planner,
        {"clarifier": "clarifier", "codegen": "codegen", "insight": "insight"},
    )
    # After asking clarifying questions we stop so the user can respond.
    graph.add_edge("clarifier", END)
    graph.add_conditional_edges(
        "codegen",
        _route_after_codegen,
        {"codegen": "codegen", "insight": "insight"},
    )
    graph.add_edge("insight", END)

    return graph.compile(checkpointer=checkpointer)
