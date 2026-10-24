"""SPEC §12 test 2: risk zeros, criticality scaling, underwater multiplier."""
from app.risk import exposure, likelihood, risk_from_shares


def test_risk_zero_when_no_poor_or_severe(cfg):
    shares = [0.9, 0.1, 0.0, 0.0]
    assert likelihood(shares, cfg) == 0.0
    assert risk_from_shares(shares, 4, 1.0, 1.0, cfg) == 0.0


def test_risk_doubles_when_criticality_doubles(cfg):
    shares = [0.0, 0.0, 0.3, 0.2]
    r1 = risk_from_shares(shares, 2, 1.0, 1.0, cfg)
    r2 = risk_from_shares(shares, 4, 1.0, 1.0, cfg)
    assert abs(r2 - 2 * r1) < 1e-9


def test_underwater_multiplier_applied(cfg):
    dry = exposure({"adt": 50000, "under_water": False}, 100000, cfg)
    wet = exposure({"adt": 50000, "under_water": True}, 100000, cfg)
    assert abs(wet - dry * cfg.underwater_multiplier) < 1e-9
