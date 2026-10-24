"""Smoke tests: config loads with all §7 keys; health + /plan via TestClient."""
from fastapi.testclient import TestClient

from app.config import get_config
from app.main import app


def test_config_has_spec_keys():
    cfg = get_config()
    for key in ("state_fips", "include_suspect_elements", "weights", "underwater_multiplier",
                "size_factor_clip", "horizon_years", "forecast_years", "transition",
                "category_transition_group", "criticality_by_category", "unit_cost",
                "cost_scale", "fixed_mobilization_per_tunnel", "bid_vs_estimate",
                "safety_floor", "budget_slider", "llm"):
        assert hasattr(cfg, key)


def test_health_and_plan_end_to_end():
    with TestClient(app) as client:
        h = client.get("/api/health").json()
        assert h["ok"] is True
        assert h["n_tunnels"] == 47
        assert h["n_rows"] == 1106

        plan = client.post("/api/plan", json={"budget": 74_000_000}).json()
        assert plan["budget"] == 74_000_000
        assert plan["total_cost_point"] <= 74_000_000 + 1e-6
        assert len(plan["funded"]) > 0
        assert "waiting" in plan
        assert plan["risk_reduction_pct"] >= 0

        # Memo from the cached plan.
        memo = client.post("/api/memo", json={"plan_id": plan["plan_id"]}).json()
        assert memo["source"] in ("llm", "template")
        assert "## 1." in memo["markdown"]

        # Findings: add -> re-plan reflects it -> reset.
        client.delete("/api/findings")
        add = client.post("/api/findings", json={
            "tunnel_number": "B16T30TWEDOTTE1", "element_number": 10132,
            "quantity": 20, "condition_state": 4, "source": "simulated",
            "note": "test"}).json()
        assert "finding" in add
        assert len(client.get("/api/findings").json()) == 1
        fid = add["finding"]["finding_id"]
        assert client.delete(f"/api/findings/{fid}").json()["ok"] is True
        assert client.get("/api/findings").json() == []

        # Free-text parse never auto-applies.
        parsed = client.post("/api/findings/parse", json={
            "text": "section loss on Ted Williams element 10132, 20 SF, severe"}).json()
        assert "proposal" in parsed
        assert parsed["used_llm"] is False


def test_greater_boston_scope():
    """Demo scope is Greater Boston only (state.GB_LAT / GB_LON); Fall River is dropped."""
    from app.state import GB_LAT, GB_LON, STATE
    STATE.load()
    assert STATE.tunnels
    for t in STATE.tunnels:
        assert GB_LAT[0] <= t["lat"] <= GB_LAT[1]
        assert GB_LON[0] <= t["lon"] <= GB_LON[1]
    assert "F02T46FCHMUN000" not in {t["tunnel_number"] for t in STATE.tunnels}
    assert {r["tunnel_number"] for r in STATE.element_rows} <= {t["tunnel_number"] for t in STATE.tunnels}


def test_config_serves_slider():
    with TestClient(app) as client:
        s = client.get("/api/config").json()["budget_slider"]
        assert s["min"] == 0 and s["max"] == 50_000_000


def test_curve_is_monotone():
    with TestClient(app) as client:
        c = client.get("/api/curve").json()
        pts = [p["risk_now_after"] for p in c["points"]]
        assert len(pts) == 51
        assert pts[0] <= c["risk_now"] + 1e-6
        assert all(a >= b - 1e-6 for a, b in zip(pts, pts[1:])) or pts[-1] < pts[0]


def test_validation_report_against_contract_130548():
    with TestClient(app) as client:
        v = client.get("/api/validation").json()
        assert v["bid"]["low_bid"] == 52_182_001.0
        assert abs(v["bid"]["low_bid_vs_estimate_pct"] - 24.62) < 0.05
        # Program budget in the staff summary is bid + 15% + 5% + traffic police (~4%).
        assert abs(v["bid"]["program_over_bid_pct"] - 24.04) < 0.05
        # Unit rates in config.yaml are the derived medians (ratio 1.0 by construction).
        assert all(abs(r["ratio"] - 1.0) < 0.01 for r in v["unit_rates"])
        b = v["backtest"]
        assert b["scope_tunnels_funded"] == 4
        assert 90 < b["callahan_ceiling_panels_good_pct"] <= 100
        assert 0.025 < v["assumptions"]["mobilization_pct"] < 0.035
        # Independent bracket: the full severe backlog sits between the 5-year tunnels program
        # and the 10-year need for the whole system (all asset types).
        assert b["program_5yr_anchor"] < b["backlog_severe_all"] < b["need_10yr_anchor"]


def test_plan_includes_program_cost():
    with TestClient(app) as client:
        p = client.post("/api/plan", json={"budget": 10_000_000}).json()
        assert abs(p["program_cost_point"] / p["total_cost_point"] - 1.24) < 0.001
