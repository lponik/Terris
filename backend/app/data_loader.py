"""CSV loading and vectorized spatial analysis utilities."""

from __future__ import annotations

import csv
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from .config import EXPECTED_CATEGORIES
from .geo import haversine_distances_miles

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = (
    "id",
    "name",
    "category",
    "lat",
    "lon",
    "state",
    "source",
    "metadata_json",
)
COUNT_RADII_MILES = (1.0, 5.0, 10.0)
NEARBY_RADIUS_MILES = 5.0
NEARBY_SITE_LIMIT = 20


@dataclass(frozen=True)
class CategoryData:
    """Immutable site values and precomputed coordinate arrays for one category."""

    category: str
    ids: tuple[str, ...]
    names: tuple[str, ...]
    lats: np.ndarray
    lons: np.ndarray
    lats_radians: np.ndarray
    lons_radians: np.ndarray
    cos_lats: np.ndarray
    states: tuple[str, ...]
    sources: tuple[str, ...]

    @property
    def size(self) -> int:
        return len(self.ids)


@dataclass(frozen=True)
class SpatialAnalysis:
    """Proximity results calculated from one distance array per category."""

    nearest_mapped_site: dict[str, Any] | None
    nearest_by_category: dict[str, dict[str, Any] | None]
    counts_within_miles: dict[str, dict[float, int]]
    nearby_sites: list[dict[str, Any]]


@dataclass(frozen=True)
class DatasetStats:
    data_path: str
    category_counts: dict[str, int]
    load_time_seconds: float
    prepare_time_seconds: float
    startup_total_seconds: float
    total_rows: int


class SpatialDataStore:
    """Holds per-category arrays and performs vectorized haversine scans."""

    def __init__(
        self,
        *,
        categories: dict[str, CategoryData],
        stats: DatasetStats,
    ) -> None:
        self._categories = categories
        self.stats = stats

    @property
    def category_counts(self) -> dict[str, int]:
        return dict(self.stats.category_counts)

    def analyze_point(self, lat: float, lon: float) -> SpatialAnalysis:
        """Calculate nearest sites, radius counts, and a bounded nearby list."""
        nearest_by_category: dict[str, dict[str, Any] | None] = {}
        counts_within_miles: dict[str, dict[float, int]] = {}
        nearby_sites: list[dict[str, Any]] = []

        for category in EXPECTED_CATEGORIES:
            sites = self._categories[category]
            if sites.size == 0:
                nearest_by_category[category] = None
                counts_within_miles[category] = {
                    radius: 0 for radius in COUNT_RADII_MILES
                }
                continue

            distances_miles = haversine_distances_miles(
                query_lat=lat,
                query_lon=lon,
                site_lats_radians=sites.lats_radians,
                site_lons_radians=sites.lons_radians,
                site_cos_lats=sites.cos_lats,
            )
            nearest_by_category[category] = _nearest_site(sites, distances_miles)
            counts_within_miles[category] = {
                radius: int(np.count_nonzero(distances_miles <= radius))
                for radius in COUNT_RADII_MILES
            }
            nearby_indices = np.flatnonzero(distances_miles <= NEARBY_RADIUS_MILES)
            nearby_sites.extend(
                _sorted_sites(
                    sites,
                    distances_miles,
                    nearby_indices,
                    limit=NEARBY_SITE_LIMIT,
                )
            )

        nearby_sites.sort(
            key=lambda site: (
                float(site["distance_miles"]),
                str(site["category"]),
                str(site["id"]),
            )
        )
        nearby_sites = nearby_sites[:NEARBY_SITE_LIMIT]

        nearest_candidates = [
            site for site in nearest_by_category.values() if site is not None
        ]
        nearest_mapped_site = min(
            nearest_candidates,
            key=lambda site: (
                float(site["distance_miles"]),
                str(site["category"]),
                str(site["id"]),
            ),
            default=None,
        )

        return SpatialAnalysis(
            nearest_mapped_site=nearest_mapped_site,
            nearest_by_category=nearest_by_category,
            counts_within_miles=counts_within_miles,
            nearby_sites=nearby_sites,
        )


def load_spatial_data(data_path: str) -> SpatialDataStore:
    """Load the processed CSV and prepare immutable NumPy arrays."""
    startup_start = perf_counter()

    csv_path = Path(data_path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Processed dataset not found at {data_path!r}. Set DATA_PATH to a valid CSV path."
        )

    load_start = perf_counter()
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        _validate_columns(reader.fieldnames)
        rows = list(reader)
    load_elapsed = perf_counter() - load_start

    prepare_start = perf_counter()
    _validate_categories(rows)
    category_rows, dropped = _group_valid_rows(rows)
    categories = {
        category: _build_category_data(category, category_rows[category])
        for category in EXPECTED_CATEGORIES
    }
    prepare_elapsed = perf_counter() - prepare_start
    startup_elapsed = perf_counter() - startup_start

    if dropped:
        logger.warning("Dropping %s rows with invalid coordinates.", dropped)

    category_counts = {
        category: categories[category].size
        for category in EXPECTED_CATEGORIES
    }
    row_count = sum(category_counts.values())

    logger.info("Loaded %s valid rows from %s in %.3fs", row_count, data_path, load_elapsed)
    logger.info("Prepared coordinate arrays in %.3fs", prepare_elapsed)
    logger.info(
        "Category counts | landfill=%s superfund=%s",
        category_counts["landfill"],
        category_counts["superfund"],
    )
    logger.info("Startup load+prepare total %.3fs", startup_elapsed)

    stats = DatasetStats(
        data_path=str(csv_path),
        category_counts=category_counts,
        load_time_seconds=round(load_elapsed, 3),
        prepare_time_seconds=round(prepare_elapsed, 3),
        startup_total_seconds=round(startup_elapsed, 3),
        total_rows=row_count,
    )
    return SpatialDataStore(categories=categories, stats=stats)


