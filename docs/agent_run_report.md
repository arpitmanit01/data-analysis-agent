# Agent Run Report — Data Analysis Agent

This report is the assignment's **Agent Run Report** deliverable. It contains the
architecture diagram, real sample agent traces (reasoning chain + tool calls +
final output), evaluation results across the test scenarios, and a short summary
of design decisions and trade-offs.

| | |
| --- | --- |
| **Domain** | Data Analysis agent (CSV → clarify → generate + execute code → insights) |
| **Framework** | LangGraph + LangChain |
| **Model** | `gpt-5.4` via Azure AI Foundry (OpenAI-compatible endpoint) |
| **Dataset used** | `tests/data/sales.csv` (30 rows, 8 columns of orders data) |

All traces below are captured verbatim from live runs (`--json-trace`).

---

## 1. Architecture

A multi-agent LangGraph state machine implementing
`reason → plan → act → observe → respond`, with a **planner** delegating to
specialists and a **self-reflection** (critic) loop around code execution.

```mermaid
flowchart TD
    START([START]) --> P[profiler<br/>load + profile CSV]
    P --> PL[planner<br/>reason → route]
    PL -- clarify --> C[clarifier<br/>ask questions]
    PL -- analyze --> CG[codegen<br/>write + execute code]
    PL -- finish --> I[insight<br/>synthesize]
    C --> E1([END: await user])
    CG -- critic: insufficient --> CG
    CG -- critic: sufficient --> I
    I --> E2([END])
```

| Component | Phase | Role (tool calls in **bold**) |
| --- | --- | --- |
| `profiler` | observe | **Loads + profiles the CSV** (shape, dtypes, nulls, summary). |
| `planner` | reason/plan | Chain-of-thought routing: clarify / analyze / finish. |
| `clarifier` | act | Asks up to 3 targeted clarifying questions, then pauses. |
| `codegen` | act/observe | Generates pandas/matplotlib code and **executes it in the sandbox**, then self-critiques. |
| `insight` | respond | Synthesizes final insights + caveats from the executed output. |

---

## 2. Sample trace A — full lifecycle with clarification + memory

This single run shows the complete reasoning chain **across a clarification
boundary**. The user asks an ambiguous question; the agent pauses and asks for
clarification; the user resumes on the **same thread**; persisted memory restores
the CSV profile, and the agent proceeds to analysis. Because the trace is
append-only, one continuous chain spans both turns.

**Turn 1 — ambiguous query**

```bash
python src/agent.py --csv tests/data/sales.csv --query "Show me the best performance."
```

Planner reasons and routes to `clarify`; the clarifier returns:

```
? What do you want to measure as "best performance": highest total sales/order_value,
  highest number of orders, highest quantity sold, or something else?
? Which dimension should performance be evaluated across: region, category,
  customer_segment, individual orders, or over time (e.g., by date/month)?
? Should "best" mean the single top performer only, or a ranked list/top N?
```

**Turn 2 — resume the same thread with answers**

```bash
python src/agent.py --csv tests/data/sales.csv --query "Show me the best performance." \
  --thread-id <printed-id> \
  --clarifications "Best = highest total order_value, by region, full dataset."
```

**Full reasoning chain (verbatim, accumulated across both turns)**

```
[observe] profiler : loaded and profiled CSV
[plan]    planner  : next_action=clarify
          reasoning: "Best performance is ambiguous ... A single clarification is needed."
[act]     clarifier: generated 3 clarifying question(s)
--- user answers, resumes same thread (memory restores CSV profile) ---
[plan]    planner  : next_action=analyze
          reasoning: "The clarification defines 'best performance' as highest total
                      order_value by region across the full dataset. We have enough
                      information to aggregate order_value by region."
[act]     codegen  : attempt 1: generated and executed code
[observe] executor : ok
[reason]  critic   : sufficient=True, retry=False
[respond] insight  : synthesized 5 insight(s)
```

**Tool call — generated code (executed in the sandbox)**

```python
region_performance = (
    df.groupby('region', as_index=True)['order_value']
      .sum().sort_values(ascending=False)
)
print("Total order_value by region:")
print(region_performance)
best_region = region_performance.index[0]
best_value = region_performance.iloc[0]
result = f"{best_region} is the best-performing region with the highest total order_value of {best_value:.2f}."
```

**Observed output**

```
Total order_value by region:
North    6462.40
South    5874.95
East     4362.40
West     3224.92
```

**Final output**

