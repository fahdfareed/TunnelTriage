# TunnelTriage: Build Specification

**Hackathon:** Hackachusetts 2026, Robotics track, challenge "Safer inspection of critical infrastructure: *The drone already flew. The budget still has to choose.*"
**Team / time:** 1–2 people, ~5 build hours. **Stack:** Python 3.11 + FastAPI (backend), React + TypeScript + Vite (frontend).
**Spec date:** 2026-10-24. Every external fact in this document has a source in §17.

> **Instructions to the build agent.** Read this whole file before writing code. Build in the order of §13. Each phase ends with acceptance checks; do not start the next phase until they pass. When this spec says **ASSUMPTION**, implement it exactly as written and make it editable in `config.yaml`. Never invent tunnel facts, element names or dollar figures that are not in the data, the config or §3.5/§17. If something is ambiguous, choose the simplest option that keeps the demo (§14) working and leave a `# DECISION:` comment.

---

## 1. Product in one paragraph

TunnelTriage decides **which tunnel repairs to fund first** with a fixed budget. It loads the federal condition data for every Massachusetts highway tunnel, forecasts how fast each part will get worse, and picks the set of repairs that removes the most safety risk for the money. It then writes a plain-English justification. When a drone or inspector reports a new defect, the plan updates live. It does **not** fly drones or detect cracks in images; it consumes those findings. Another team (InspectPath) does that part.

**One-line pitch:** "The drone already flew. TunnelTriage decides what to fix first, and shows what waiting will cost."

## 2. Goals and non-goals

**Goals (must ship):**
1. Real Massachusetts tunnel inventory and element condition data, cached locally.
2. A transparent risk score per element and per tunnel.
3. A 10-year do-nothing deterioration forecast.
4. A budget-constrained repair plan (optimizer) with cost ranges.
5. A "cost of waiting" number (repair now vs. in 2 years).
6. Findings intake: structured form **and** free-text (LLM-parsed), then a live re-plan with a before/after diff.
7. An AI-written board memo grounded only in computed facts, with a template fallback.
8. A single-page React UI: map, budget slider, plan list, tunnel detail, findings, memo, assumptions/data notes.

**Non-goals (do not build):** image or video analysis, drone route planning, user accounts, a database server, deployment pipelines, editing of the raw federal data, mobile layout beyond "doesn't break".

## 3. Data sources (verified live on 2026-10-24)

### 3.1 National Tunnel Inventory, inventory layer
- Service: `https://services.arcgis.com/xOi1kZaI0eWDREZv/ArcGIS/rest/services/NTAD_National_Tunnel_Inventory/FeatureServer/0`
- Publisher: FHWA via USDOT/BTS NTAD, published 2025-08-26. Point geometry. Max 1,000 records per request. JSON.
- Massachusetts filter: `state_code_i3 = '25'` (FIPS code, string). FHWA lists **48** Massachusetts tunnels for 2025.
- Fields used (exact names):

| Field | Meaning | Use |
|---|---|---|
| `tunnel_number_i1` | Unique tunnel ID, e.g. `B16T27TWWDOTTW3` | Primary key |
| `tunnel_name_i2` | e.g. `TED WILLIAMS TUNNEL WESTBOUND` | Display; grouping (§5.4) |
| `year` | Data year (2025) | Display |
| `year_built_a1`, `year_rehabilitated_a2` | Years (0 = none) | Display, age |
| `adt_a4`, `adtt_a5` | Average daily traffic, daily truck traffic | Exposure (§6.3) |
| `tunnel_length_g1` | Length (feet, per SNTI) | Display |
| `owner_c1`, `toll_c4` | Coded integers | Display raw codes only |
| `under_navigable_waterway_n1` | 1 = under navigable water | Exposure multiplier |
| `actual_routine_inspection_date_` | Epoch milliseconds | Display "last inspected" |
| `routine_inspection_interval_d3` | Months | Display |
| `portal_latitude_i13`, `portal_longitude_i14` | Portal location | Map |

Note the truncated field names (`actual_routine_inspection_date_` has a trailing underscore). Use exact names.

### 3.2 National Tunnel Inventory, element data table
- Service: `https://services.arcgis.com/xOi1kZaI0eWDREZv/ArcGIS/rest/services/NTAD_National_Tunnel_Inventory_Element_Data/FeatureServer/1`
- Published 2025-08-26. Table (no geometry). Max 1,000 records per request. JSON.
- Massachusetts filter: `state = '25'`. **1,120 rows** for Massachusetts (verified with `returnCountOnly`), so pagination is required.
- Fields: `OBJECTID`, `state`, `tunnel_number`, `element_number` (int), `epn` (int or null; parent element number for protective-system rows), `total_quantity`, `condition_state_1` … `condition_state_4` (ints).
- Condition states: 1 = good, 2 = fair, 3 = poor, 4 = severe (standard element-inspection convention; confirm wording in the data dictionary). `total_quantity` is split across the four states.
- Data dictionary: https://doi.org/10.21949/1529051

### 3.3 Element names: not in the feed
The feed has element **numbers only**. Names, categories and units live in FHWA's *Specifications for the National Tunnel Inventory* (SNTI, 2015): `https://www.fhwa.dot.gov/bridge/inspection/tunnel/snti/hif15006.pdf`. The SNTI groups elements into: Structural, Joints & Gaskets, Civil, Mechanical, Electrical, Fire/Life Safety/Security, Signs, Protective Systems. See §5.2 for how to build the lookup, with a hard 20-minute timebox and a fallback.

