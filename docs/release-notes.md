# Release Notes

Signed semantic-version tags for this project. Each tag maps to a milestone commit
on `main`. Use these notes when publishing the matching GitHub Release.

| Version | Tag commit | Milestone |
|---------|-----------|-----------|
| v0.1.0 | Core agent | LangGraph orchestration, sandboxed execution, CLI, eval harness |
| v0.2.0 | UI + deploy | Streamlit UI, Docker, initial docs |
| v0.3.0 | Docs | Practical README, architecture deep-dive, themed banners |
| v0.3.1 | Fixes | Chart artifacts + resumed-run clarify flags |
| v1.0.0 | Stable | First complete, evaluated (5/5) release |

---

## v0.1.0 - Core data-analysis agent
First functional agent milestone.

- LangGraph orchestration: profiler, planner, clarifier, codegen, and insight nodes
- Sandboxed code execution (in-process exec with AST/import denylist and timeout)
- Command-line interface
- 5-scenario evaluation harness

## v0.2.0 - Streamlit UI, Docker, and initial docs
- Streamlit chat interface
- Docker and docker-compose deployment
- Initial README, design-decision wikis, and first agent run report

## v0.3.0 - Documentation overhaul
- Lighter, practical README
- Deep-dive moved to docs/architecture.md
- Light/dark themed project banners

## v0.3.1 - Bug fixes
- Charts now save to the artifacts directory instead of the working directory
- Resumed runs no longer mis-report as still needing clarification

## v1.0.0 - First complete stable release
Data Analysis Agent: CSV intake, clarifying questions, code generation and sandboxed
execution, and insight synthesis. Evaluation 5/5.

Includes the Streamlit UI, Docker deployment, full documentation, and an Agent Run
Report built from real captured traces.
