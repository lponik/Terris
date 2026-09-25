"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
import math
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import uuid4

try:
    import resource
except ImportError:  # pragma: no cover - non-Unix fallback
    resource = None  # type: ignore[assignment]

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings, load_settings
from .data_loader import (
    NEARBY_RADIUS_MILES,
    NEARBY_SITE_LIMIT,
    SpatialDataStore,
    load_spatial_data,
)
from .models import (
    AnalyzeRequest,
    AnalyzeResponse,
    CategoryCounts,
    CountsWithinMiles,
    HealthResponse,
    Location,
    Meta,
    NearestByCategory,
    ProximitySite,
    RadiusCounts,
    StatsResponse,
)

logger = logging.getLogger(__name__)

# FINAL PRODUCTION READINESS CHECKLIST:
# - Deterministic proximity calculations intact
# - No AI dependency in request path
# - Vectorized coordinate arrays prepared once at startup
# - CORS restricted in production via FRONTEND_ORIGIN
# - Safe structured error handling
# - Ready for Render backend + Vercel frontend deployment


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _process_rss_mb() -> float | None:
    if resource is None:
        return None
    try:
        max_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except Exception:
        return None
    if sys.platform == "darwin":
        return round(float(max_rss) / (1024.0 * 1024.0), 2)
    return round(float(max_rss) / 1024.0, 2)


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=payload)


def _proximity_site(item: dict[str, Any] | None) -> ProximitySite | None:
    if item is None:
        return None
    payload = dict(item)
    payload["distance_miles"] = round(float(payload["distance_miles"]), 2)
    return ProximitySite(**payload)


def _radius_counts(counts: dict[float, int]) -> RadiusCounts:
    return RadiusCounts(
        within_1_mile=counts[1.0],
        within_5_miles=counts[5.0],
        within_10_miles=counts[10.0],
    )


def _validate_coordinates_or_400(lat: float, lon: float) -> None:
    if not math.isfinite(lat) or not math.isfinite(lon):
        raise HTTPException(status_code=400, detail="Coordinates must be finite numbers.")
    if lat < -90.0 or lat > 90.0:
        raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90.")
    if lon < -180.0 or lon > 180.0:
        raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180.")


def _build_analyze_response(store: SpatialDataStore, settings: Settings, lat: float, lon: float) -> AnalyzeResponse:
    spatial_analysis = store.analyze_point(lat, lon)

    return AnalyzeResponse(
        location=Location(lat=lat, lon=lon),
        nearest_mapped_site=_proximity_site(spatial_analysis.nearest_mapped_site),
        nearest_by_category=NearestByCategory(
            landfill=_proximity_site(spatial_analysis.nearest_by_category["landfill"]),
            superfund=_proximity_site(
                spatial_analysis.nearest_by_category["superfund"]
            ),
        ),
        counts_within_miles=CountsWithinMiles(
            landfill=_radius_counts(spatial_analysis.counts_within_miles["landfill"]),
            superfund=_radius_counts(
                spatial_analysis.counts_within_miles["superfund"]
            ),
        ),
        nearby_sites=[
            site
            for item in spatial_analysis.nearby_sites
            if (site := _proximity_site(item)) is not None
        ],
        meta=Meta(
            version=settings.version,
            timestamp_utc=_utcnow(),
            nearby_radius_miles=NEARBY_RADIUS_MILES,
            nearby_site_limit=NEARBY_SITE_LIMIT,
            notes=[
                "Distances use mapped source coordinates and vectorized haversine calculations.",
                "Superfund points are representative mapped locations. NPL coordinates come from the EPA NPL dataset, retained legacy-only points may be boundary-derived, and some SAA-only points are address-geocoded. These points do not represent contamination boundaries or exact contamination locations.",
                "Proximity does not estimate personal exposure or health risk.",
            ],
        ),
    )


def _get_store(request: Request) -> SpatialDataStore:
    store: SpatialDataStore | None = getattr(request.app.state, "store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Dataset not loaded")
    return store


def _get_settings(request: Request) -> Settings:
    current_settings: Settings | None = getattr(request.app.state, "settings", None)
    if current_settings is None:
        raise HTTPException(status_code=503, detail="Settings not loaded")
    return current_settings


def _get_request_id(request: Request) -> str:
    header_request_id = request.headers.get("x-request-id", "").strip()
    return header_request_id or str(uuid4())


def _is_app_ready(request: Request) -> bool:
    required_state_keys = ("store", "settings", "startup_time", "startup_total_seconds")
    return all(hasattr(request.app.state, key) for key in required_state_keys)


def _get_uptime_seconds(request: Request) -> float | None:
    startup_time = getattr(request.app.state, "startup_time", None)
    if not isinstance(startup_time, datetime):
        return None
    return round((_utcnow() - startup_time).total_seconds(), 3)


def _get_startup_total_seconds(request: Request) -> float | None:
    startup_total = getattr(request.app.state, "startup_total_seconds", None)
    if isinstance(startup_total, (int, float)):
        return round(float(startup_total), 3)
    return None