Element numbers observed in Massachusetts data (non-exhaustive): 10001, 10010, 10012, 10031, 10041, 10059, 10061, 10070, 10080, 10099, 10101, 10120, 10130, 10131, 10132, 10139, 10140, 10151, 10158, 10161, 10169, 10170, 10200, 10201, 10300, 10301, 10400, 10550, 10600, 10601, 10620, 10621, 10650, 10700, 10750, 10800, 10850, 10870, 10890, 10911, 10950, 10951, 10952.

### 3.4 Optional: history (only if Phase 7 time remains)
FHWA publishes yearly NTI downloads for 2018–2026 in Excel and XML at `https://www.fhwa.dot.gov/bridge/inspection/tunnel/inventory/download.cfm`. It is **not verified** whether these include element data. Use them only to calibrate deterioration rates (§6.4). Do not block on this.

### 3.5 Budget anchors (hard-coded constants with sources, §17)

| Constant key | Value | Meaning |
|---|---|---|
| `cip_fy27_31_tunnels_total` | 370,000,000 | Tunnels program, FY27–31 draft capital plan (read from a chart; label "approx.") |
| `cip_fy27_31_tunnels_per_year` | 74,000,000 | 370M ÷ 5. Default slider value |
| `contract_tunnel_preservation_2025_program` | 64,727,001 | "Tunnel Preservation within MHS Tunnels" total program budget (bid $52,182,001) |
| `contract_cana_2026_program` | 128,482,140 | CANA Tunnel & Vent Building Rehab total budget (bid $103,174,700) |
| `contract_ups_2025_program` | 21,598,325 | Central Artery UPS replacement total budget |
| `contract_four_tunnels_2022` | 15,300,000 | 2022 four-tunnel repair contract |
| `mhs_10yr_need_2024` | 1,950,000,000 | 10-year need, whole Metropolitan Highway System, all asset types |
| `bid_vs_estimate_low` | -0.32 | Lowest observed bid vs. MassDOT estimate (UPS contract) |
| `bid_vs_estimate_high` | 0.35 | Highest observed (CANA contract) |

## 4. Repository layout

```
tunneltriage/
  SPEC.md
  README.md                      # how to run, 10 lines max
  config.yaml                    # every tunable number and assumption (§7)
  data/
    raw/                         # untouched API responses (committed)
      inventory_ma.json
      elements_ma.json
    element_dictionary.csv       # §5.2 (committed)
    processed/                   # generated by pipeline (committed for demo safety)
      tunnels.json
      elements.json
      data_notes.json
    demo_findings.json           # scripted demo findings (§14)
  backend/
    pyproject.toml / requirements.txt
    app/
      main.py                    # FastAPI app, CORS, routes
      config.py                  # loads config.yaml into pydantic models
      constants.py               # §3.5 constants + source URLs
      fetch.py                   # §5.1 pagination + caching
      dictionary.py              # §5.2
      process.py                 # §5.3–5.4 normalization, DQ flags, grouping
      risk.py                    # §6.1–6.3
      forecast.py                # §6.4
      actions.py                 # §6.5 candidate repairs + costs
      optimizer.py               # §6.6 OR-Tools + greedy fallback
      waiting.py                 # §6.7 cost of waiting
      findings.py                # §8 apply/parse findings
      memo.py                    # §9 LLM memo + template + number check
      llm.py                     # provider wrapper (anthropic | bedrock | none)
      state.py                   # in-memory state: base data + applied findings
      schemas.py                 # pydantic request/response models (§10)
    scripts/
      build_data.py              # runs fetch → dictionary → process; idempotent
    tests/
      test_process.py test_risk.py test_forecast.py test_optimizer.py
      test_findings.py test_memo.py
  frontend/
    package.json vite.config.ts index.html
    src/
      main.tsx App.tsx api.ts types.ts format.ts
      components/
        Header.tsx BudgetBar.tsx MapView.tsx PlanPanel.tsx
        TunnelDetail.tsx FindingsPanel.tsx MemoPanel.tsx
        AssumptionsPanel.tsx DataNotesPanel.tsx DiffBanner.tsx
```

Libraries. Backend: `fastapi`, `uvicorn`, `pydantic>=2`, `pyyaml`, `requests`, `numpy`, `pandas`, `ortools`, `rapidfuzz`, `pytest`, `httpx`; optional `anthropic` or `boto3`; `pdfplumber` only for §5.2. Frontend: `react`, `react-dom`, `leaflet` + `react-leaflet`, `recharts`, no CSS framework (plain CSS modules) or Tailwind if the team prefers.

## 5. Data pipeline (`scripts/build_data.py`)

### 5.1 Fetch with pagination and caching
```
def fetch_all(layer_url, where):
    rows, offset = [], 0
    while True:
        params = {"where": where, "outFields": "*", "returnGeometry": "false",
                  "orderByFields": "OBJECTID", "resultOffset": offset,
                  "resultRecordCount": 1000, "f": "json"}
        r = requests.get(layer_url + "/query", params=params, timeout=30)
        r.raise_for_status(); j = r.json()
        if "error" in j: raise RuntimeError(j["error"])
        batch = [f["attributes"] for f in j.get("features", [])]
        rows += batch; offset += len(batch)
        if not batch or not j.get("exceededTransferLimit"): break
    return rows
```
- Inventory: `where = "state_code_i3='25'"`. Elements: `where = "state='25'"`.
- Write raw arrays to `data/raw/*.json`. If the network fails and raw files exist, use them and log a warning. **Commit the raw files** so the demo never depends on hackathon Wi-Fi.
- Before fetching, call `returnCountOnly=true` and assert the final row count equals it.