def _validate_columns(fieldnames: list[str] | None) -> None:
    available = set(fieldnames or [])
    missing = [column for column in REQUIRED_COLUMNS if column not in available]
    if missing:
        raise ValueError(f"Dataset missing required columns: {missing}")


def _validate_categories(rows: list[dict[str, str]]) -> None:
    categories = [(row.get("category") or "").strip() for row in rows]
    if any(not category for category in categories):
        raise ValueError(
            "Invalid category strings detected in CSV. Empty category values are not allowed. "
            f"Expected exactly: {sorted(EXPECTED_CATEGORIES)}"
        )

    observed = set(categories)
    expected = set(EXPECTED_CATEGORIES)
    unknown = observed - expected
    if unknown:
        raise ValueError(
            "Invalid category strings detected in CSV. "
            f"Observed categories: {sorted(observed)}. Unexpected categories: {sorted(unknown)}. "
            f"Expected exactly: {sorted(expected)}"
        )

    missing = expected - observed
    if missing:
        logger.warning(
            "Expected category values missing from dataset (continuing with empty arrays): %s",
            sorted(missing),
        )


def _group_valid_rows(
    rows: list[dict[str, str]],
) -> tuple[dict[str, list[tuple[dict[str, str], float, float]]], int]:
    grouped: dict[str, list[tuple[dict[str, str], float, float]]] = {
        category: [] for category in EXPECTED_CATEGORIES
    }
    dropped = 0

    for row in rows:
        category = (row.get("category") or "").strip()
        lat = _parse_coordinate(row.get("lat"), minimum=-90.0, maximum=90.0)
        lon = _parse_coordinate(row.get("lon"), minimum=-180.0, maximum=180.0)
        if lat is None or lon is None:
            dropped += 1
            continue
        grouped[category].append((row, lat, lon))

    return grouped, dropped


def _parse_coordinate(value: str | None, *, minimum: float, maximum: float) -> float | None:
    try:
        parsed = float((value or "").strip())
    except ValueError:
        return None
    if not math.isfinite(parsed) or parsed < minimum or parsed > maximum:
        return None
    return parsed


def _build_category_data(
    category: str,
    rows: list[tuple[dict[str, str], float, float]],
) -> CategoryData:
    ids = tuple((row.get("id") or "").strip() for row, _, _ in rows)
    names = tuple((row.get("name") or "").strip() for row, _, _ in rows)
    states = tuple((row.get("state") or "").strip() for row, _, _ in rows)
    sources = tuple((row.get("source") or "").strip() for row, _, _ in rows)
    lats = _readonly_float_array([lat for _, lat, _ in rows])
    lons = _readonly_float_array([lon for _, _, lon in rows])
    lats_radians = _readonly_float_array(np.radians(lats))
    lons_radians = _readonly_float_array(np.radians(lons))
    cos_lats = _readonly_float_array(np.cos(lats_radians))

    return CategoryData(
        category=category,
        ids=ids,
        names=names,
        lats=lats,
        lons=lons,
        lats_radians=lats_radians,
        lons_radians=lons_radians,
        cos_lats=cos_lats,
        states=states,
        sources=sources,
    )


def _readonly_float_array(values: Any) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    array.setflags(write=False)
    return array


def _nearest_site(
    sites: CategoryData,
    distances_miles: np.ndarray,
) -> dict[str, Any] | None:
    if sites.size == 0:
        return None
    threshold = float(np.min(distances_miles))
    candidates = np.flatnonzero(distances_miles <= threshold)
    matches = _sorted_sites(sites, distances_miles, candidates, limit=1)
    return matches[0] if matches else None


def _sorted_sites(
    sites: CategoryData,
    distances_miles: np.ndarray,
    candidate_indices: np.ndarray,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    sorted_indices = sorted(
        (int(index) for index in candidate_indices),
        key=lambda index: (float(distances_miles[index]), sites.ids[index]),
    )[:limit]

    return [
        {
            "id": sites.ids[index],
            "name": sites.names[index],
            "category": sites.category,
            "distance_miles": float(distances_miles[index]),
            "lat": float(sites.lats[index]),
            "lon": float(sites.lons[index]),
            "state": sites.states[index],
            "source": sites.sources[index],
        }
        for index in sorted_indices
    ]
