"""Validation against a real MassDOT award: contract 130548 (Tunnel Preservation within MHS Tunnels).

Everything here is computed from data/calibration/contract_130548.json, a hand transcription of the
public staff summary and bid tabulation. Unit rates in config.yaml are derived from the awarded prices;
the backtest compares what the model would fund against what MassDOT actually bought.
"""
from __future__ import annotations

import json
import statistics as st
from functools import lru_cache
from typing import Dict, List

from .config import DATA_DIR, Config
from .constants import BUDGET_ANCHORS

CONTRACT_PATH = DATA_DIR / "calibration" / "contract_130548.json"


@lru_cache(maxsize=1)
def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text())


def derive_unit_rates(contract: dict | None = None) -> Dict[str, Dict[str, dict]]:
    """Median awarded (low-bid) unit price per (unit type, tier). light -> cs3, heavy -> cs4."""
    contract = contract or load_contract()
    groups: Dict[str, Dict[str, List[float]]] = {}
    for it in contract["items"]:
        m = it.get("maps_to")
        if m:
            groups.setdefault(m["unit_type"], {}).setdefault(m["tier"], []).append(it["low_bid"])
    return {
        ut: {
            tier: {"median": st.median(v), "min": min(v), "max": max(v), "n": len(v)}
            for tier, v in tiers.items()
        }
        for ut, tiers in groups.items()
    }


def unit_rate_table(cfg: Config, contract: dict | None = None) -> List[dict]:
    derived = derive_unit_rates(contract)
    rows = []
    for ut in ("area/length", "each", "system"):
        for tier, state in (("light", "cs3"), ("heavy", "cs4")):
            d = derived[ut][tier]
            ours = getattr(cfg.unit_cost[ut], state) * cfg.cost_scale
            rows.append({
                "unit_type": ut, "tier": tier, "state": state, "our_rate": ours,
                "observed_median": d["median"], "observed_min": d["min"], "observed_max": d["max"],
                "n_items": d["n"], "ratio": ours / d["median"] if d["median"] else None,
            })
    return rows


def bid_facts(contract: dict | None = None) -> dict:
    c = contract or load_contract()
    low = min(c["bids"].values())
    high = max(c["bids"].values())
    mob = next(i for i in c["items"] if i["item"] == "748")
    pb = c["program_budget"]
    return {
        "office_estimate": c["office_estimate"],
        "low_bid": low,
        "second_bid": high,
        "low_bid_vs_estimate_pct": 100 * (low / c["office_estimate"] - 1),
        "second_bid_vs_estimate_pct": 100 * (high / c["office_estimate"] - 1),
        "program_total": pb["total"],
        "program_over_bid_pct": 100 * (pb["total"] / pb["bid"] - 1),
        "mobilization_low_bid": mob["low_bid"],
        "mobilization_pct_of_bid": 100 * mob["low_bid"] / low,
        "mobilization_two_bid_avg": st.mean([mob["low_bid"], mob["two_bid_avg"]]),
        "bidders_who_bid": c["bidders_who_bid"],
        "eligible_bidders": c["eligible_bidders"],
    }


def contract_spend_by_category(contract: dict | None = None) -> List[dict]:
    c = contract or load_contract()
    cats: Dict[str, float] = {}
    for it in c["items"]:
        cats[it["category"]] = cats.get(it["category"], 0.0) + it["qty"] * it["low_bid"]
    listed = sum(cats.values())
    low = min(c["bids"].values())
    cats["Smaller items (not itemized here)"] = max(0.0, low - listed)
    return sorted(({"category": k, "amount": v} for k, v in cats.items()), key=lambda r: -r["amount"])