**Acceptance:** `elements_ma.json` has the same count as `returnCountOnly` (1,120 at time of writing). `inventory_ma.json` has ≥ 40 rows (FHWA says 48).

### 5.2 Element dictionary (`data/element_dictionary.csv`), timebox 20 minutes
Columns: `element_number,name,category,unit,criticality,is_system_element,source`

1. Try: download `hif15006.pdf`, extract text with `pdfplumber`, and regex lines matching `^\s*(1\d{4})\s+(.+?)\s+(SF|LF|EA|sq\.?\s*ft|ft|each)?\s*$` within the element tables. Map each table heading to `category`. Set `source=SNTI`.
2. If step 1 doesn't yield ≥ 30 of the observed element numbers in §3.3 within 20 minutes, **stop** and write the fallback for every element number present in the data:
   - `name = f"Element {n}"`, `category = "Unknown"`, `source = "fallback"`.
   - `unit`: `"each"` if the max `total_quantity` for that element across Massachusetts ≤ 50, else `"area/length"`.
   - `is_system_element = (unit == "each")`.
   - `criticality = 3`.
3. A human can then edit names and criticality by hand. The UI must always show the element number next to the name, so a wrong name never hides the real ID.

**Criticality (1–5), ASSUMPTION, editable.** Meaning: consequence to the public if this element fails. Defaults by SNTI category once names exist: Structural 4; Civil 2; Joints & Gaskets 3; Mechanical 4; Electrical 4; Fire/Life Safety/Security 5; Signs 2; Protective Systems 2; Unknown 3. Override per element in `config.yaml → criticality_overrides`. Any element whose name contains "ceiling" or "hanger" gets 5, because overhead elements fall onto traffic.

### 5.3 Normalize elements and data-quality flags (`process.py`)
For each raw element row build:
```
ElementRow {
  key: f"{tunnel_number}|{element_number}|{epn or 0}"
  tunnel_number, element_number, epn,
  total, cs: [cs1, cs2, cs3, cs4],
  shares: [cs_k / total] (0s if total == 0),
  dq_flags: list[str]
}
```
Data-quality rules (record in `data_notes.json` with counts and examples):
- **DQ_SUM_MISMATCH:** `sum(cs) != total`. Keep the row; rescale shares by `sum(cs)`.
- **DQ_ZERO_TOTAL:** `total == 0`. Exclude from scoring.
- **DQ_SUSPECT_ALL_CS4 (critical):** for an element number, compute across Massachusetts rows the fraction where `total <= 2 and cs4 == total`. If that fraction ≥ 0.8 and the element appears in ≥ 5 tunnels, flag **every** row of that element and **exclude it from risk, actions and optimizer by default**.
  - Why: in the 2025 data, single-unit elements such as 10750, 10200, 10600, 10620, 10700 and 10800 are recorded 100% in condition state 4 in nearly every Massachusetts tunnel. For example, 10750 appears as `total=1, cs4=1` in most tunnels. That pattern is almost certainly a reporting convention, not 30 tunnels in severe condition. Taken literally, the optimizer would rank these first.
  - `config.yaml → include_suspect_elements: false` toggles it. The Data Notes panel must list the excluded element numbers and the count of affected rows, in plain words.
- **DQ_BINARY_PATTERN (informational):** `total > 1000 and cs2 == 0 and cs3 == 0 and cs4 > 0`, which is common for 10950–10952 (possibly protective systems). Keep in scoring; show a note.
- **DQ_ORPHAN:** element row's `tunnel_number` not in the inventory. Keep it, with tunnel name "Unknown tunnel".

### 5.4 Normalize tunnels and group for the map
```
Tunnel {
  tunnel_number, name, year_built, year_rehab, adt, adtt, length_ft,
  under_water: bool, lat, lon, last_inspection_date (ISO, from epoch ms or null),
  inspection_interval_months, group_id
}
```
- `group_id` = tunnel name with direction words and trailing segment tokens removed. Uppercase, strip `NORTHBOUND|SOUTHBOUND|EASTBOUND|WESTBOUND|EB|WB|NB|SB|- 93NB|- 93SB`, collapse spaces. Expected groups include `I-90 CONNECTOR TUNNEL`, `THOMAS P. TIP ONEILL JR TUNNEL`, `TED WILLIAMS TUNNEL`, `CANA TUNNEL`. The map shows **one marker per group** at the mean lat/lon of its segments. Clicking a marker lists its segments.
- If `name` is empty, use `tunnel_number` as the name and the group.

**Acceptance:** `tunnels.json` and `elements.json` are written. `data_notes.json` lists DQ_SUSPECT_ALL_CS4 and includes element 10750 (if the 2025 pattern still holds). There are ≥ 6 map groups.

## 6. Analytics model

All parameters live in `config.yaml` (§7). Every formula below must be implemented as a pure function with a unit test.

### 6.1 Element likelihood (poor-condition share)
```
likelihood(row) = w3 * share3 + w4 * share4        # defaults w3 = 0.3, w4 = 1.0
```

