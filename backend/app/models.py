"""Pydantic models for API inputs and outputs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    lon: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")


class Location(BaseModel):
    lat: float
    lon: float


class Signals(BaseModel):
    nearest_landfill_miles: float | None
    nearest_military_base_miles: float | None
    nearest_superfund_npl_miles: float | None = None
    superfund_count_3mi: int = 0


class ScoreBreakdown(BaseModel):
    landfill_proximity: float
    military_proximity: float
    superfund_proximity: float = 0.0


class Score(BaseModel):
    total: float
    breakdown: ScoreBreakdown
    band: Literal["Low", "Moderate", "High"]
    top_drivers: list[str]
    meta: dict[str, Any] | None = None


class EvidenceItem(BaseModel):
    id: str | None
    name: str | None
    distance_miles: float | None
    lat: float | None = None
    lon: float | None = None
    state: str | None
    source: str | None


class Evidence(BaseModel):
    landfill: list[EvidenceItem]
    military_base: list[EvidenceItem]
    superfund_npl: list[EvidenceItem] = Field(default_factory=list)


class Meta(BaseModel):
    version: str
    timestamp_utc: datetime
    notes: list[str]


class AnalyzeResponse(BaseModel):
    location: Location
    signals: Signals
    score: Score
    evidence: Evidence
    meta: Meta


class CategoryCounts(BaseModel):
    landfill: int
    military_base: int
    superfund_npl: int = 0
    total: int


class StatsResponse(BaseModel):
    dataset_loaded: bool
    data_path: str
    category_counts: CategoryCounts
    load_time_seconds: float
    tree_build_time_seconds: float
    startup_total_seconds: float
    cache_size: int
    version: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    dataset_loaded: bool
    version: str
    timestamp_utc: datetime
    ready: bool | None = None
    uptime_seconds: float | None = None
    startup_total_seconds: float | None = None
