# Implementation Plan: TunnelTriage

This plan formalizes the already-built TunnelTriage system. Tasks marked complete reflect code
present in the repository and verified by the passing pytest suite (30 passed). Open tasks are
optional enhancements and verification steps.

- [x] 1. Project skeleton and configuration
  - Create backend package, `config.yaml` with all tunable keys, `config.py` pydantic loaders,
    `constants.py` budget anchors and source URLs, `requirements.txt`, and the Vite frontend app.
  - _Requirements: 1, 5, 6, 7, 11, 12, 13_

- [x] 2. Data fetch and caching pipeline
  - [x] 2.1 Implement `fetch.py` paginated ArcGIS fetch with count assertion and raw-file fallback
    - _Requirements: 1.1, 1.2, 1.3, 1.5_
  - [x] 2.2 Commit raw inventory and element JSON and wire `scripts/build_data.py`
    - _Requirements: 1.4, 1.6_

- [x] 3. Element dictionary with fallback
  - Implement `dictionary.py` SNTI extraction within the timebox, full fallback coverage,
    criticality defaults, overrides, and overhead-keyword rule; write `element_dictionary.csv`.
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.6_

- [x] 4. Normalization, data-quality flags, and grouping
  - [x] 4.1 Implement `process.py` row normalization, shares, and stable keys
    - _Requirements: 3.1_
  - [x] 4.2 Implement DQ rules (sum mismatch, zero total, suspect-all-CS4, binary, orphan) and
    write `data_notes.json`
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_
  - [x] 4.3 Implement tunnel grouping and `build_groups` for the map
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 5. Risk scoring
  - Implement `risk.py` likelihood, size factor, exposure, and element risk as pure functions.
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [x] 6. Deterioration forecast
  - Implement `forecast.py` per-category Markov forecast and `tunnel_risk_series`.
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 7. Candidate actions and costs
  - Implement `actions.py` FIX_SEVERE / FIX_POOR_AND_SEVERE generation, cost point and range,
    mobilization, benefit over horizon, and the statewide backlog calibration check.
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [x] 8. Budget-constrained optimizer
  - Implement `optimizer.py` CP-SAT multiple-choice knapsack with mobilization and safety-floor
    forcing, greedy fallback, and the full Plan output structure.
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

- [x] 9. Cost of waiting
  - Implement `waiting.py` cost-now vs cost-in-2-years and extra-risk computation.
  - _Requirements: 9.1, 9.2, 9.3_

- [x] 10. In-memory state and plan caching
  - Implement `state.py` load, plan build/cache/invalidate, curve, and findings overlay.
  - _Requirements: 8.3, 10.4_

- [x] 11. Findings intake and parsing
  - [x] 11.1 Implement structured finding application with quantity conservation and row creation
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  - [x] 11.2 Implement free-text parse with fuzzy candidates and LLM candidate selection fallback
    - _Requirements: 10.5, 10.6_
  - [x] 11.3 Wire safety-floor forcing and expose finding mutation routes
    - _Requirements: 10.7_

- [x] 12. Board memo generation
  - Implement `memo.py` facts payload, LLM memo, number guard, and deterministic template; wrap
    providers in `llm.py` with a `none` default.
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 13. FastAPI routes
  - Implement all `/api` routes in `main.py` with load guards, CORS, and pydantic schemas.
  - _Requirements: 8.3, 9.3, 10.*, 11.*, 12.1_

- [x] 14. Frontend single-page UI
  - [x] 14.1 Header, stat tiles, BudgetBar with tick marks, debounced plan requests
    - _Requirements: 12.1, 12.2_
  - [x] 14.2 MapView (one marker per group, radius by ADT, color by risk)
    - _Requirements: 4.2, 4.3, 12.1_
  - [x] 14.3 Plan panel with funded/unfunded items, reason chips, and safety-floor banner
    - _Requirements: 12.3_
  - [x] 14.4 Tunnel detail with stacked condition bars, DQ icons, and risk chart
    - _Requirements: 12.4_
  - [x] 14.5 Findings panel (parse, structured form, list, demo loader) with DiffBanner
    - _Requirements: 10.5, 12.5_
  - [x] 14.6 Memo panel with verified/template badge and copy-to-clipboard
    - _Requirements: 12.6_
  - [x] 14.7 Assumptions and Data Notes panels
    - _Requirements: 12.7_
  - [x] 14.8 Display rules, simulated chip, and honesty footer
    - _Requirements: 12.8, 13.1, 13.2, 13.3, 13.4_

- [x] 15. Test suite
  - Implement pytest coverage for process, risk, forecast, optimizer, findings, memo, and API.
  - _Requirements: all (verification)_

- [ ] 16. Optional: calibrate deterioration rates from historical NTI data
  - Load 2018–2026 yearly NTI downloads if available and estimate transition probabilities per
    category, labeling the Assumptions panel "calibrated" when used.
  - _Requirements: 6.6_

- [ ] 17. Optional: expand validation backtest coverage
  - Extend `validation.py` beyond contract 130548 with additional committed calibration contracts
    and surface the comparison in the Validation panel.
  - _Requirements: 7.5_

- [ ] 18. Optional: end-to-end smoke check script
  - Add a script that starts the backend, asserts `/api/health`, requests a plan at $74M under
    the 2 s budget, applies a demo finding, and generates a memo with `LLM_PROVIDER=none`.
  - _Requirements: 8.6, 10.7, 11.5_