### 6.2 Size factor
Large elements with the same share matter more than small ones, but this must not swamp everything.
```
median_total[element_number] = median of totals for that element across MA rows
size_factor = clip(sqrt(total / median_total), 0.5, 2.0)
```

### 6.3 Exposure and element risk
```
exposure(tunnel) = 0.5 + 0.5 * (adt / max_adt_in_MA)          # 0.5..1.0
if under_water: exposure *= underwater_multiplier             # default 1.2
risk(row) = 100 * criticality(element) * exposure(tunnel) * likelihood(row) * size_factor(row)
tunnel_risk = sum(risk of its scored rows); group_risk = sum over segments
statewide_risk = sum over all scored rows
```
Risk is a **relative index** ("risk points"), not a probability. The UI must say so in a tooltip.

### 6.4 Deterioration forecast (Markov, ASSUMPTION)
Yearly transition matrix per category (defaults; system elements use the `system` row):
```
P = [[1-p12, p12,     0,      0  ],
     [0,     1-p23,   p23,    0  ],
     [0,     0,       1-p34,  p34],
     [0,     0,       0,      1  ]]
defaults: structural/civil/joints/protective/unknown: p12=0.05 p23=0.04 p34=0.03
          mechanical/electrical/fire_life_safety/signs/system: p12=0.08 p23=0.06 p34=0.05
shares(t+1) = shares(t) @ P
```
- Rows with `is_system_element = true` always use the `system` rates, whatever their category.
- `forecast(row, years=10)` returns 11 share vectors (t = 0..10). Rows of P must sum to 1 (test).
- Risk at year t uses shares(t) in §6.1–6.3.
- Label these as **default deterioration rates (not calibrated)** in the Assumptions panel. If §3.4 history is loaded in Phase 7, estimate p's by category from year-over-year share changes and show "calibrated from 2018–2026 data".

### 6.5 Candidate repair actions and costs (ASSUMPTION)
For each scored row, generate up to two **mutually exclusive** actions:

| Action | Effect at t = 0 | Quantity costed |
|---|---|---|
| `FIX_SEVERE` | move all CS4 quantity to CS1 | `cs4` |
| `FIX_POOR_AND_SEVERE` | move CS3 + CS4 quantity to CS1 | `cs3 + cs4` |

Skip an action if its quantity is 0. Skip `FIX_POOR_AND_SEVERE` if `cs3 == 0`, since it would duplicate `FIX_SEVERE`.

Unit cost, all **PLACEHOLDER ASSUMPTIONS** in `config.yaml`:
```
unit_cost[unit][state] (USD per unit moved)
  area/length: cs3 = 120,   cs4 = 300
  each:        cs3 = 15000, cs4 = 40000
cost_point = cost_scale * sum(qty_in_state * unit_cost[unit][state])
mobilization: + fixed_mobilization_per_tunnel (default 250,000) once per tunnel that has ≥1 funded action
cost_low  = cost_point * (1 + bid_vs_estimate_low)     # ×0.68
cost_high = cost_point * (1 + bid_vs_estimate_high)    # ×1.35
```
- `cost_scale` default 1.0. **Calibration check** (print on startup, show in Assumptions panel): `backlog_cs4_cost` = cost to apply FIX_SEVERE to every scored row statewide, and `backlog_cs34_cost` the same for FIX_POOR_AND_SEVERE. Show them next to the 5-year tunnels program ($370M) so judges can see the scale. The team adjusts `cost_scale` by hand if the backlog is wildly off. Never claim these are real MassDOT costs.
- Benefit over horizon H (default 5 years):
```
benefit(action) = sum_{t=0..H} [ risk_do_nothing(row, t) - risk_with_action(row, t) ]
```
where `risk_with_action` starts from the post-action shares and then deteriorates with the same P.

### 6.6 Optimizer (`optimizer.py`)
Multiple-choice knapsack with mobilization:
```
variables: x[a] ∈ {0,1} for each action a; y[tunnel] ∈ {0,1}
maximize   Σ benefit[a]·x[a]
subject to Σ_{a in row} x[a] ≤ 1                       (one action per element row)
           x[a] ≤ y[tunnel(a)]                          (mobilization)
           Σ cost_point[a]·x[a] + Σ mob·y[t] ≤ budget   (costs in $1,000 integers)
           x[a] = 1 for every action in `forced` (§8.3 safety floor), if feasible
```
- Solver: OR-Tools CP-SAT, `max_time_in_seconds = 3`, 8 workers. If `ortools` import fails or no solution, use the **greedy fallback**: sort actions by `benefit/cost_point` descending, add if within budget and row not taken, add mobilization when a tunnel is first used. Return `solver: "cp-sat" | "greedy"`.
- Output `Plan`:
```
Plan {
  plan_id, budget, horizon, solver,
  funded: [PlanItem], unfunded_top: [PlanItem] (top 15 by benefit not funded),
  total_cost_point, total_cost_low, total_cost_high,
  risk_now, risk_h_do_nothing, risk_h_with_plan, risk_reduction_pct,
  by_group: [{group_id, risk_now, risk_h_with_plan, funded_cost}],
  forced_unmet: [action_id]   # safety-floor items that didn't fit the budget
}
PlanItem { action_id, rank, tunnel_number, tunnel_name, group_id, element_number,
  element_name, action, qty, cost_point, cost_low, cost_high, benefit,
  benefit_per_million, risk_now_row, reason_codes: [str] }
```
- `rank` = order by `benefit_per_million` among funded items.
- `reason_codes` are short machine facts used by the memo, e.g. `HIGH_CS4_SHARE`, `HIGH_TRAFFIC`, `UNDER_WATER`, `OVERHEAD_ELEMENT`, `NEW_FINDING`, `SAFETY_FLOOR`.
- **Monotonicity test (CP-SAT only):** for budgets [0, 10M, 25M, 50M, 74M, 150M], `risk_h_with_plan` is non-increasing. Greedy is not guaranteed monotonic, so when the greedy fallback is used, compute the plan for the requested budget and also re-use the best plan found for any smaller cached budget if it has higher total benefit (keeps the slider from "getting worse" on screen).
- Performance: < 2 s for Massachusetts (~1,000 actions).

