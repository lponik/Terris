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
    nearest_industrial_frs_miles: float | None
    nearest_superfund_npl_miles: float | None = None
    industrial_count_1mi: int
    industrial_count_3mi: int
    industrial_count_10mi: int
    superfund_count_3mi: int = 0


class ScoreBreakdown(BaseModel):
    landfill_proximity: float
    military_proximity: float
    industrial_density: float
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
    industrial_frs: list[EvidenceItem]
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
    industrial_frs: int
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


class ReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class ReportDriver(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    detail: str


class ReportSiteTypeContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_type: str
    what_it_can_indicate: str


class ReportNextStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str
    why: str


class ReportConfidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: Literal["Low", "Moderate", "High"]
    rationale: str


class ReportMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ai_used: bool
    ai_fallback: bool
    cached: bool
    cache_key: str
    model: str | None
    generated_at: str
    note: str | None


class ReportBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    top_drivers_explained: list[ReportDriver]
    site_type_context: list[ReportSiteTypeContext]
    recommended_next_steps: list[ReportNextStep]
    limitations: list[str]
    confidence: ReportConfidence


class ReportResponse(ReportBody):
    meta: ReportMeta
