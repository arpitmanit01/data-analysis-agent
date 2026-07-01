"""Lightweight evaluation harness.

Runs the agent across a set of scenarios and scores each output against
expected results. Scoring is intentionally simple and transparent:

  * `expect_keywords`  -> fraction of required keywords present (case-insensitive)
  * `expect_contains`  -> substring must appear in the final response
  * `should_clarify`   -> whether the agent asked clarifying questions

A scenario passes when its score >= `pass_threshold` (default 0.5).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .runner import DataAnalysisAgent


@dataclass
class ScenarioResult:
    name: str
    passed: bool
    score: float
    details: dict = field(default_factory=dict)


def _score_scenario(scenario: dict, final: dict) -> ScenarioResult:
    response = (final.get("final_response") or "").lower()
    checks: dict[str, float] = {}

    keywords = [k.lower() for k in scenario.get("expect_keywords", [])]
    if keywords:
        hits = sum(1 for k in keywords if k in response)
        checks["keywords"] = hits / len(keywords)

    contains = scenario.get("expect_contains")
    if contains:
        checks["contains"] = 1.0 if contains.lower() in response else 0.0

    if "should_clarify" in scenario:
        asked = bool(final.get("needs_user_input"))
        checks["clarify"] = 1.0 if asked == scenario["should_clarify"] else 0.0

    score = sum(checks.values()) / len(checks) if checks else 0.0
    threshold = scenario.get("pass_threshold", 0.5)
    return ScenarioResult(
        name=scenario["name"],
        passed=score >= threshold,
        score=round(score, 3),
        details={"checks": checks, "response_preview": response[:200]},
    )


def run_evaluation(scenarios_path: str, *, use_memory: bool = False) -> dict:
    """Execute all scenarios and return an aggregate report."""
    with open(scenarios_path, encoding="utf-8") as fh:
        scenarios = json.load(fh)

    agent = DataAnalysisAgent(use_memory=use_memory)
    results: list[ScenarioResult] = []

    for scenario in scenarios:
        clarifications = scenario.get("clarifications", "")
        # For deterministic eval, auto-proceed unless the scenario tests clarify.
        if not clarifications and not scenario.get("should_clarify"):
            clarifications = "(Proceed with best assumptions.)"
        try:
            final = agent.run(
                scenario["csv"],
                scenario["query"],
                clarifications=clarifications,
            )
            results.append(_score_scenario(scenario, final))
        except Exception as exc:  # noqa: BLE001
            results.append(
                ScenarioResult(scenario["name"], False, 0.0, {"error": str(exc)})
            )

    passed = sum(1 for r in results if r.passed)
    return {
        "total": len(results),
        "passed": passed,
        "pass_rate": round(passed / len(results), 3) if results else 0.0,
        "results": [r.__dict__ for r in results],
    }


def print_report(report: dict) -> None:
    print("\n=== Evaluation Report ===")
    for r in report["results"]:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['name']} (score={r['score']})")
    print(
        f"\n{report['passed']}/{report['total']} scenarios passed "
        f"(pass_rate={report['pass_rate']})\n"
    )