### 6.7 Cost of waiting (`waiting.py`)
For the funded set at the current budget:
```
cost_now = Σ cost_point (funded) + mobilization
forecast each funded row 2 years with no action; recompute the same action's
quantity from the year-2 shares × total (CS4 qty, or CS3+CS4 qty)
cost_in_2y = cost of those larger quantities (same unit costs)
extra_risk_2y = Σ_{t=0..1} risk_do_nothing - risk_with_action   (risk absorbed while waiting)
```
Return `{cost_now, cost_in_2y, cost_increase_pct, extra_risk_2y}`. The UI shows: "Waiting 2 years: +X% repair cost and Y risk-point-years of exposure." Do not add inflation (keep it explainable). Add a note "excludes construction inflation".

## 7. `config.yaml` (create exactly with these keys)

```yaml
state_fips: "25"
include_suspect_elements: false
weights: { w3: 0.3, w4: 1.0 }
underwater_multiplier: 1.2
size_factor_clip: [0.5, 2.0]
horizon_years: 5
forecast_years: 10
transition:
  default:  { p12: 0.05, p23: 0.04, p34: 0.03 }
  system:   { p12: 0.08, p23: 0.06, p34: 0.05 }
category_transition_group:
  Structural: default
  Civil: default
  Joints & Gaskets: default
  Protective Systems: default
  Unknown: default
  Mechanical: system
  Electrical: system
  Fire/Life Safety/Security: system
  Signs: system
criticality_by_category:
  Structural: 4
  Civil: 2
  Joints & Gaskets: 3
  Mechanical: 4
  Electrical: 4
  Fire/Life Safety/Security: 5
  Signs: 2
  Protective Systems: 2
  Unknown: 3
criticality_overrides: {}        # e.g. { 10140: 5 } after names are known
overhead_keywords: [ceiling, hanger]
unit_cost:
  area/length: { cs3: 120, cs4: 300 }
  each:        { cs3: 15000, cs4: 40000 }
cost_scale: 1.0
fixed_mobilization_per_tunnel: 250000
bid_vs_estimate: { low: -0.32, high: 0.35 }
safety_floor:
  enabled: true
  min_criticality: 5
  min_cs4_share: 0.10
budget_slider: { min: 0, max: 150000000, step: 1000000, default: 74000000 }
llm:
  provider: none            # anthropic | bedrock | none ; env LLM_PROVIDER overrides
  model: claude-sonnet-5-5  # env LLM_MODEL overrides
  max_tokens: 900
  timeout_s: 20
```

Every config key must be shown read-only in the Assumptions panel, grouped and labelled in plain words, with the word **Assumption** on unit costs, transition rates and criticality.

## 8. Findings intake ("the drone already flew")

### 8.1 Structured finding
```
Finding { finding_id, tunnel_number, element_number, epn (default 0),
  quantity (int > 0), condition_state (3 or 4), source ("drone"|"inspector"|"simulated"),
  note (str ≤ 280), created_at }
```
Applying a finding to row R (create R with `total = quantity` if it doesn't exist; flag `NEW_FROM_FINDING`):
- Move `quantity` into the target state, taking it from the best states first (CS1, then CS2, then CS3 if the target is 4). Never let any state go negative; cap `quantity` at the available amount. **Total quantity is conserved** (test).
- Findings are stored in memory (`state.py`), applied on top of the base data, and listed in the UI with a remove button. `DELETE /api/findings` resets.
- Every finding adds reason code `NEW_FINDING` to affected plan items.

### 8.2 Free-text finding (LLM)
`POST /api/findings/parse {text}` returns **a proposed Finding plus candidates; it never applies it automatically.**
1. Candidate tunnels: fuzzy-match the text against tunnel names and group IDs with `rapidfuzz` (top 3). Candidate elements: fuzzy-match against dictionary names (top 3); if the dictionary is the fallback, match on "Element NNNNN" or any 5-digit number in the text.
2. If an LLM is configured, send the text plus the candidate lists and ask for JSON only: `{tunnel_number, element_number, quantity, condition_state, note}` chosen **from the candidates**. Validate with pydantic; reject values not in the candidates.
3. If no LLM or validation fails: return the top fuzzy matches; quantity = first number in the text; state = 4 if the text contains any of [severe, failed, falling, loose, exposed rebar, spall], else 3.
4. The UI shows the proposal in an editable form; the user clicks **Apply**.

### 8.3 Safety floor
If `safety_floor.enabled`, any row with `criticality ≥ min_criticality` and `share4 ≥ min_cs4_share` (after findings) has its `FIX_SEVERE` action **forced** in the optimizer. If forced items exceed the budget, fund as many as fit by benefit, list the rest in `forced_unmet`, and the UI shows a red banner: "Budget does not cover N safety-critical repairs."

### 8.4 Re-plan diff
After any finding change, the frontend re-requests the plan at the same budget and shows a `DiffBanner`: items that **entered** the funded list, items that **left**, and items whose rank moved by ≥ 3. Use `action_id` for matching.

## 9. Board memo (`memo.py`)

`POST /api/memo {plan_id}` returns `{markdown, source: "llm"|"template", warnings: []}`.

**Facts payload** (the only data the memo may use): budget; solver; total cost point/low/high; risk now; risk in H years do nothing; with plan; reduction %; cost-of-waiting result; top 8 funded items (tunnel name, element number + name, action, qty, cost range, reason codes); top 5 unfunded by benefit; forced_unmet; findings applied; assumption flags (dictionary source, costs are placeholders, deterioration not calibrated); the §3.5 anchors.

**LLM prompt (system):**
> You write a one-page memo for a state DOT tunnel engineer to take to a capital programming committee. Use ONLY numbers and names present in the FACTS JSON. Do not add any number that is not in FACTS. Say clearly that unit costs and deterioration rates are planning assumptions. Structure: 1) Recommendation (2 sentences). 2) What this budget funds (bullets). 3) What it leaves unfunded and the risk of waiting. 4) Safety-critical items. 5) Assumptions and data notes. Under 350 words. Plain language.

