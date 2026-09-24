#!/usr/bin/env python3
"""Normalize and rebuild the three-category Terris runtime dataset."""

from __future__ import annotations

import csv
import json
import math
import os
import re
from collections import defaultdict
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

CATEGORY_FILES = {
    "landfill": PROCESSED_DIR / "landfill.csv",
    "military_base": PROCESSED_DIR / "military_base.csv",
    "superfund_npl": PROCESSED_DIR / "superfund_npl.csv",
}

US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA", "HI",
    "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD", "ME", "MI", "MN",
    "MO", "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA",
    "WI", "WV", "WY", "PR", "VI", "GU", "AS", "MP",
}


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def parse_coordinate(value: Any) -> float | None:
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def parse_metadata(value: Any) -> dict[str, Any] | None:
    try:
        parsed = json.loads(str(value or "{}"))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def choose_representative(rows: list[dict[str, Any]]) -> dict[str, Any]:
    representative = dict(rows[0])
    if len(rows) == 1:
        return representative

    representative["lat"] = sum(float(row["lat"]) for row in rows) / len(rows)
    representative["lon"] = sum(float(row["lon"]) for row in rows) / len(rows)
    metadata = dict(representative["metadata"])
    metadata["combined_boundary_parts"] = len(rows)
    metadata["representative_point"] = "mean_of_boundary_part_centroids"
    representative["metadata"] = metadata
    return representative


def clean_category(category: str, path: Path) -> tuple[list[dict[str, str]], dict[str, int]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required processed file: {path}")

    stats = {
        "input_rows": 0,
        "rows_written": 0,
        "dropped_rows": 0,
        "dropped_invalid_category": 0,
        "dropped_missing_required": 0,
        "dropped_invalid_coordinates": 0,
        "dropped_outside_coverage": 0,
        "dropped_invalid_metadata": 0,
        "collapsed_duplicate_ids": 0,
    }
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in UNIFIED_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path.name} is missing columns: {missing}")

        for row in reader:
            stats["input_rows"] += 1
            row_category = clean_text(row.get("category"))
            if row_category != category:
                stats["dropped_invalid_category"] += 1
                continue

            site_id = clean_text(row.get("id"))
            name = clean_text(row.get("name"))
            state = clean_text(row.get("state")).upper()
            source = clean_text(row.get("source"))
            if not site_id or not name or not state or not source:
                stats["dropped_missing_required"] += 1
                continue
            if state not in US_STATE_CODES:
                stats["dropped_outside_coverage"] += 1
                continue

            lat = parse_coordinate(row.get("lat"))
            lon = parse_coordinate(row.get("lon"))
            if (
                lat is None
                or lon is None
                or not -90.0 <= lat <= 90.0
                or not -180.0 <= lon <= 180.0
                or (lat == 0.0 and lon == 0.0)
            ):
                stats["dropped_invalid_coordinates"] += 1
                continue

            metadata = parse_metadata(row.get("metadata_json"))
            if metadata is None:
                stats["dropped_invalid_metadata"] += 1
                continue

            grouped[site_id].append(
                {
                    "id": site_id,
                    "name": name,
                    "category": category,
                    "lat": lat,
                    "lon": lon,
                    "state": state,
                    "source": source,
                    "metadata": metadata,
                }
            )

    cleaned: list[dict[str, str]] = []
    for site_id in sorted(grouped):
        candidates = grouped[site_id]
        representative = choose_representative(candidates)
        stats["collapsed_duplicate_ids"] += len(candidates) - 1
        cleaned.append(
            {
                "id": representative["id"],
                "name": representative["name"],
                "category": representative["category"],
                "lat": f"{float(representative['lat']):.8f}",
                "lon": f"{float(representative['lon']):.8f}",
                "state": representative["state"],
                "source": representative["source"],
                "metadata_json": json.dumps(
                    representative["metadata"],
                    separators=(",", ":"),
                    ensure_ascii=True,
                    sort_keys=True,
                ),
            }
        )

    cleaned.sort(key=lambda row: (row["state"], row["name"].casefold(), row["id"]))
    stats["rows_written"] = len(cleaned)
    stats["dropped_rows"] = stats["input_rows"] - stats["rows_written"]
    return cleaned, stats


def write_csv_atomic(path: Path, rows: list[dict[str, str]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=UNIFIED_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def main() -> int:
    cleaned_by_category: dict[str, list[dict[str, str]]] = {}
    stats_by_category: dict[str, dict[str, int]] = {}

    for category, path in CATEGORY_FILES.items():
        cleaned, stats = clean_category(category, path)
        cleaned_by_category[category] = cleaned
        stats_by_category[category] = stats

    for category, path in CATEGORY_FILES.items():
        write_csv_atomic(path, cleaned_by_category[category])

    all_rows = [
        row
        for category in CATEGORY_FILES
        for row in cleaned_by_category[category]
    ]
    write_csv_atomic(PROCESSED_DIR / "all_sites.csv", all_rows)

    process_stats = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "pipeline": "clean_processed_data.py",
        "categories": list(CATEGORY_FILES),
        "datasets": stats_by_category,
        "all_sites_rows": len(all_rows),
    }
    (PROCESSED_DIR / "process_stats.json").write_text(
        json.dumps(process_stats, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(process_stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
