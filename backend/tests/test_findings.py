"""SPEC §12 test 5: quantity conserved, no negative states, create-on-missing, reset."""
from app.findings import apply_finding, new_finding, parse_text


def _row(key, cs):
    return {"key": key, "tunnel_number": key.split("|")[0],
            "element_number": int(key.split("|")[1]), "epn": 0,
            "total": sum(cs), "cs": list(cs), "shares": [0, 0, 0, 0],
            "dq_flags": [], "scored": sum(cs) > 0}


def test_total_quantity_conserved_and_no_negative():
    rbk = {"T1|10001|0": _row("T1|10001|0", [70, 20, 8, 2])}
    before_total = rbk["T1|10001|0"]["total"]
    f = new_finding({"tunnel_number": "T1", "element_number": 10001,
                     "quantity": 50, "condition_state": 4})
    _, row = apply_finding(rbk, f)
    assert row["total"] == before_total        # conserved
    assert all(c >= 0 for c in row["cs"])       # no negatives
    assert row["cs"][3] >= 2                     # CS4 grew


def test_cap_at_available():
    # Ask to move more than exists in other states; capped, total still conserved.
    rbk = {"T1|10001|0": _row("T1|10001|0", [5, 0, 0, 0])}
    f = new_finding({"tunnel_number": "T1", "element_number": 10001,
                     "quantity": 999, "condition_state": 4})
    _, row = apply_finding(rbk, f)
    assert row["total"] == 5
    assert row["cs"][3] == 5
    assert all(c >= 0 for c in row["cs"])


def test_finding_on_missing_row_creates_it():
    rbk = {}
    f = new_finding({"tunnel_number": "T9", "element_number": 10200,
                     "quantity": 12, "condition_state": 4})
    key, row = apply_finding(rbk, f)
    assert key in rbk
    assert row["cs"][3] == 12
    assert "NEW_FROM_FINDING" in row["dq_flags"]


def test_parse_text_heuristic_no_llm(cfg):
    tunnels = [{"tunnel_number": "B16T37SUMDOTV10", "name": "SUMNER TUNNEL",
                "group_id": "SUMNER TUNNEL"}]
    dictionary = {10061: {"element_number": 10061, "name": "Element 10061",
                          "category": "Unknown", "unit": "area/length", "criticality": 3,
                          "is_system_element": False, "source": "fallback"}}
    out = parse_text("active leak with spalling, 1500 SF on Sumner element 10061",
                     tunnels, dictionary, cfg)
    assert out["used_llm"] is False
    assert out["proposal"]["condition_state"] == 4  # "spalling"/"leak" -> severe words
    assert out["proposal"]["quantity"] == 1500
    assert out["proposal"]["tunnel_number"] == "B16T37SUMDOTV10"


def test_parse_quantity_skips_element_number(cfg):
    # When the element number appears before the quantity, don't treat it as qty.
    tunnels = [{"tunnel_number": "B16T37SUMDOTV10", "name": "SUMNER TUNNEL",
                "group_id": "SUMNER TUNNEL"}]
    dictionary = {10061: {"element_number": 10061, "name": "Element 10061",
                          "category": "Unknown", "unit": "area/length", "criticality": 3,
                          "is_system_element": False, "source": "fallback"}}
    out = parse_text("element 10061 on Sumner, 1500 SF severe", tunnels, dictionary, cfg)
    assert out["proposal"]["quantity"] == 1500
    assert out["proposal"]["element_number"] == 10061
