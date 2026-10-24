"""Markov deterioration forecast (SPEC §6.4). Default rates, not calibrated."""
from __future__ import annotations

from typing import Dict, List

from .config import Config
from .risk import RiskContext


def transition_matrix(rates) -> List[List[float]]:
    """4x4 upper-bidiagonal Markov matrix; each row sums to 1 (SPEC §6.4)."""
    p12, p23, p34 = rates.p12, rates.p23, rates.p34
    return [
        [1 - p12, p12, 0.0, 0.0],
        [0.0, 1 - p23, p23, 0.0],
        [0.0, 0.0, 1 - p34, p34],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _rates_for(ctx: RiskContext, element_number: int, cfg: Config):
    d = ctx.dictionary.get(element_number, {})
    if d.get("is_system_element"):
        return cfg.transition["system"]
    group = cfg.category_transition_group.get(d.get("category", "Unknown"), "default")
    return cfg.transition.get(group, cfg.transition["default"])


def step(shares: List[float], P: List[List[float]]) -> List[float]:
    """shares(t+1) = shares(t) @ P."""
    return [sum(shares[i] * P[i][j] for i in range(4)) for j in range(4)]


def forecast_shares(shares: List[float], P: List[List[float]], years: int) -> List[List[float]]:
    """Returns years+1 share vectors (t = 0..years)."""
    out = [list(shares)]
    cur = list(shares)
    for _ in range(years):
        cur = step(cur, P)
        out.append(cur)
    return out


def forecast_row(ctx: RiskContext, row: dict, cfg: Config, years: int = 10) -> List[List[float]]:
    P = transition_matrix(_rates_for(ctx, row["element_number"], cfg))
    return forecast_shares(row["shares"], P, years)


def row_risk_over_time(ctx: RiskContext, row: dict, cfg: Config, years: int) -> List[float]:
    series = forecast_row(ctx, row, cfg, years)
    return [ctx.row_risk(row, shares=s) for s in series]


def tunnel_risk_series(ctx: RiskContext, rows: List[dict], tunnel_number: str, cfg: Config, years: int = 10) -> List[Dict]:
    scored = [r for r in rows if r["tunnel_number"] == tunnel_number and r["scored"]]
    totals = [0.0] * (years + 1)
    for r in scored:
        for t, v in enumerate(row_risk_over_time(ctx, r, cfg, years)):
            totals[t] += v
    return [{"year": t, "risk": totals[t]} for t in range(years + 1)]