**Number guard:** extract every number from the LLM output (regex `\d[\d,]*\.?\d*`; normalize commas, `$`, `%`, `M`); each must match a number in the facts payload after the same normalization, allowing rounding to 1 decimal and $X.YM formatting of facts. Years 2018–2035 and list numbering 1–10 are allowed. If any number fails, return the **template memo** with `warnings: ["LLM output contained unverified numbers; template used"]`.

**Template memo:** deterministic f-string with the same five sections.

`llm.py`: `complete(system, user) -> str | None`. Providers: `anthropic` (env `ANTHROPIC_API_KEY`) or `bedrock` (AWS credentials). On any error or timeout, return None. Provider `none` always returns None. The app must be fully demoable with `none`.

## 10. API (FastAPI)

All JSON. Prefix `/api`. CORS allow `http://localhost:5173`.

| Method & path | Request | Response |
|---|---|---|
| GET `/health` | — | `{ok, data_year, n_tunnels, n_rows, n_scored_rows, dictionary_source, llm_provider}` |
| GET `/tunnels` | — | `[Tunnel & {risk_now, group_id}]` |
| GET `/groups` | — | `[{group_id, name, lat, lon, segments: [tunnel_number], risk_now, adt_max}]` |
| GET `/tunnels/{tunnel_number}` | — | `{tunnel, elements: [ElementRow & {element_name, category, criticality, risk_now, dq_flags}], forecast: [{year, risk}]}` |
| GET `/dictionary` | — | element dictionary rows |
| GET `/data-notes` | — | `data_notes.json` + calibration check (§6.5) |
| GET `/config` | — | config with labels, for the Assumptions panel |
| GET `/constants` | — | §3.5 constants with source URLs |
| POST `/plan` | `{budget:int, horizon?:int}` | `Plan` + `waiting` (§6.7) |
| GET `/findings` | — | `[Finding]` |
| POST `/findings` | `Finding` minus id/created_at | `{finding, affected_row_key}` |
| DELETE `/findings/{id}` | — | `{ok}` |
| DELETE `/findings` | — | `{ok}` (reset) |
| POST `/findings/parse` | `{text}` | `{proposal: Finding-like, tunnel_candidates, element_candidates, used_llm: bool}` |
| POST `/memo` | `{plan_id}` | `{markdown, source, warnings}` |

Plans are cached in memory by `plan_id` (uuid4). Any finding change invalidates the cache.

## 11. Frontend (single page)

### 11.1 Layout (desktop first, ≥ 1280 px)
```
┌──────────────────────────────────────────────────────────────────────┐
│ Header: TunnelTriage · "The drone already flew. The budget chooses." │
│ Stat tiles: Risk now | Risk in 5 yrs (do nothing) | With this plan   │
│             | Plan cost (range) | Waiting 2 yrs: +X% cost            │
├──────────────────────────────────────────────────────────────────────┤
│ BudgetBar: slider $0–$150M, value label, tick marks:                 │
│   $15.3M (2022 four-tunnel contract) · $64.7M (2025 Tunnel           │
│   Preservation) · $74M (≈ yearly tunnels program) · $128.5M (CANA)   │
├───────────────────────────────┬──────────────────────────────────────┤
│ MapView (Leaflet, OSM tiles)  │ Right panel tabs:                    │
│  one circle per group,        │  [Plan] [Tunnel] [Findings] [Memo]   │
│  radius ∝ sqrt(ADT),          │  [Assumptions] [Data notes]          │
│  colour = risk with plan      │                                      │
│  (sequential, 5 bins)         │                                      │
└───────────────────────────────┴──────────────────────────────────────┘
```
- Map centred on Boston (42.355, −71.050), zoom 14; include a "Fit all" button for tunnels outside Boston.
- Slider changes are debounced 250 ms and then call `POST /plan`. Show a small spinner; keep the previous plan visible until the new one arrives.
- Number formatting (`format.ts`): `$64.7M`, `$850K`, risk points with no decimals, percentages with 0 decimals.

