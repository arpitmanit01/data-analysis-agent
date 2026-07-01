"""Assignment-spec entrypoint: `python src/evaluate.py --scenarios ...`."""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_analysis_agent.config import get_settings  # noqa: E402
from data_analysis_agent.evaluation import print_report, run_evaluation  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the data-analysis agent.")
    parser.add_argument(
        "--scenarios",
        default=os.path.join(os.path.dirname(__file__), "..", "tests", "scenarios.json"),
        help="Path to scenarios JSON.",
    )
    parser.add_argument("--out", default=None, help="Optional path to save JSON report.")
    args = parser.parse_args(argv)

    if not get_settings().has_api_key:
        print("ERROR: set AZURE_AI_API_KEY in .env to run evaluation.", file=sys.stderr)
        return 2

    report = run_evaluation(os.path.abspath(args.scenarios))
    print_report(report)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"Saved report to {args.out}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
