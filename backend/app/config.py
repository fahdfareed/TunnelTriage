"""Loads config.yaml into typed pydantic models (SPEC §7)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

import yaml
from pydantic import BaseModel

BACKEND_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BACKEND_DIR / "config.yaml"
DATA_DIR = BACKEND_DIR.parent / "data"


class Weights(BaseModel):
    w3: float
    w4: float


class TransitionRates(BaseModel):
    p12: float
    p23: float
    p34: float


class UnitCostPair(BaseModel):
    cs3: float
    cs4: float


class BidVsEstimate(BaseModel):
    low: float
    high: float


class ProgramOverheads(BaseModel):
    contingency: float
    construction_engineering: float
    traffic_police: float


class SafetyFloor(BaseModel):
    enabled: bool
    min_criticality: int
    min_cs4_share: float


class BudgetSlider(BaseModel):
    min: int
    max: int
    step: int
    default: int


class LLMConfig(BaseModel):
    provider: str
    model: str
    max_tokens: int
    timeout_s: int


class Config(BaseModel):
    state_fips: str
    include_suspect_elements: bool
    weights: Weights
    underwater_multiplier: float
    size_factor_clip: List[float]
    horizon_years: int
    forecast_years: int
    transition: Dict[str, TransitionRates]
    category_transition_group: Dict[str, str]
    criticality_by_category: Dict[str, int]
    criticality_overrides: Dict[int, int]
    overhead_keywords: List[str]
    unit_cost: Dict[str, UnitCostPair]
    cost_scale: float
    mobilization_pct: float = 0.0
    fixed_mobilization_per_tunnel: int
    bid_vs_estimate: BidVsEstimate
    program_overheads: ProgramOverheads
    safety_floor: SafetyFloor
    budget_slider: BudgetSlider
    llm: LLMConfig


@lru_cache(maxsize=1)
def get_config() -> Config:
    with open(CONFIG_PATH, "r") as f:
        raw = yaml.safe_load(f)
    # criticality_overrides keys may be strings from YAML; normalize to int.
    raw["criticality_overrides"] = {
        int(k): int(v) for k, v in (raw.get("criticality_overrides") or {}).items()
    }
    cfg = Config(**raw)
    # Env overrides for the LLM provider/model (SPEC §9).
    if os.environ.get("LLM_PROVIDER"):
        cfg.llm.provider = os.environ["LLM_PROVIDER"]
    if os.environ.get("LLM_MODEL"):
        cfg.llm.model = os.environ["LLM_MODEL"]
    return cfg
