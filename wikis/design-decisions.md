# Design Decisions & Trade-offs

This document records the key implementation choices, the alternatives that were
considered, and the trade-offs accepted. It is the source of truth for "why" the
project is built the way it is.

## 1. Agentic framework: LangGraph + LangChain

**Chosen:** LangGraph (orchestration) on top of LangChain (LLM + structured
output).

**Alternatives:** LangChain `AgentExecutor` only, CrewAI, a custom loop.

**Rationale / trade-offs:**
- The known-good reference already authenticates via LangChain `ChatOpenAI`
  against Azure AI Foundry, so LangChain integration is proven.
- LangGraph gives an explicit state machine (nodes + conditional edges), which
  makes the `reason → plan → act → observe → respond` loop and the self-critique
  retry cycle first-class and inspectable — better than an opaque agent executor.
- LangGraph's checkpointer cleanly delivers the **memory/persistence** bonus.
- Trade-off: more wiring code than a one-liner `AgentExecutor`, but far clearer
  control flow and easier testing.

## 2. LLM endpoint: Azure AI Foundry via `ChatOpenAI`

**Chosen:** `ChatOpenAI(api_key=AZURE_AI_API_KEY, base_url=".../models",
model="gpt-5.4")`, mirroring the reference notebook exactly.

**Rationale:** Reuses a verified-working configuration; all values are
externalized to `.env`. `AZURE_OPENAI_API_KEY` is accepted as a fallback env var.

## 3. Code execution sandbox: simple in-process `exec` + light guardrails

**Chosen (per explicit user decision):** in-process `exec` with a namespace
containing only `df`, `pd`, `np`, `plt`; an AST denylist for dangerous imports;
and a wall-clock timeout via a worker thread.

**Alternatives considered:**
- Subprocess sandbox with resource limits.
- `RestrictedPython`-style restricted execution.
- Docker-isolated execution.

**Trade-off (important):** in-process `exec` is **not a security boundary**. A
worker thread cannot be force-killed in CPython, and generated code shares the
interpreter. This was chosen for development speed on a trusted, self-authored
LLM in a single-user assignment context. For untrusted input or production, swap
`tools/code_exec.py` for subprocess or Docker isolation — the interface
(`execute_code(code, df) -> ExecutionResult`) is designed to make that swap
localized.

## 4. Structured output via Pydantic

Every agent hand-off (`PlannerDecision`, `ClarifyingQuestions`, `GeneratedCode`,
`InsightSummary`, `Critique`) is a Pydantic model bound through
`with_structured_output`. This avoids brittle free-text parsing and gives the
planner a reliable routing signal.

## 5. Clarify-then-resume via interrupt + persisted thread

Rather than blocking the process waiting for input, the `clarifier` node ends the
graph with `needs_user_input=True`. The user re-invokes on the same `thread_id`
with `--clarifications`; the SQLite checkpointer restores the CSV profile and
prior context, and the planner proceeds to analysis. This keeps the CLI and UI
stateless between turns while preserving memory.

## 6. Retry/critique loop bounds

The codegen → execute → critic loop is capped at 3 attempts (also enforced
defensively in the planner) to guarantee termination and bound cost/latency,
trading a small amount of answer quality on hard questions for reliability.

## 7. Evaluation approach: transparent keyword/behaviour scoring

Scoring uses simple, explainable checks (`expect_keywords`, `expect_contains`,
`should_clarify`) rather than an LLM judge, so results are deterministic and
free of extra API cost. Trade-off: less nuanced than an LLM grader, but
reproducible and easy to audit.
