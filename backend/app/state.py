"""In-memory application state: base data, dictionary, risk context, plan cache.

Loads processed JSON written by scripts/build_data.py. Findings (Phase 6) will
layer on top of this later; for now it exposes the base data and analytics.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .actions import backlog_calibration, candidate_actions
from .config import DATA_DIR, Config, get_config
from .dictionary import read_csv
from .optimizer import optimize
from .risk import RiskContext
from .waiting import cost_of_waiting

log = logging.getLogger(__name__)
PROCESSED = DATA_DIR / "processed"


class AppState:
    def __init__(self) -> None:
        self.cfg: Config = get_config()
        self.tunnels: List[dict] = []
        self.element_rows: List[dict] = []
        self.dictionary: Dict[int, dict] = {}
        self.data_notes: dict = {}
        self.ctx: Optional[RiskContext] = None
        self._actions: List[dict] = []
        self._actions_by_id: Dict[str, dict] = {}
        self._rows_by_key: Dict[str, dict] = {}
        self._plan_cache: Dict[str, dict] = {}
        self.loaded = False

    def load(self) -> None:
        if not (PROCESSED / "tunnels.json").exists():
            log.warning("Processed data not found at %s; run scripts/build_data.py", PROCESSED)
            return
        self.tunnels = json.loads((PROCESSED / "tunnels.json").read_text())
        self.element_rows = json.loads((PROCESSED / "elements.json").read_text())
        self.data_notes = json.loads((PROCESSED / "data_notes.json").read_text())
        self.dictionary = read_csv(DATA_DIR / "element_dictionary.csv")
        self._build_derived()
        self.loaded = True

    def _build_derived(self) -> None:
        self.ctx = RiskContext(self.tunnels, self.element_rows, self.dictionary, self.cfg)
        self._rows_by_key = {r["key"]: r for r in self.element_rows}
        for r in self.element_rows:
            r["_risk_now"] = self.ctx.row_risk(r) if r["scored"] else 0.0
        self._actions = candidate_actions(self.ctx, self.element_rows, self.cfg)
        self._actions_by_id = {a["action_id"]: a for a in self._actions}
        self.calibration = backlog_calibration(self.ctx, self.element_rows, self.cfg)

    def make_plan(self, budget: int, horizon: Optional[int] = None) -> dict:
        plan = optimize(self._actions, self.ctx, self._rows_by_key, self.cfg, budget, horizon)
        waiting = cost_of_waiting(plan["funded"], self.ctx, self._rows_by_key,
                                  self._actions_by_id, self.cfg)
        plan["waiting"] = waiting
        self._plan_cache[plan["plan_id"]] = plan
        return plan

    def get_plan(self, plan_id: str) -> Optional[dict]:
        return self._plan_cache.get(plan_id)

    def n_scored(self) -> int:
        return sum(1 for r in self.element_rows if r["scored"])

    def dictionary_source(self) -> str:
        srcs = {d["source"] for d in self.dictionary.values()}
        return "SNTI" if "SNTI" in srcs else "fallback"


STATE = AppState()