### 11.2 Panels
- **Plan:** table of funded items: rank, tunnel, element (number + name), action, qty, cost range, risk removed, reason chips. Clicking a row opens Tunnel detail. Below it, "Not funded (top 15)". The red banner for `forced_unmet`.
- **Tunnel:** header facts (name, year built, ADT, length, last inspected, under water). Element table with a 100% stacked bar per row (CS1–CS4, green→red, colour-blind-safe), DQ flag icons with tooltips, risk now. Line chart of tunnel risk, years 0–10, do nothing vs. with plan.
- **Findings:** (a) free-text box + "Parse" → editable proposal → Apply; (b) structured form with tunnel and element dropdowns; (c) list of applied findings with remove; (d) "Load demo findings" button that applies `demo_findings.json` one by one with a 1.5 s pause (for stage use). Show `DiffBanner` after each change.
- **Memo:** "Generate memo" button; render markdown; badge "AI-written, numbers verified" or "Template". Copy-to-clipboard.
- **Assumptions:** everything from `/config` and the calibration check, in plain words.
- **Data notes:** DQ counts, excluded suspect elements with an explanation, dictionary source, data publication date, source links.

### 11.3 Visual rules
- Condition colours: CS1 `#2e7d32`, CS2 `#9ccc65`, CS3 `#ffa726`, CS4 `#c62828`. Always pair colour with a text label or tooltip.
- Never display a risk number without its unit "risk points". Never show a cost without "est." or a range.

## 12. Tests and acceptance (pytest; `pytest -q` must pass before the demo)

1. `test_process.py`: pagination stops on `exceededTransferLimit=false`; shares sum to 1 (±1e-9) when the total > 0; 10750 is flagged DQ_SUSPECT_ALL_CS4 on a fixture built from §3.2's pattern; group_id strips directions (`"TED WILLIAMS TUNNEL WESTBOUND"` and `"... EASTBOUND"` → same group).
2. `test_risk.py`: risk is 0 when share3 = share4 = 0; doubles when criticality doubles; the underwater multiplier is applied.
3. `test_forecast.py`: P rows sum to 1; share4 is non-decreasing over time; the sum of shares stays 1.
4. `test_optimizer.py`: cost ≤ budget; ≤ 1 action per row; monotonic risk vs. budget (§6.6); greedy and CP-SAT both run; forced items are included when they fit.
5. `test_findings.py`: total quantity conserved; no negative states; a finding on a missing row creates it; reset restores the base plan exactly.
6. `test_memo.py`: the number guard rejects a fabricated number ("$999M") and accepts numbers from the facts; the template contains all five headings.

**End-to-end acceptance (manual, 5 minutes):** backend starts with `uvicorn app.main:app --reload`, frontend with `npm run dev`; map shows ≥ 6 groups; slider at $74M returns a plan in < 2 s; applying a demo finding changes the plan and shows a diff; the memo renders with `LLM_PROVIDER=none`.

## 13. Build order with timeboxes (5 hours)

| Phase | Time | Deliverable | Done when |
|---|---|---|---|
| 0 | 0:00–0:15 | Repo skeleton, config.yaml, constants.py, requirements, Vite app boots | Both servers start |
| 1 | 0:15–0:45 | fetch.py + build_data.py; raw JSON cached and committed | Counts match (§5.1) |
| 2 | 0:45–1:05 | Dictionary: **20-minute hard timebox**, then fallback (§5.2) | CSV covers every element in data |
| 3 | 1:05–1:35 | process.py + DQ flags + grouping; `/health`, `/groups`, `/tunnels` | Tests 1 pass |
| 4 | 1:35–2:30 | risk, forecast, actions, optimizer, waiting; `/plan` | Tests 2–4 pass; plan < 2 s |
| 5 | 2:30–3:30 | Frontend: header tiles, BudgetBar, MapView, Plan panel, Tunnel panel | Slider drives map + plan |
| 6 | 3:30–4:05 | Findings (structured + parse + demo findings), DiffBanner, safety floor | Test 5 passes; diff visible |
| 7 | 4:05–4:30 | Memo (template first, then LLM + number guard); Assumptions + Data notes panels | Test 6 passes |
| 8 | 4:30–5:00 | **Feature freeze.** Seed demo, rehearse §14 twice, record a 2-min backup video, README | Demo runs offline |

**Two-person split:** Person A owns `backend/` (Phases 1–4, 6 backend, 7 backend). Person B builds the frontend against a hard-coded mock of `/plan` and `/groups` (write `frontend/src/mock.ts` from the §6.6 and §10 shapes) from 0:15, then switches to real endpoints at ~2:30.

**Cut list, in this order, if behind schedule:** (1) LLM parse → structured form only; (2) LLM memo → template only; (3) forecast chart on the Tunnel panel; (4) cost of waiting tile; (5) CP-SAT → greedy only. **Never cut:** real data, DQ suspect handling, budget slider + plan, one finding → re-plan diff.

## 14. Demo script (3 minutes) and demo data

