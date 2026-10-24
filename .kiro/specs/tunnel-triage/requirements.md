# Requirements: TunnelTriage

## Introduction

TunnelTriage is a budget-constrained decision-support tool for prioritizing Massachusetts
highway tunnel repairs. It ingests public FHWA National Tunnel Inventory (NTI) condition
data, computes a transparent risk score per element and tunnel, forecasts deterioration,
and selects the set of repairs that removes the most safety risk for a fixed budget. It
produces a plain-language board memo and re-plans live when new inspection or drone findings
arrive.

The product is explicitly decision support, not an engineering assessment. It does not fly
drones, analyze imagery, or detect defects; it consumes findings produced elsewhere. Every
computed quantity must be traceable to the source data, the configuration, or a documented
assumption.

Pitch: "The drone already flew. TunnelTriage decides what to fix first, and shows what
waiting will cost."

## Glossary

- **Element**: A component of a tunnel (e.g. ceiling panel, liner) tracked by the NTI with a
  numeric `element_number`.
- **Condition state (CS1–CS4)**: Standard element-inspection grades: 1 good, 2 fair, 3 poor,
  4 severe. An element's `total_quantity` is split across the four states.
- **Risk points**: A relative risk index (not a probability) combining criticality, exposure,
  condition, and element size.
- **Finding**: A new observed defect (from a drone, inspector, or simulation) that moves
  quantity into a worse condition state.
- **Safety floor**: Repairs that must be funded first because the element is highly critical
  and significantly degraded.

## Requirements

### Requirement 1: Real tunnel condition data, cached locally

**User Story:** As an analyst, I want the real Massachusetts tunnel inventory and element
condition data loaded and cached, so that the tool reflects actual federal records and the
demo never depends on live network access.

#### Acceptance Criteria
1. WHEN the data pipeline runs THEN the system SHALL fetch the NTI inventory layer filtered to
   `state_code_i3 = '25'` and the element data table filtered to `state = '25'`.
2. WHEN fetching any layer THEN the system SHALL paginate 1,000 records at a time and stop when
   `exceededTransferLimit` is false.
3. WHEN fetching completes THEN the system SHALL assert the element row count equals the
   `returnCountOnly` count for that layer.
4. WHEN fetching completes THEN the system SHALL write untouched raw responses to
   `data/raw/inventory_ma.json` and `data/raw/elements_ma.json` and commit them.
5. IF the network fails AND raw files exist THEN the system SHALL use the cached raw files and
   log a warning rather than failing.
6. THE inventory file SHALL contain at least 40 rows and the element file SHALL match its
   reported count.

### Requirement 2: Element dictionary with safe fallback

**User Story:** As an analyst, I want element numbers mapped to names, categories, units, and
criticality, so that the UI is readable even when the authoritative source cannot be parsed.

#### Acceptance Criteria
1. WHEN building the dictionary THEN the system SHALL attempt to extract names and categories
   from the SNTI specification PDF within a hard 20-minute timebox.
2. IF extraction does not cover at least 30 of the observed element numbers within the timebox
   THEN the system SHALL write a fallback entry for every element number present in the data.
3. WHEN a fallback entry is written THEN its name SHALL be `Element {n}`, category `Unknown`,
   source `fallback`, unit `each` if the max quantity for that element ≤ 50 else `area/length`,
   `is_system_element` true when unit is `each`, and `criticality` 3.
4. THE dictionary SHALL be stored at `data/element_dictionary.csv` with columns
   `element_number,name,category,unit,criticality,is_system_element,source`.
5. THE UI SHALL always display the element number alongside the name so an incorrect name
   never hides the real identifier.
6. WHEN assigning criticality THEN the system SHALL apply category defaults, allow per-element
   overrides from config, and force criticality 5 for any element whose name contains
   `ceiling` or `hanger`.

### Requirement 3: Normalization and data-quality flagging

**User Story:** As an analyst, I want condition data normalized with explicit data-quality
flags, so that known reporting artifacts do not distort the prioritization.

#### Acceptance Criteria
1. WHEN normalizing an element row THEN the system SHALL compute condition-state shares and
   produce a stable key `{tunnel_number}|{element_number}|{epn or 0}`.
2. IF the condition states do not sum to the total THEN the system SHALL flag DQ_SUM_MISMATCH,
   keep the row, and rescale shares by the state sum.
3. IF the total is zero THEN the system SHALL flag DQ_ZERO_TOTAL and exclude the row from
   scoring.
4. WHEN an element appears in at least 5 tunnels AND at least 80% of its rows are a single unit
   fully in CS4 THEN the system SHALL flag every row of that element DQ_SUSPECT_ALL_CS4 and
   exclude it from risk, actions, and optimizer by default.
