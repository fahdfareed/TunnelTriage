"""Risk model: pure functions (SPEC §6.1-6.3).

risk is a relative index ("risk points"), not a probability.
"""
from __future__ import annotations

from typing import Dict, List

from .config import Config


def likelihood(shares: List[float], cfg: Config) -> float:
    """Poor-condition share weighting (SPEC §6.1). shares = [s1,s2,s3,s4]."""
    return cfg.weights.w3 * shares[2] + cfg.weights.w4 * shares[3]


def median_totals(rows: List[dict]) -> Dict[int, float]:
    by_num: Dict[int, List[int]] = {}
    for r in rows:
        if r["total"] > 0:
            by_num.setdefault(r["element_number"], []).append(r["total"])
    out: Dict[int, float] = {}
    for n, totals in by_num.items():
        s = sorted(totals)
        m = len(s)
        out[n] = (s[m // 2] if m % 2 else (s[m // 2 - 1] + s[m // 2]) / 2)
    return out


def size_factor(total: int, median_total: float, cfg: Config) -> float:
    """sqrt(total / median) clipped to the configured range (SPEC §6.2)."""
    lo, hi = cfg.size_factor_clip
    if not median_total or median_total <= 0 or total <= 0:
        return lo
    raw = (total / median_total) ** 0.5
    return max(lo, min(hi, raw))


def exposure(tunnel: dict, max_adt: int, cfg: Config) -> float:
    """ADT-scaled exposure 0.5..1.0, boosted if under navigable water (SPEC §6.3)."""
    adt = tunnel.get("adt", 0) or 0
    e = 0.5 + 0.5 * (adt / max_adt if max_adt else 0.0)
    if tunnel.get("under_water"):
        e *= cfg.underwater_multiplier
    return e


def risk_from_shares(
    shares: List[float],
    criticality: int,
    exposure_val: float,
    size_factor_val: float,
    cfg: Config,
) -> float:
    """risk = 100 * criticality * exposure * likelihood * size_factor (SPEC §6.3)."""
    return 100.0 * criticality * exposure_val * likelihood(shares, cfg) * size_factor_val


class RiskContext:
    """Precomputed statewide values so per-row risk is cheap."""

    def __init__(self, tunnels: List[dict], rows: List[dict], dictionary: Dict[int, dict], cfg: Config):
        self.cfg = cfg
        self.dictionary = dictionary
        self.tunnels = {t["tunnel_number"]: t for t in tunnels}
        self.max_adt = max((t.get("adt", 0) or 0 for t in tunnels), default=0)
        self.median_totals = median_totals(rows)

    def criticality(self, element_number: int) -> int:
        d = self.dictionary.get(element_number)
        return d["criticality"] if d else 3

    def row_risk(self, row: dict, shares: List[float] | None = None) -> float:
        tunnel = self.tunnels.get(row["tunnel_number"], {})
        exp = exposure(tunnel, self.max_adt, self.cfg)
        sf = size_factor(row["total"], self.median_totals.get(row["element_number"], 0), self.cfg)
        crit = self.criticality(row["element_number"])
        return risk_from_shares(shares or row["shares"], crit, exp, sf, self.cfg)


def tunnel_risk(ctx: RiskContext, rows: List[dict], tunnel_number: str) -> float:
    return sum(ctx.row_risk(r) for r in rows if r["tunnel_number"] == tunnel_number and r["scored"])


def statewide_risk(ctx: RiskContext, rows: List[dict]) -> float:
    return sum(ctx.row_risk(r) for r in rows if r["scored"])
