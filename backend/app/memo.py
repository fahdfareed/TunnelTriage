"""Board memo: LLM with a number guard, deterministic template fallback (SPEC §9)."""
from __future__ import annotations

import re
from typing import List

from .llm import complete

SYSTEM_PROMPT = (
    "You write a one-page memo for a state DOT tunnel engineer to take to a capital "
    "programming committee. Use ONLY numbers and names present in the FACTS JSON. Do not "
    "add any number that is not in FACTS. Say clearly that unit costs and deterioration "
    "rates are planning assumptions. Structure: 1) Recommendation (2 sentences). 2) What "
    "this budget funds (bullets). 3) What it leaves unfunded and the risk of waiting. "
    "4) Safety-critical items. 5) Assumptions and data notes. Under 350 words. Plain language."
)


def build_facts(plan: dict, waiting: dict, findings: List[dict], anchors: dict, dictionary_source: str) -> dict:
    """The only data the memo may use (SPEC §9)."""
    return {
        "budget": plan["budget"],
        "solver": plan["solver"],
        "total_cost_point": round(plan["total_cost_point"]),
        "total_cost_low": round(plan["total_cost_low"]),
        "total_cost_high": round(plan["total_cost_high"]),
        "risk_now": round(plan["risk_now"]),
        "risk_h_do_nothing": round(plan["risk_h_do_nothing"]),
        "risk_h_with_plan": round(plan["risk_h_with_plan"]),
        "risk_reduction_pct": round(plan["risk_reduction_pct"], 1),
        "horizon": plan["horizon"],
        "cost_of_waiting": {
            "cost_increase_pct": round(waiting["cost_increase_pct"], 1),
            "extra_risk_2y": round(waiting["extra_risk_2y"]),
        },
        "top_funded": [
            {
                "tunnel_name": i["tunnel_name"], "element_number": i["element_number"],
                "element_name": i["element_name"], "action": i["action"], "qty": i["qty"],
                "cost_low": round(i["cost_low"]), "cost_high": round(i["cost_high"]),
                "reason_codes": i["reason_codes"],
            }
            for i in plan["funded"][:8]
        ],
        "top_unfunded": [
            {"tunnel_name": i["tunnel_name"], "element_number": i["element_number"],
             "element_name": i["element_name"], "benefit": round(i["benefit"])}
            for i in plan["unfunded_top"][:5]
        ],
        "forced_unmet_count": len(plan["forced_unmet"]),
        "findings_applied": len(findings),
        "assumptions": {
            "dictionary_source": dictionary_source,
            "costs_are_placeholders": True,
            "deterioration_not_calibrated": True,
        },
        "anchors": anchors,
    }


# ---- Number guard (SPEC §9) ----

_NUM = re.compile(r"\d[\d,]*\.?\d*")


def _collect_numbers(obj) -> set:
    nums = set()

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v)
        elif isinstance(x, bool):
            pass
        elif isinstance(x, (int, float)):
            nums.add(round(float(x), 1))
            nums.add(round(float(x) / 1e6, 1))  # $X.YM form
            nums.add(round(float(x) / 1e3, 1))  # $X.YK form
        elif isinstance(x, str):
            for m in _NUM.findall(x):
                try:
                    nums.add(round(float(m.replace(",", "")), 1))
                except ValueError:
                    pass

    walk(obj)
    return nums


def _normalize_token(tok: str) -> float | None:
    t = tok.strip().replace(",", "").replace("$", "").replace("%", "")
    mult = 1.0
    if t.lower().endswith("m"):
        mult = 1.0  # value already expressed in millions by the writer
        t = t[:-1]
    elif t.lower().endswith("k"):
        mult = 1.0
        t = t[:-1]
    try:
        return round(float(t) * mult, 1)
    except ValueError:
        return None


def check_numbers(text: str, facts: dict) -> List[str]:
    """Return a list of unverified numbers found in the memo (SPEC §9)."""
    allowed = _collect_numbers(facts)
    bad: List[str] = []
    # Tolerant match: allow rounding to 1 decimal.
    for raw in re.findall(r"\$?\d[\d,]*\.?\d*\s*[MmKk%]?", text):
        val = _normalize_token(raw)
        if val is None:
            continue
        # Years and list numbering are allowed (SPEC §9).
        if 2018 <= val <= 2035 and val == int(val):
            continue
        if 1 <= val <= 10 and val == int(val):
            continue
        if any(abs(val - a) <= 0.1 for a in allowed):
            continue
        bad.append(raw.strip())
    return bad


# ---- Template fallback (SPEC §9) ----

def _m(n: float) -> str:
    return f"${n / 1e6:.1f}M"


def template_memo(facts: dict) -> str:
    f = facts
    funded = "\n".join(
        f"- {i['tunnel_name']}: element {i['element_number']} ({i['element_name']}), "
        f"{i['action']}, qty {i['qty']}, est. {_m(i['cost_low'])}-{_m(i['cost_high'])}"
        for i in f["top_funded"]
    ) or "- (no items funded at this budget)"
    unfunded = "\n".join(
        f"- {i['tunnel_name']}: element {i['element_number']} ({i['element_name']})"
        for i in f["top_unfunded"]
    ) or "- (none)"
    return f"""# Tunnel repair funding recommendation

## 1. Recommendation
With a budget of {_m(f['budget'])}, fund the plan below to cut modeled {f['horizon']}-year
risk by {f['risk_reduction_pct']}% (from {f['risk_h_do_nothing']} to {f['risk_h_with_plan']} risk points).
Estimated cost is {_m(f['total_cost_low'])}-{_m(f['total_cost_high'])} (point estimate {_m(f['total_cost_point'])}).

## 2. What this budget funds
{funded}

## 3. What it leaves unfunded and the risk of waiting
Top unfunded items by benefit:
{unfunded}
Waiting 2 years raises repair cost about {f['cost_of_waiting']['cost_increase_pct']}% and
absorbs {f['cost_of_waiting']['extra_risk_2y']} risk-point-years of exposure (excludes inflation).

## 4. Safety-critical items
Safety-floor items not covered by this budget: {f['forced_unmet_count']}.
Current statewide risk index: {f['risk_now']} risk points.

## 5. Assumptions and data notes
Unit costs are planning placeholders, not MassDOT costs. Deterioration rates are default
(not calibrated). Element names source: {f['assumptions']['dictionary_source']}.
Solver: {f['solver']}. Findings applied in this scenario: {f['findings_applied']}.
Planning tool using public FHWA data and stated assumptions. Not an engineering assessment.
"""


def generate_memo(facts: dict) -> dict:
    user = __import__("json").dumps(facts)
    raw = complete(SYSTEM_PROMPT, user)
    if raw:
        bad = check_numbers(raw, facts)
        if not bad:
            return {"markdown": raw, "source": "llm", "warnings": []}
        return {
            "markdown": template_memo(facts),
            "source": "template",
            "warnings": ["LLM output contained unverified numbers; template used"],
        }
    return {"markdown": template_memo(facts), "source": "template", "warnings": []}
