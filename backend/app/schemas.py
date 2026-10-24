"""Pydantic request/response models for the in-scope endpoints (SPEC §10)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class PlanRequest(BaseModel):
    budget: int
    horizon: Optional[int] = None


class MemoRequest(BaseModel):
    plan_id: str
