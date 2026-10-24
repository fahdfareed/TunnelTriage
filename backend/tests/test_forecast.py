"""SPEC §12 test 3: P rows sum to 1, share4 non-decreasing, shares conserved."""
from app.forecast import forecast_shares, transition_matrix


def test_transition_rows_sum_to_one(cfg):
    for rates in (cfg.transition["default"], cfg.transition["system"]):
        P = transition_matrix(rates)
        for row in P:
            assert abs(sum(row) - 1.0) < 1e-12


def test_share4_non_decreasing_and_shares_conserved(cfg):
    P = transition_matrix(cfg.transition["default"])
    series = forecast_shares([0.7, 0.2, 0.08, 0.02], P, 10)
    prev4 = -1.0
    for s in series:
        assert abs(sum(s) - 1.0) < 1e-9
        assert s[3] >= prev4 - 1e-12
        prev4 = s[3]
