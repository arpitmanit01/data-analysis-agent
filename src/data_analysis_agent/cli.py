"""Command-line interface for the Data Analysis Agent.

Usage:
    python src/agent.py --csv data.csv --query "Which region sells most?"
    python src/agent.py --csv data.csv --query "..." --no-clarify --json-trace
"""

from __future__ import annotations

import argparse
import sys

from .config import config_error_message, get_settings
from .llm import LLMConfigurationError
from .runner import DataAnalysisAgent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="data-analysis-agent",
        description="Agentic CSV data-analysis assistant.",
    )
    parser.add_argument("--csv", required=True, help="Path to the CSV file.")
    parser.add_argument("--query", required=True, help="Analysis question.")
    parser.add_argument(
        "--domain",
        default="data-analysis",
        help="Domain (fixed to data-analysis; accepted for spec compatibility).",
    )
    parser.add_argument("--thread-id", default=None, help="Resume a prior session.")
    parser.add_argument(
        "--clarifications",
        default="",
        help="Answers to clarifying questions (skips the clarify step).",
    )
    parser.add_argument(
        "--no-clarify",
        action="store_true",
        help="Auto-proceed without pausing for clarifying questions.",
    )
    parser.add_argument(
        "--no-stream", action="store_true", help="Disable streaming step output."
    )
    parser.add_argument(
        "--json-trace", action="store_true", help="Print the full JSON trace."
    )
    parser.add_argument(
        "--no-memory", action="store_true", help="Disable persistent memory."
    )
    return parser


def _print_header(settings) -> None:
    print(f"\n=== Data Analysis Agent (model={settings.model}) ===\n")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()

    config_error = config_error_message(settings)
    if config_error:
        print(f"ERROR: {config_error}", file=sys.stderr)
        return 2

    _print_header(settings)

    try:
        agent = DataAnalysisAgent(use_memory=not args.no_memory)
        clarifications = args.clarifications
        # If the user pre-answered or asked to skip, treat as clarified.
        if args.no_clarify and not clarifications:
            clarifications = "(No clarifications; proceed with best assumptions.)"

        thread_id = args.thread_id or agent.new_thread_id()
        print(f"Session thread: {thread_id}\n")

        if args.no_stream:
            final = agent.run(
                args.csv,
                args.query,
                thread_id=thread_id,
                clarifications=clarifications,
            )
        else:
            final = _run_streaming(agent, args, thread_id, clarifications)

    except LLMConfigurationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: agent run failed: {exc}", file=sys.stderr)
        return 1

    return _report(final, args)


def _run_streaming(agent, args, thread_id, clarifications) -> dict:
    final: dict = {}
    for node_name, output in agent.stream(
        args.csv, args.query, thread_id=thread_id, clarifications=clarifications
    ):
        for event in output.get("trace", []):
            print(f"  [{event['phase']:>8}] {event['step']}: {event['detail']}")
        final.update(output)
    final["thread_id"] = thread_id
    return final


def _report(final: dict, args) -> int:
    if final.get("needs_user_input"):
        print("\n--- Clarifying questions ---")
        for q in final.get("pending_questions", []):
            print(f"  ? {q}")
        print(
            "\nRe-run with --clarifications \"...\" and "
            f"--thread-id {final.get('thread_id')} to continue."
        )
        return 0

    print("\n" + "=" * 60)
    print(final.get("final_response", "(no response produced)"))
    print("=" * 60)

    if args.json_trace:
        import json

        print("\n--- TRACE ---")
        print(json.dumps(final.get("trace", []), indent=2, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
