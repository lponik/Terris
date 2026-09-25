#!/usr/bin/env python3
"""Smoke test for the Terris environmental-proximity bundle and API contract."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from build_data import PipelineError, validate_repository
from backend.app.data_loader import SpatialDataStore, load_spatial_data

ALL_SITES_PATH = REPO_ROOT / "data" / "processed" / "all_sites.csv"


def analyze_point(store: SpatialDataStore, lat: float, lon: float) -> dict[str, Any]:
    result = store.analyze_point(lat, lon)
    return {
        "query_point": {"lat": lat, "lon": lon},
        "nearest_by_category": {
            category: (
                {
                    "id": site["id"],
                    "name": site["name"],
                    "distance_miles": round(site["distance_miles"], 4),
                }
                if site is not None
                else None
            )
            for category, site in result.nearest_by_category.items()
        },
        "counts_within_miles": result.counts_within_miles,
        "nearby_sites": [
            {
                "id": site["id"],
                "category": site["category"],
                "distance_miles": round(site["distance_miles"], 4),
            }
            for site in result.nearby_sites[:10]
        ],
    }


def check_api_contract() -> None:
    request_body = json.dumps({"lat": 40.7128, "lon": -74.0060}).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:8000/analyze",
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError:
        print("Backend not reachable at http://127.0.0.1:8000; skipping live API check.")
        return

    required = {
        "location",
        "nearest_mapped_site",
        "nearest_by_category",
        "counts_within_miles",
        "nearby_sites",
        "meta",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise AssertionError(f"Analyze response missing proximity fields: {missing}")
    forbidden = sorted({"score", "signals", "evidence"} & set(payload))
    if forbidden:
        raise AssertionError(f"Analyze response still contains retired fields: {forbidden}")
    if "military_base" in json.dumps(payload):
        raise AssertionError("Analyze response still contains military-base data")

    distances = [site["distance_miles"] for site in payload["nearby_sites"]]
    if distances != sorted(distances):
        raise AssertionError("Analyze response nearby_sites is not sorted by distance")


def main() -> int:
    try:
        validate_repository(REPO_ROOT)
    except PipelineError as exc:
        raise AssertionError(f"Generated data bundle failed validation: {exc}") from exc

    store = load_spatial_data(str(ALL_SITES_PATH))
    samples = {
        "NYC": (40.7128, -74.0060),
        "Chicago": (41.8781, -87.6298),
        "LA": (34.0522, -118.2437),
    }

    for name, (lat, lon) in samples.items():
        packet = analyze_point(store, lat=lat, lon=lon)
        print(f"\n=== {name} ({lat}, {lon}) ===")
        print(json.dumps(packet, indent=2))

    check_api_contract()
    print("\nSmoke test complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
