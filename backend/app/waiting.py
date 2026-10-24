"""Cost of waiting 2 years (SPEC §6.7). Excludes construction inflation."""
from __future__ import annotations

from typing import Dict, List

from .actions import _cost_point
from .config import Config
from .forecast import _rates_for, forecast_shares, transition_matrix
from .risk import RiskContext


def cost_of_waiting(funded_items: List[dict], ctx: RiskContext, rows_by_key: Dict[str, dict],
                    actions_by_id: Dict[str, dict], cfg: Config) -> dict:
    cost_now = 0.0
    cost_in_2y = 0.0
    extra_risk_2y = 0.0
    mobilized = set()

    for item in funded_items:
        a = actions_by_id.get(item["action_id"])
        if not a:
            continue
        row = rows_by_key.get(a["row_key"])
        if not row:
            continue
        cost_now += a["cost_point"]
        if a["tunnel_number"] not in mobilized:
            # Same mobilization either way, so waiting never looks cheaper than it is.
            cost_now += cfg.fixed_mobilization_per_tunnel
            cost_in_2y += cfg.fixed_mobilization_per_tunnel
            mobilized.add(a["tunnel_number"])

        P = transition_matrix(_rates_for(ctx, row["element_number"], cfg))
        series = forecast_shares(row["shares"], P, 2)
        shares_2y = series[2]
        cs_2y = [round(s * row["total"]) for s in shares_2y]

        states = [3] if a["action"] == "FIX_SEVERE" else [2, 3]
        future_row = {**row, "cs": cs_2y}
        cost_in_2y += _cost_point(ctx, future_row, states)

        post_total = sum(a["post_cs"])
        post_shares = [c / post_total for c in a["post_cs"]] if post_total else [0, 0, 0, 0]
        with_action = forecast_shares(post_shares, P, 2)
        for t in range(2):
            extra_risk_2y += ctx.row_risk(row, shares=series[t]) - ctx.row_risk(row, shares=with_action[t])

    pct = (100 * (cost_in_2y - cost_now) / cost_now) if cost_now else 0.0
    return {
        "cost_now": cost_now,
        "cost_in_2y": cost_in_2y,
        "cost_increase_pct": pct,
        "extra_risk_2y": extra_risk_2y,
        "note": "Excludes construction inflation.",
    }
