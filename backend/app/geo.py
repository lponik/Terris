"""Geospatial helpers for distance conversions."""

from __future__ import annotations

import numpy as np

EARTH_RADIUS_MILES = 3958.7613



def lat_lon_to_radians(lat: float, lon: float) -> np.ndarray:
    """Convert a single latitude/longitude pair to radians."""
    return np.deg2rad(np.array([[lat, lon]], dtype=np.float64))



def degrees_array_to_radians(lat_lon_deg: np.ndarray) -> np.ndarray:
    """Convert an (n,2) array of degree coordinates to radians."""
    return np.deg2rad(lat_lon_deg.astype(np.float64, copy=False))



def radians_to_miles(distance_radians: np.ndarray | float) -> np.ndarray | float:
    """Convert haversine angular distance to miles."""
    return distance_radians * EARTH_RADIUS_MILES



def miles_to_radians(distance_miles: float) -> float:
    """Convert miles to haversine angular distance radians."""
    return distance_miles / EARTH_RADIUS_MILES
