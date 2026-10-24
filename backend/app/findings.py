"""Findings intake: apply structured findings and parse free text (SPEC §8).

Findings are stored in memory and applied on top of the base element rows.
Total quantity is always conserved; no condition state goes negative.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from rapidfuzz import fuzz, process

from .config import Config
from .llm import complete

log = logging.getLogger(__name__)

SEVERE_WORDS = ["severe", "failed", "falling", "loose", "exposed rebar", "spall"]


def new_finding(data: dict) -> dict:
    return {
        "finding_id": str(uuid.uuid4()),
        "tunnel_number": data["tunnel_number"],
        "element_number": int(data["element_number"]),
        "epn": int(data.get("epn") or 0),
        "quantity": int(data["quantity"]),
        "condition_state": int(data["condition_state"]),
        "source": data.get("source", "simulated"),
        "note": (data.get("note") or "")[:280],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def apply_finding(rows_by_key: Dict[str, dict], finding: dict) -> Tuple[str, dict]:
    """Move `quantity` into the target state from the best states first (SPEC §8.1).

    Creates the row if missing. Total quantity is conserved; states never go negative.
    Returns (row_key, mutated_row).
    """
    key = f"{finding['tunnel_number']}|{finding['element_number']}|{finding['epn']}"
    target = finding["condition_state"]  # 3 or 4
    qty = finding["quantity"]

    row = rows_by_key.get(key)
    if row is None:
        # New row: all quantity starts in the target state (SPEC §8.1).
        cs = [0, 0, 0, 0]
        cs[target - 1] = qty
        row = {
            "key": key,
            "tunnel_number": finding["tunnel_number"],
            "element_number": finding["element_number"],
            "epn": finding["epn"],
            "total": qty,
            "cs": cs,
            "shares": _shares(cs),
            "dq_flags": ["NEW_FROM_FINDING"],
            "scored": qty > 0,
        }
        rows_by_key[key] = row
        return key, row

    cs = list(row["cs"])
    ti = target - 1
    remaining = min(qty, sum(cs) - cs[ti])  # cap at what can be moved from other states
    # Pull from the best (lowest-index) states first, but not from the target itself.
    for si in range(0, 4):
        if remaining <= 0:
            break
        if si == ti:
            continue
        move = min(cs[si], remaining)
        cs[si] -= move
        cs[ti] += move
        remaining -= move

    row["cs"] = cs
    row["total"] = sum(cs)
    row["shares"] = _shares(cs)
    if "NEW_FROM_FINDING" not in row["dq_flags"]:
        row["dq_flags"] = list(row["dq_flags"])
    row["scored"] = row["total"] > 0 and "DQ_ZERO_TOTAL" not in row["dq_flags"]
    return key, row


def _shares(cs: List[int]) -> List[float]:
    s = sum(cs)
    return [c / s for c in cs] if s > 0 else [0.0, 0.0, 0.0, 0.0]


# ---- Free-text parsing (SPEC §8.2) ----

def _candidates(text: str, tunnels: List[dict], dictionary: Dict[int, dict]) -> Tuple[List[dict], List[dict]]:
    names = {}
    for t in tunnels:
        names[t["name"]] = t["tunnel_number"]
        names.setdefault(t["group_id"], t["tunnel_number"])
    tunnel_hits = process.extract(text, list(names.keys()), scorer=fuzz.partial_ratio, limit=3)
    tunnel_candidates = [
        {"tunnel_number": names[name], "label": name, "score": score}
        for name, score, _ in tunnel_hits
    ]

    is_fallback = all(d["source"] == "fallback" for d in dictionary.values())
    element_candidates: List[dict] = []
    if is_fallback:
        for m in re.findall(r"\b(1\d{4})\b", text):
            n = int(m)
            if n in dictionary:
                element_candidates.append({"element_number": n, "label": dictionary[n]["name"], "score": 100})
        element_candidates = element_candidates[:3]
    else:
        name_to_num = {d["name"]: n for n, d in dictionary.items()}
        el_hits = process.extract(text, list(name_to_num.keys()), scorer=fuzz.partial_ratio, limit=3)
        element_candidates = [
            {"element_number": name_to_num[name], "label": name, "score": score}
            for name, score, _ in el_hits
        ]
    return tunnel_candidates, element_candidates


def _heuristic_proposal(text: str, tc: List[dict], ec: List[dict]) -> dict:
    nums = [int(n) for n in re.findall(r"\b(\d+)\b", text)]
    # Don't mistake a 5-digit element number for the quantity: prefer the first
    # number that isn't a candidate element number (SPEC §8.2 step 3, refined).
    element_nums = {c["element_number"] for c in ec}
    quantity = next((n for n in nums if n not in element_nums), None)
    if quantity is None:
        quantity = nums[0] if nums else 1
    state = 4 if any(w in text.lower() for w in SEVERE_WORDS) else 3
    return {
        "tunnel_number": tc[0]["tunnel_number"] if tc else None,
        "element_number": ec[0]["element_number"] if ec else None,
        "quantity": quantity,
        "condition_state": state,
        "note": text[:280],
    }


def parse_text(text: str, tunnels: List[dict], dictionary: Dict[int, dict], cfg: Config) -> dict:
    """Propose a finding from free text. Never applies it (SPEC §8.2)."""
    tc, ec = _candidates(text, tunnels, dictionary)
    used_llm = False
    proposal = _heuristic_proposal(text, tc, ec)

    if cfg.llm.provider != "none" and tc and ec:
        system = (
            "You extract a single tunnel defect finding from text. Respond with JSON only: "
            '{"tunnel_number","element_number","quantity","condition_state","note"}. '
            "Choose tunnel_number and element_number ONLY from the provided candidates. "
            "condition_state is 3 (poor) or 4 (severe)."
        )
        user = json.dumps({
            "text": text,
            "tunnel_candidates": tc,
            "element_candidates": ec,
        })
        raw = complete(system, user)
        parsed = _validate_llm(raw, tc, ec)
        if parsed:
            proposal = parsed
            used_llm = True

    return {
        "proposal": proposal,
        "tunnel_candidates": tc,
        "element_candidates": ec,
        "used_llm": used_llm,
    }


def _validate_llm(raw: Optional[str], tc: List[dict], ec: List[dict]) -> Optional[dict]:
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        obj = json.loads(m.group(0) if m else raw)
        tn = obj.get("tunnel_number")
        en = int(obj.get("element_number"))
        if tn not in {c["tunnel_number"] for c in tc}:
            return None
        if en not in {c["element_number"] for c in ec}:
            return None
        state = int(obj.get("condition_state"))
        if state not in (3, 4):
            return None
        return {
            "tunnel_number": tn,
            "element_number": en,
            "quantity": int(obj.get("quantity") or 1),
            "condition_state": state,
            "note": (obj.get("note") or "")[:280],
        }
    except Exception:
        return None
