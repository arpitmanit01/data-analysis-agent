<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/banner-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/assets/banner-light.svg">
  <img alt="Data Analysis Agent" src="docs/assets/banner-light.svg" width="720">
</picture>

# Data Analysis Agent

**Chat with your CSV.** Ask a question in plain English. The agent profiles your
data, asks for clarification when needed, writes and runs the analysis code, and
hands back clear, data-grounded insights.

</div>

---

## What it does

- 📊 **Upload a CSV, ask a question.** No SQL or pandas required.
- 🤔 **Asks smart clarifying questions** when your request is ambiguous.
- 🧑‍💻 **Writes and executes analysis code** for you, then double-checks its own work.
- 💡 **Returns insights, caveats, and charts**, not just raw numbers.
- 🖥️ **CLI or web UI**, with a live view of the agent's reasoning.

## Quickstart

**Prerequisites:** Python 3.13+ and an Azure AI Foundry API key.

**First, configure your key** (needed by every run method below):

```bash
cp .env.example .env                     # then edit .env and set AZURE_AI_API_KEY
```

The repo ships with a sample dataset at `tests/data/sales.csv` (columns:
`order_id, order_date, region, category, quantity, unit_price, order_value,
customer_segment`). Every option below includes a ready to run example against it.

Pick the way that suits you:

- [Option A: CLI (pip)](#option-a-cli-with-pip)
- [Option B: CLI (uv)](#option-b-cli-with-uv)
- [Option C: Streamlit UI (local code)](#option-c-streamlit-ui-local-code)
- [Option D: Docker (local build and run)](#option-d-docker-local-build-and-run)

### Option A: CLI with pip

```bash
# 1. Install into your environment (a virtualenv is recommended)
pip install -r requirements.txt

# 2. Run the bundled example
python src/agent.py --csv tests/data/sales.csv \
  --query "Which region has the highest total order_value?"
```

### Option B: CLI with uv

[uv](https://docs.astral.sh/uv/) manages the virtualenv and dependencies for you.

```bash
# 1. Install (creates .venv and resolves from uv.lock)
uv sync

# 2. Run the bundled example
uv run python src/agent.py --csv tests/data/sales.csv \
  --query "Which region has the highest total order_value?"
```

### Option C: Streamlit UI (local code)

Runs the web UI straight from the source. Use whichever installer you set up above.

```bash
streamlit run app/streamlit_app.py       # http://localhost:8501
# with uv:
uv run streamlit run app/streamlit_app.py
```

**Try the example:** open http://localhost:8501, upload `tests/data/sales.csv`,
and ask *"Which region has the highest total order_value?"*.

### Option D: Docker (local build and run)

Builds the image from this repo and runs it in a container. Requires Docker.

**Web UI (default):**

```bash
docker compose up --build                # http://localhost:8501
```

Then upload `tests/data/sales.csv` in the browser, as in Option C.

**CLI (one-off run of the example):**

```bash
# Build the image once
docker build -t data-analysis-agent:latest .

# Run the bundled example (the CSV is baked into the image under tests/data/)
docker run --rm --env-file .env data-analysis-agent:latest \
  python src/agent.py --csv tests/data/sales.csv \
  --query "Which region has the highest total order_value?"
```

## How it works (at a glance)

A small team of specialist agents, coordinated by a planner, running a
`reason → plan → act → observe → respond` loop:

```
profiler → planner → ┬─ clarifier  (ask questions)
                     ├─ codegen    (write + run code, self-critique) ⟲
                     └─ insight     (summarize findings)
```

📖 **Want the full picture?** See the [Architecture deep-dive](docs/architecture.md).

## Opinionated choices

This project makes a few deliberate choices to stay simple and fast. All of them
are swappable. See [Design Decisions](wikis/design-decisions.md) for the full
rationale and trade-offs.

| Area | Choice |
| --- | --- |
| Agent framework | **LangGraph + LangChain** |
| LLM provider | **Azure AI Foundry** (any OpenAI-compatible endpoint works) |
| Memory / persistence | **SQLite** checkpointer (per conversation thread) |
| Code execution | **In-process sandbox** with guardrails ⚠️ *not* for untrusted input |
| Dependencies | **uv** (with a `requirements.txt` fallback) |

## Usage tips

```bash
# Let the agent ask clarifying questions first, then resume on the same thread:
python src/agent.py --csv <file.csv> --query "Show me the best performance."
python src/agent.py --csv <file.csv> --query "Show me the best performance." \
  --thread-id <printed-id> --clarifications "Total order_value by region."

# Skip clarifying questions and see the full JSON reasoning trace:
python src/agent.py --csv <file.csv> --query "..." --no-clarify --json-trace
```

Configuration (model, temperature, timeouts, guardrail limits) is set via `.env`.
See the [full reference](docs/architecture.md#configuration-reference).

## Evaluation

```bash
python src/evaluate.py --scenarios tests/scenarios.json --out eval_results.json
```

Runs representative scenarios and scores each output against expected results.
See the [Agent Run Report](docs/agent_run_report.md) for a sample run and results.

## Documentation

| Doc | What's inside |
| --- | --- |
| [Architecture deep-dive](docs/architecture.md) | Agent loop, tools, techniques, config, project layout |
| [Design Decisions](wikis/design-decisions.md) | Why each choice was made + trade-offs |
| [Agent Run Report](docs/agent_run_report.md) | Sample trace, clarification flow, evaluation results |

## Features

Multi-agent orchestration · conversation memory · streaming responses ·
Streamlit UI · Docker deployment · structured (Pydantic) outputs · retries,
timeouts & guardrails · full reasoning trace.
