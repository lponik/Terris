#!/usr/bin/env python3
"""Rebuild filtered industrial data using FRS National Program participation (Option A).

Offline-only, memory-safe streaming implementation.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
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

FACILITY_EXACT_NAME = "NATIONAL_FACILITY_FILE.CSV"
PROGRAM_EXACT_NAME = "NATIONAL_PROGRAM_FILE.CSV"

FACILITY_FALLBACK_PATTERNS = ["*NATIONAL*FACILITY*FILE*.CSV", "*FACILITY*FILE*.CSV", "*FACILITY*.CSV"]
PROGRAM_FALLBACK_PATTERNS = ["*NATIONAL*PROGRAM*FILE*.CSV", "*PROGRAM*FILE*.CSV", "*PROGRAM*.CSV"]

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

CATEGORY_VALUES = {
    "landfill",
    "military_base",
    "industrial_frs",
    "superfund_npl",
}

PROCESS_STATS_PATH = PROCESSED_DIR / "process_stats.json"
SUMMARY_PATH = PROCESSED_DIR / "summary.json"
SUPERFUND_PATH = PROCESSED_DIR / "superfund_npl.csv"
INDUSTRIAL_FILTER_AUDIT_PATH = PROCESSED_DIR / "industrial_filter_audit.json"
INDUSTRIAL_KEEP_AUDIT_PATH = PROCESSED_DIR / "industrial_keep_audit.json"

PROGRAM_FILTER_RULES = [
    "TRI",
    "TOXIC RELEASE",
    "RCRA",
    "CERCLA",
    "SUPERFUND",
    "SUPER FUND",
    "NPL",
]

PROGRAM_RULE_LABELS = {
    "TRI": "TRI",
    "TOXIC RELEASE": "TOXIC_RELEASE",
    "RCRA": "RCRA",
    "CERCLA": "CERCLA",
    "SUPERFUND": "SUPERFUND",
    "SUPER FUND": "SUPERFUND_SPACE",
    "NPL": "NPL",
}

KEEP_KEYWORDS = (
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

FACILITY_COLUMN_CANDIDATES = {
    "registry_id": ["REGISTRY_ID", "REGISTRYID"],
    "name": ["PRIMARY_NAME", "PRIMARYNAME", "FACILITY_NAME"],
    "lat": ["LATITUDE83", "LATITUDE"],
    "lon": ["LONGITUDE83", "LONGITUDE"],
    "state": ["STATE_CODE", "STATE"],
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
    "naics": ["NAICS", "NAICS_CODE", "PRIMARY_NAICS", "NAICSCODE"],
    "sic": ["SIC", "SIC_CODE", "PRIMARY_SIC", "SICCODE"],
}

PROGRAM_COLUMN_CANDIDATES = {
    "registry_id": ["REGISTRY_ID", "REGISTRYID"],
    "program_code": ["PROGRAM_CODE", "PROGRAM", "PROGRAMCODE"],
    "program_name": ["PROGRAM_NAME", "PROGRAMNAME"],
}


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



def detect_raw_file(raw_dir: Path, exact_name: str, fallback_patterns: list[str]) -> Path:
    exact_path = raw_dir / exact_name
    if exact_path.exists():
        return exact_path

    lower_exact = exact_name.lower()
    case_insensitive_match: list[Path] = []
    for path in raw_dir.iterdir():
        if path.is_file() and path.name.lower() == lower_exact:
            case_insensitive_match.append(path)
    if case_insensitive_match:
        case_insensitive_match.sort(key=lambda p: p.name)
        return case_insensitive_match[0]

    matches: dict[Path, None] = {}
    for pattern in fallback_patterns:
        for path in raw_dir.glob(pattern):
            if path.is_file():
                matches[path] = None

    if matches:
        ordered = sorted(matches.keys(), key=lambda p: (-p.stat().st_size, p.name))
        chosen = ordered[0]
        logging.warning(
            "Using fallback raw file match for %s: %s",
            exact_name,
            chosen.name,
        )
        return chosen

    csv_files = sorted(path.name for path in raw_dir.iterdir() if path.is_file() and path.suffix.lower() == ".csv")
    raise FileNotFoundError(
        f"Missing required raw file {exact_name!r} in {raw_dir}. "
        f"Available CSV files: {csv_files if csv_files else 'none'}"
    )



def detect_optional_raw_file(raw_dir: Path, exact_name: str, fallback_patterns: list[str]) -> Path | None:
    try:
        return detect_raw_file(raw_dir, exact_name, fallback_patterns)
    except FileNotFoundError:
        logging.warning(
            "Optional raw file %s not found. Falling back to facility-level program filtering.",
            exact_name,
        )
        return None


def describe_headers(label: str, fieldnames: list[str]) -> None:
    preview = fieldnames[:20]
    logging.info("%s header detected with %d columns", label, len(fieldnames))
    logging.info("%s header preview: %s", label, preview)



def find_program_columns(fieldnames: list[str]) -> dict[str, Any]:
    registry_col = pick_column(fieldnames, PROGRAM_COLUMN_CANDIDATES["registry_id"])
    program_code_col = pick_column(fieldnames, PROGRAM_COLUMN_CANDIDATES["program_code"])
    program_name_col = pick_column(fieldnames, PROGRAM_COLUMN_CANDIDATES["program_name"])

    if registry_col is None:
        raise ValueError(
            "Could not find registry ID column in NATIONAL_PROGRAM_FILE.CSV. "
            f"Tried {PROGRAM_COLUMN_CANDIDATES['registry_id']}"
        )

    fallback_text_columns: list[str] = []
    if program_code_col is None and program_name_col is None:
        fallback_text_columns = [col for col in fieldnames if col != registry_col]
        logging.warning(
            "Program code/name columns not found. Falling back to scanning all non-registry columns for matches."
        )

    logging.info(
        "Program column mapping | registry=%s program_code=%s program_name=%s",
        registry_col,
        program_code_col,
        program_name_col,
    )

    return {
        "registry_col": registry_col,
        "program_code_col": program_code_col,
        "program_name_col": program_name_col,
        "fallback_text_columns": fallback_text_columns,
    }



def find_facility_columns(fieldnames: list[str]) -> dict[str, str | None]:
    mapped: dict[str, str | None] = {}
    for key, candidates in FACILITY_COLUMN_CANDIDATES.items():
        mapped[key] = pick_column(fieldnames, candidates)

    required = ["registry_id", "lat", "lon"]
    missing = [key for key in required if mapped.get(key) is None]
    if missing:
        raise ValueError(
            "Missing required facility columns after fallback mapping: "
            f"{missing}. Facility header columns: {fieldnames}"
        )

    logging.info(
        (
            "Facility column mapping | registry=%s name=%s lat=%s lon=%s state=%s "
            "city=%s county=%s postal_code=%s program_code=%s program_name=%s naics=%s sic=%s"
        ),
        mapped.get("registry_id"),
        mapped.get("name"),
        mapped.get("lat"),
        mapped.get("lon"),
        mapped.get("state"),
        mapped.get("city"),
        mapped.get("county"),
        mapped.get("postal_code"),
        mapped.get("program_code"),
        mapped.get("program_name"),
        mapped.get("naics"),
        mapped.get("sic"),
    )

    return mapped



def match_program_rule(program_code: Any, program_name: Any, fallback_text: str = "") -> str | None:
    code_text = str(program_code or "")
    name_text = str(program_name or "")
    haystack = f"{code_text} {name_text} {fallback_text}".upper()

    for token in PROGRAM_FILTER_RULES:
        if token in haystack:
            return PROGRAM_RULE_LABELS[token]
    return None



def build_eligible_registry_ids(program_path: Path, progress_every: int) -> tuple[set[str], dict[str, Any]]:
    eligible_registry_ids: set[str] = set()
    rule_hits: Counter[str] = Counter()

    rows_scanned = 0
    rows_matched = 0
    rows_missing_registry = 0

    with program_path.open("r", encoding="utf-8", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            raise ValueError(f"Program file has no header row: {program_path}")

        describe_headers("Program file", fieldnames)
        columns = find_program_columns(fieldnames)

        for row in reader:
            rows_scanned += 1
            if progress_every > 0 and rows_scanned % progress_every == 0:
                logging.info(
                    "Program scan progress | rows_scanned=%s matched_rows=%s unique_registry_ids=%s",
                    rows_scanned,
                    rows_matched,
                    len(eligible_registry_ids),
                )

            registry_id = clean_registry_id(row.get(columns["registry_col"], ""))
            if not registry_id:
                rows_missing_registry += 1
                continue

            fallback_text = ""
            fallback_cols: list[str] = columns["fallback_text_columns"]
            if fallback_cols:
                fallback_text = " ".join(str(row.get(col, "")) for col in fallback_cols)

            rule = match_program_rule(
                program_code=row.get(columns["program_code_col"], "") if columns["program_code_col"] else "",
                program_name=row.get(columns["program_name_col"], "") if columns["program_name_col"] else "",
                fallback_text=fallback_text,
            )
            if rule is None:
                continue

            rows_matched += 1
            rule_hits[rule] += 1
            eligible_registry_ids.add(registry_id)

    stats = {
        "program_rows_scanned": rows_scanned,
        "program_rows_matched": rows_matched,
        "program_rows_missing_registry": rows_missing_registry,
        "industrial_registry_ids_count": len(eligible_registry_ids),
        "program_match_counts_by_rule": dict(sorted(rule_hits.items())),
    }

    logging.info("Program scan complete | %s", stats)
    return eligible_registry_ids, stats



def ensure_overwrite_allowed(path: Path, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}. Re-run with --overwrite")
    if path.exists() and overwrite:
        path.unlink()



def stream_facilities_to_output(
    facility_path: Path,
    output_path: Path,
    eligible_registry_ids: set[str] | None,
    overwrite: bool,
    progress_every: int,
    low_signal_filter_enabled: bool,
) -> dict[str, Any]:
    ensure_overwrite_allowed(output_path, overwrite=overwrite)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    filter_mode = "program_file_registry_join" if eligible_registry_ids is not None else "facility_program_field_fallback"

    rows_scanned = 0
    rows_registry_match = 0
    rows_program_field_match = 0
    rows_dropped_no_program_match = 0
    rows_written = 0
    rows_dropped_invalid_coords = 0
    rows_missing_registry = 0
    rows_removed_low_signal = 0
    rows_dropped_no_keep_keyword = 0
    rule_hits: Counter[str] = Counter()
    keep_keyword_hits: Counter[str] = Counter()
    unique_registry_ids_written: set[str] = set()
    removed_examples: list[str] = []

    with facility_path.open("r", encoding="utf-8", newline="", errors="replace") as src_handle:
        reader = csv.DictReader(src_handle)
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            raise ValueError(f"Facility file has no header row: {facility_path}")

        describe_headers("Facility file", fieldnames)
        columns = find_facility_columns(fieldnames)
        fallback_scan_all_columns = False
        if eligible_registry_ids is None and columns["program_code"] is None and columns["program_name"] is None:
            fallback_scan_all_columns = True
            logging.warning(
                "Facility program columns not found. Falling back to scanning all facility columns for rule matches."
            )

        with output_path.open("a", encoding="utf-8", newline="") as out_handle:
            writer = csv.DictWriter(out_handle, fieldnames=UNIFIED_COLUMNS)
            if out_handle.tell() == 0:
                writer.writeheader()

            for row in reader:
                rows_scanned += 1
                if progress_every > 0 and rows_scanned % progress_every == 0:
                    logging.info(
                        "Facility scan progress | rows_scanned=%s registry_matches=%s rows_written=%s",
                        rows_scanned,
                        rows_registry_match,
                        rows_written,
                    )

                registry_id = clean_registry_id(row.get(columns["registry_id"], ""))
                if not registry_id:
                    rows_missing_registry += 1
                    continue

                if eligible_registry_ids is not None:
                    if registry_id not in eligible_registry_ids:
                        continue
                else:
                    fallback_text = ""
                    if fallback_scan_all_columns:
                        fallback_text = " ".join(str(row.get(col, "")) for col in fieldnames)

                    rule = match_program_rule(
                        program_code=row.get(columns["program_code"], "") if columns["program_code"] else "",
                        program_name=row.get(columns["program_name"], "") if columns["program_name"] else "",
                        fallback_text=fallback_text,
                    )
                    if rule is None:
                        rows_dropped_no_program_match += 1
                        continue
                    rows_program_field_match += 1
                    rule_hits[rule] += 1

                rows_registry_match += 1

                lat = parse_float(row.get(columns["lat"], ""))
                lon = parse_float(row.get(columns["lon"], ""))
                if not is_valid_coord(lat, lon):
                    rows_dropped_invalid_coords += 1
                    continue

                name = ""
                if columns["name"]:
                    name = str(row.get(columns["name"], "")).strip()
                if not name:
                    name = f"FRS Facility {registry_id}"

                matched_keep_keyword = match_any_keep(name, KEEP_KEYWORDS)
                if matched_keep_keyword is None:
                    rows_dropped_no_keep_keyword += 1
                    continue
                keep_keyword_hits[matched_keep_keyword] += 1

                if low_signal_filter_enabled:
                    program_values: list[str] = []
                    if columns.get("program_code"):
                        value = row.get(columns["program_code"], "")
                        if value:
                            program_values.append(str(value))
                    if columns.get("program_name"):
                        value = row.get(columns["program_name"], "")
                        if value:
                            program_values.append(str(value))

                    naics_values: list[str] = []
                    if columns.get("naics"):
                        naics_raw = row.get(columns["naics"], "")
                        if naics_raw:
                            naics_values.append(str(naics_raw))

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

                state = ""
                if columns["state"]:
                    state = clean_state(row.get(columns["state"], ""))

                metadata: dict[str, str] = {}
                if columns["city"]:
                    city = str(row.get(columns["city"], "")).strip()
                    if city:
                        metadata["city"] = city
                if columns["county"]:
                    county = str(row.get(columns["county"], "")).strip()
                    if county:
                        metadata["county"] = county
                if columns["postal_code"]:
                    postal_code = str(row.get(columns["postal_code"], "")).strip()
                    if postal_code:
                        metadata["postal_code"] = postal_code

                writer.writerow(
                    {
                        "id": f"frs_{registry_id}",
                        "name": name,
                        "category": "industrial_frs",
                        "lat": lat,
                        "lon": lon,
                        "state": state,
                        "source": "EPA_FRS_FILTERED_PROGRAMS",
                        "metadata_json": json.dumps(metadata, separators=(",", ":")),
                    }
                )
                rows_written += 1
                unique_registry_ids_written.add(registry_id)

    stats = {
        "filter_mode": filter_mode,
        "facility_rows_scanned": rows_scanned,
        "facility_rows_registry_match": rows_registry_match,
        "facility_rows_program_field_match": rows_program_field_match,
        "facility_rows_dropped_no_program_match": rows_dropped_no_program_match,
        "rows_written_industrial": rows_written,
        "rows_dropped_invalid_coords": rows_dropped_invalid_coords,
        "rows_dropped_no_keep_keyword": rows_dropped_no_keep_keyword,
        "facility_rows_missing_registry": rows_missing_registry,
        "unique_registry_ids_written": len(unique_registry_ids_written),
        "facility_program_match_counts_by_rule": dict(sorted(rule_hits.items())),
        "low_signal_filter_enabled": low_signal_filter_enabled,
        "removed_low_signal": rows_removed_low_signal,
        "removed_examples": removed_examples,
        "keep_keyword_hits_by_keyword": dict(sorted(keep_keyword_hits.items())),
        "keep_top_keywords": [
            {"keyword": keyword, "count": count}
            for keyword, count in sorted(keep_keyword_hits.items(), key=lambda item: (-item[1], item[0]))[:10]
        ],
    }

    logging.info("Facility filtering complete | %s", stats)
    return stats



def validate_unified_header(path: Path) -> None:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
    missing = [col for col in UNIFIED_COLUMNS if col not in fieldnames]
    if missing:
        raise ValueError(f"{path} missing unified columns {missing}. Found {fieldnames}")



def rebuild_all_sites(processed_dir: Path, overwrite: bool) -> dict[str, int]:
    landfill_path = processed_dir / "landfill.csv"
    military_path = processed_dir / "military_base.csv"
    industrial_path = processed_dir / "industrial_frs.csv"
    superfund_path = processed_dir / "superfund_npl.csv"
    all_sites_path = processed_dir / "all_sites.csv"

    ensure_overwrite_allowed(all_sites_path, overwrite=overwrite)

    input_specs = [
        ("landfill", landfill_path),
        ("military_base", military_path),
        ("industrial_frs", industrial_path),
    ]
    if superfund_path.exists():
        input_specs.append(("superfund_npl", superfund_path))

    for category, path in input_specs:
        if not path.exists():
            raise FileNotFoundError(
                f"Cannot rebuild all_sites.csv because {path} is missing for category {category}."
            )
        validate_unified_header(path)

    counts = {"landfill": 0, "military_base": 0, "industrial_frs": 0, "superfund_npl": 0}

    with all_sites_path.open("a", encoding="utf-8", newline="") as out_handle:
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
                    if category not in CATEGORY_VALUES:
                        raise ValueError(
                            f"{in_path}:{row_num} invalid category {category!r}. Allowed: {sorted(CATEGORY_VALUES)}"
                        )

                    writer.writerow({key: row.get(key, "") for key in UNIFIED_COLUMNS})
                    counts[expected_category] += 1

    logging.info("Rebuilt all_sites.csv with category counts: %s", counts)
    return counts



def write_summary(
    summary_path: Path,
    category_counts: dict[str, int],
    program_stats: dict[str, Any],
    facility_stats: dict[str, Any],
    facility_file: Path,
    program_file: Path | None,
) -> None:
    registry_ids_count = program_stats.get("industrial_registry_ids_count")
    if not registry_ids_count:
        registry_ids_count = facility_stats.get("unique_registry_ids_written", 0)

    program_match_counts = program_stats.get("program_match_counts_by_rule")
    if not program_match_counts:
        program_match_counts = facility_stats.get("facility_program_match_counts_by_rule", {})

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts_by_category": {
            "landfill": int(category_counts.get("landfill", 0)),
            "military_base": int(category_counts.get("military_base", 0)),
            "industrial_frs": int(category_counts.get("industrial_frs", 0)),
            "superfund_npl": int(category_counts.get("superfund_npl", 0)),
        },
        "total_rows": int(sum(category_counts.values())),
        "industrial_registry_ids_count": int(registry_ids_count),
        "rows_written_industrial": int(facility_stats.get("rows_written_industrial", 0)),
        "rows_dropped_invalid_coords": int(facility_stats.get("rows_dropped_invalid_coords", 0)),
        "industrial_filter_rules": [
            "TRI",
            "TOXIC RELEASE",
            "RCRA",
            "CERCLA",
            "SUPERFUND",
            "SUPER FUND",
            "NPL",
        ],
        "industrial_filter_source": facility_stats.get("filter_mode"),
        "program_match_counts_by_rule": program_match_counts,
        "program_rows_scanned": int(program_stats.get("program_rows_scanned", 0)),
        "program_rows_matched": int(program_stats.get("program_rows_matched", 0)),
        "facility_rows_scanned": int(facility_stats.get("facility_rows_scanned", 0)),
        "low_signal_filter_enabled": bool(facility_stats.get("low_signal_filter_enabled", False)),
        "removed_low_signal": int(facility_stats.get("removed_low_signal", 0)),
        "industrial_low_signal_rules": build_low_signal_rules(),
        "industrial_keep_keywords": list(KEEP_KEYWORDS),
        "industrial_keep_matcher_rules": build_keep_matcher_rules(),
        "keep_top_keywords": facility_stats.get("keep_top_keywords", []),
        "raw_files": {
            "facility_file": facility_file.name,
            "program_file": program_file.name if program_file else None,
        },
    }

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logging.info("Wrote summary to %s", summary_path)



def write_process_stats(
    process_stats_path: Path,
    category_counts: dict[str, int],
    program_stats: dict[str, Any],
    facility_stats: dict[str, Any],
) -> None:
    registry_ids_count = program_stats.get("industrial_registry_ids_count")
    if not registry_ids_count:
        registry_ids_count = facility_stats.get("unique_registry_ids_written", 0)

    program_match_counts = program_stats.get("program_match_counts_by_rule")
    if not program_match_counts:
        program_match_counts = facility_stats.get("facility_program_match_counts_by_rule", {})

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "datasets": {
            "industrial_frs": {
                "rows_written": int(facility_stats.get("rows_written_industrial", 0)),
                "dropped_rows": int(facility_stats.get("rows_dropped_invalid_coords", 0)),
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
        "industrial_filter_rules": [
            "TRI",
            "TOXIC RELEASE",
            "RCRA",
            "CERCLA",
            "SUPERFUND",
            "SUPER FUND",
            "NPL",
        ],
        "industrial_filter_source": facility_stats.get("filter_mode"),
        "industrial_registry_ids_count": int(registry_ids_count),
        "program_match_counts_by_rule": program_match_counts,
        "low_signal_filter_enabled": bool(facility_stats.get("low_signal_filter_enabled", False)),
        "removed_low_signal": int(facility_stats.get("removed_low_signal", 0)),
        "industrial_low_signal_rules": build_low_signal_rules(),
        "industrial_keep_keywords": list(KEEP_KEYWORDS),
        "industrial_keep_matcher_rules": build_keep_matcher_rules(),
        "keep_top_keywords": facility_stats.get("keep_top_keywords", []),
    }

    process_stats_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logging.info("Wrote process stats to %s", process_stats_path)


def write_low_signal_audit(
    *,
    audit_path: Path,
    removed_low_signal: int,
    removed_examples: list[str],
    enabled: bool,
) -> None:
    payload = build_low_signal_audit(
        method="rebuild_industrial_filtered.py",
        removed_low_signal=removed_low_signal,
        removed_examples=removed_examples,
        enabled=enabled,
    )
    audit_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logging.info("Wrote industrial low-signal audit to %s", audit_path)


def write_keep_audit(
    *,
    audit_path: Path,
    kept_rows: int,
    keep_keyword_hits_by_keyword: dict[str, int],
) -> None:
    payload = build_keep_audit(
        method="rebuild_industrial_filtered.py",
        kept_rows=kept_rows,
        keep_keyword_hits=keep_keyword_hits_by_keyword,
        keep_keywords=KEEP_KEYWORDS,
    )
    try:
        audit_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logging.info("Wrote industrial keep audit to %s", audit_path)
    except OSError as exc:
        logging.warning("Unable to write industrial keep audit: %s", exc)



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild filtered industrial_frs using FRS program participation.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files.")
    parser.add_argument(
        "--progress-every",
        type=int,
        default=500_000,
        help="Log progress every N scanned rows (default: 500000).",
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

    industrial_path = PROCESSED_DIR / "industrial_frs.csv"
    all_sites_path = PROCESSED_DIR / "all_sites.csv"

    if not args.overwrite:
        existing_outputs = [
            path
            for path in [industrial_path, all_sites_path, SUMMARY_PATH]
            if path.exists()
        ]
        if existing_outputs:
            raise FileExistsError(
                "Refusing to overwrite existing output files without --overwrite: "
                + ", ".join(str(path) for path in existing_outputs)
            )

    facility_path = detect_raw_file(RAW_DIR, FACILITY_EXACT_NAME, FACILITY_FALLBACK_PATTERNS)
    program_path = detect_optional_raw_file(RAW_DIR, PROGRAM_EXACT_NAME, PROGRAM_FALLBACK_PATTERNS)

    logging.info("Using facility file: %s", facility_path)
    logging.info("Using program file: %s", program_path if program_path else "none (facility fallback mode)")

    eligible_registry_ids: set[str] | None = None
    program_stats: dict[str, Any] = {
        "program_rows_scanned": 0,
        "program_rows_matched": 0,
        "program_rows_missing_registry": 0,
        "industrial_registry_ids_count": 0,
        "program_match_counts_by_rule": {},
    }
    if program_path is not None:
        eligible_registry_ids, program_stats = build_eligible_registry_ids(
            program_path=program_path,
            progress_every=args.progress_every,
        )

    facility_stats = stream_facilities_to_output(
        facility_path=facility_path,
        output_path=industrial_path,
        eligible_registry_ids=eligible_registry_ids,
        overwrite=args.overwrite,
        progress_every=args.progress_every,
        low_signal_filter_enabled=not args.no_low_signal_filter,
    )

    category_counts = rebuild_all_sites(processed_dir=PROCESSED_DIR, overwrite=args.overwrite)

    write_summary(
        summary_path=SUMMARY_PATH,
        category_counts=category_counts,
        program_stats=program_stats,
        facility_stats=facility_stats,
        facility_file=facility_path,
        program_file=program_path,
    )

    write_process_stats(
        process_stats_path=PROCESS_STATS_PATH,
        category_counts=category_counts,
        program_stats=program_stats,
        facility_stats=facility_stats,
    )
    write_low_signal_audit(
        audit_path=INDUSTRIAL_FILTER_AUDIT_PATH,
        removed_low_signal=int(facility_stats.get("removed_low_signal", 0)),
        removed_examples=list(facility_stats.get("removed_examples", [])),
        enabled=bool(facility_stats.get("low_signal_filter_enabled", False)),
    )
    write_keep_audit(
        audit_path=INDUSTRIAL_KEEP_AUDIT_PATH,
        kept_rows=int(facility_stats.get("rows_written_industrial", 0)),
        keep_keyword_hits_by_keyword=dict(facility_stats.get("keep_keyword_hits_by_keyword", {})),
    )

    logging.info("Industrial filtering complete.")
    logging.info("Final counts | %s", category_counts)
    logging.info(
        "Low-signal exclusion | input_rows=%s removed_low_signal=%s remaining_rows=%s",
        facility_stats.get("facility_rows_scanned", 0),
        facility_stats.get("removed_low_signal", 0),
        facility_stats.get("rows_written_industrial", 0),
    )
    logging.info(
        "Industrial summary | registry_ids=%s rows_written=%s dropped_invalid_coords=%s",
        program_stats.get("industrial_registry_ids_count", 0)
        or facility_stats.get("unique_registry_ids_written", 0),
        facility_stats.get("rows_written_industrial", 0),
        facility_stats.get("rows_dropped_invalid_coords", 0),
    )
    logging.info("Keep keyword hits (top 10) | %s", facility_stats.get("keep_top_keywords", []))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