5. THE suspect-element exclusion SHALL be toggleable via `include_suspect_elements` in config.
6. WHEN an element row has no matching inventory tunnel THEN the system SHALL flag DQ_ORPHAN,
   keep it, and label the tunnel "Unknown tunnel".
7. WHEN normalization completes THEN the system SHALL record DQ counts and examples in
   `data/processed/data_notes.json`.

### Requirement 4: Tunnel grouping for the map

**User Story:** As a viewer, I want tunnel segments grouped into named tunnels on a map, so
that I see one marker per real tunnel rather than per direction.

#### Acceptance Criteria
1. WHEN grouping tunnels THEN the system SHALL derive a `group_id` by removing direction words
   and trailing segment tokens from the tunnel name and normalizing case and spacing.
2. THE map SHALL show one marker per group at the mean latitude and longitude of its segments.
3. WHEN a marker is clicked THEN the UI SHALL list the segments in that group.
4. IF a tunnel name is empty THEN the system SHALL use the tunnel number as both name and group.
5. THE processed data SHALL yield at least 6 map groups.

### Requirement 5: Transparent risk scoring

**User Story:** As an analyst, I want a transparent, reproducible risk score per element and
tunnel, so that rankings can be explained and defended.

#### Acceptance Criteria
1. THE element likelihood SHALL be a weighted sum of the poor and severe condition shares.
2. THE size factor SHALL scale by the square root of quantity relative to the element's median,
   clipped to the configured bounds.
3. THE exposure factor SHALL scale with average daily traffic and apply the underwater
   multiplier when the tunnel is under navigable water.
4. THE element risk SHALL combine criticality, exposure, likelihood, and size factor.
5. THE tunnel risk SHALL be the sum of its scored rows, group risk the sum over segments, and
   statewide risk the sum over all scored rows.
6. WHEN both poor and severe shares are zero THEN the risk SHALL be zero.
7. WHEN criticality doubles THEN the risk SHALL double.
8. THE UI SHALL present risk as a relative index labeled "risk points", never as a probability.

### Requirement 6: Deterioration forecast

**User Story:** As a planner, I want a do-nothing deterioration forecast, so that I can see how
risk grows if repairs are deferred.

#### Acceptance Criteria
1. THE forecast SHALL apply a per-category yearly Markov transition matrix to condition shares.
2. WHEN a row is a system element THEN the forecast SHALL use the system transition rates
   regardless of category.
3. WHEN forecasting THEN the system SHALL return share vectors for years 0 through 10.
4. EACH transition matrix row SHALL sum to 1.
5. OVER time the severe share SHALL be non-decreasing and the total of shares SHALL remain 1.
6. THE Assumptions panel SHALL label deterioration rates as default and not calibrated unless
   calibrated from historical data.

### Requirement 7: Candidate repair actions and costs

**User Story:** As a planner, I want each degraded element to have candidate repair actions
with cost ranges, so that the optimizer has options to choose from.

#### Acceptance Criteria
1. FOR each scored row the system SHALL generate up to two mutually exclusive actions:
   `FIX_SEVERE` (move CS4 to CS1) and `FIX_POOR_AND_SEVERE` (move CS3+CS4 to CS1).
2. THE system SHALL skip an action whose quantity is zero and skip `FIX_POOR_AND_SEVERE` when
   CS3 is zero.
3. THE action cost SHALL be computed from configurable per-unit, per-state placeholder costs
   plus a fixed mobilization cost applied once per funded tunnel.
4. THE system SHALL present a cost range using the configured low and high bid-vs-estimate
   factors.
5. ON startup the system SHALL print and expose a calibration check comparing the statewide
   repair backlog cost to the published 5-year tunnels program figure.
6. THE benefit of an action SHALL be the risk reduction summed over the planning horizon,
   comparing do-nothing deterioration to post-action deterioration.
7. THE UI SHALL never present placeholder costs as actual MassDOT costs.

### Requirement 8: Budget-constrained optimizer

**User Story:** As a decision-maker, I want the tool to select the repair set that removes the
most risk within my budget, so that funding goes where it helps most.

#### Acceptance Criteria
1. THE optimizer SHALL maximize total benefit subject to at most one action per element row,
   mobilization coupling per tunnel, and a total cost within the budget.
2. THE optimizer SHALL use OR-Tools CP-SAT with a short time limit and fall back to a greedy
   benefit-per-cost heuristic if the solver is unavailable or finds no solution.
3. THE plan output SHALL report the solver used, funded items, top unfunded items, cost point
   and range, risk now, risk at horizon do-nothing and with plan, reduction percent, and a
   per-group breakdown.
4. EACH funded item SHALL include a rank by benefit-per-million and machine-readable reason
   codes.
