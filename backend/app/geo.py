"""Vectorized great-circle distance helpers."""

from __future__ import annotations

import numpy as np

EARTH_RADIUS_MILES = 3958.7613


def haversine_distances_miles(
    query_lat: float,
    query_lon: float,
    site_lats_radians: np.ndarray,
    site_lons_radians: np.ndarray,
    site_cos_lats: np.ndarray,
) -> np.ndarray:
    """Return great-circle distances from one point to arrays of site coordinates."""
    query_lat_radians, query_lon_radians = np.radians([query_lat, query_lon])

    delta_lat = site_lats_radians - query_lat_radians
    delta_lon = site_lons_radians - query_lon_radians
    haversine = (
        np.sin(delta_lat / 2.0) ** 2
        + np.cos(query_lat_radians)
        * site_cos_lats
        * np.sin(delta_lon / 2.0) ** 2
    )

    # Floating-point rounding can push the expression just outside [0, 1].
    haversine = np.clip(haversine, 0.0, 1.0)
    angular_distance = 2.0 * np.arctan2(
        np.sqrt(haversine),
        np.sqrt(1.0 - haversine),
    )
    return angular_distance * EARTH_RADIUS_MILES
