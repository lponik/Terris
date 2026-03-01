"""FastAPI application entrypoint."""

from __future__ import annotations

import copy
import logging
import math
import sys
from collections import OrderedDict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from threading import RLock
from typing import Any

try:
    import resource
except ImportError:  # pragma: no cover - non-Unix fallback
    resource = None  # type: ignore[assignment]

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings, load_settings
from .data_loader import SpatialDataStore, load_spatial_data
from .models import (
    AnalyzeRequest,
    AnalyzeResponse,
    CategoryCounts,
    Evidence,
    HealthResponse,
    Location,
    Meta,
    ReportRequest,
    ReportResponse,
    Score,
    ScoreBreakdown,
    Signals,
    StatsResponse,
)
from .report_confidence import compute_confidence
from .report_fallback import build_fallback_report
from .report_limits import cache_get, cache_set, get_client_ip
from .scoring import compute_score

logger = logging.getLogger(__name__)

REPORT_SCORE_VERSION = "v2"
REPORT_GENERATOR_VERSION = "deterministic_v1"

# FINAL PRODUCTION READINESS CHECKLIST:
# - Deterministic scoring intact
# - No AI dependency in request path
# - BallTrees built once at startup
# - CORS restricted in production via FRONTEND_ORIGIN
# - Safe structured error handling
# - Ready for Render backend + Vercel frontend deployment


class AnalysisCache:
    """Thread-safe in-memory LRU cache for analyze responses."""

    def __init__(self, maxsize: int) -> None:
        if maxsize <= 0:
            raise ValueError("CACHE_SIZE must be > 0")
        self.maxsize = maxsize
        self._store: OrderedDict[tuple[float, float], AnalyzeResponse] = OrderedDict()
        self._lock = RLock()

    def get(self, key: tuple[float, float]) -> AnalyzeResponse | None:
        with self._lock:
            value = self._store.get(key)
            if value is None:
                return None
            self._store.move_to_end(key)
            return copy.deepcopy(value)

    def set(self, key: tuple[float, float], value: AnalyzeResponse) -> None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = copy.deepcopy(value)
            if len(self._store) > self.maxsize:
                self._store.popitem(last=False)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _utcnow_iso() -> str:
    return _utcnow().isoformat()


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


def _rounded_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rounded_items: list[dict[str, Any]] = []
    for item in items:
        rounded_item = dict(item)
        distance = rounded_item.get("distance_miles")
        if isinstance(distance, float):
            rounded_item["distance_miles"] = round(distance, 2)
        rounded_items.append(rounded_item)
    return rounded_items


def _validate_coordinates_or_400(lat: float, lon: float) -> None:
    if not math.isfinite(lat) or not math.isfinite(lon):
        raise HTTPException(status_code=400, detail="Coordinates must be finite numbers.")
    if lat < -90.0 or lat > 90.0:
        raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90.")
    if lon < -180.0 or lon > 180.0:
        raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180.")


