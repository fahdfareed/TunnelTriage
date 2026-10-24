"""Pydantic request/response models (SPEC §10)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    budget: int
    horizon: Optional[int] = None


class MemoRequest(BaseModel):
    plan_id: str


class FindingRequest(BaseModel):
    tunnel_number: str
    element_number: int
    epn: int = 0
    quantity: int = Field(gt=0)
    condition_state: int = Field(ge=3, le=4)
    source: str = "simulated"
    note: str = ""


class ParseRequest(BaseModel):
    text: str
