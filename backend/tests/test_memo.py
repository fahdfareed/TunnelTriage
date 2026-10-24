"""SPEC §12 test 6: number guard rejects fabricated numbers; template has 5 headings."""
from app.memo import check_numbers, template_memo


def _facts():
    return {
        "budget": 74_000_000, "solver": "cp-sat",
        "total_cost_point": 72_000_000, "total_cost_low": 49_000_000,
        "total_cost_high": 97_000_000, "risk_now": 29251,
        "risk_h_do_nothing": 39016, "risk_h_with_plan": 6897,
        "risk_reduction_pct": 82.3, "horizon": 5,
        "cost_of_waiting": {"cost_increase_pct": 15.0, "extra_risk_2y": 1234},
        "top_funded": [
            {"tunnel_name": "TED WILLIAMS TUNNEL", "element_number": 10132,
             "element_name": "Element 10132", "action": "FIX_SEVERE", "qty": 20,
             "cost_low": 100000, "cost_high": 200000, "reason_codes": ["HIGH_CS4_SHARE"]},
        ],
        "top_unfunded": [
            {"tunnel_name": "SUMNER TUNNEL", "element_number": 10061,
             "element_name": "Element 10061", "benefit": 500},
        ],
        "forced_unmet_count": 0, "findings_applied": 1,
        "assumptions": {"dictionary_source": "fallback", "costs_are_placeholders": True,
                        "deterioration_not_calibrated": True},
        "anchors": {"cip_fy27_31_tunnels_per_year": 74_000_000},
    }


def test_number_guard_rejects_fabricated():
    facts = _facts()
    bad = check_numbers("We recommend spending $999M immediately.", facts)
    assert any("999" in b for b in bad)


def test_number_guard_accepts_facts():
    facts = _facts()
    text = "Budget is $74.0M and risk falls 82.3% by 2030."
    assert check_numbers(text, facts) == []


def test_template_has_five_sections():
    md = template_memo(_facts())
    for heading in ("## 1.", "## 2.", "## 3.", "## 4.", "## 5."):
        assert heading in md