settings = load_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_time = _utcnow()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )

    logger.info("========== TERRIS BACKEND STARTUP ==========")
    logger.info("environment=%s version=%s", settings.environment, settings.version)
    logger.info("data_path=%s", settings.data_path)
    logger.info("cors_allow_origins=%s", list(settings.cors_allow_origins))

    try:
        store = load_spatial_data(settings.data_path)
    except Exception:
        logger.exception("Failed to load dataset at startup.")
        raise

    app.state.store = store
    app.state.settings = settings
    app.state.startup_time = startup_time
    app.state.startup_total_seconds = store.stats.startup_total_seconds
    app.state.first_analyze_success_logged = False

    rss_mb = _process_rss_mb()
    if rss_mb is not None:
        logger.info("startup_rss_mb=%.2f", rss_mb)
    logger.info("dataset_rows=%s", store.stats.total_rows)
    logger.info("========== TERRIS BACKEND READY ==========")
    yield


app = FastAPI(
    title="Environmental Proximity API",
    description="Deterministic proximity to mapped landfills and Superfund sites.",
    debug=False,
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allow_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details: list[dict[str, str]] = []
    for error in exc.errors()[:8]:
        location = ".".join(str(item) for item in error.get("loc", []))
        details.append(
            {
                "field": location or "body",
                "message": str(error.get("msg", "Invalid value")),
            }
        )
    logger.warning(
        "request_validation_error method=%s path=%s errors=%s",
        request.method,
        request.url.path,
        len(exc.errors()),
    )
    return _error_response(
        status_code=400,
        code="invalid_request",
        message="Invalid request payload.",
        details=details,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    log_method = logger.warning if exc.status_code < 500 else logger.error
    log_method(
        "http_error method=%s path=%s status=%s detail=%s",
        request.method,
        request.url.path,
        exc.status_code,
        detail,
    )
    return _error_response(
        status_code=exc.status_code,
        code="request_error",
        message=detail,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception method=%s path=%s", request.method, request.url.path)
    return _error_response(
        status_code=500,
        code="internal_error",
        message="Internal server error.",
    )


@app.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    request_id = _get_request_id(request)
    start = perf_counter()
    loaded = hasattr(request.app.state, "store")
    ready = _is_app_ready(request)
    uptime_seconds = _get_uptime_seconds(request)
    startup_total_seconds = _get_startup_total_seconds(request)
    current_settings = getattr(request.app.state, "settings", settings)
    response = HealthResponse(
        status="ok",
        dataset_loaded=bool(loaded),
        version=current_settings.version,
        timestamp_utc=_utcnow(),
        ready=ready,
        uptime_seconds=uptime_seconds,
        startup_total_seconds=startup_total_seconds,
    )
    duration_ms = round((perf_counter() - start) * 1000.0, 2)
    logger.info(
        "health_request request_id=%s ready=%s dataset_loaded=%s duration_ms=%.2f",
        request_id,
        ready,
        bool(loaded),
        duration_ms,
    )
    return response


@app.head("/health", include_in_schema=False)
def health_head(request: Request) -> Response:
    loaded = hasattr(request.app.state, "store")
    ready = _is_app_ready(request)
    status_code = 200 if loaded and ready else 503
    return Response(status_code=status_code)


@app.get("/stats", response_model=StatsResponse)
def stats(request: Request) -> StatsResponse:
    store = _get_store(request)
    current_settings = _get_settings(request)

    counts = store.category_counts
    total = counts["landfill"] + counts["superfund"]

    return StatsResponse(
        dataset_loaded=True,
        data_path=store.stats.data_path,
        category_counts=CategoryCounts(
            landfill=counts["landfill"],
            superfund=counts["superfund"],
            total=total,
        ),
        load_time_seconds=store.stats.load_time_seconds,
        prepare_time_seconds=store.stats.prepare_time_seconds,
        startup_total_seconds=store.stats.startup_total_seconds,
        version=current_settings.version,
    )


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: Request, payload: AnalyzeRequest) -> AnalyzeResponse:
    request_id = _get_request_id(request)
    start = perf_counter()
    outcome = "success"
    try:
        _validate_coordinates_or_400(payload.lat, payload.lon)
        response = _build_analyze_response(
            store=_get_store(request),
            settings=_get_settings(request),
            lat=payload.lat,
            lon=payload.lon,
        )
        if not bool(getattr(request.app.state, "first_analyze_success_logged", False)):
            uptime_seconds = _get_uptime_seconds(request)
            logger.info(
                "analyze_first_success_after_startup request_id=%s uptime_seconds=%s",
                request_id,
                uptime_seconds if uptime_seconds is not None else "-",
            )
            request.app.state.first_analyze_success_logged = True
        return response
    except HTTPException as exc:
        outcome = f"http_{exc.status_code}"
        raise
    except Exception:
        outcome = "error"
        logger.exception(
            "analyze_request_failed request_id=%s lat=%.6f lon=%.6f",
            request_id,
            payload.lat,
            payload.lon,
        )
        raise
    finally:
        duration_ms = round((perf_counter() - start) * 1000.0, 2)
        logger.info(
            "analyze_request request_id=%s lat=%.6f lon=%.6f outcome=%s duration_ms=%.2f",
            request_id,
            payload.lat,
            payload.lon,
            outcome,
            duration_ms,
        )
