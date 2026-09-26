"""Pydantic models for API inputs and outputs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    lon: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")


class Location(BaseModel):
    lat: float
    lon: float


SiteCategory = Literal["landfill", "superfund"]


class ProximitySite(BaseModel):
    id: str
    name: str
    category: SiteCategory
    distance_miles: float
    lat: float
    lon: float
    state: str
    source: str


class NearestByCategory(BaseModel):
    landfill: ProximitySite | None
    superfund: ProximitySite | None


class RadiusCounts(BaseModel):
    within_1_mile: int
    within_5_miles: int
    within_10_miles: int


class CountsWithinMiles(BaseModel):
    landfill: RadiusCounts
    superfund: RadiusCounts


class Meta(BaseModel):
    version: str
    timestamp_utc: datetime
    nearby_radius_miles: float
    nearby_site_limit: int
    notes: list[str]


class AnalyzeResponse(BaseModel):
    location: Location
    nearest_mapped_site: ProximitySite | None
    nearest_by_category: NearestByCategory
    counts_within_miles: CountsWithinMiles
    nearby_sites: list[ProximitySite]
    meta: Meta


class CategoryCounts(BaseModel):
    landfill: int
    superfund: int
    total: int


class StatsResponse(BaseModel):
    dataset_loaded: bool
    data_path: str
    category_counts: CategoryCounts
    load_time_seconds: float
    prepare_time_seconds: float
    startup_total_seconds: float
    version: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    dataset_loaded: bool
    version: str
    timestamp_utc: datetime
    ready: bool | None = None
    uptime_seconds: float | None = None
    startup_total_seconds: float | None = None
