#!/usr/bin/env python3
"""Smoke test for end-to-end PFAS distance/risk scoring data bundle."""

from __future__ import annotations

import csv
import json
import math
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ALL_SITES_PATH = REPO_ROOT / "data" / "processed" / "all_sites.csv"
SUMMARY_PATH = REPO_ROOT / "data" / "processed" / "summary.json"
RAW_DIR = REPO_ROOT / "data" / "raw"

CATEGORIES = ["industrial_frs", "military_base", "landfill", "superfund_npl"]


# Great-circle distance in miles.
def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.7613
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return radius_miles * c


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def analyze_point(lat: float, lon: float, radii_miles: tuple[int, ...] = (5, 10)) -> dict[str, Any]:
    if not ALL_SITES_PATH.exists():
        raise FileNotFoundError(
            f"Missing processed file: {ALL_SITES_PATH}. Run scripts/process_all.py first."
        )

    nearest: dict[str, dict[str, Any] | None] = {category: None for category in CATEGORIES}
    counts = {
        str(radius): {category: 0 for category in CATEGORIES}
        for radius in sorted(radii_miles)
    }
    top_three: dict[str, list[dict[str, Any]]] = {category: [] for category in CATEGORIES}

    with ALL_SITES_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            category = (row.get("category") or "").strip()
            if category not in CATEGORIES:
                continue

            site_lat = parse_float(row.get("lat"))
            site_lon = parse_float(row.get("lon"))
            if site_lat is None or site_lon is None:
                continue

            distance = haversine_miles(lat, lon, site_lat, site_lon)

            current_nearest = nearest[category]
            if current_nearest is None or distance < current_nearest["distance_miles"]:
                nearest[category] = {
                    "id": row.get("id") or "",
                    "name": row.get("name") or "",
                    "distance_miles": distance,
                }

            for radius in radii_miles:
                if distance <= radius:
                    counts[str(radius)][category] += 1

            items = top_three[category]
            items.append(
                {
                    "id": row.get("id") or "",
                    "name": row.get("name") or "",
                    "distance_miles": distance,
                }
            )
            items.sort(key=lambda entry: entry["distance_miles"])
            del items[3:]

    return {
        "query_point": {"lat": lat, "lon": lon},
        "nearest_distances_miles": {
            category: (
                round(nearest[category]["distance_miles"], 4)
                if nearest[category] is not None
                else None
            )
            for category in CATEGORIES
        },
        "counts_within_radius": counts,
        "top_3_nearest_by_category": {
            category: [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "distance_miles": round(item["distance_miles"], 4),
                }
                for item in top_three[category]
            ]
            for category in CATEGORIES
        },
    }


def _superfund_gdb_present() -> bool:
    return any(path.is_dir() and path.suffix.lower() == ".gdb" for path in RAW_DIR.glob("*.gdb"))


def assert_superfund_in_summary_if_present() -> None:
    if not _superfund_gdb_present():
        return
    if not SUMMARY_PATH.exists():
        raise FileNotFoundError(f"Missing summary file: {SUMMARY_PATH}. Run scripts/validate.py first.")

    payload = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    counts = payload.get("counts_by_category", {})
    if not isinstance(counts, dict) or "superfund_npl" not in counts:
        raise AssertionError("summary.json missing counts_by_category.superfund_npl while .gdb is present.")


def check_api_superfund_fields() -> None:
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
        print("Backend not reachable at http://127.0.0.1:8000; skipping API superfund smoke check.")
        return

    signals = payload.get("signals", {})
    evidence = payload.get("evidence", {})
    breakdown = payload.get("score", {}).get("breakdown", {})

    missing = []
    if "nearest_superfund_npl_miles" not in signals:
        missing.append("signals.nearest_superfund_npl_miles")
    if "superfund_count_3mi" not in signals:
        missing.append("signals.superfund_count_3mi")
    if "superfund_npl" not in evidence:
        missing.append("evidence.superfund_npl")
    if "superfund_proximity" not in breakdown:
        missing.append("score.breakdown.superfund_proximity")

    if missing:
        raise AssertionError(f"Analyze response missing expected superfund fields: {missing}")


def main() -> int:
    assert_superfund_in_summary_if_present()

    samples = {
        "NYC": (40.7128, -74.0060),
        "Chicago": (41.8781, -87.6298),
        "LA": (34.0522, -118.2437),
    }

    for name, (lat, lon) in samples.items():
        packet = analyze_point(lat=lat, lon=lon)
        print(f"\n=== {name} ({lat}, {lon}) ===")
        print(json.dumps(packet, indent=2))

    check_api_superfund_fields()

    print("\nSmoke test complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
