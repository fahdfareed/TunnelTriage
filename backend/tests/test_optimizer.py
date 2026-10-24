"""SPEC §12 test 4: budget respected, <=1 action/row, monotonic risk, both solvers, forced items."""
import pytest

from app.actions import candidate_actions
from app.optimizer import _solve_greedy, optimize, safety_floor_forced
from app.process import normalize_elements, normalize_tunnels
from app.risk import RiskContext


def _dictionary():
    # Two element types: one structural (crit 4), one fire/life-safety (crit 5).
    return {
        10001: {"element_number": 10001, "name": "Liner", "category": "Structural",
                "unit": "area/length", "criticality": 4, "is_system_element": False, "source": "t"},
        10900: {"element_number": 10900, "name": "Fire system", "category": "Fire/Life Safety/Security",
                "unit": "each", "criticality": 5, "is_system_element": True, "source": "t"},
    }


def _build(cfg):
    inv = [
        {"tunnel_number_i1": "T1", "tunnel_name_i2": "ALPHA TUNNEL", "adt_a4": 80000,
         "under_navigable_waterway_n1": 0, "portal_latitude_i13": 42.3, "portal_longitude_i14": -71.0},
        {"tunnel_number_i1": "T2", "tunnel_name_i2": "BETA TUNNEL", "adt_a4": 40000,
         "under_navigable_waterway_n1": 1, "portal_latitude_i13": 42.4, "portal_longitude_i14": -71.1},
    ]

    def er(tn, n, total, cs):
        return {"tunnel_number": tn, "element_number": n, "epn": None, "total_quantity": total,
                "condition_state_1": cs[0], "condition_state_2": cs[1],
                "condition_state_3": cs[2], "condition_state_4": cs[3]}

    raw = [
        er("T1", 10001, 1000, [600, 200, 120, 80]),
        er("T1", 10900, 4, [1, 0, 0, 3]),
        er("T2", 10001, 2000, [1500, 300, 150, 50]),
    ]
    tunnels = normalize_tunnels(inv)
    rows = normalize_elements(raw, cfg)
    ctx = RiskContext(tunnels, rows, _dictionary(), cfg)
    rows_by_key = {r["key"]: r for r in rows}
    for r in rows:
        r["_risk_now"] = ctx.row_risk(r) if r["scored"] else 0.0
    actions = candidate_actions(ctx, rows, cfg)
    return ctx, rows, rows_by_key, actions


def test_cost_within_budget_and_one_action_per_row(cfg):
    ctx, rows, rbk, actions = _build(cfg)
    budget = 10_000_000
    plan = optimize(actions, ctx, rbk, cfg, budget)
    assert plan["total_cost_point"] <= budget + 1e-6
    seen = {}
    for item in plan["funded"]:
        a = next(a for a in actions if a["action_id"] == item["action_id"])
        seen[a["row_key"]] = seen.get(a["row_key"], 0) + 1
    assert all(c <= 1 for c in seen.values())


def _build_large(cfg):
    """A bigger fixture (many rows across several tunnels) so CP-SAT engages."""
    import random
    rng = random.Random(7)
    inv, raw = [], []

    def er(tn, n, total, cs):
        return {"tunnel_number": tn, "element_number": n, "epn": None, "total_quantity": total,
                "condition_state_1": cs[0], "condition_state_2": cs[1],
                "condition_state_3": cs[2], "condition_state_4": cs[3]}

    for ti in range(6):
        tn = f"T{ti}"
        inv.append({"tunnel_number_i1": tn, "tunnel_name_i2": f"TUNNEL {ti}",
                    "adt_a4": rng.randint(20000, 90000), "under_navigable_waterway_n1": ti % 2,
                    "portal_latitude_i13": 42.3 + ti * 0.01, "portal_longitude_i14": -71.0})
        for r in range(8):
            total = rng.randint(200, 3000)
            cs4 = rng.randint(0, total // 10)
            cs3 = rng.randint(0, total // 8)
            cs2 = rng.randint(0, total // 6)
            raw.append(er(tn, 10001, total, [total - cs2 - cs3 - cs4, cs2, cs3, cs4]))

    tunnels = normalize_tunnels(inv)
    rows = normalize_elements(raw, cfg)
    ctx = RiskContext(tunnels, rows, _dictionary(), cfg)
    rbk = {r["key"]: r for r in rows}
    for r in rows:
        r["_risk_now"] = ctx.row_risk(r) if r["scored"] else 0.0
    actions = candidate_actions(ctx, rows, cfg)
    return ctx, rows, rbk, actions


def test_monotonic_risk_vs_budget(cfg):
    ctx, rows, rbk, actions = _build_large(cfg)
    prev = None
    saw_cpsat = False
    for budget in [0, 10_000_000, 25_000_000, 50_000_000, 74_000_000, 150_000_000]:
        plan = optimize(actions, ctx, rbk, cfg, budget)
        if plan["solver"] != "cp-sat":
            pytest.skip("CP-SAT unavailable; monotonicity not guaranteed for greedy")
        saw_cpsat = True
        if prev is not None:
            assert plan["risk_h_with_plan"] <= prev + 1e-6
        prev = plan["risk_h_with_plan"]
    assert saw_cpsat


def test_both_solvers_run(cfg):
    ctx, rows, rbk, actions = _build(cfg)
    greedy = _solve_greedy(actions, 10_000_000, cfg.fixed_mobilization_per_tunnel, set())
    assert greedy["solver"] == "greedy"
    plan = optimize(actions, ctx, rbk, cfg, 10_000_000)
    assert plan["solver"] in ("cp-sat", "greedy")


def test_forced_items_included_when_they_fit(cfg):
    ctx, rows, rbk, actions = _build(cfg)
    forced = safety_floor_forced(actions, ctx, rbk, cfg)
    # The fire system row (crit 5, share4 = 0.75) must be forced.
    assert any("10900" in aid and "FIX_SEVERE" in aid for aid in forced)
    plan = optimize(actions, ctx, rbk, cfg, 100_000_000)
    funded_ids = {i["action_id"] for i in plan["funded"]}
    assert forced.issubset(funded_ids)
    assert plan["forced_unmet"] == []