```
## Insights
- North is the top-performing region, with total order_value of 6,462.40.
- South ranks second at 5,874.95, which is 587.45 below North.
- East generated 4,362.40 in total order_value, placing third.
- West is the lowest-performing region at 3,224.92.
- The gap between the best and worst regions is 3,237.48 (6,462.40 minus 3,224.92).

## Caveats
- Performance here is measured only by total order_value; no other metrics such
  as profit, order count, or growth are included.
- The output does not show the time period or order volumes, so comparisons are
  limited to totals only.

## Summary
Based on total order_value, North is the best-performing region at 6,462.40,
ahead of South (5,874.95), East (4,362.40), and West (3,224.92).
```

---

## 3. Sample trace B — analysis with a chart artifact

Demonstrates the code-execution tool producing a saved chart artifact.

```bash
python src/agent.py --csv tests/data/sales.csv \
  --query "Plot total order_value by region as a bar chart and tell me which region is the top performer." \
  --no-clarify --json-trace
```

**Steps**

```
[observe] profiler : loaded and profiled CSV
[plan]    planner  : next_action=analyze
[act]     codegen  : attempt 1: generated and executed code
[observe] executor : ok  (ARTIFACTS: total_order_value_by_region.png)
[reason]  critic   : sufficient=True, retry=False
[respond] insight  : synthesized 5 insight(s)
```

**Tool call — generated code (excerpt)**

```python
region_totals = df.groupby('region')['order_value'].sum().sort_values(ascending=False)
plt.figure(figsize=(8, 5))
region_totals.plot(kind='bar', color='steelblue', edgecolor='black')
plt.title('Total Order Value by Region'); plt.xlabel('Region'); plt.ylabel('Total Order Value')
plt.tight_layout()
plt.savefig(f"{ARTIFACTS_DIR}/total_order_value_by_region.png")
result = f"{region_totals.index[0]} is the top-performing region with a total order value of {region_totals.iloc[0]:.2f}."
```

The chart is written to `artifacts/total_order_value_by_region.png` and is
rendered inline in the Streamlit UI.

---

## 4. Evaluation results

Run with `python src/evaluate.py --scenarios tests/scenarios.json`. Scoring is
transparent: the fraction of expected keywords present, substring checks, and
correct clarify behaviour; a scenario passes at score ≥ its threshold.

| Scenario | What it checks | Score | Result |
| --- | --- | --- | --- |
| `top_region_by_revenue` | Grouped sum + rank by region | 1.0 | ✅ PASS |
| `avg_order_value_by_segment` | Grouped mean by segment | 1.0 | ✅ PASS |
| `best_selling_category_by_quantity` | Grouped sum of quantity | 1.0 | ✅ PASS |
| `monthly_revenue_trend` | Date-based Jan vs Feb comparison | 1.0 | ✅ PASS |
| `ambiguous_needs_clarification` | Guard behaviour (must ask) | 1.0 | ✅ PASS |

**Aggregate: 5/5 passed (pass_rate = 1.0).** Sample verified answers from the run:

- *top region* → "North has the highest total order_value at 6462.40."
- *avg by segment* → "Corporate customers have the highest average order_value at 1096.14."
- *best-selling category* → "Office Supplies sold the most units overall, with 130 total units."
- *monthly trend* → "January total order_value was 12,199.79, while February totaled 7,724.88."
- *ambiguous* → agent correctly paused and asked clarifying questions (no analysis).

Machine-readable results are written to `eval_results.json` via `--out`.

---

## 5. Design decisions & trade-offs (summary)

- **LangGraph + LangChain** — an explicit, inspectable state machine for the
  agent loop; also provides persistence and streaming for free.
- **Azure AI Foundry `ChatOpenAI`** — reuses a verified-working configuration;
  all values externalized to `.env`.
- **Multi-agent + self-reflection** — a planner delegates to specialists, and a
  critic can trigger up to 3 code attempts; the loop is bounded to guarantee
  termination and cap latency/cost.
- **Pydantic structured output** — every agent hand-off is typed, avoiding
  brittle free-text parsing and giving the planner a reliable routing signal.
- **Simple in-process `exec` sandbox** with an AST/import denylist and a
  wall-clock timeout — chosen for development speed. **Explicitly not a security
  boundary**; swap for subprocess/Docker isolation for untrusted input.
- **SQLite checkpointer** — zero-setup, file-based conversation memory keyed by
  `thread_id`, enabling the clarify → resume flow shown in trace A.

Full rationale and alternatives: [`wikis/design-decisions.md`](../wikis/design-decisions.md).

---

## 6. Reproduce

```bash
pip install -r requirements.txt            # or: uv sync
cp .env.example .env                        # set AZURE_AI_API_KEY

# Trace A (clarify then resume): run the two commands in section 2.
# Trace B (chart):
python src/agent.py --csv tests/data/sales.csv \
  --query "Plot total order_value by region as a bar chart and tell me which region is the top performer." \
  --no-clarify --json-trace

# Evaluation:
python src/evaluate.py --scenarios tests/scenarios.json --out eval_results.json
```
