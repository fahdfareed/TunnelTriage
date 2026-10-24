"""FastAPI app: read routes + /plan (SPEC §10, Phases 0-4 scope)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_config
from .constants import ANCHOR_LABELS, BUDGET_ANCHORS, DATA_YEAR, SOURCES
from .findings import new_finding, parse_text
from .forecast import tunnel_risk_series
from .memo import build_facts, generate_memo
from .schemas import FindingRequest, MemoRequest, ParseRequest, PlanRequest
from .state import STATE


@asynccontextmanager
async def lifespan(app: FastAPI):
    STATE.load()
    yield


app = FastAPI(title="TunnelTriage", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    cfg = get_config()
    return {
        "ok": STATE.loaded,
        "data_year": DATA_YEAR,
        "n_tunnels": len(STATE.tunnels),
        "n_rows": len(STATE.element_rows),
        "n_scored_rows": STATE.n_scored() if STATE.loaded else 0,
        "dictionary_source": STATE.dictionary_source() if STATE.loaded else "none",
        "llm_provider": cfg.llm.provider,
    }


def _require_loaded() -> None:
    if not STATE.loaded:
        raise HTTPException(503, "Data not loaded. Run scripts/build_data.py.")


@app.get("/api/tunnels")
def tunnels() -> list:
    _require_loaded()
    out = []
    for t in STATE.tunnels:
        risk = sum(r["_risk_now"] for r in STATE.element_rows
                   if r["tunnel_number"] == t["tunnel_number"] and r["scored"])
        out.append({**t, "risk_now": risk})
    return out


@app.get("/api/groups")
def groups() -> list:
    _require_loaded()
    from .process import build_groups
    base = build_groups(STATE.tunnels)
    risk_by_group: dict = {}
    for r in STATE.element_rows:
        if not r["scored"]:
            continue
        t = STATE.ctx.tunnels.get(r["tunnel_number"], {})
        gid = t.get("group_id", "")
        risk_by_group[gid] = risk_by_group.get(gid, 0.0) + r["_risk_now"]
    for g in base:
        g["risk_now"] = risk_by_group.get(g["group_id"], 0.0)
    return base


@app.get("/api/tunnels/{tunnel_number}")
def tunnel_detail(tunnel_number: str) -> dict:
    _require_loaded()
    tunnel = next((t for t in STATE.tunnels if t["tunnel_number"] == tunnel_number), None)
    if not tunnel:
        raise HTTPException(404, "tunnel not found")
    elements = []
    for r in STATE.element_rows:
        if r["tunnel_number"] != tunnel_number:
            continue
        d = STATE.dictionary.get(r["element_number"], {})
        elements.append({
            "key": r["key"], "element_number": r["element_number"], "epn": r["epn"],
            "total": r["total"], "cs": r["cs"], "shares": r["shares"],
            "dq_flags": r["dq_flags"], "scored": r["scored"],
            "element_name": d.get("name", f"Element {r['element_number']}"),
            "category": d.get("category", "Unknown"),
            "criticality": d.get("criticality", 3),
            "risk_now": r.get("_risk_now", 0.0),
        })
    forecast = tunnel_risk_series(STATE.ctx, STATE.element_rows, tunnel_number,
                                  STATE.cfg, STATE.cfg.forecast_years)
    return {"tunnel": tunnel, "elements": elements, "forecast": forecast}


@app.get("/api/dictionary")
def dictionary() -> list:
    _require_loaded()
    return [STATE.dictionary[n] for n in sorted(STATE.dictionary)]


@app.get("/api/data-notes")
def data_notes() -> dict:
    _require_loaded()
    return {**STATE.data_notes, "calibration": STATE.calibration}


@app.get("/api/config")
def config() -> dict:
    return get_config().model_dump()


@app.get("/api/constants")
def constants() -> dict:
    return {
        "anchors": BUDGET_ANCHORS,
        "labels": ANCHOR_LABELS,
        "sources": SOURCES,
    }


@app.post("/api/plan")
def plan(req: PlanRequest) -> dict:
    _require_loaded()
    return STATE.make_plan(req.budget, req.horizon)


# ---- Findings (SPEC §8) ----

@app.get("/api/findings")
def list_findings() -> list:
    _require_loaded()
    return STATE.findings


@app.post("/api/findings")
def add_finding(req: FindingRequest) -> dict:
    _require_loaded()
    finding = new_finding(req.model_dump())
    affected_row_key = STATE.add_finding(finding)
    return {"finding": finding, "affected_row_key": affected_row_key}


@app.delete("/api/findings/{finding_id}")
def delete_finding(finding_id: str) -> dict:
    _require_loaded()
    return {"ok": STATE.remove_finding(finding_id)}


@app.delete("/api/findings")
def reset_findings() -> dict:
    _require_loaded()
    STATE.reset_findings()
    return {"ok": True}


@app.post("/api/findings/parse")
def parse_finding(req: ParseRequest) -> dict:
    _require_loaded()
    return parse_text(req.text, STATE.tunnels, STATE.dictionary, STATE.cfg)


# ---- Memo (SPEC §9) ----

@app.post("/api/memo")
def memo(req: MemoRequest) -> dict:
    _require_loaded()
    plan = STATE.get_plan(req.plan_id)
    if not plan:
        raise HTTPException(404, "plan_id not found (re-run POST /plan)")
    facts = build_facts(plan, plan["waiting"], STATE.findings, BUDGET_ANCHORS,
                        STATE.dictionary_source())
    return generate_memo(facts)
