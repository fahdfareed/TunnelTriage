"""In-memory application state: base data, dictionary, findings, plan cache.

The base element rows (as loaded from disk) are never mutated. Findings are
stored in memory and applied on top of a deep-copied working set; any findings
change rebuilds the working set and re-derives analytics, and invalidates the
plan cache (SPEC §8).
"""
from __future__ import annotations

import copy
import json
import logging
from typing import Dict, List, Optional

from .actions import backlog_calibration, candidate_actions
from .config import DATA_DIR, Config, get_config
from .dictionary import read_csv
from .findings import apply_finding
from .optimizer import budget_curve, optimize
from .risk import RiskContext
from .waiting import cost_of_waiting

log = logging.getLogger(__name__)
PROCESSED = DATA_DIR / "processed"


# Greater Boston bounding box (lat, lon).
GB_LAT = (42.15, 42.55)
GB_LON = (-71.35, -70.85)

class AppState:
    def __init__(self) -> None:
        self.cfg: Config = get_config()
        self.tunnels: List[dict] = []
        self._base_rows: List[dict] = []
        self.element_rows: List[dict] = []  # working set (base + findings)
        self.dictionary: Dict[int, dict] = {}
        self.data_notes: dict = {}
        self.findings: List[dict] = []
        self.ctx: Optional[RiskContext] = None
        self._actions: List[dict] = []
        self._actions_by_id: Dict[str, dict] = {}
        self._rows_by_key: Dict[str, dict] = {}
        self._plan_cache: Dict[str, dict] = {}
        self.calibration: dict = {}
        self.loaded = False
        self._curve_cache: Optional[List[dict]] = None

    def load(self) -> None:
        if not (PROCESSED / "tunnels.json").exists():
            log.warning("Processed data not found at %s; run scripts/build_data.py", PROCESSED)
            return
        # Demo scope: Greater Boston only (drops e.g. Fall River).
        self.tunnels = [
            t for t in json.loads((PROCESSED / "tunnels.json").read_text())
            if t["lat"] is not None and t["lon"] is not None
            and GB_LAT[0] <= t["lat"] <= GB_LAT[1] and GB_LON[0] <= t["lon"] <= GB_LON[1]
        ]
        in_scope = {t["tunnel_number"] for t in self.tunnels}
        self._base_rows = [
            r for r in json.loads((PROCESSED / "elements.json").read_text())
            if r["tunnel_number"] in in_scope
        ]
        self.data_notes = json.loads((PROCESSED / "data_notes.json").read_text())
        self.dictionary = read_csv(DATA_DIR / "element_dictionary.csv")
        self._rebuild()
        self.loaded = True

    def _rebuild(self) -> None:
        """Rebuild the working set from base rows + applied findings, re-derive analytics."""
        self.element_rows = copy.deepcopy(self._base_rows)
        self._rows_by_key = {r["key"]: r for r in self.element_rows}
        affected: set = set()
        for finding in self.findings:
            key, _ = apply_finding(self._rows_by_key, finding)
            affected.add(key)
        # The working rows list must include any newly created rows.
        self.element_rows = list(self._rows_by_key.values())

        self.ctx = RiskContext(self.tunnels, self.element_rows, self.dictionary, self.cfg)
        for r in self.element_rows:
            r["_risk_now"] = self.ctx.row_risk(r) if r["scored"] else 0.0
        self._actions = candidate_actions(self.ctx, self.element_rows, self.cfg)
        # Tag actions on finding-affected rows with the NEW_FINDING reason code.
        for a in self._actions:
            if a["row_key"] in affected and "NEW_FINDING" not in a["reason_codes"]:
                a["reason_codes"].append("NEW_FINDING")
        self._actions_by_id = {a["action_id"]: a for a in self._actions}
        self.calibration = backlog_calibration(self.ctx, self.element_rows, self.cfg)
        self._plan_cache.clear()
        self._curve_cache = None

    # ---- Findings management (SPEC §8) ----

    def add_finding(self, finding: dict) -> str:
        self.findings.append(finding)
        self._rebuild()
        return f"{finding['tunnel_number']}|{finding['element_number']}|{finding['epn']}"

    def remove_finding(self, finding_id: str) -> bool:
        before = len(self.findings)
        self.findings = [f for f in self.findings if f["finding_id"] != finding_id]
        if len(self.findings) != before:
            self._rebuild()
            return True
        return False

    def reset_findings(self) -> None:
        self.findings = []
        self._rebuild()

    # ---- Planning ----

    def make_plan(self, budget: int, horizon: Optional[int] = None) -> dict:
        plan = optimize(self._actions, self.ctx, self._rows_by_key, self.cfg, budget, horizon)
        waiting = cost_of_waiting(plan["funded"], self.ctx, self._rows_by_key,
                                  self._actions_by_id, self.cfg)
        plan["waiting"] = waiting
        self._plan_cache[plan["plan_id"]] = plan
        return plan

    def get_curve(self, budgets: List[int]) -> List[dict]:
        if self._curve_cache is None:
            self._curve_cache = budget_curve(self._actions, self.ctx, self._rows_by_key, self.cfg, budgets)
        return self._curve_cache

    def plan_risk_now(self) -> float:
        return sum(r["_risk_now"] for r in self.element_rows if r.get("_risk_now"))

    def get_plan(self, plan_id: str) -> Optional[dict]:
        return self._plan_cache.get(plan_id)

    def n_scored(self) -> int:
        return sum(1 for r in self.element_rows if r["scored"])

    def dictionary_source(self) -> str:
        srcs = {d["source"] for d in self.dictionary.values()}
        return "SNTI" if "SNTI" in srcs else "fallback"


STATE = AppState()
