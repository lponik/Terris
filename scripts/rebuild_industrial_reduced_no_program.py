#!/usr/bin/env python3
"""Rebuild reduced industrial_frs using only NATIONAL_FACILITY_FILE.CSV.

Reduction pipeline:
1) Stage 1 high-signal filter:
   - NAICS prefix filter if NAICS column exists.
   - Otherwise fallback to facility-name keyword proxy filter.
2) Stage 2 spatial capping:
   - 0.05 degree grid
   - max 10 facilities per cell

This script is offline-only and memory-safe using chunked streaming.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from industrial_keyword_matcher import (
    build_keep_audit,
    build_keep_matcher_rules,
    match_any_keep,
)
from industrial_low_signal_filter import build_low_signal_audit, build_low_signal_rules, match_low_signal_reason

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

FACILITY_FILENAME = "NATIONAL_FACILITY_FILE.CSV"

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

ALLOWED_CATEGORIES = {"industrial_frs", "military_base", "landfill", "superfund_npl"}

GRID_SIZE_DEG = 0.05
MAX_PER_CELL = 5
DEFAULT_PROGRESS_EVERY = 500_000
DEFAULT_CHUNK_SIZE = 100_000

NAICS_PREFIXES = ("21", "22", "31", "32", "33", "324", "325", "326", "562")
KEYWORD_TOKENS = (
    "CHEM",
    "REFIN",
    "PETRO",
    "PLATING",
    "COATING",
    "PULP",
    "PAPER",
    "LANDFILL",
    "WASTE",
    "INCIN",
    "SOLVENT",
    "POLY",
    "FLUOR",
    "AFFF",
    "FIRE FOAM",
)

COLUMN_CANDIDATES = {
    "registry_id": ["REGISTRY_ID", "REGISTRYID"],
    "name": ["PRIMARY_NAME", "PRIMARYNAME", "FACILITY_NAME"],
    "lat": ["LATITUDE83", "LATITUDE"],
    "lon": ["LONGITUDE83", "LONGITUDE"],
    "state": ["STATE_CODE", "STATE"],
    "naics": ["NAICS", "NAICS_CODE", "PRIMARY_NAICS", "NAICSCODE"],
    "sic": ["SIC", "SIC_CODE", "PRIMARY_SIC", "SICCODE"],
    "city": ["CITY_NAME", "CITY"],
    "county": ["COUNTY_NAME", "COUNTY"],
    "postal_code": ["POSTAL_CODE", "ZIP", "ZIP_CODE"],
    "program_code": [
        "PGM_SYS_ACRNMS",
        "PGM_SYS_ACRONYMS",
        "PGM_SYS_ACRNYMS",
        "PROGRAM_CODE",
        "PROGRAM",
        "PROGRAMCODE",
    ],
    "program_name": ["PROGRAM_NAME", "PROGRAMNAME"],
}

INDUSTRIAL_OUTPUT = PROCESSED_DIR / "industrial_frs.csv"
ALL_SITES_OUTPUT = PROCESSED_DIR / "all_sites.csv"
SUMMARY_OUTPUT = PROCESSED_DIR / "summary.json"
PROCESS_STATS_OUTPUT = PROCESSED_DIR / "process_stats.json"
INDUSTRIAL_FILTER_AUDIT_PATH = PROCESSED_DIR / "industrial_filter_audit.json"
INDUSTRIAL_KEEP_AUDIT_PATH = PROCESSED_DIR / "industrial_keep_audit.json"

LANDFILL_PATH = PROCESSED_DIR / "landfill.csv"
MILITARY_PATH = PROCESSED_DIR / "military_base.csv"
SUPERFUND_PATH = PROCESSED_DIR / "superfund_npl.csv"


def init_csv_limits() -> None:
    max_int = sys.maxsize
    while True:
        try:
            csv.field_size_limit(max_int)
            return
        except OverflowError:
            max_int = int(max_int / 10)



def normalize_col(name: str | None) -> str:
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]+", "", str(name).strip().lower())



def pick_column(fieldnames: list[str], candidates: list[str]) -> str | None:
    lookup = {normalize_col(field): field for field in fieldnames if field}
    for candidate in candidates:
        key = normalize_col(candidate)
        if key in lookup:
            return lookup[key]
    return None



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



def is_valid_coord(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0



def clean_registry_id(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".", 1)[0]
    return text



def clean_state(value: Any) -> str:
    if value is None:
        return ""
    state = str(value).strip().upper()
    if len(state) == 2 and state.isalpha():
        return state
    return ""



def detect_required_facility_file(raw_dir: Path) -> Path:
    exact = raw_dir / FACILITY_FILENAME
    if exact.exists():
        return exact

    matches = sorted(
        [path for path in raw_dir.glob("*FACILITY*.CSV") if path.is_file()],
        key=lambda p: (-p.stat().st_size, p.name),
    )
    if matches:
        chosen = matches[0]
        logging.warning("Using fallback facility file match: %s", chosen.name)
        return chosen

    csv_files = sorted(path.name for path in raw_dir.glob("*.csv"))
    raise FileNotFoundError(
        f"Missing required raw file {FACILITY_FILENAME!r} in {raw_dir}. "
        f"Available CSV files: {csv_files if csv_files else 'none'}"
    )



def ensure_overwrite_allowed(path: Path, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}. Re-run with --overwrite")
    if path.exists() and overwrite:
        path.unlink()



def describe_headers(label: str, fieldnames: list[str]) -> None:
    logging.info("%s header detected with %d columns", label, len(fieldnames))
    logging.info("%s header preview: %s", label, fieldnames[:20])



def map_facility_columns(fieldnames: list[str]) -> dict[str, str | None]:
    mapped: dict[str, str | None] = {}
    for key, candidates in COLUMN_CANDIDATES.items():
        mapped[key] = pick_column(fieldnames, candidates)

    required = ["registry_id", "name", "lat", "lon", "state"]
    missing = [key for key in required if mapped.get(key) is None]
    if missing:
        raise ValueError(
            "Missing required facility columns after fallback mapping: "
            f"{missing}. Header columns: {fieldnames}"
        )

    logging.info(
        (
            "Facility column mapping | registry=%s name=%s lat=%s lon=%s state=%s "
            "naics=%s sic=%s city=%s county=%s postal_code=%s program_code=%s program_name=%s"
        ),
        mapped.get("registry_id"),
        mapped.get("name"),
        mapped.get("lat"),
        mapped.get("lon"),
        mapped.get("state"),
        mapped.get("naics"),
        mapped.get("sic"),
        mapped.get("city"),
        mapped.get("county"),
        mapped.get("postal_code"),
        mapped.get("program_code"),
        mapped.get("program_name"),
    )

    return mapped



def stage1_method(mapped_columns: dict[str, str | None]) -> str:
    return "NAICS filter" if mapped_columns.get("naics") else "keyword filter"



def split_codes(value: str) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[^A-Za-z0-9]+", value)
    return [part for part in parts if part]



def match_naics(naics_raw: str) -> bool:
    for token in split_codes(naics_raw):
        upper = token.upper()
        if upper.startswith(NAICS_PREFIXES):
            return True
    return False


def grid_key(lat: float, lon: float) -> tuple[int, int]:
    return (math.floor(lat / GRID_SIZE_DEG), math.floor(lon / GRID_SIZE_DEG))



def flush_chunk(
    *,
    rows: list[dict[str, Any]],
    writer: csv.DictWriter,
    cell_counts: dict[tuple[int, int], int],
    max_per_cell: int,
    state_counter: Counter[str],
) -> tuple[int, int]:
    if not rows:
        return 0, 0

    rows.sort(key=lambda r: (r["cell_key"][0], r["cell_key"][1], r["name"].upper(), r["registry_id"]))

    kept = 0
    capped = 0
    for row in rows:
        cell = row["cell_key"]
        current = cell_counts.get(cell, 0)
        if current >= max_per_cell:
            capped += 1
            continue

        cell_counts[cell] = current + 1
        writer.writerow(
            {
                "id": f"frs_{row['registry_id']}",
                "name": row["name"],
                "category": "industrial_frs",
                "lat": row["lat"],
                "lon": row["lon"],
                "state": row["state"],
                "source": "EPA_FRS_REDUCED_GRIDCAP",
                "metadata_json": json.dumps(row["metadata"], separators=(",", ":")),
            }
        )
        kept += 1
        if row["state"]:
            state_counter[row["state"]] += 1

    rows.clear()
    return kept, capped



def reduce_industrial(
    *,
    facility_path: Path,
    output_path: Path,
    overwrite: bool,
    progress_every: int,
    chunk_size: int,
    low_signal_filter_enabled: bool,
) -> dict[str, Any]:
    ensure_overwrite_allowed(output_path, overwrite)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows_scanned = 0
    rows_missing_registry = 0
    rows_dropped_invalid_coords = 0
    rows_stage1_kept = 0
    rows_stage2_kept = 0
    rows_stage2_capped = 0
    rows_removed_low_signal = 0
    removed_examples: list[str] = []
    keep_keyword_hits: Counter[str] = Counter()

    state_counter: Counter[str] = Counter()
    cell_counts: dict[tuple[int, int], int] = {}
    stage1_buffer: list[dict[str, Any]] = []

    with facility_path.open("r", encoding="utf-8", newline="", errors="replace") as in_handle:
        reader = csv.DictReader(in_handle)
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            raise ValueError(f"Facility file has no header row: {facility_path}")

        describe_headers("Facility file", fieldnames)
        mapped = map_facility_columns(fieldnames)
        stage1 = stage1_method(mapped)
        logging.info("Stage 1 method selected: %s", stage1)

        with output_path.open("a", encoding="utf-8", newline="") as out_handle:
            writer = csv.DictWriter(out_handle, fieldnames=UNIFIED_COLUMNS)
            if out_handle.tell() == 0:
                writer.writeheader()

            for row in reader:
                rows_scanned += 1
                if progress_every > 0 and rows_scanned % progress_every == 0:
                    logging.info(
                        (
                            "Progress | rows_scanned=%s rows_stage1_kept=%s rows_stage2_kept=%s "
                            "rows_stage2_capped=%s active_cells=%s"
                        ),
                        rows_scanned,
                        rows_stage1_kept,
                        rows_stage2_kept,
                        rows_stage2_capped,
                        len(cell_counts),
                    )

                registry_id = clean_registry_id(row.get(mapped["registry_id"], ""))
                if not registry_id:
                    rows_missing_registry += 1
                    continue

                lat = parse_float(row.get(mapped["lat"], ""))
                lon = parse_float(row.get(mapped["lon"], ""))
                if not is_valid_coord(lat, lon):
                    rows_dropped_invalid_coords += 1
                    continue

                name = str(row.get(mapped["name"], "")).strip()
                if not name:
                    name = f"FRS Facility {registry_id}"

                keep_stage1 = False
                matched_keep_keyword: str | None = None
                if mapped.get("naics"):
                    naics_value = str(row.get(mapped["naics"], "")).strip()
                    keep_stage1 = match_naics(naics_value)
                else:
                    matched_keep_keyword = match_any_keep(name, KEYWORD_TOKENS)
                    keep_stage1 = matched_keep_keyword is not None

                if not keep_stage1:
                    continue

                rows_stage1_kept += 1
                if matched_keep_keyword:
                    keep_keyword_hits[matched_keep_keyword] += 1

                program_values: list[str] = []
                if mapped.get("program_code"):
                    value = row.get(mapped["program_code"], "")
                    if value:
                        program_values.append(str(value))
                if mapped.get("program_name"):
                    value = row.get(mapped["program_name"], "")
                    if value:
                        program_values.append(str(value))

                naics_values: list[str] = []
                if mapped.get("naics"):
                    naics_value = str(row.get(mapped["naics"], "")).strip()
                    if naics_value:
                        naics_values.append(naics_value)

                if low_signal_filter_enabled:
                    low_signal_reason = match_low_signal_reason(
                        facility_name=name,
                        program_values=program_values,
                        naics_values=naics_values,
                    )
                    if low_signal_reason:
                        rows_removed_low_signal += 1
                        if len(removed_examples) < 20:
                            removed_examples.append(name)
                        continue

                state = clean_state(row.get(mapped["state"], ""))
                metadata: dict[str, str] = {}

                if mapped.get("city"):
                    city = str(row.get(mapped["city"], "")).strip()
                    if city:
                        metadata["city"] = city
                if mapped.get("county"):
                    county = str(row.get(mapped["county"], "")).strip()
                    if county:
                        metadata["county"] = county
                if mapped.get("postal_code"):
                    postal_code = str(row.get(mapped["postal_code"], "")).strip()
                    if postal_code:
                        metadata["postal_code"] = postal_code
                if mapped.get("naics"):
                    naics_val = str(row.get(mapped["naics"], "")).strip()
                    if naics_val:
                        metadata["naics"] = naics_val
                if mapped.get("sic"):
                    sic_val = str(row.get(mapped["sic"], "")).strip()
                    if sic_val:
                        metadata["sic"] = sic_val

                stage1_buffer.append(
                    {
                        "registry_id": registry_id,
                        "name": name,
                        "lat": lat,
                        "lon": lon,
                        "state": state,
                        "cell_key": grid_key(lat, lon),
                        "metadata": metadata,
                    }
                )

                if len(stage1_buffer) >= chunk_size:
                    kept, capped = flush_chunk(
                        rows=stage1_buffer,
                        writer=writer,
                        cell_counts=cell_counts,
                        max_per_cell=MAX_PER_CELL,
                        state_counter=state_counter,
                    )
                    rows_stage2_kept += kept
                    rows_stage2_capped += capped

            kept, capped = flush_chunk(
                rows=stage1_buffer,
                writer=writer,
                cell_counts=cell_counts,
                max_per_cell=MAX_PER_CELL,
                state_counter=state_counter,
            )
            rows_stage2_kept += kept
            rows_stage2_capped += capped

    top_states = [
        {"state": state, "count": count}
        for state, count in sorted(state_counter.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]

    stage1_label = stage1
    if low_signal_filter_enabled:
        stage1_label = f"{stage1} + low-signal utility/water facility exclusion"

    keep_top_keywords = [
        {"keyword": keyword, "count": count}
        for keyword, count in sorted(keep_keyword_hits.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]

    stats = {
        "rows_scanned": rows_scanned,
        "rows_missing_registry": rows_missing_registry,
        "rows_dropped_invalid_coords": rows_dropped_invalid_coords,
        "rows_stage1_kept": rows_stage1_kept,
        "rows_stage2_kept": rows_stage2_kept,
        "rows_stage2_capped": rows_stage2_capped,
        "stage1_method": stage1_label,
        "stage2_method": f"grid cap {GRID_SIZE_DEG}deg max {MAX_PER_CELL}/cell",
        "grid_size_degrees": GRID_SIZE_DEG,
        "max_per_cell": MAX_PER_CELL,
        "nonempty_grid_cells": len(cell_counts),
        "top_states_by_count": top_states,
        "low_signal_filter_enabled": low_signal_filter_enabled,
        "removed_low_signal": rows_removed_low_signal,
        "removed_examples": removed_examples,
        "keep_keyword_hits_by_keyword": dict(sorted(keep_keyword_hits.items())),
        "keep_top_keywords": keep_top_keywords,
    }
    logging.info("Industrial reduction complete | %s", stats)
    return stats



def validate_unified_header(path: Path) -> None:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
    missing = [col for col in UNIFIED_COLUMNS if col not in fieldnames]
    if missing:
        raise ValueError(f"{path} missing required unified columns {missing}. Found {fieldnames}")



def rebuild_all_sites(overwrite: bool) -> dict[str, int]:
    ensure_overwrite_allowed(ALL_SITES_OUTPUT, overwrite)

    input_specs = [
        ("landfill", LANDFILL_PATH),
        ("military_base", MILITARY_PATH),
        ("industrial_frs", INDUSTRIAL_OUTPUT),
    ]
    if SUPERFUND_PATH.exists():
        input_specs.append(("superfund_npl", SUPERFUND_PATH))

    for category, path in input_specs:
        if not path.exists():
            raise FileNotFoundError(
                f"Cannot rebuild all_sites.csv because {path} is missing for category {category}."
            )
        validate_unified_header(path)

    counts = {"landfill": 0, "military_base": 0, "industrial_frs": 0, "superfund_npl": 0}

    with ALL_SITES_OUTPUT.open("a", encoding="utf-8", newline="") as out_handle:
        writer = csv.DictWriter(out_handle, fieldnames=UNIFIED_COLUMNS)
        if out_handle.tell() == 0:
            writer.writeheader()

        for expected_category, in_path in input_specs:
            with in_path.open("r", encoding="utf-8", newline="") as in_handle:
                reader = csv.DictReader(in_handle)
                for row_num, row in enumerate(reader, start=2):
                    category = str(row.get("category", "")).strip()
                    if category != expected_category:
                        raise ValueError(
                            f"{in_path}:{row_num} expected category {expected_category!r}, found {category!r}"
                        )
                    if category not in ALLOWED_CATEGORIES:
                        raise ValueError(
                            f"{in_path}:{row_num} invalid category {category!r}. Allowed: {sorted(ALLOWED_CATEGORIES)}"
                        )

                    writer.writerow({col: row.get(col, "") for col in UNIFIED_COLUMNS})
                    counts[expected_category] += 1

    logging.info("Rebuilt all_sites.csv with category counts: %s", counts)
    return counts



def write_summary(category_counts: dict[str, int], reduction_stats: dict[str, Any], facility_file: Path) -> None:
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts_by_category": {
            "landfill": int(category_counts.get("landfill", 0)),
            "military_base": int(category_counts.get("military_base", 0)),
            "industrial_frs": int(category_counts.get("industrial_frs", 0)),
            "superfund_npl": int(category_counts.get("superfund_npl", 0)),
        },
        "total_rows": int(sum(category_counts.values())),
        "reduction_method": {
            "stage1": reduction_stats.get("stage1_method"),
            "stage2": reduction_stats.get("stage2_method"),
        },
        "rows_scanned": int(reduction_stats.get("rows_scanned", 0)),
        "rows_stage1_kept": int(reduction_stats.get("rows_stage1_kept", 0)),
        "rows_stage2_kept": int(reduction_stats.get("rows_stage2_kept", 0)),
        "rows_stage2_capped": int(reduction_stats.get("rows_stage2_capped", 0)),
        "rows_dropped_invalid_coords": int(reduction_stats.get("rows_dropped_invalid_coords", 0)),
        "low_signal_filter_enabled": bool(reduction_stats.get("low_signal_filter_enabled", False)),
        "removed_low_signal": int(reduction_stats.get("removed_low_signal", 0)),
        "industrial_low_signal_rules": build_low_signal_rules(),
        "industrial_keep_keywords": list(KEYWORD_TOKENS),
        "industrial_keep_matcher_rules": build_keep_matcher_rules(),
        "keep_top_keywords": reduction_stats.get("keep_top_keywords", []),
        "top_states_by_count": reduction_stats.get("top_states_by_count", []),
        "raw_files": {
            "facility_file": facility_file.name,
        },
    }

    SUMMARY_OUTPUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logging.info("Wrote summary to %s", SUMMARY_OUTPUT)



def write_process_stats(category_counts: dict[str, int], reduction_stats: dict[str, Any]) -> None:
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "datasets": {
            "industrial_frs": {
                "rows_written": int(reduction_stats.get("rows_stage2_kept", 0)),
                "dropped_rows": int(reduction_stats.get("rows_dropped_invalid_coords", 0)),
            },
            "landfill": {
                "rows_written": int(category_counts.get("landfill", 0)),
                "dropped_rows": 0,
            },
            "military_base": {
                "rows_written": int(category_counts.get("military_base", 0)),
                "dropped_rows": 0,
            },
            "superfund_npl": {
                "rows_written": int(category_counts.get("superfund_npl", 0)),
                "dropped_rows": 0,
            },
        },
        "reduction_method": {
            "stage1": reduction_stats.get("stage1_method"),
            "stage2": reduction_stats.get("stage2_method"),
        },
        "rows_scanned": int(reduction_stats.get("rows_scanned", 0)),
        "rows_stage1_kept": int(reduction_stats.get("rows_stage1_kept", 0)),
        "rows_stage2_kept": int(reduction_stats.get("rows_stage2_kept", 0)),
        "rows_stage2_capped": int(reduction_stats.get("rows_stage2_capped", 0)),
        "low_signal_filter_enabled": bool(reduction_stats.get("low_signal_filter_enabled", False)),
        "removed_low_signal": int(reduction_stats.get("removed_low_signal", 0)),
        "industrial_low_signal_rules": build_low_signal_rules(),
        "industrial_keep_keywords": list(KEYWORD_TOKENS),
        "industrial_keep_matcher_rules": build_keep_matcher_rules(),
        "keep_top_keywords": reduction_stats.get("keep_top_keywords", []),
        "top_states_by_count": reduction_stats.get("top_states_by_count", []),
    }

    PROCESS_STATS_OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logging.info("Wrote process stats to %s", PROCESS_STATS_OUTPUT)


def write_low_signal_audit(
    *,
    removed_low_signal: int,
    removed_examples: list[str],
    enabled: bool,
) -> None:
    payload = build_low_signal_audit(
        method="rebuild_industrial_reduced_no_program.py",
        removed_low_signal=removed_low_signal,
        removed_examples=removed_examples,
        enabled=enabled,
    )
    INDUSTRIAL_FILTER_AUDIT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logging.info("Wrote industrial low-signal audit to %s", INDUSTRIAL_FILTER_AUDIT_PATH)


def write_keep_audit(
    *,
    kept_rows: int,
    keep_keyword_hits_by_keyword: dict[str, int],
) -> None:
    payload = build_keep_audit(
        method="rebuild_industrial_reduced_no_program.py",
        kept_rows=kept_rows,
        keep_keyword_hits=keep_keyword_hits_by_keyword,
        keep_keywords=KEYWORD_TOKENS,
    )
    try:
        INDUSTRIAL_KEEP_AUDIT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logging.info("Wrote industrial keep audit to %s", INDUSTRIAL_KEEP_AUDIT_PATH)
    except OSError as exc:
        logging.warning("Unable to write industrial keep audit: %s", exc)



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild reduced industrial_frs using only NATIONAL_FACILITY_FILE.CSV."
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files.")
    parser.add_argument(
        "--progress-every",
        type=int,
        default=DEFAULT_PROGRESS_EVERY,
        help=f"Log progress every N scanned rows (default: {DEFAULT_PROGRESS_EVERY}).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Chunk size for deterministic intra-chunk ordering (default: {DEFAULT_CHUNK_SIZE}).",
    )
    parser.add_argument(
        "--no-low-signal-filter",
        action="store_true",
        help="Disable low-signal utility/water facility exclusion.",
    )
    return parser.parse_args()



def main() -> int:
    args = parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s | %(message)s")
    init_csv_limits()

    if not RAW_DIR.exists():
        raise FileNotFoundError(f"Missing raw directory: {RAW_DIR}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if not args.overwrite:
        existing_outputs = [
            path for path in [INDUSTRIAL_OUTPUT, ALL_SITES_OUTPUT, SUMMARY_OUTPUT] if path.exists()
        ]
        if existing_outputs:
            raise FileExistsError(
                "Refusing to overwrite existing output files without --overwrite: "
                + ", ".join(str(path) for path in existing_outputs)
            )

    facility_path = detect_required_facility_file(RAW_DIR)
    logging.info("Using facility file: %s", facility_path)

    reduction_stats = reduce_industrial(
        facility_path=facility_path,
        output_path=INDUSTRIAL_OUTPUT,
        overwrite=args.overwrite,
        progress_every=args.progress_every,
        chunk_size=max(1, args.chunk_size),
        low_signal_filter_enabled=not args.no_low_signal_filter,
    )

    category_counts = rebuild_all_sites(overwrite=args.overwrite)

    write_summary(
        category_counts=category_counts,
        reduction_stats=reduction_stats,
        facility_file=facility_path,
    )
    write_process_stats(
        category_counts=category_counts,
        reduction_stats=reduction_stats,
    )
    write_low_signal_audit(
        removed_low_signal=int(reduction_stats.get("removed_low_signal", 0)),
        removed_examples=list(reduction_stats.get("removed_examples", [])),
        enabled=bool(reduction_stats.get("low_signal_filter_enabled", False)),
    )
    write_keep_audit(
        kept_rows=int(reduction_stats.get("rows_stage2_kept", 0)),
        keep_keyword_hits_by_keyword=dict(reduction_stats.get("keep_keyword_hits_by_keyword", {})),
    )

    logging.info("Industrial reduction pipeline complete.")
    logging.info("Final category counts: %s", category_counts)
    logging.info(
        "Low-signal exclusion | input_rows=%s removed_low_signal=%s remaining_rows=%s",
        reduction_stats.get("rows_scanned", 0),
        reduction_stats.get("removed_low_signal", 0),
        reduction_stats.get("rows_stage2_kept", 0),
    )
    logging.info(
        "Reduction totals | rows_scanned=%s stage1_kept=%s stage2_kept=%s",
        reduction_stats.get("rows_scanned", 0),
        reduction_stats.get("rows_stage1_kept", 0),
        reduction_stats.get("rows_stage2_kept", 0),
    )
    logging.info("Keep keyword hits (top 10) | %s", reduction_stats.get("keep_top_keywords", []))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
