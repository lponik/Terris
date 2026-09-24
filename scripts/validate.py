#!/usr/bin/env python3
"""Validate the three-category processed bundle and write summary.json."""

from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

UNIFIED_COLUMNS = [
    "id",
    "name",
    "category",
    "lat",
    "lon",
    "state",
    "source",
    "metadata_json",
]

CATEGORY_BY_FILE = {
    "landfill.csv": "landfill",
    "military_base.csv": "military_base",
    "superfund_npl.csv": "superfund_npl",
}
ALLOWED_CATEGORIES = set(CATEGORY_BY_FILE.values())
ALL_SITES_FILENAME = "all_sites.csv"
SUMMARY_PATH = PROCESSED_DIR / "summary.json"
PROCESS_STATS_PATH = PROCESSED_DIR / "process_stats.json"


def parse_float(value: Any) -> float | None:
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def read_rows(
    path: Path,
    *,
    expected_category: str | None,
    errors: list[str],
) -> tuple[list[dict[str, str]], dict[str, dict[str, Any]]]:
    if not path.exists():
        errors.append(f"Missing file: {path}")
        return [], {}

    category_stats: dict[str, dict[str, Any]] = {}
    seen_ids: set[tuple[str, str]] = set()
    rows: list[dict[str, str]] = []

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        if fieldnames != UNIFIED_COLUMNS:
            errors.append(
                f"{path.name} columns must be exactly {UNIFIED_COLUMNS}; found {fieldnames}"
            )
            return [], {}

        for row_num, row in enumerate(reader, start=2):
            rows.append(row)
            category = (row.get("category") or "").strip()
            if category not in ALLOWED_CATEGORIES:
                errors.append(f"{path.name}:{row_num} invalid category {category!r}")
                continue
            if expected_category and category != expected_category:
                errors.append(
                    f"{path.name}:{row_num} expected {expected_category!r}, found {category!r}"
                )

            site_id = (row.get("id") or "").strip()
            name = (row.get("name") or "").strip()
            state = (row.get("state") or "").strip()
            source = (row.get("source") or "").strip()
            if not site_id or not name or not state or not source:
                errors.append(f"{path.name}:{row_num} missing required text value")

            identity = (category, site_id)
            if identity in seen_ids:
                errors.append(f"{path.name}:{row_num} duplicate site id {site_id!r}")
            seen_ids.add(identity)

            lat = parse_float(row.get("lat"))
            lon = parse_float(row.get("lon"))
            if (
                lat is None
                or lon is None
                or not -90.0 <= lat <= 90.0
                or not -180.0 <= lon <= 180.0
                or (lat == 0.0 and lon == 0.0)
            ):
                errors.append(
                    f"{path.name}:{row_num} invalid coordinates lat={row.get('lat')} lon={row.get('lon')}"
                )
                continue

            try:
                metadata = json.loads(row.get("metadata_json") or "")
                if not isinstance(metadata, dict):
                    raise ValueError("metadata must be an object")
            except (json.JSONDecodeError, ValueError):
                errors.append(f"{path.name}:{row_num} metadata_json must be a JSON object")

            stats = category_stats.setdefault(
                category,
                {
                    "rows": 0,
                    "min_lat": lat,
                    "max_lat": lat,
                    "min_lon": lon,
                    "max_lon": lon,
                },
            )
            stats["rows"] += 1
            stats["min_lat"] = min(stats["min_lat"], lat)
            stats["max_lat"] = max(stats["max_lat"], lat)
            stats["min_lon"] = min(stats["min_lon"], lon)
            stats["max_lon"] = max(stats["max_lon"], lon)

    return rows, category_stats


def row_signature(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(row.get(column, "") for column in UNIFIED_COLUMNS)


def load_process_stats() -> dict[str, Any]:
    if not PROCESS_STATS_PATH.exists():
        return {}
    try:
        payload = json.loads(PROCESS_STATS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def main() -> int:
    errors: list[str] = []
    category_rows: list[dict[str, str]] = []
    file_row_counts: dict[str, int] = {}
    coordinate_sanity: dict[str, dict[str, float | None]] = {}

    for filename, category in CATEGORY_BY_FILE.items():
        rows, stats = read_rows(
            PROCESSED_DIR / filename,
            expected_category=category,
            errors=errors,
        )
        category_rows.extend(rows)
        file_row_counts[filename] = len(rows)
        category_stats = stats.get(category)
        coordinate_sanity[category] = {
            "min_lat": category_stats.get("min_lat") if category_stats else None,
            "max_lat": category_stats.get("max_lat") if category_stats else None,
            "min_lon": category_stats.get("min_lon") if category_stats else None,
            "max_lon": category_stats.get("max_lon") if category_stats else None,
        }

    all_rows, _ = read_rows(
        PROCESSED_DIR / ALL_SITES_FILENAME,
        expected_category=None,
        errors=errors,
    )
    file_row_counts[ALL_SITES_FILENAME] = len(all_rows)

    expected_signatures = sorted(row_signature(row) for row in category_rows)
    actual_signatures = sorted(row_signature(row) for row in all_rows)
    if actual_signatures != expected_signatures:
        errors.append("all_sites.csv does not exactly match the three category CSV files")

    process_stats = load_process_stats()
    dataset_stats = process_stats.get("datasets", {})
    if not isinstance(dataset_stats, dict):
        dataset_stats = {}

    counts_by_category = {
        category: file_row_counts[filename]
        for filename, category in CATEGORY_BY_FILE.items()
    }
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts_by_category": counts_by_category,
        "total_rows": sum(counts_by_category.values()),
        "coordinate_sanity_by_category": coordinate_sanity,
        "file_row_counts": file_row_counts,
        "cleaning": {
            category: {
                key: int(value)
                for key, value in stats.items()
                if isinstance(value, int)
            }
            for category, stats in dataset_stats.items()
            if category in ALLOWED_CATEGORIES and isinstance(stats, dict)
        },
    }

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))

    if errors:
        print("\nVALIDATION FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("\nVALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