def _build_analyze_response(store: SpatialDataStore, settings: Settings, lat: float, lon: float) -> AnalyzeResponse:
    landfill_raw = store.nearest_k("landfill", lat, lon, k=3, round_distance_miles=False)
    military_raw = store.nearest_k("military_base", lat, lon, k=3, round_distance_miles=False)
    industrial_raw = store.nearest_k("industrial_frs", lat, lon, k=3, round_distance_miles=False)
    superfund_raw = store.nearest_k("superfund_npl", lat, lon, k=3, round_distance_miles=False)

    landfill_evidence = _rounded_evidence(landfill_raw)
    military_evidence = _rounded_evidence(military_raw)
    industrial_evidence = _rounded_evidence(industrial_raw)
    superfund_evidence = _rounded_evidence(superfund_raw)

    signals_payload = {
        "nearest_landfill_miles": landfill_raw[0]["distance_miles"] if landfill_raw else None,
        "nearest_military_base_miles": military_raw[0]["distance_miles"] if military_raw else None,
        "nearest_industrial_frs_miles": industrial_raw[0]["distance_miles"] if industrial_raw else None,
        "nearest_superfund_npl_miles": superfund_raw[0]["distance_miles"] if superfund_raw else None,
        "industrial_count_1mi": store.count_within("industrial_frs", lat, lon, radius_miles=1.0),
        "industrial_count_3mi": store.count_within("industrial_frs", lat, lon, radius_miles=3.0),
        "industrial_count_10mi": store.count_within("industrial_frs", lat, lon, radius_miles=10.0),
        "superfund_count_3mi": store.count_within("superfund_npl", lat, lon, radius_miles=3.0),
    }

    score_payload = compute_score(signals_payload)

    return AnalyzeResponse(
        location=Location(lat=lat, lon=lon),
        signals=Signals(**signals_payload),
        score=Score(
            total=score_payload["total"],
            breakdown=ScoreBreakdown(**score_payload["breakdown"]),
            band=score_payload["band"],
            top_drivers=score_payload["top_drivers"],
            meta=score_payload.get("meta"),
        ),
        evidence=Evidence(
            landfill=landfill_evidence,
            military_base=military_evidence,
            industrial_frs=industrial_evidence,
            superfund_npl=superfund_evidence,
        ),
        meta=Meta(
            version=settings.version,
            timestamp_utc=_utcnow(),
            notes=[
                "Deterministic score from landfill proximity, military proximity, industrial density, and superfund proximity signals.",
                "Distances computed via haversine metric on BallTree and reported in miles.",
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


def _get_cache(request: Request) -> AnalysisCache:
    cache: AnalysisCache | None = getattr(request.app.state, "analysis_cache", None)
    if cache is None:
        raise HTTPException(status_code=503, detail="Analyze cache not loaded")
    return cache


def _analyze_with_cache(request: Request, lat: float, lon: float) -> AnalyzeResponse:
    store = _get_store(request)
    current_settings = _get_settings(request)
    cache = _get_cache(request)

    cache_key = (
        round(lat, current_settings.cache_rounding_decimals),
        round(lon, current_settings.cache_rounding_decimals),
    )

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    response = _build_analyze_response(store=store, settings=current_settings, lat=lat, lon=lon)
    cache.set(cache_key, response)
    return response


def _build_report_cache_key(lat: float, lon: float) -> str:
    return f"{lat:.4f},{lon:.4f}|score_{REPORT_SCORE_VERSION}|report_{REPORT_GENERATOR_VERSION}"


def _mark_cached_response(report_payload: dict[str, Any], cache_key: str) -> dict[str, Any]:
    cached_payload = copy.deepcopy(report_payload)
    meta = cached_payload.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    meta["cached"] = True
    meta["cache_key"] = cache_key
    if "generated_at" not in meta or not isinstance(meta.get("generated_at"), str):
        meta["generated_at"] = _utcnow_iso()
    cached_payload["meta"] = meta
    return cached_payload


def _log_report_request(
    *,
    ip: str,
    lat: float,
    lon: float,
    cache_hit: bool,
    outcome: str,
    reason: str | None,
) -> None:
    logger.info(
        "report_request ip=%s lat=%.4f lon=%.4f cache_hit=%s outcome=%s reason=%s",
        ip,
        lat,
        lon,
        cache_hit,
        outcome,
        reason or "-",
    )


settings = load_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    app.state.analysis_cache = AnalysisCache(maxsize=settings.cache_size)

    rss_mb = _process_rss_mb()
    if rss_mb is not None:
        logger.info("startup_rss_mb=%.2f", rss_mb)
    logger.info("dataset_rows=%s", store.stats.total_rows)
    logger.info("========== TERRIS BACKEND READY ==========")
    yield


app = FastAPI(
    title="Environmental Exposure Risk API",
    description="Deterministic spatial risk analysis for landfills, military bases, industrial facilities, and superfund sites.",
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
    loaded = hasattr(request.app.state, "store")
    current_settings = getattr(request.app.state, "settings", settings)
    return HealthResponse(
        status="ok",
        dataset_loaded=bool(loaded),
        version=current_settings.version,
        timestamp_utc=_utcnow(),
    )


@app.get("/stats", response_model=StatsResponse)
def stats(request: Request) -> StatsResponse:
    store = _get_store(request)
    current_settings = _get_settings(request)

    counts = store.category_counts
    total = counts["landfill"] + counts["military_base"] + counts["industrial_frs"] + counts["superfund_npl"]

    return StatsResponse(
        dataset_loaded=True,
        data_path=store.stats.data_path,
        category_counts=CategoryCounts(
            landfill=counts["landfill"],
            military_base=counts["military_base"],
            industrial_frs=counts["industrial_frs"],
            superfund_npl=counts["superfund_npl"],
            total=total,
        ),
        load_time_seconds=store.stats.load_time_seconds,
        tree_build_time_seconds=store.stats.tree_build_time_seconds,
        startup_total_seconds=store.stats.startup_total_seconds,
        cache_size=current_settings.cache_size,
        version=current_settings.version,
    )


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: Request, payload: AnalyzeRequest) -> AnalyzeResponse:
    _validate_coordinates_or_400(payload.lat, payload.lon)
    try:
        return _analyze_with_cache(request=request, lat=payload.lat, lon=payload.lon)
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "analyze_request_failed lat=%.6f lon=%.6f",
            payload.lat,
            payload.lon,
        )
        raise


@app.post("/report", response_model=ReportResponse)
def report(request: Request, payload: ReportRequest) -> ReportResponse:
    _validate_coordinates_or_400(payload.lat, payload.lon)
    current_settings = _get_settings(request)
    ip = get_client_ip(request)
    cache_key = _build_report_cache_key(payload.lat, payload.lon)

    cached_payload = cache_get(cache_key, ttl_seconds=current_settings.report_cache_ttl_seconds)
    if cached_payload is not None:
        response_payload = _mark_cached_response(cached_payload, cache_key)
        _log_report_request(
            ip=ip,
            lat=payload.lat,
            lon=payload.lon,
            cache_hit=True,
            outcome="success",
            reason="cache_hit",
        )
        return ReportResponse.model_validate(response_payload)

    try:
        analysis = _analyze_with_cache(request=request, lat=payload.lat, lon=payload.lon)
        confidence = compute_confidence(analysis)
        deterministic_payload = build_fallback_report(
            analysis,
            confidence,
            "Deterministic explanation generated from proximity and density screening signals.",
            cached=False,
            cache_key=cache_key,
        )
        response = ReportResponse.model_validate(deterministic_payload)
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "report_request_failed ip=%s lat=%.6f lon=%.6f",
            ip,
            payload.lat,
            payload.lon,
        )
        raise

    cache_set(
        cache_key,
        response.model_dump(mode="json"),
        ttl_seconds=current_settings.report_cache_ttl_seconds,
        max_items=current_settings.report_cache_max_items,
    )
    _log_report_request(
        ip=ip,
        lat=payload.lat,
        lon=payload.lon,
        cache_hit=False,
        outcome="success",
        reason="deterministic_report",
    )
    return response
