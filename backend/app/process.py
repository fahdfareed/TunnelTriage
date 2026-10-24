"""Normalize elements and tunnels, apply data-quality flags, group for the map.

SPEC §5.3 (element normalization + DQ flags) and §5.4 (tunnel grouping).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .config import Config

DIRECTION_PAT = re.compile(
    r"\b(NORTHBOUND|SOUTHBOUND|EASTBOUND|WESTBOUND|EB|WB|NB|SB)\b", re.I
)
SEGMENT_PAT = re.compile(r"-\s*93\s*(NB|SB|EB|WB)\b", re.I)


def _shares(cs: List[int], total: int) -> List[float]:
    s = sum(cs)
    if total <= 0 or s <= 0:
        return [0.0, 0.0, 0.0, 0.0]
    # Rescale by actual sum so shares always sum to 1 (handles DQ_SUM_MISMATCH).
    return [c / s for c in cs]


def _epoch_ms_to_iso(v) -> Optional[str]:
    if v in (None, 0, ""):
        return None
    try:
        return datetime.fromtimestamp(int(v) / 1000, tz=timezone.utc).date().isoformat()
    except (ValueError, OverflowError, OSError):
        return None


def normalize_elements(raw: List[dict], cfg: Config) -> List[dict]:
    """Build ElementRow dicts with shares and per-row DQ flags (SPEC §5.3)."""
    # First pass: per-element-number stats for the suspect-all-CS4 rule.
    by_number: Dict[int, List[dict]] = {}
    for r in raw:
        by_number.setdefault(int(r["element_number"]), []).append(r)

    suspect_numbers = _suspect_all_cs4_numbers(by_number)

    rows: List[dict] = []
    for r in raw:
        n = int(r["element_number"])
        epn = r.get("epn")
        epn = int(epn) if epn not in (None, "") else 0
        total = int(r.get("total_quantity") or 0)
        cs = [int(r.get(f"condition_state_{k}") or 0) for k in range(1, 5)]
        flags: List[str] = []

        if sum(cs) != total:
            flags.append("DQ_SUM_MISMATCH")
        if total == 0:
            flags.append("DQ_ZERO_TOTAL")
        if n in suspect_numbers:
            flags.append("DQ_SUSPECT_ALL_CS4")
        if total > 1000 and cs[1] == 0 and cs[2] == 0 and cs[3] > 0:
            flags.append("DQ_BINARY_PATTERN")

        scored = total > 0 and "DQ_ZERO_TOTAL" not in flags
        if "DQ_SUSPECT_ALL_CS4" in flags and not cfg.include_suspect_elements:
            scored = False

        rows.append({
            "key": f"{r['tunnel_number']}|{n}|{epn}",
            "tunnel_number": r["tunnel_number"],
            "element_number": n,
            "epn": epn,
            "total": total,
            "cs": cs,
            "shares": _shares(cs, total),
            "dq_flags": flags,
            "scored": scored,
        })
    return rows


def _suspect_all_cs4_numbers(by_number: Dict[int, List[dict]]) -> set:
    """DQ_SUSPECT_ALL_CS4: single-unit rows ~100% in CS4 across many tunnels (SPEC §5.3)."""
    suspect = set()
    for n, group in by_number.items():
        tunnels = {g["tunnel_number"] for g in group}
        if len(tunnels) < 5:
            continue
        frac = sum(
            1 for g in group
            if int(g.get("total_quantity") or 0) <= 2
            and int(g.get("condition_state_4") or 0) == int(g.get("total_quantity") or 0)
            and int(g.get("total_quantity") or 0) > 0
        ) / len(group)
        if frac >= 0.8:
            suspect.add(n)
    return suspect


def _group_id(name: str) -> str:
    g = DIRECTION_PAT.sub(" ", name or "")
    g = SEGMENT_PAT.sub(" ", g)
    g = re.sub(r"\s+", " ", g).strip().upper()
    return g


def normalize_tunnels(raw: List[dict]) -> List[dict]:
    """Build Tunnel dicts with group_id (SPEC §5.4)."""
    out: List[dict] = []
    for r in raw:
        # Inventory layer keys the tunnel as tunnel_number_i1; the element layer
        # keys it as tunnel_number. They share the same value (the join key).
        tn = r.get("tunnel_number_i1") or r.get("tunnel_number")
        name = (r.get("tunnel_name_i2") or "").strip() or tn
        out.append({
            "tunnel_number": tn,
            "name": name,
            "year_built": r.get("year_built_a1") or 0,
            "year_rehab": r.get("year_rehabilitated_a2") or 0,
            "adt": int(r.get("adt_a4") or 0),
            "adtt": int(r.get("adtt_a5") or 0),
            "length_ft": r.get("tunnel_length_g1") or 0,
            "under_water": int(r.get("under_navigable_waterway_n1") or 0) == 1,
            "lat": r.get("portal_latitude_i13"),
            "lon": r.get("portal_longitude_i14"),
            "last_inspection_date": _epoch_ms_to_iso(r.get("actual_routine_inspection_date_")),
            "inspection_interval_months": r.get("routine_inspection_interval_d3") or 0,
            "group_id": _group_id(name),
        })
    return out


def build_groups(tunnels: List[dict]) -> List[dict]:
    """One marker per group at the mean lat/lon of its segments (SPEC §5.4)."""
    groups: Dict[str, List[dict]] = {}
    for t in tunnels:
        groups.setdefault(t["group_id"], []).append(t)
    out = []
    for gid, segs in groups.items():
        lats = [s["lat"] for s in segs if s["lat"] is not None]
        lons = [s["lon"] for s in segs if s["lon"] is not None]
        out.append({
            "group_id": gid,
            "name": gid,
            "lat": sum(lats) / len(lats) if lats else None,
            "lon": sum(lons) / len(lons) if lons else None,
            "segments": [s["tunnel_number"] for s in segs],
            "adt_max": max((s["adt"] for s in segs), default=0),
        })
    return out


def build_data_notes(element_rows: List[dict], tunnels: List[dict], cfg: Config) -> dict:
    """Counts and examples for each DQ flag (SPEC §5.3)."""
    tunnel_numbers = {t["tunnel_number"] for t in tunnels}
    counts: Dict[str, int] = {}
    examples: Dict[str, List[str]] = {}
    suspect_numbers = set()
    orphans = 0
    for row in element_rows:
        if row["tunnel_number"] not in tunnel_numbers:
            orphans += 1
        for flag in row["dq_flags"]:
            counts[flag] = counts.get(flag, 0) + 1
            examples.setdefault(flag, [])
            if len(examples[flag]) < 3:
                examples[flag].append(row["key"])
            if flag == "DQ_SUSPECT_ALL_CS4":
                suspect_numbers.add(row["element_number"])
    return {
        "flag_counts": counts,
        "flag_examples": examples,
        "orphan_rows": orphans,
        "suspect_elements": {
            "numbers": sorted(suspect_numbers),
            "affected_rows": counts.get("DQ_SUSPECT_ALL_CS4", 0),
            "excluded_by_default": not cfg.include_suspect_elements,
            "explanation": (
                "Some single-unit elements are recorded 100% in condition state 4 in "
                "nearly every Massachusetts tunnel. We treat that as a reporting "
                "convention, not a statewide crisis, and exclude them from scoring by "
                "default. Toggle with include_suspect_elements."
            ),
        },
        "data_year": 2025,
    }