5. WHEN using CP-SAT across increasing budgets THEN the risk-with-plan SHALL be non-increasing.
6. THE plan for the Massachusetts dataset SHALL be produced in under 2 seconds.
7. WHEN safety-floor items exceed the budget THEN the system SHALL fund as many as fit and list
   the remainder in `forced_unmet`.

### Requirement 9: Cost of waiting

**User Story:** As a decision-maker, I want to see what deferring the funded repairs for two
years costs, so that I understand the price of delay.

#### Acceptance Criteria
1. THE system SHALL compute the cost to perform the funded repairs now versus after two years
   of do-nothing deterioration, using the same unit costs.
2. THE system SHALL compute the extra risk absorbed while waiting over the two-year period.
3. THE response SHALL include cost now, cost in two years, cost increase percent, and extra
   risk, and SHALL note that construction inflation is excluded.

### Requirement 10: Findings intake and live re-plan

**User Story:** As an inspector, I want to submit new defect findings as a structured form or
free text, so that the plan updates to reflect fresh field information.

#### Acceptance Criteria
1. THE system SHALL accept a structured finding with tunnel, element, quantity, condition state
   (3 or 4), source, and an optional note.
2. WHEN a finding is applied THEN the system SHALL move quantity into the target state from the
   best states first, never allow a state to go negative, and conserve total quantity.
3. IF the finding targets a row that does not exist THEN the system SHALL create it and flag it.
4. THE system SHALL store findings in memory, list them with a remove option, and support a
   full reset that restores the base plan exactly.
5. THE system SHALL parse a free-text finding into a proposed finding plus fuzzy-matched tunnel
   and element candidates, and SHALL never apply it automatically.
6. WHEN an LLM is configured THEN parsing SHALL select values only from the candidate lists and
   validate them; otherwise it SHALL fall back to fuzzy matches and keyword-based state.
7. WHEN a finding changes THEN the system SHALL force the safety-floor actions and the frontend
   SHALL re-request the plan and show a diff of entered, left, and significantly re-ranked items.

### Requirement 11: AI board memo grounded in computed facts

**User Story:** As an engineer presenting to a committee, I want a one-page memo generated from
the plan, so that I can communicate the recommendation in plain language without fabricated
numbers.

#### Acceptance Criteria
1. THE memo SHALL be generated only from a facts payload derived from the plan, waiting result,
   findings, and documented assumptions.
2. WHEN an LLM is configured THEN the memo SHALL follow a five-section structure under the word
   limit and use only numbers present in the facts payload.
3. THE system SHALL verify every number in the LLM output against the facts payload after
   normalization, allowing rounding, currency/percent formatting, year ranges, and list numbers.
4. IF any number fails verification THEN the system SHALL return the deterministic template memo
   with a warning.
5. THE application SHALL be fully demoable with the LLM provider set to `none`.

### Requirement 12: Single-page operator UI

**User Story:** As an operator, I want one screen with the map, budget slider, plan, tunnel
detail, findings, memo, and assumptions, so that I can run the whole workflow in one place.

#### Acceptance Criteria
1. THE UI SHALL show a header, stat tiles (risk now, risk in 5 years do-nothing, risk with
   plan, plan cost range, waiting impact), a budget slider with labeled tick marks, a map, and
   a tabbed right panel.
2. WHEN the slider changes THEN the UI SHALL debounce, request a new plan, show a spinner, and
   keep the previous plan visible until the new one arrives.
3. THE Plan panel SHALL list funded items with reason chips and the top unfunded items, and
   SHALL show a red banner when safety-critical repairs are unfunded.
4. THE Tunnel panel SHALL show tunnel facts, an element table with stacked condition bars and
   DQ icons, and a risk chart comparing do-nothing to with-plan over years 0–10.
5. THE Findings panel SHALL support free-text parse, a structured form, an applied-findings
   list with removal, and a demo-findings loader, showing a diff after each change.
6. THE Memo panel SHALL render the markdown with a badge indicating verified AI or template and
   a copy-to-clipboard control.
7. THE Assumptions and Data notes panels SHALL present config, the calibration check, DQ
   counts, excluded suspect elements, dictionary source, and source links in plain words.
8. THE UI SHALL pair condition colors with text labels, never show risk without the unit, and
   never show a cost without "est." or a range.

### Requirement 13: Honesty and safety guardrails

**User Story:** As a stakeholder, I want the tool to be explicit about its limits and only use
public data, so that it is not mistaken for an engineering assessment.

#### Acceptance Criteria
1. THE UI SHALL mark simulated findings with a "Simulated" chip and never present them as real.
2. THE footer SHALL state that the tool uses public FHWA data and stated assumptions and is not
   an engineering assessment.
3. THE system SHALL never present risk points as probabilities or placeholder costs as actual
   costs.
4. THE system SHALL show only condition shares and recommendations, nothing about vulnerabilities
   beyond what the public dataset contains.
