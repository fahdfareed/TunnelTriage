"""SPEC §12 test 1: pagination, shares, DQ_SUSPECT_ALL_CS4, group_id."""
from app.fetch import fetch_all
from app.process import _group_id, normalize_elements


class FakeResp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


def test_pagination_stops_on_transfer_limit_false(monkeypatch):
    pages = [
        {"features": [{"attributes": {"OBJECTID": i}} for i in range(1000)],
         "exceededTransferLimit": True},
        {"features": [{"attributes": {"OBJECTID": i}} for i in range(120)],
         "exceededTransferLimit": False},
    ]
    calls = {"n": 0}

    def fake_get(url, params, timeout):
        p = pages[calls["n"]]
        calls["n"] += 1
        return FakeResp(p)

    monkeypatch.setattr("app.fetch.requests.get", fake_get)
    rows = fetch_all("http://x", "state='25'")
    assert len(rows) == 1120
    assert calls["n"] == 2


def _raw(tn, n, total, cs):
    return {
        "tunnel_number": tn, "element_number": n, "epn": None,
        "total_quantity": total,
        "condition_state_1": cs[0], "condition_state_2": cs[1],
        "condition_state_3": cs[2], "condition_state_4": cs[3],
    }


def test_shares_sum_to_one_when_total_positive(cfg):
    rows = normalize_elements([_raw("T1", 10001, 100, [70, 20, 5, 5])], cfg)
    assert abs(sum(rows[0]["shares"]) - 1.0) < 1e-9


def test_sum_mismatch_rescales(cfg):
    # cs sums to 90 but total says 100 -> shares rescale by 90, still sum to 1.
    rows = normalize_elements([_raw("T1", 10001, 100, [60, 20, 5, 5])], cfg)
    assert "DQ_SUM_MISMATCH" in rows[0]["dq_flags"]
    assert abs(sum(rows[0]["shares"]) - 1.0) < 1e-9


def test_suspect_all_cs4_flagged_and_excluded(cfg):
    # Element 10750: single-unit, 100% CS4, across 6 tunnels -> suspect, excluded.
    raw = [_raw(f"T{i}", 10750, 1, [0, 0, 0, 1]) for i in range(6)]
    rows = normalize_elements(raw, cfg)
    assert all("DQ_SUSPECT_ALL_CS4" in r["dq_flags"] for r in rows)
    assert all(r["scored"] is False for r in rows)


def test_group_id_strips_direction():
    assert _group_id("TED WILLIAMS TUNNEL WESTBOUND") == _group_id("TED WILLIAMS TUNNEL EASTBOUND")
    assert _group_id("TED WILLIAMS TUNNEL WESTBOUND") == "TED WILLIAMS TUNNEL"
