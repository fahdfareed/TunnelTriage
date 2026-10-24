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
        assert h["n_tunnels"] == 48
        assert h["n_rows"] == 1120

        plan = client.post("/api/plan", json={"budget": 74_000_000}).json()
        assert plan["budget"] == 74_000_000
        assert plan["total_cost_point"] <= 74_000_000 + 1e-6
        assert len(plan["funded"]) > 0
        assert "waiting" in plan
        assert plan["risk_reduction_pct"] >= 0
