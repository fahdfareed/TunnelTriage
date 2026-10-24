# Design: TunnelTriage

## Overview

TunnelTriage is a two-tier application. A Python/FastAPI backend owns the data pipeline,
analytics, optimizer, findings state, and memo generation. A React/TypeScript/Vite frontend
renders a single operator page that talks to the backend over a JSON API under `/api`.

The backend keeps all processed data and applied findings in memory (no database). Processed
data is committed to the repo so the demo runs offline. All tunable numbers and assumptions
live in `config.yaml`, loaded into typed config objects and surfaced read-only in the UI.

The authoritative behavior contract is `SPEC.md` at the repo root; this design maps those
sections onto the modules that implement them.

## Architecture

```
┌──────────────────────────── Frontend (Vite dev :5173) ────────────────────────────┐
│ App.tsx orchestrates: Header, BudgetBar, MapView, right-panel tabs                 │
│ api.ts  → fetch wrappers   format.ts → display formatting   types.ts → shared types│
│ Panels: Plan, TunnelDetail, Findings, Memo, Assumptions, DataNotes, Validation     │
│ Charts: CurveChart, StackedBar, DiffBanner                                         │
└───────────────────────────────── HTTP /api/* ─────────────────────────────────────┘
                                      │
┌──────────────────────────── Backend (uvicorn :8000) ──────────────────────────────┐
│ main.py        FastAPI routes + CORS + lifespan load                               │
│ state.py       in-memory STATE: base data + findings + plan cache                  │
│ config.py      loads config.yaml into pydantic models                              │
│ constants.py   §3.5 budget anchors + source URLs                                   │
│                                                                                    │
│ Pipeline:  fetch.py → dictionary.py → process.py   (via scripts/build_data.py)     │
│ Analytics: risk.py → forecast.py → actions.py → optimizer.py → waiting.py          │
│ Intake:    findings.py (apply + parse)                                             │
│ Output:    memo.py (+ llm.py provider wrapper)                                     │
│ Extra:     validation.py (backtest vs MassDOT contract 130548)                     │
│ schemas.py request/response models                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
          │
   data/raw (committed)  →  data/processed (committed)  +  data/element_dictionary.csv
```

### Data flow

1. `scripts/build_data.py` runs `fetch → dictionary → process`, writing `data/raw/*.json`,
   `data/element_dictionary.csv`, and `data/processed/{tunnels,elements,data_notes}.json`.
2. On startup `STATE.load()` reads processed data, the dictionary, and config, then computes
   per-row current risk.
3. `POST /api/plan` builds candidate actions, runs the optimizer at the requested budget,
   computes cost-of-waiting, caches the plan by `plan_id`, and returns it.
4. Findings mutate the in-memory overlay on base data and invalidate the plan cache; the
   frontend re-requests the plan and diffs it.
5. `POST /api/memo` assembles a facts payload from a cached plan and generates the memo.

## Components and Interfaces

### Configuration (`config.py`, `config.yaml`)
Loads `config.yaml` into pydantic models exposing weights, underwater multiplier, size-factor
clip, horizon, forecast years, transition matrices by category, criticality by category,
overrides, overhead keywords, unit costs, cost scale, mobilization, bid-vs-estimate factors,
safety floor, budget slider, and LLM settings. `LLM_PROVIDER` and `LLM_MODEL` env vars override
config. Every key is serialized to `/api/config` for the Assumptions panel.

### Constants (`constants.py`)
Holds the §3.5 budget anchors with labels, the data year, and the source URL list surfaced by
`/api/constants` and the Data Notes panel.

### Fetch (`fetch.py`)
`fetch_all(layer_url, where)` paginates the ArcGIS feature service 1,000 rows at a time,
stopping on `exceededTransferLimit=false`, and asserts the count against `returnCountOnly`.
Falls back to committed raw files on network failure.

### Dictionary (`dictionary.py`)
Builds `element_dictionary.csv`. Attempts SNTI PDF extraction within a 20-minute timebox; on
insufficient coverage, writes a fallback row for every element present in the data. Applies
criticality defaults, config overrides, and the overhead-keyword rule.

### Process (`process.py`)
Normalizes element rows (key, shares) and tunnels (facts, `group_id`), applies the DQ rules
(DQ_SUM_MISMATCH, DQ_ZERO_TOTAL, DQ_SUSPECT_ALL_CS4, DQ_BINARY_PATTERN, DQ_ORPHAN), and
produces `data_notes.json`. `build_groups(tunnels)` derives map groups (one marker per group,
mean lat/lon, segment list).

### Risk (`risk.py`)
Pure functions for likelihood, size factor, exposure, and element risk per Requirement 5.
Produces `_risk_now` per scored row consumed by routes and the optimizer.

### Forecast (`forecast.py`)
Applies the per-category Markov matrix (system elements use the system row) to produce share
vectors for years 0–10. `tunnel_risk_series` produces the do-nothing risk series for a tunnel.

### Actions (`actions.py`)
Generates `FIX_SEVERE` and `FIX_POOR_AND_SEVERE` candidate actions with point cost and low/high
range, mobilization per tunnel, and benefit = risk reduction over the horizon. Exposes the
statewide backlog calibration check.

### Optimizer (`optimizer.py`)
Multiple-choice knapsack with mobilization coupling and a safety-floor forcing constraint.
Primary solver OR-Tools CP-SAT with a short time limit; greedy benefit/cost fallback when
CP-SAT is unavailable or finds nothing. Returns the `Plan` structure including `solver`,
funded/unfunded items, costs, risk metrics, `by_group`, and `forced_unmet`.