`data/demo_findings.json`, three **simulated** findings, labelled `source: "simulated"`. Choose real `tunnel_number` and `element_number` values present in the processed data:
1. Ted Williams segment (`B16T30TWEDOTTE1`), element 10132, quantity 20, state 4, note "Simulated drone finding: section loss observed on overhead element."
2. Sumner (`B16T37SUMDOTV10`), element 10061, quantity 1500, state 4, note "Simulated inspector finding: active leak with spalling."
3. Callahan (`B16T36CALDOTV12`), element 10070, quantity 3000, state 3, note "Simulated drone finding: delamination on liner."

If any of these keys is missing after processing, pick the existing row with the highest `share4` in that tunnel and log the substitution.

**Script:**
1. **0:00–0:25, hook.** "Massachusetts has 48 highway tunnels, third most in the country. In the past year MassDOT's board has taken up tunnel contracts of $52 million and $103 million. The staff summaries describe the scope, not how repairs were ranked." Show the map.
2. **0:25–1:10, the slider.** Set $74M ("about one year of the tunnels program"). Point to the stat tiles and the top 5 funded items. Drag to $15.3M: tunnels turn red, and the safety banner appears if triggered. Drag back.
3. **1:10–1:50, the drone already flew.** Paste demo finding 1 as free text → Parse → Apply. The DiffBanner shows what entered and left the plan. Say "this is where InspectPath-style robots plug in".
4. **1:50–2:20, cost of waiting + memo.** Show the "+X% if we wait 2 years" tile. Generate the memo; show the "numbers verified" badge.
5. **2:20–2:45, honesty.** Open Data notes: "We found that some elements are recorded as severe in nearly every tunnel, so we treat that as a reporting convention, not a crisis." Open Assumptions: costs are placeholders, rates are defaults.
6. **2:45–3:00, business.** "State DOTs own about 500 tunnels nationally; the same engine works on bridges, which use the same element-condition format. Pilot ask: one MassDOT tunnel engineer, one hour, to calibrate costs."

## 15. Guardrails and honesty rules
- Use only public data. Never label simulated findings as real; the UI shows a "Simulated" chip.
- The app is decision support, not an engineering assessment. Show this in the footer: "Planning tool using public FHWA data and stated assumptions. Not an engineering assessment."
- Never present risk points as probabilities, or placeholder costs as MassDOT costs.
- Keep tunnel security in mind: show condition shares and recommendations only, nothing about vulnerabilities beyond what the public dataset already contains.

## 16. Using this spec with Kiro (judges score Kiro use)
- Put this file in `.kiro/steering/product.md` (or reference it from there) so every Kiro session has the product context.
- Ask Kiro to generate a spec per phase in §13 (requirements → design → tasks), pointing it at the matching section numbers. Approve each phase's tasks before running them.
- Add one agent hook: on save of `backend/app/*.py`, run `pytest -q` and report failures. Show this hook firing in the pitch.
- Keep the `.kiro/` folder in the submitted repo as evidence.

## 17. Sources (for `constants.py` and the Data notes panel)
- NTI inventory service: https://services.arcgis.com/xOi1kZaI0eWDREZv/ArcGIS/rest/services/NTAD_National_Tunnel_Inventory/FeatureServer
- NTI element data service: https://services.arcgis.com/xOi1kZaI0eWDREZv/ArcGIS/rest/services/NTAD_National_Tunnel_Inventory_Element_Data/FeatureServer
- NTI element data catalog entry: https://catalog.data.gov/dataset/national-tunnel-inventory-element-data1
- NTI data dictionary: https://doi.org/10.21949/1529051
- SNTI specification (element names): https://www.fhwa.dot.gov/bridge/inspection/tunnel/snti/hif15006.pdf
- SNTI inventory and element fields: https://www.fhwa.dot.gov/bridge/inspection/tunnel/snti/inventory_element.pdf
- 2025 tunnel counts by state (MA = 48, rank 3): https://www.fhwa.dot.gov/bridge/inspection/tunnel/inventory/tunnelsbystate2025.cfm
- NTI yearly downloads 2018–2026: https://www.fhwa.dot.gov/bridge/inspection/tunnel/inventory/download.cfm
- MassDOT tunnel inspection policy P-25-002: https://www.mass.gov/doc/p-25-002-tunnel-inspection-and-testing-program/download
- Draft FY27–31 Capital Investment Plan (May 13, 2026): https://www.mass.gov/doc/draft-fy27-31-capital-investment-plan-presented-to-the-cpc-on-may-13-2026/download
- Tunnel Preservation within MHS Tunnels staff summary (Sept 2025): https://www.mass.gov/doc/staff-summary-for-the-tunnel-preservation-within-mhs-tunnels-presented-to-the-cpc-on-september-10-2025/download
- CANA Tunnel and Vent Building Rehabilitation staff summary (Sept 2026): https://www.mass.gov/doc/staff-summary-for-the-boston-cana-tunnel-and-vent-building-rehabilitation-submitted-to-the-massdot-board-on-september-23-2026/download
- Central Artery UPS replacement staff summary (Nov 2025): https://www.mass.gov/doc/staff-summary-for-the-boston-ups-system-replacements-in-the-central-artery-tunnels-presented-to-the-cpc-on-november-12-2025/download
- 2024 MHS triennial report: https://www.mass.gov/doc/2024-metropolitan-highway-system-triennial-report-presented-at-the-massdot-board-meeting-on-march-19-2025/download
- 2022 four-tunnel contract (NBC Boston): https://www.nbcboston.com/news/local/state-to-address-declining-conditions-in-boston-highway-tunnels/2867536/
