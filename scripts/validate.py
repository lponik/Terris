#!/usr/bin/env python3
"""Validate processed PFAS bundle outputs and write summary.json."""

from __future__ import annotations

import csv
import json
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

REQUIRED_CATEGORY_BY_FILE = {
    "industrial_frs.csv": "industrial_frs",
    "military_base.csv": "military_base",
    "landfill.csv": "landfill",
}

OPTIONAL_CATEGORY_BY_FILE = {
    "superfund_npl.csv": "superfund_npl",
}

ALLOWED_CATEGORIES = set(REQUIRED_CATEGORY_BY_FILE.values()) | set(OPTIONAL_CATEGORY_BY_FILE.values())
ALL_SITES_FILENAME = "all_sites.csv"
SUMMARY_PATH = PROCESSED_DIR / "summary.json"
PROCESS_STATS_PATH = PROCESSED_DIR / "process_stats.json"


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


def valid_coord(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def read_dropped_counts() -> dict[str, int]:
    if not PROCESS_STATS_PATH.exists():
        return {}
    try:
        payload = json.loads(PROCESS_STATS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

    dropped: dict[str, int] = {}
    datasets = payload.get("datasets", {})
    if isinstance(datasets, dict):
        for category, stats in datasets.items():
            if isinstance(stats, dict):
                dropped[category] = int(stats.get("dropped_rows", 0))
    return dropped


def read_process_metadata() -> dict[str, Any]:
    if not PROCESS_STATS_PATH.exists():
        return {}
    try:
        payload = json.loads(PROCESS_STATS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

    datasets = payload.get("datasets", {})
    industrial_stats = datasets.get("industrial_frs", {}) if isinstance(datasets, dict) else {}

    metadata: dict[str, Any] = {
        "industrial_filter_rules": payload.get("industrial_filter_rules"),
        "industrial_low_signal_rules": payload.get("industrial_low_signal_rules"),
        "industrial_registry_ids_count": payload.get("industrial_registry_ids_count"),
        "program_match_counts_by_rule": payload.get("program_match_counts_by_rule"),
        "rows_written_industrial": industrial_stats.get("rows_written"),
        "rows_dropped_invalid_coords": industrial_stats.get("dropped_rows"),
        "low_signal_filter_enabled": payload.get("low_signal_filter_enabled"),
        "removed_low_signal": payload.get("removed_low_signal"),
        "reduction_method": payload.get("reduction_method"),
        "rows_scanned": payload.get("rows_scanned"),
        "rows_stage1_kept": payload.get("rows_stage1_kept"),
        "rows_stage2_kept": payload.get("rows_stage2_kept"),
        "rows_stage2_capped": payload.get("rows_stage2_capped"),
        "top_states_by_count": payload.get("top_states_by_count"),
        "industrial_filter_source": payload.get("industrial_filter_source"),
    }
    return metadata


def read_existing_summary_metadata() -> dict[str, Any]:
    if not SUMMARY_PATH.exists():
        return {}
    try:
        payload = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

    return {
        "industrial_filter_rules": payload.get("industrial_filter_rules"),
        "industrial_low_signal_rules": payload.get("industrial_low_signal_rules"),
        "industrial_registry_ids_count": payload.get("industrial_registry_ids_count"),
        "program_match_counts_by_rule": payload.get("program_match_counts_by_rule"),
        "rows_written_industrial": payload.get("rows_written_industrial"),
        "rows_dropped_invalid_coords": payload.get("rows_dropped_invalid_coords"),
        "low_signal_filter_enabled": payload.get("low_signal_filter_enabled"),
        "removed_low_signal": payload.get("removed_low_signal"),
        "reduction_method": payload.get("reduction_method"),
        "rows_scanned": payload.get("rows_scanned"),
        "rows_stage1_kept": payload.get("rows_stage1_kept"),
        "rows_stage2_kept": payload.get("rows_stage2_kept"),
        "rows_stage2_capped": payload.get("rows_stage2_capped"),
        "top_states_by_count": payload.get("top_states_by_count"),
        "industrial_filter_source": payload.get("industrial_filter_source"),
    }


def validate_file(
    path: Path,
    expected_category: str | None,
    errors: list[str],
    category_stats: dict[str, dict[str, Any]],
    required: bool = True,
) -> int:
    if not path.exists():
        if required:
            errors.append(f"Missing file: {path}")
        return 0

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []

        missing_columns = [col for col in UNIFIED_COLUMNS if col not in fieldnames]
        if missing_columns:
            errors.append(
                f"{path.name} missing required columns: {missing_columns}. "
                f"Found columns: {fieldnames}"
            )
            return 0

        row_count = 0
        for row_num, row in enumerate(reader, start=2):
            row_count += 1
            category = (row.get("category") or "").strip()
            if not category:
                errors.append(f"{path.name}:{row_num} missing category")
                continue
            if category not in ALLOWED_CATEGORIES:
                errors.append(f"{path.name}:{row_num} invalid category '{category}'")
                continue
            if expected_category and category != expected_category:
                errors.append(
                    f"{path.name}:{row_num} expected category '{expected_category}' "
                    f"but found '{category}'"
                )

            if not (row.get("id") or "").strip():
                errors.append(f"{path.name}:{row_num} missing id")

            lat = parse_float(row.get("lat"))
            lon = parse_float(row.get("lon"))
            if not valid_coord(lat, lon):
                errors.append(
                    f"{path.name}:{row_num} invalid coordinates lat={row.get('lat')} lon={row.get('lon')}"
                )
                continue

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

            metadata_json = row.get("metadata_json")
            if metadata_json is None:
                errors.append(f"{path.name}:{row_num} missing metadata_json value")
            else:
                try:
                    json.loads(metadata_json)
                except json.JSONDecodeError:
                    errors.append(f"{path.name}:{row_num} metadata_json is not valid JSON")

    return row_count


def build_summary(
    category_stats: dict[str, dict[str, Any]],
    file_row_counts: dict[str, int],
    dropped_counts: dict[str, int],
    process_metadata: dict[str, Any],
    existing_summary_metadata: dict[str, Any],
) -> dict[str, Any]:
    ordered_categories = ["industrial_frs", "military_base", "landfill", "superfund_npl"]
    counts_by_category = {
        category: int(category_stats.get(category, {}).get("rows", 0))
        for category in ordered_categories
    }

    sanity = {}
    for category in ordered_categories:
        stats = category_stats.get(category)
        if not stats:
            sanity[category] = {
                "min_lat": None,
                "max_lat": None,
                "min_lon": None,
                "max_lon": None,
            }
            continue
        sanity[category] = {
            "min_lat": stats["min_lat"],
            "max_lat": stats["max_lat"],
            "min_lon": stats["min_lon"],
            "max_lon": stats["max_lon"],
        }

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts_by_category": counts_by_category,
        "total_rows": sum(counts_by_category.values()),
        "coordinate_sanity_by_category": sanity,
        "file_row_counts": file_row_counts,
        "dropped_rows_by_category": {
            category: int(dropped_counts.get(category, 0))
            for category in ordered_categories
        },
    }

    industrial_filter_rules = process_metadata.get("industrial_filter_rules")
    if not industrial_filter_rules:
        industrial_filter_rules = existing_summary_metadata.get("industrial_filter_rules")
    if industrial_filter_rules:
        summary["industrial_filter_rules"] = industrial_filter_rules

    industrial_low_signal_rules = process_metadata.get("industrial_low_signal_rules")
    if not industrial_low_signal_rules:
        industrial_low_signal_rules = existing_summary_metadata.get("industrial_low_signal_rules")
    if industrial_low_signal_rules:
        summary["industrial_low_signal_rules"] = industrial_low_signal_rules

    low_signal_filter_enabled = process_metadata.get("low_signal_filter_enabled")
    if low_signal_filter_enabled is None:
        low_signal_filter_enabled = existing_summary_metadata.get("low_signal_filter_enabled")
    if low_signal_filter_enabled is not None:
        summary["low_signal_filter_enabled"] = bool(low_signal_filter_enabled)

    removed_low_signal = process_metadata.get("removed_low_signal")
    if removed_low_signal is None:
        removed_low_signal = existing_summary_metadata.get("removed_low_signal")
    if removed_low_signal is not None:
        summary["removed_low_signal"] = int(removed_low_signal)

    industrial_registry_ids_count = process_metadata.get("industrial_registry_ids_count")
    if industrial_registry_ids_count is None:
        industrial_registry_ids_count = existing_summary_metadata.get("industrial_registry_ids_count")
    if industrial_registry_ids_count is not None:
        summary["industrial_registry_ids_count"] = int(industrial_registry_ids_count)

    program_match_counts_by_rule = process_metadata.get("program_match_counts_by_rule")
    if not program_match_counts_by_rule:
        program_match_counts_by_rule = existing_summary_metadata.get("program_match_counts_by_rule")
    if isinstance(program_match_counts_by_rule, dict):
        summary["program_match_counts_by_rule"] = program_match_counts_by_rule

    rows_written_industrial = process_metadata.get("rows_written_industrial")
    if rows_written_industrial is None:
        rows_written_industrial = existing_summary_metadata.get("rows_written_industrial")
    if rows_written_industrial is not None:
        summary["rows_written_industrial"] = int(rows_written_industrial)

    rows_dropped_invalid_coords = process_metadata.get("rows_dropped_invalid_coords")
    if rows_dropped_invalid_coords is None:
        rows_dropped_invalid_coords = existing_summary_metadata.get("rows_dropped_invalid_coords")
    if rows_dropped_invalid_coords is not None:
        summary["rows_dropped_invalid_coords"] = int(rows_dropped_invalid_coords)

    reduction_method = process_metadata.get("reduction_method")
    if not reduction_method:
        reduction_method = existing_summary_metadata.get("reduction_method")
    if isinstance(reduction_method, dict):
        if summary.get("low_signal_filter_enabled"):
            stage1_value = reduction_method.get("stage1")
            if isinstance(stage1_value, str):
                note = " + low-signal utility/water facility exclusion"
                if note not in stage1_value:
                    reduction_method = dict(reduction_method)
                    reduction_method["stage1"] = stage1_value + note
        summary["reduction_method"] = reduction_method

    rows_scanned = process_metadata.get("rows_scanned")
    if rows_scanned is None:
        rows_scanned = existing_summary_metadata.get("rows_scanned")
    if rows_scanned is not None:
        summary["rows_scanned"] = int(rows_scanned)

    rows_stage1_kept = process_metadata.get("rows_stage1_kept")
    if rows_stage1_kept is None:
        rows_stage1_kept = existing_summary_metadata.get("rows_stage1_kept")
    if rows_stage1_kept is not None:
        summary["rows_stage1_kept"] = int(rows_stage1_kept)

    rows_stage2_kept = process_metadata.get("rows_stage2_kept")
    if rows_stage2_kept is None:
        rows_stage2_kept = existing_summary_metadata.get("rows_stage2_kept")
    if rows_stage2_kept is not None:
        summary["rows_stage2_kept"] = int(rows_stage2_kept)

    rows_stage2_capped = process_metadata.get("rows_stage2_capped")
    if rows_stage2_capped is None:
        rows_stage2_capped = existing_summary_metadata.get("rows_stage2_capped")
    if rows_stage2_capped is not None:
        summary["rows_stage2_capped"] = int(rows_stage2_capped)

    top_states_by_count = process_metadata.get("top_states_by_count")
    if not top_states_by_count:
        top_states_by_count = existing_summary_metadata.get("top_states_by_count")
    if isinstance(top_states_by_count, list):
        summary["top_states_by_count"] = top_states_by_count

    industrial_filter_source = process_metadata.get("industrial_filter_source")
    if not industrial_filter_source:
        industrial_filter_source = existing_summary_metadata.get("industrial_filter_source")
    if industrial_filter_source:
        summary["industrial_filter_source"] = industrial_filter_source

    return summary


def main() -> int:
    errors: list[str] = []
    category_stats: dict[str, dict[str, Any]] = {}
    file_row_counts: dict[str, int] = {}

    for filename, expected_category in REQUIRED_CATEGORY_BY_FILE.items():
        path = PROCESSED_DIR / filename
        file_row_counts[filename] = validate_file(
            path=path,
            expected_category=expected_category,
            errors=errors,
            category_stats=category_stats,
            required=True,
        )

    for filename, expected_category in OPTIONAL_CATEGORY_BY_FILE.items():
        path = PROCESSED_DIR / filename
        file_row_counts[filename] = validate_file(
            path=path,
            expected_category=expected_category,
            errors=errors,
            category_stats=category_stats,
            required=False,
        )

    all_sites_path = PROCESSED_DIR / ALL_SITES_FILENAME
    file_row_counts[ALL_SITES_FILENAME] = validate_file(
        path=all_sites_path,
        expected_category=None,
        errors=errors,
        category_stats={},
    )

    expected_total = sum(file_row_counts[name] for name in REQUIRED_CATEGORY_BY_FILE)
    expected_total += sum(file_row_counts.get(name, 0) for name in OPTIONAL_CATEGORY_BY_FILE)
    all_sites_rows = file_row_counts[ALL_SITES_FILENAME]
    if all_sites_rows != expected_total:
        errors.append(
            f"all_sites.csv row count mismatch: expected {expected_total}, found {all_sites_rows}"
        )

    dropped_counts = read_dropped_counts()
    process_metadata = read_process_metadata()
    existing_summary_metadata = read_existing_summary_metadata()
    summary = build_summary(
        category_stats=category_stats,
        file_row_counts=file_row_counts,
        dropped_counts=dropped_counts,
        process_metadata=process_metadata,
        existing_summary_metadata=existing_summary_metadata,
    )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))

    if errors:
        print("\nVALIDATION FAILED", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        print(f"\nWrote summary to {SUMMARY_PATH}", file=sys.stderr)
        return 1

    print(f"\nValidation passed. Wrote summary to {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