### Waiting (`waiting.py`)
Computes cost-now vs cost-in-2-years for the funded set and the extra risk absorbed while
waiting, excluding inflation.

### State (`state.py`)
Singleton `STATE` holding base processed data, dictionary, config, the in-memory findings
overlay, and the plan cache. Methods: `load`, `make_plan`, `get_plan`, `get_curve`,
`plan_risk_now`, `add_finding`, `remove_finding`, `reset_findings`, `n_scored`,
`dictionary_source`. Any finding change invalidates cached plans.

### Findings (`findings.py`)
`new_finding(payload)` builds a finding with id and timestamp. Applying conserves total
quantity, pulls from best states first, never goes negative, and creates missing rows.
`parse_text(text, tunnels, dictionary, cfg)` returns a proposal plus fuzzy tunnel/element
candidates; uses the LLM only to select among candidates, else keyword/fuzzy fallback.

### Memo (`memo.py`, `llm.py`)
`build_facts(plan, waiting, findings, anchors, dictionary_source)` assembles the only data the
memo may use. `generate_memo(facts)` calls the LLM (via `llm.py`), runs the number guard, and
returns the verified LLM memo or the deterministic template with a warning. `llm.py` wraps the
`anthropic`, `bedrock`, and `none` providers; any error returns None.

### Validation (`validation.py`)
Backtests derived unit rates against MassDOT contract 130548 in `data/calibration/`, surfaced
at `/api/validation`. This is an implementation addition beyond the original spec; it supports
the calibration-honesty story.

### Frontend
`App.tsx` holds budget, selected tunnel, active tab, current plan, and findings. `api.ts`
wraps the endpoints below; `format.ts` enforces display rules; `types.ts` mirrors the API
shapes. Components map to the panels in Requirement 12.

## API Surface

All JSON under `/api`, CORS allows `http://localhost:5173` plus any `CORS_ALLOW_ORIGINS`.

| Method & path | Request | Response |
|---|---|---|
| GET `/api/health` | — | status, counts, dictionary source, llm provider |
| GET `/api/tunnels` | — | tunnels with `risk_now` |
| GET `/api/groups` | — | map groups with `risk_now` |
| GET `/api/tunnels/{id}` | — | tunnel, elements, forecast series |
| GET `/api/dictionary` | — | dictionary rows |
| GET `/api/data-notes` | — | DQ notes + calibration |
| GET `/api/config` | — | config for Assumptions panel |
| GET `/api/constants` | — | anchors, labels, sources |
| POST `/api/plan` | `{budget, horizon?}` | Plan + waiting |
| GET `/api/curve` | — | risk-after-repairs per budget step |
| GET `/api/validation` | — | backtest vs contract 130548 |
| GET `/api/findings` | — | findings list |
| POST `/api/findings` | finding | `{finding, affected_row_key}` |
| DELETE `/api/findings/{id}` | — | `{ok}` |
| DELETE `/api/findings` | — | `{ok}` (reset) |
| POST `/api/findings/parse` | `{text}` | proposal + candidates |
| POST `/api/memo` | `{plan_id}` | `{markdown, source, warnings}` |

## Data Models

- **Tunnel**: tunnel_number, name, year_built, year_rehab, adt, adtt, length_ft, under_water,
  lat, lon, last_inspection_date, inspection_interval_months, group_id.
- **ElementRow**: key, tunnel_number, element_number, epn, total, cs[4], shares[4], dq_flags,
  scored, plus joined element_name/category/criticality and `_risk_now`.
- **Finding**: finding_id, tunnel_number, element_number, epn, quantity, condition_state,
  source, note, created_at.
- **Plan / PlanItem**: as defined in SPEC §6.6 (funded, unfunded_top, costs, risk metrics,
  by_group, forced_unmet; item rank, reason_codes, benefit_per_million).

## Error Handling

- Routes guard with `_require_loaded()` and return 503 when processed data is absent.
- Unknown `tunnel_number` or `plan_id` returns 404.
- Fetch failures fall back to committed raw files with a warning.
- Optimizer falls back from CP-SAT to greedy on import error or no solution.
- LLM failures/timeouts return None, triggering the template memo; number-guard failures also
  fall back to the template with a warning.
- Finding application caps quantity at available amount so no state goes negative.

## Testing Strategy

Pytest suite under `backend/tests` mirrors SPEC §12:
- `test_process.py`: pagination stop condition, shares sum to 1, DQ_SUSPECT_ALL_CS4 on the
  single-unit-all-CS4 pattern, group_id strips direction words.
- `test_risk.py`: zero risk when poor/severe shares are zero, risk doubles with criticality,
  underwater multiplier applied.
- `test_forecast.py`: transition rows sum to 1, severe share non-decreasing, shares sum stays 1.
- `test_optimizer.py`: cost ≤ budget, ≤ 1 action per row, monotonic risk vs budget for CP-SAT,
  both solvers run, forced items included when they fit.
- `test_findings.py`: total quantity conserved, no negative states, missing row created, reset
  restores the base plan.
- `test_memo.py`: number guard rejects fabricated numbers and accepts facts numbers, template
  contains all five headings.
- `test_api.py`: route-level checks across the endpoints.

Manual end-to-end acceptance: both servers start, map shows ≥ 6 groups, slider at $74M returns
a plan in < 2 s, applying a demo finding changes the plan and shows a diff, and the memo renders
with `LLM_PROVIDER=none`.