def backtest(state) -> dict:
    """Compare the model with the contract at the contract's own price."""
    c = load_contract()
    low_bid = min(c["bids"].values())
    scope = set(c["scope_tunnels"])

    severe, heavy_all = 0.0, 0.0
    sev_rows, best_rows = {}, {}
    for a in state._actions:
        if a["group_id"] not in scope:
            continue
        if a["action"] == "FIX_SEVERE":
            sev_rows[a["row_key"]] = a
        cur = best_rows.get(a["row_key"])
        if cur is None or a["cost_point"] > cur["cost_point"]:
            best_rows[a["row_key"]] = a
    severe = sum(a["cost_point"] for a in sev_rows.values())
    heavy_all = sum(a["cost_point"] for a in best_rows.values())

    plan = state.make_plan(int(low_bid))
    by_group: Dict[str, float] = {}
    for a in plan["funded"]:
        by_group[a["group_id"]] = by_group.get(a["group_id"], 0.0) + a["cost_point"]
    funded_total = sum(by_group.values())
    in_scope = sum(v for k, v in by_group.items() if k in scope)
    ranked = sorted(by_group.items(), key=lambda kv: -kv[1])
    scope_funded = {g: by_group.get(g, 0.0) for g in sorted(scope)}
    top5 = [g for g, _ in ranked[:5]]

    callahan_cats = {"Callahan ceiling system", "Ventilation plenums & ducts"}
    callahan_contract = sum(
        it["qty"] * it["low_bid"] for it in c["items"] if it["category"] in callahan_cats
    )
    # Federal condition ratings for Callahan's ceiling panels (the contract's biggest Callahan item).
    panel_total = panel_good = 0
    for r in state.element_rows:
        t = state.ctx.tunnels.get(r["tunnel_number"], {})
        name = state.dictionary.get(r["element_number"], {}).get("name", "")
        if t.get("group_id") == "CALLAHAN TUNNEL" and "Ceiling Panels" in name:
            panel_total += r["total"]
            panel_good += r["cs"][0]
    cal = state.calibration
    return {
        "backlog_severe_all": cal["backlog_cs4_cost"],
        "backlog_poor_and_severe_all": cal["backlog_cs34_cost"],
        "program_5yr_anchor": BUDGET_ANCHORS["cip_fy27_31_tunnels_total"],
        "need_10yr_anchor": BUDGET_ANCHORS["mhs_10yr_need_2024"],
        "callahan_ceiling_panels_good_pct": 100 * panel_good / panel_total if panel_total else None,
        "callahan_contract_spend": callahan_contract,
        "callahan_model_funded": by_group.get("CALLAHAN TUNNEL", 0.0),
        "contract": {"id": c["contract"], "title": c["title"], "bid_opening": c["bid_opening"],
                     "scope_tunnels": sorted(scope), "low_bid": low_bid},
        "model_cost_severe_only": severe,
        "model_cost_poor_and_severe": heavy_all,
        "severe_only_ratio_to_bid": severe / low_bid,
        "plan_budget": low_bid,
        "plan_funded_total": funded_total,
        "scope_share_of_funded_pct": 100 * in_scope / funded_total if funded_total else 0.0,
        "scope_funded": scope_funded,
        "top5_funded_groups": top5,
        "scope_tunnels_in_top5": sum(1 for g in top5 if g in scope),
        "scope_tunnels_funded": sum(1 for v in scope_funded.values() if v > 0),
        "funded_by_group": [{"group_id": g, "amount": v} for g, v in ranked],
    }


def validation_report(state, cfg: Config) -> dict:
    c = load_contract()
    return {
        "contract": {k: c[k] for k in ("contract", "title", "bid_opening", "source", "scope_tunnels", "items_note")},
        "bid": bid_facts(c),
        "assumed_bid_range": {"low": cfg.bid_vs_estimate.low, "high": cfg.bid_vs_estimate.high},
        "unit_rates": unit_rate_table(cfg, c),
        "spend_by_category": contract_spend_by_category(c),
        "backtest": backtest(state),
        "assumptions": {
            "cost_scale": cfg.cost_scale,
            "mobilization_pct": cfg.mobilization_pct,
            "program_overheads": cfg.program_overheads.model_dump(),
        },
    }
