"""Dataset loading and spatial indexing utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from .config import EXPECTED_CATEGORIES
from .geo import degrees_array_to_radians, lat_lon_to_radians, miles_to_radians, radians_to_miles

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


@dataclass(frozen=True)
class CategoryIndex:
    category: str
    tree: BallTree | None
    row_indices: np.ndarray


@dataclass(frozen=True)
class DatasetStats:
    data_path: str
    category_counts: dict[str, int]
    load_time_seconds: float
    tree_build_time_seconds: float
    startup_total_seconds: float
    total_rows: int


class SpatialDataStore:
    """Holds category-specific BallTrees and source records."""

    def __init__(
        self,
        *,
        category_indexes: dict[str, CategoryIndex],
        ids: np.ndarray,
        names: np.ndarray,
        lats: np.ndarray,
        lons: np.ndarray,
        states: np.ndarray,
        sources: np.ndarray,
        metadata_json: np.ndarray,
        stats: DatasetStats,
    ) -> None:
        self._category_indexes = category_indexes
        self._ids = ids
        self._names = names
        self._lats = lats
        self._lons = lons
        self._states = states
        self._sources = sources
        self._metadata_json = metadata_json
        self.stats = stats

    @property
    def category_counts(self) -> dict[str, int]:
        return dict(self.stats.category_counts)

    def nearest_k(
        self,
        category: str,
        lat: float,
        lon: float,
        k: int = 3,
        include_metadata: bool = False,
        round_distance_miles: bool = True,
    ) -> list[dict[str, Any]]:
        index = self._category_indexes.get(category)
        if index is None or index.tree is None or index.row_indices.size == 0:
            return []

        query_point = lat_lon_to_radians(lat, lon)
        k_eff = max(1, min(k, index.row_indices.size))
        distances_rad, local_indices = index.tree.query(query_point, k=k_eff)

        results: list[dict[str, Any]] = []
        for distance_rad, local_idx in zip(distances_rad[0], local_indices[0], strict=True):
            global_idx = int(index.row_indices[int(local_idx)])
            distance_miles = float(radians_to_miles(float(distance_rad)))
            if round_distance_miles:
                distance_miles = round(distance_miles, 2)

            item = {
                "id": _none_if_empty(self._ids[global_idx]),
                "name": _none_if_empty(self._names[global_idx]),
                "distance_miles": distance_miles,
                "lat": float(self._lats[global_idx]),
                "lon": float(self._lons[global_idx]),
                "state": _none_if_empty(self._states[global_idx]),
                "source": _none_if_empty(self._sources[global_idx]),
            }
            if include_metadata:
                item["metadata"] = _none_if_empty(self._metadata_json[global_idx])
            results.append(item)

        return results

    def count_within(self, category: str, lat: float, lon: float, radius_miles: float) -> int:
        index = self._category_indexes.get(category)
        if index is None or index.tree is None or index.row_indices.size == 0:
            return 0

        query_point = lat_lon_to_radians(lat, lon)
        radius_rad = miles_to_radians(radius_miles)
        counts = index.tree.query_radius(query_point, r=radius_rad, count_only=True)
        return int(counts[0])



def load_spatial_data(data_path: str) -> SpatialDataStore:
    """Load processed CSV and build BallTree indexes."""
    startup_start = perf_counter()

    csv_path = Path(data_path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Processed dataset not found at {data_path!r}. Set DATA_PATH to a valid CSV path."
        )

    load_start = perf_counter()
    dataframe = pd.read_csv(csv_path, usecols=REQUIRED_COLUMNS, keep_default_na=False, low_memory=False)
    load_elapsed = perf_counter() - load_start

    _validate_columns(dataframe)
    _validate_categories(dataframe)
    dataframe = _clean_coordinates(dataframe)

    row_count = len(dataframe)
    logger.info("Loaded %s rows from %s in %.2fs", row_count, data_path, load_elapsed)

    ids = dataframe["id"].to_numpy(dtype=object)
    names = dataframe["name"].to_numpy(dtype=object)
    lats = dataframe["lat"].to_numpy(dtype=np.float64)
    lons = dataframe["lon"].to_numpy(dtype=np.float64)
    states = dataframe["state"].to_numpy(dtype=object)
    sources = dataframe["source"].to_numpy(dtype=object)
    metadata_json = dataframe["metadata_json"].to_numpy(dtype=object)

    category_array = dataframe["category"].to_numpy(dtype=object)
    coords_deg = dataframe[["lat", "lon"]].to_numpy(dtype=np.float64)
    coords_rad = degrees_array_to_radians(coords_deg)

    build_start = perf_counter()
    category_indexes: dict[str, CategoryIndex] = {}
    category_counts: dict[str, int] = {}

    for category in EXPECTED_CATEGORIES:
        row_indices = np.flatnonzero(category_array == category)
        category_counts[category] = int(row_indices.size)

        tree: BallTree | None = None
        if row_indices.size > 0:
            category_coords_rad = coords_rad[row_indices]
            tree = BallTree(category_coords_rad, metric="haversine")

        category_indexes[category] = CategoryIndex(
            category=category,
            tree=tree,
            row_indices=row_indices,
        )

    tree_elapsed = perf_counter() - build_start
    startup_elapsed = perf_counter() - startup_start

    logger.info("Built BallTrees in %.2fs", tree_elapsed)
    logger.info(
        "Category counts | landfill=%s military_base=%s industrial_frs=%s superfund_npl=%s",
        category_counts["landfill"],
        category_counts["military_base"],
        category_counts["industrial_frs"],
        category_counts["superfund_npl"],
    )
    logger.info("Startup load+build total %.2fs", startup_elapsed)

    stats = DatasetStats(
        data_path=str(csv_path),
        category_counts=category_counts,
        load_time_seconds=round(load_elapsed, 3),
        tree_build_time_seconds=round(tree_elapsed, 3),
        startup_total_seconds=round(startup_elapsed, 3),
        total_rows=row_count,
    )

    return SpatialDataStore(
        category_indexes=category_indexes,
        ids=ids,
        names=names,
        lats=lats,
        lons=lons,
        states=states,
        sources=sources,
        metadata_json=metadata_json,
        stats=stats,
    )



def _validate_columns(dataframe: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_COLUMNS if col not in dataframe.columns]
    if missing:
        raise ValueError(f"Dataset missing required columns: {missing}")



def _validate_categories(dataframe: pd.DataFrame) -> None:
    category_values = dataframe["category"].astype(str).str.strip()
    if category_values.eq("").any():
        raise ValueError(
            "Invalid category strings detected in CSV. Empty category values are not allowed. "
            f"Expected exactly: {sorted(EXPECTED_CATEGORIES)}"
        )

    observed = {str(item).strip() for item in category_values.unique().tolist() if str(item).strip()}
    expected = set(EXPECTED_CATEGORIES)

    unknown = observed - expected
    if unknown:
        observed_sorted = sorted(observed)
        unknown_sorted = sorted(unknown)
        raise ValueError(
            "Invalid category strings detected in CSV. "
            f"Observed categories: {observed_sorted}. Unexpected categories: {unknown_sorted}. "
            f"Expected exactly: {sorted(expected)}"
        )

    missing = expected - observed
    if missing:
        logger.warning(
            "Expected category values missing from dataset (continuing with empty indexes): %s",
            sorted(missing),
        )



def _clean_coordinates(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = dataframe.copy()
    dataframe["lat"] = pd.to_numeric(dataframe["lat"], errors="coerce")
    dataframe["lon"] = pd.to_numeric(dataframe["lon"], errors="coerce")

    valid_mask = (
        dataframe["lat"].between(-90.0, 90.0)
        & dataframe["lon"].between(-180.0, 180.0)
        & dataframe["category"].astype(str).str.strip().ne("")
    )

    dropped = int((~valid_mask).sum())
    if dropped > 0:
        logger.warning("Dropping %s rows with invalid coordinates or empty categories.", dropped)

    return dataframe.loc[valid_mask].reset_index(drop=True)



def _none_if_empty(value: Any) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text
