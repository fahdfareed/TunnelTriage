"""Candidate repair actions, costs, and benefit (SPEC §6.5).

All unit costs are PLACEHOLDER ASSUMPTIONS, never real MassDOT costs.
"""
from __future__ import annotations

from typing import Dict, List

from .config import Config
from .forecast import _rates_for, forecast_shares, transition_matrix
from .risk import RiskContext


def _reason_codes(ctx: RiskContext, row: dict) -> List[str]:
    codes: List[str] = []
    if row["shares"][3] >= 0.10:
        codes.append("HIGH_CS4_SHARE")
    tunnel = ctx.tunnels.get(row["tunnel_number"], {})
    if ctx.max_adt and (tunnel.get("adt", 0) or 0) >= 0.5 * ctx.max_adt:
        codes.append("HIGH_TRAFFIC")
    if tunnel.get("under_water"):
        codes.append("UNDER_WATER")
    d = ctx.dictionary.get(row["element_number"], {})
    if any(kw in d.get("name", "").lower() for kw in ctx.cfg.overhead_keywords):
        codes.append("OVERHEAD_ELEMENT")
    return codes


def _apply_to_cs1(cs: List[int], states: List[int]) -> List[int]:
    """Move all quantity in the given states (0-indexed) into CS1."""
    out = list(cs)
    for s in states:
        out[0] += out[s]
        out[s] = 0
    return out


def _cost_point(ctx: RiskContext, row: dict, states_moved: List[int]) -> float:
    d = ctx.dictionary.get(row["element_number"], {})
    unit = d.get("unit", "area/length")
    uc = ctx.cfg.unit_cost[unit]
    per = {2: uc.cs3, 3: uc.cs4}  # state index 2 -> cs3, 3 -> cs4
    total = sum(row["cs"][s] * per[s] for s in states_moved)
    return ctx.cfg.cost_scale * total


def _benefit(ctx: RiskContext, row: dict, post_cs: List[int], cfg: Config) -> float:
    """Integrated risk reduction over the horizon vs. do-nothing (SPEC §6.5)."""
    H = cfg.horizon_years
    P = transition_matrix(_rates_for(ctx, row["element_number"], cfg))

    do_nothing = forecast_shares(row["shares"], P, H)
    post_total = sum(post_cs)
    post_shares = [c / post_total for c in post_cs] if post_total > 0 else [0, 0, 0, 0]
    with_action = forecast_shares(post_shares, P, H)

    benefit = 0.0
    for t in range(H + 1):
        benefit += ctx.row_risk(row, shares=do_nothing[t]) - ctx.row_risk(row, shares=with_action[t])
    return benefit


def candidate_actions(ctx: RiskContext, rows: List[dict], cfg: Config) -> List[dict]:
    """Up to two mutually exclusive actions per scored row (SPEC §6.5)."""
    low = 1 + cfg.bid_vs_estimate.low
    high = 1 + cfg.bid_vs_estimate.high
    actions: List[dict] = []
    for row in rows:
        if not row["scored"]:
            continue
        cs3, cs4 = row["cs"][2], row["cs"][3]
        base_codes = _reason_codes(ctx, row)
        tunnel = ctx.tunnels.get(row["tunnel_number"], {})

        variants = []
        if cs4 > 0:
            variants.append(("FIX_SEVERE", [3], cs4))
        if cs3 > 0:
            variants.append(("FIX_POOR_AND_SEVERE", [2, 3], cs3 + cs4))

        for name, states, qty in variants:
            if qty <= 0:
                continue
            post_cs = _apply_to_cs1(row["cs"], states)
            cost_point = _cost_point(ctx, row, states)
            benefit = _benefit(ctx, row, post_cs, cfg)
            d = ctx.dictionary.get(row["element_number"], {})
            actions.append({
                "action_id": f"{row['key']}|{name}",
                "row_key": row["key"],
                "tunnel_number": row["tunnel_number"],
                "tunnel_name": tunnel.get("name", row["tunnel_number"]),
                "group_id": tunnel.get("group_id", ""),
                "element_number": row["element_number"],
                "element_name": d.get("name", f"Element {row['element_number']}"),
                "action": name,
                "qty": qty,
                "cost_point": cost_point,
                "cost_low": cost_point * low,
                "cost_high": cost_point * high,
                "benefit": benefit,
                "benefit_per_million": benefit / (cost_point / 1e6) if cost_point > 0 else 0.0,
                "risk_now_row": ctx.row_risk(row),
                "reason_codes": list(base_codes),
                "post_cs": post_cs,
            })
    return actions


def backlog_calibration(ctx: RiskContext, rows: List[dict], cfg: Config) -> dict:
    """Cost to fix all CS4 (and all CS3+CS4) statewide, for scale sanity (SPEC §6.5)."""
    cs4_cost = 0.0
    cs34_cost = 0.0
    for row in rows:
        if not row["scored"]:
            continue
        if row["cs"][3] > 0:
            cs4_cost += _cost_point(ctx, row, [3])
        if row["cs"][2] > 0 or row["cs"][3] > 0:
            cs34_cost += _cost_point(ctx, row, [2, 3])
    return {
        "backlog_cs4_cost": cs4_cost,
        "backlog_cs34_cost": cs34_cost,
        "tunnels_5yr_program_anchor": 370_000_000,
        "note": "Placeholder unit costs. Adjust cost_scale by hand if backlog is wildly off.",
    }
