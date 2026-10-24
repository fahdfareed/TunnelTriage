"""Budget-constrained repair optimizer (SPEC §6.6).

Multiple-choice knapsack with per-tunnel mobilization. CP-SAT with greedy fallback.
Costs are scaled to $1,000 integers for the solver.
"""
from __future__ import annotations

import logging
import uuid
from typing import Dict, List, Optional, Set

from .config import Config
from .risk import RiskContext

log = logging.getLogger(__name__)
SCALE = 1000  # dollars -> $1,000 integer units


def safety_floor_forced(actions: List[dict], ctx: RiskContext, rows_by_key: Dict[str, dict], cfg: Config) -> Set[str]:
    """FIX_SEVERE forced for critical, high-CS4 rows (SPEC §8.3)."""
    if not cfg.safety_floor.enabled:
        return set()
    forced = set()
    for a in actions:
        if a["action"] != "FIX_SEVERE":
            continue
        row = rows_by_key.get(a["row_key"])
        if not row:
            continue
        crit = ctx.criticality(a["element_number"])
        if crit >= cfg.safety_floor.min_criticality and row["shares"][3] >= cfg.safety_floor.min_cs4_share:
            forced.add(a["action_id"])
    return forced


def _solve_cpsat(actions, budget, mob, forced, time_limit=3) -> Optional[dict]:
    try:
        from ortools.sat.python import cp_model
    except Exception:
        return None

    model = cp_model.CpModel()
    budget_k = int(budget // SCALE)
    mob_k = int(round(mob / SCALE))

    x = {a["action_id"]: model.NewBoolVar(a["action_id"]) for a in actions}
    tunnels = sorted({a["tunnel_number"] for a in actions})
    y = {t: model.NewBoolVar(f"y_{t}") for t in tunnels}

    # One action per row.
    by_row: Dict[str, List[dict]] = {}
    for a in actions:
        by_row.setdefault(a["row_key"], []).append(a)
    for row_key, acts in by_row.items():
        model.Add(sum(x[a["action_id"]] for a in acts) <= 1)

    # Mobilization linking.
    for a in actions:
        model.Add(x[a["action_id"]] <= y[a["tunnel_number"]])

    # Forced safety-floor items (only if feasible; soft handling after solve).
    for aid in forced:
        if aid in x:
            model.Add(x[aid] == 1)

    # Budget.
    cost_terms = [int(round(a["cost_point"] / SCALE)) * x[a["action_id"]] for a in actions]
    mob_terms = [mob_k * y[t] for t in tunnels]
    model.Add(sum(cost_terms) + sum(mob_terms) <= budget_k)

    model.Maximize(sum(int(round(a["benefit"] * 1000)) * x[a["action_id"]] for a in actions))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    funded = [a for a in actions if solver.Value(x[a["action_id"]]) == 1]
    return {"funded": funded, "solver": "cp-sat"}


def _solve_greedy(actions, budget, mob, forced) -> dict:
    """Benefit/cost greedy with forced items first (SPEC §6.6 fallback)."""
    funded: List[dict] = []
    used_rows: Set[str] = set()
    mobilized: Set[str] = set()
    spent = 0.0

    def try_add(a) -> bool:
        nonlocal spent
        if a["row_key"] in used_rows:
            return False
        add_mob = mob if a["tunnel_number"] not in mobilized else 0
        if spent + a["cost_point"] + add_mob > budget:
            return False
        funded.append(a)
        used_rows.add(a["row_key"])
        mobilized.add(a["tunnel_number"])
        spent += a["cost_point"] + add_mob
        return True

    forced_actions = [a for a in actions if a["action_id"] in forced]
    forced_actions.sort(key=lambda a: a["benefit_per_million"], reverse=True)
    for a in forced_actions:
        try_add(a)

    rest = [a for a in actions if a["action_id"] not in forced]
    rest.sort(key=lambda a: a["benefit_per_million"], reverse=True)
    for a in rest:
        try_add(a)
    return {"funded": funded, "solver": "greedy"}


def _risk_at_horizon(ctx, rows_by_key, cfg, funded_ids, actions_by_id):
    """Statewide risk at horizon H: do-nothing vs. with the funded plan."""
    from .forecast import _rates_for, forecast_shares, transition_matrix
    H = cfg.horizon_years
    do_nothing = 0.0
    with_plan = 0.0
    funded_by_row = {}
    for aid in funded_ids:
        a = actions_by_id[aid]
        funded_by_row[a["row_key"]] = a
    for row in rows_by_key.values():
        if not row["scored"]:
            continue
        P = transition_matrix(_rates_for(ctx, row["element_number"], cfg))
        dn = forecast_shares(row["shares"], P, H)[H]
        do_nothing += ctx.row_risk(row, shares=dn)
        a = funded_by_row.get(row["key"])
        if a:
            post_total = sum(a["post_cs"])
            post_shares = [c / post_total for c in a["post_cs"]] if post_total else [0, 0, 0, 0]
            wp = forecast_shares(post_shares, P, H)[H]
            with_plan += ctx.row_risk(row, shares=wp)
        else:
            with_plan += ctx.row_risk(row, shares=dn)
    return do_nothing, with_plan


def optimize(actions, ctx: RiskContext, rows_by_key, cfg: Config, budget: int, horizon: Optional[int] = None) -> dict:
    if horizon is not None:
        cfg = cfg.model_copy(update={"horizon_years": horizon})
    mob = cfg.fixed_mobilization_per_tunnel
    forced = safety_floor_forced(actions, ctx, rows_by_key, cfg)

    result = _solve_cpsat(actions, budget, mob, forced)
    if result is None:
        result = _solve_greedy(actions, budget, mob, forced)

    funded = result["funded"]
    funded_ids = {a["action_id"] for a in funded}
    actions_by_id = {a["action_id"]: a for a in actions}

    # Mark forced items that didn't fit.
    forced_unmet = [aid for aid in forced if aid not in funded_ids]
    for a in funded:
        if a["action_id"] in forced:
            if "SAFETY_FLOOR" not in a["reason_codes"]:
                a["reason_codes"].append("SAFETY_FLOOR")

    funded.sort(key=lambda a: a["benefit_per_million"], reverse=True)
    for i, a in enumerate(funded, 1):
        a["rank"] = i

    total_cost_point = sum(a["cost_point"] for a in funded)
    mobilized = {a["tunnel_number"] for a in funded}
    total_cost_point += mob * len(mobilized)
    low = 1 + cfg.bid_vs_estimate.low
    high = 1 + cfg.bid_vs_estimate.high

    risk_now = sum(r["_risk_now"] for r in rows_by_key.values() if r.get("_risk_now"))
    risk_dn, risk_wp = _risk_at_horizon(ctx, rows_by_key, cfg, funded_ids, actions_by_id)

    unfunded = [a for a in actions if a["action_id"] not in funded_ids]
    unfunded.sort(key=lambda a: a["benefit"], reverse=True)

    by_group: Dict[str, dict] = {}
    for a in funded:
        g = by_group.setdefault(a["group_id"], {"group_id": a["group_id"], "funded_cost": 0.0})
        g["funded_cost"] += a["cost_point"]

    return {
        "plan_id": str(uuid.uuid4()),
        "budget": budget,
        "horizon": cfg.horizon_years,
        "solver": result["solver"],
        "funded": [_plan_item(a) for a in funded],
        "unfunded_top": [_plan_item(a) for a in unfunded[:15]],
        "total_cost_point": total_cost_point,
        "total_cost_low": total_cost_point * low,
        "total_cost_high": total_cost_point * high,
        "risk_now": risk_now,
        "risk_h_do_nothing": risk_dn,
        "risk_h_with_plan": risk_wp,
        "risk_reduction_pct": (100 * (risk_dn - risk_wp) / risk_dn) if risk_dn else 0.0,
        "by_group": list(by_group.values()),
        "forced_unmet": forced_unmet,
    }


def _plan_item(a: dict) -> dict:
    return {k: a[k] for k in (
        "action_id", "rank", "tunnel_number", "tunnel_name", "group_id",
        "element_number", "element_name", "action", "qty", "cost_point",
        "cost_low", "cost_high", "benefit", "benefit_per_million",
        "risk_now_row", "reason_codes",
    ) if k in a}
