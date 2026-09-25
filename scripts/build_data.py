#!/usr/bin/env python3
"""Build the Terris runtime data bundle from versioned cleaned snapshots."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import shutil
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

COLUMNS = [
    "id",
    "name",
    "category",
    "lat",
    "lon",
    "state",
    "source",
    "metadata_json",
]

SNAPSHOT_FILES = {
    "landfill": Path("data/snapshots/landfill.csv"),
    "superfund_legacy": Path("data/snapshots/superfund_legacy.csv"),
    "superfund_npl": Path("data/snapshots/superfund_npl.csv"),
    "superfund_saa": Path("data/snapshots/superfund_saa.csv"),
}
SOURCES_PATH = Path("data/snapshots/sources.json")
ALL_SITES_PATH = Path("data/processed/all_sites.csv")
MANIFEST_PATH = Path("data/processed/manifest.json")
HEAT_FILES = {
    "landfill": Path("frontend/public/heat/landfill.json"),
    "superfund": Path("frontend/public/heat/superfund.json"),
}
COMBINED_HEAT_PATH = Path("frontend/public/heat/combined.json")

NPL_STATUSES = ("Final NPL", "Proposed NPL", "Deleted NPL")
SUPERFUND_CATEGORY = "superfund"
NPL_SOURCE = "EPA NPL"
SAA_SOURCE = "EPA FOIA-014"
LEGACY_SOURCE = "EPA NPL Superfund boundaries (legacy)"

US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA", "HI",
    "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD", "ME", "MI", "MN",
    "MO", "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA",
    "WI", "WV", "WY", "PR", "VI", "GU", "AS", "MP",
}


class PipelineError(ValueError):
    """Raised when a snapshot or generated artifact is invalid."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _parse_metadata(value: Any, location: str) -> dict[str, Any]:
    def reject_constant(constant: str) -> None:
        raise ValueError(f"non-standard JSON constant {constant}")

    try:
        parsed = json.loads(str(value or ""), parse_constant=reject_constant)
    except (json.JSONDecodeError, ValueError) as exc:
        raise PipelineError(f"{location}: metadata_json must be a valid JSON object") from exc
    if not isinstance(parsed, dict):
        raise PipelineError(f"{location}: metadata_json must be a JSON object")
    return parsed


def _parse_coordinate(value: Any, *, name: str, location: str) -> float:
    try:
        coordinate = float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise PipelineError(f"{location}: {name} must be numeric") from exc
    if not math.isfinite(coordinate):
        raise PipelineError(f"{location}: {name} must be finite")
    return coordinate


def _read_snapshot(
    root: Path,
    category: str,
    relative_path: Path,
    seen_ids: set[str],
    *,
    preserve_coordinate_text: bool = False,
) -> list[dict[str, str]]:
    path = root / relative_path
    if not path.is_file():
        raise PipelineError(f"Missing snapshot: {relative_path}")

    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != COLUMNS:
            raise PipelineError(
                f"{relative_path}: columns must be exactly {COLUMNS}; found {reader.fieldnames or []}"
            )

        for row_number, row in enumerate(reader, start=2):
            location = f"{relative_path}:{row_number}"
            row_category = _clean_text(row.get("category"))
            if row_category != category:
                raise PipelineError(
                    f"{location}: expected category {category!r}, found {row_category!r}"
                )

            site_id = _clean_text(row.get("id"))
            name = _clean_text(row.get("name"))
            state = _clean_text(row.get("state")).upper()
            source = _clean_text(row.get("source"))
            if not site_id or not name or not state or not source:
                raise PipelineError(f"{location}: id, name, state, and source are required")
            if site_id in seen_ids:
                raise PipelineError(f"{location}: duplicate site id {site_id!r}")
            seen_ids.add(site_id)
            if state not in US_STATE_CODES:
                raise PipelineError(f"{location}: unsupported state or territory code {state!r}")

            lat = _parse_coordinate(row.get("lat"), name="lat", location=location)
            lon = _parse_coordinate(row.get("lon"), name="lon", location=location)
            if not -90.0 <= lat <= 90.0 or not -180.0 <= lon <= 180.0:
                raise PipelineError(f"{location}: coordinates are outside valid latitude/longitude bounds")
            if lat == 0.0 and lon == 0.0:
                raise PipelineError(f"{location}: null-island coordinates are not allowed")

            metadata = _parse_metadata(row.get("metadata_json"), location)
            lat_text = _clean_text(row.get("lat")) if preserve_coordinate_text else f"{lat:.8f}"
            lon_text = _clean_text(row.get("lon")) if preserve_coordinate_text else f"{lon:.8f}"
            rows.append(
                {
                    "id": site_id,
                    "name": name,
                    "category": category,
                    "lat": lat_text,
                    "lon": lon_text,
                    "state": state,
                    "source": source,
                    "metadata_json": json.dumps(
                        metadata,
                        allow_nan=False,
                        ensure_ascii=True,
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                }
            )

    rows.sort(key=lambda row: (row["state"], row["name"].casefold(), row["id"]))
    if not rows:
        raise PipelineError(f"{relative_path}: snapshot contains no rows")
    return rows


def _epa_id(row: dict[str, str], location: str) -> str:
    metadata = _parse_metadata(row["metadata_json"], location)
    external_id = _clean_text(metadata.get("external_id")).upper()
    if len(external_id) != 12 or not external_id.isalnum():
        raise PipelineError(f"{location}: Superfund record lacks a valid EPA ID")
    if row["id"] != f"superfund_{external_id}":
        raise PipelineError(
            f"{location}: id must be 'superfund_<EPA_ID>' for EPA ID {external_id!r}"
        )
    return external_id


def _read_superfund_snapshot(
    root: Path,
    source_key: str,
    relative_path: Path,
) -> dict[str, dict[str, str]]:
    rows = _read_snapshot(
        root,
        SUPERFUND_CATEGORY,
        relative_path,
        set(),
        preserve_coordinate_text=True,
    )
    by_epa_id: dict[str, dict[str, str]] = {}
    expected_source = {
        "superfund_legacy": LEGACY_SOURCE,
        "superfund_npl": NPL_SOURCE,
        "superfund_saa": SAA_SOURCE,
    }[source_key]
    for index, row in enumerate(rows, start=2):
        location = f"{relative_path}:{index}"
        if row["source"] != expected_source:
            raise PipelineError(
                f"{location}: expected source {expected_source!r}, found {row['source']!r}"
            )
        epa_id = _epa_id(row, location)
        if epa_id in by_epa_id:
            raise PipelineError(f"{location}: duplicate Superfund EPA ID {epa_id!r}")
        metadata = _parse_metadata(row["metadata_json"], location)
        if source_key == "superfund_npl":
            status = metadata.get("npl_status")
            if status not in NPL_STATUSES:
                raise PipelineError(
                    f"{location}: unexpected NPL status {status!r}; expected one of {list(NPL_STATUSES)}"
                )
        elif source_key == "superfund_saa":
            if metadata.get("saa") is not True:
                raise PipelineError(f"{location}: SAA snapshot rows must set saa=true")
            if metadata.get("coordinate_basis") != "address_geocoded":
                raise PipelineError(
                    f"{location}: SAA snapshot rows must use address_geocoded coordinates"
                )
        by_epa_id[epa_id] = row
    return by_epa_id


def _merge_superfund(
    legacy_by_epa_id: dict[str, dict[str, str]],
    npl_by_epa_id: dict[str, dict[str, str]],
    saa_by_epa_id: dict[str, dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    npl_saa_overlap = set(npl_by_epa_id) & set(saa_by_epa_id)
    legacy_npl_overlap = set(legacy_by_epa_id) & set(npl_by_epa_id)
    legacy_saa_overlap = set(legacy_by_epa_id) & set(saa_by_epa_id)
    all_epa_ids = set(legacy_by_epa_id) | set(npl_by_epa_id) | set(saa_by_epa_id)
    merged: list[dict[str, str]] = []
    for epa_id in sorted(all_epa_ids):
        if epa_id in npl_by_epa_id:
            row = dict(npl_by_epa_id[epa_id])
            metadata = _parse_metadata(row["metadata_json"], f"merged Superfund {epa_id}")
            metadata["saa"] = epa_id in npl_saa_overlap
            metadata["sources"] = [NPL_SOURCE, SAA_SOURCE] if epa_id in npl_saa_overlap else [NPL_SOURCE]
        elif epa_id in legacy_by_epa_id:
            row = dict(legacy_by_epa_id[epa_id])
            metadata = _parse_metadata(row["metadata_json"], f"merged Superfund {epa_id}")
            metadata["npl_status"] = None
            metadata["saa"] = epa_id in saa_by_epa_id
            metadata["sources"] = (
                [LEGACY_SOURCE, SAA_SOURCE]
                if epa_id in saa_by_epa_id
                else [LEGACY_SOURCE]
            )
        else:
            row = dict(saa_by_epa_id[epa_id])
            metadata = _parse_metadata(row["metadata_json"], f"merged Superfund {epa_id}")
            metadata["npl_status"] = None
            metadata["saa"] = True
            metadata["sources"] = [SAA_SOURCE]
            metadata["coordinate_basis"] = "address_geocoded"
        row["category"] = SUPERFUND_CATEGORY
        row["metadata_json"] = json.dumps(
            metadata,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        merged.append(row)

    merged.sort(key=lambda row: (row["state"], row["name"].casefold(), row["id"]))
    status_counts = {
        status: sum(
            _parse_metadata(row["metadata_json"], row["id"]).get("npl_status") == status
            for row in npl_by_epa_id.values()
        )
        for status in NPL_STATUSES
    }
    stats = {
        "new_npl_source_row_count": len(npl_by_epa_id),
        "npl_unique_epa_ids": len(npl_by_epa_id),
        "npl_status_counts": status_counts,
        "filtered_saa_source_row_count": len(saa_by_epa_id),
        "overlapping_epa_ids": len(npl_saa_overlap),
        "npl_only_sites": len(npl_by_epa_id) - len(npl_saa_overlap),
        "saa_non_npl_sites": len(saa_by_epa_id) - len(npl_saa_overlap),
        "saa_only_sites_added": len(set(saa_by_epa_id) - set(npl_by_epa_id) - set(legacy_by_epa_id)),
        "legacy_source_row_count": len(legacy_by_epa_id),
        "legacy_npl_overlap": len(legacy_npl_overlap),
        "legacy_saa_overlap": len(legacy_saa_overlap),
        "new_npl_sites_added": len(set(npl_by_epa_id) - set(legacy_by_epa_id)),
        "legacy_only_sites_retained": len(set(legacy_by_epa_id) - set(npl_by_epa_id) - set(saa_by_epa_id)),
        "final_unique_superfund_site_count": len(merged),
        "dedupe_key": "EPA ID",
        "coordinate_precedence": "NEW NPL coordinate > legacy boundary coordinate > SAA coordinate",
    }
    return merged, stats


def _load_sources(root: Path) -> tuple[dict[str, Any], bytes]:
    path = root / SOURCES_PATH
    if not path.is_file():
        raise PipelineError(f"Missing source metadata: {SOURCES_PATH}")
    payload_bytes = path.read_bytes()
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError as exc:
        raise PipelineError(f"{SOURCES_PATH}: invalid JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise PipelineError(f"{SOURCES_PATH}: schema_version must be 1")
    if payload.get("strategy") != "snapshot-first":
        raise PipelineError(f"{SOURCES_PATH}: strategy must be 'snapshot-first'")
    if not isinstance(payload.get("provenance_note"), str) or not payload["provenance_note"]:
        raise PipelineError(f"{SOURCES_PATH}: provenance_note is required")

    sources = payload.get("sources")
    cleaning = payload.get("cleaning")
    if not isinstance(sources, dict) or set(sources) != set(SNAPSHOT_FILES):
        raise PipelineError(f"{SOURCES_PATH}: sources must describe exactly {list(SNAPSHOT_FILES)}")
    if not isinstance(cleaning, dict) or set(cleaning) != set(SNAPSHOT_FILES):
        raise PipelineError(f"{SOURCES_PATH}: cleaning must describe exactly {list(SNAPSHOT_FILES)}")

    for category in SNAPSHOT_FILES:
        source = sources.get(category)
        stats = cleaning.get(category)
        if not isinstance(source, dict):
            raise PipelineError(f"{SOURCES_PATH}: sources.{category} must be an object")
        for field in ("publisher", "dataset", "source_label", "raw_artifacts"):
            if not source.get(field):
                raise PipelineError(f"{SOURCES_PATH}: sources.{category}.{field} is required")
        if not isinstance(source["raw_artifacts"], list):
            raise PipelineError(f"{SOURCES_PATH}: sources.{category}.raw_artifacts must be a list")
        if not isinstance(stats, dict) or not isinstance(stats.get("rows_written"), int):
            raise PipelineError(f"{SOURCES_PATH}: cleaning.{category}.rows_written must be an integer")

    return payload, payload_bytes


def _csv_bytes(rows: list[dict[str, str]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _heat_bytes(rows: list[dict[str, str]]) -> bytes:
    points = [[float(row["lat"]), float(row["lon"])] for row in rows]
    return json.dumps(points, allow_nan=False, separators=(",", ":")).encode("utf-8")


def _coordinate_stats(rows: list[dict[str, str]]) -> dict[str, float]:
    latitudes = [float(row["lat"]) for row in rows]
    longitudes = [float(row["lon"]) for row in rows]
    return {
        "min_lat": min(latitudes),
        "max_lat": max(latitudes),
        "min_lon": min(longitudes),
        "max_lon": max(longitudes),
    }


def _bundle_version(snapshot_payloads: Mapping[Path, bytes]) -> str:
    digest = hashlib.sha256()
    for path in sorted(snapshot_payloads, key=lambda item: item.as_posix()):
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(snapshot_payloads[path])
        digest.update(b"\0")
    return f"snapshot-{digest.hexdigest()[:12]}"


def build_artifacts(root: Path = REPO_ROOT) -> tuple[dict[Path, bytes], dict[str, Any]]:
    """Return every generated artifact as bytes without changing the repository."""
    source_metadata, source_metadata_bytes = _load_sources(root)
    snapshot_payloads: dict[Path, bytes] = {SOURCES_PATH: source_metadata_bytes}
    landfill_path = SNAPSHOT_FILES["landfill"]
    landfill_rows = _read_snapshot(root, "landfill", landfill_path, set())
    legacy_by_epa_id = _read_superfund_snapshot(
        root, "superfund_legacy", SNAPSHOT_FILES["superfund_legacy"]
    )
    npl_by_epa_id = _read_superfund_snapshot(
        root, "superfund_npl", SNAPSHOT_FILES["superfund_npl"]
    )
    saa_by_epa_id = _read_superfund_snapshot(
        root, "superfund_saa", SNAPSHOT_FILES["superfund_saa"]
    )

    source_rows = {
        "landfill": len(landfill_rows),
        "superfund_legacy": len(legacy_by_epa_id),
        "superfund_npl": len(npl_by_epa_id),
        "superfund_saa": len(saa_by_epa_id),
    }
    for source_key, relative_path in SNAPSHOT_FILES.items():
        expected_rows = source_metadata["cleaning"][source_key]["rows_written"]
        if source_rows[source_key] != expected_rows:
            raise PipelineError(
                f"{relative_path}: found {source_rows[source_key]} rows, "
                f"but sources.json records {expected_rows}"
            )
        snapshot_payloads[relative_path] = (root / relative_path).read_bytes()

    expected_landfill_source = source_metadata["sources"]["landfill"]["source_label"]
    landfill_sources = {row["source"] for row in landfill_rows}
    if landfill_sources != {expected_landfill_source}:
        raise PipelineError(
            f"{landfill_path}: source values {sorted(landfill_sources)} "
            f"do not match {expected_landfill_source!r}"
        )

    superfund_rows, superfund_merge = _merge_superfund(
        legacy_by_epa_id, npl_by_epa_id, saa_by_epa_id
    )
    superfund_merge["new_npl_source_row_count"] = source_metadata["cleaning"]["superfund_npl"]["input_rows"]
    all_ids = [row["id"] for row in landfill_rows + superfund_rows]
    if len(all_ids) != len(set(all_ids)):
        raise PipelineError("Generated dataset contains duplicate site IDs")

    rows_by_category = {
        "landfill": landfill_rows,
        SUPERFUND_CATEGORY: superfund_rows,
    }
    all_rows = landfill_rows + superfund_rows

    artifacts: dict[Path, bytes] = {ALL_SITES_PATH: _csv_bytes(all_rows)}
    for category, output_path in HEAT_FILES.items():
        artifacts[output_path] = _heat_bytes(rows_by_category[category])
    artifacts[COMBINED_HEAT_PATH] = _heat_bytes(all_rows)

    counts = {category: len(rows) for category, rows in rows_by_category.items()}
    output_details: dict[str, dict[str, Any]] = {}
    for path, payload in artifacts.items():
        details: dict[str, Any] = {
            "bytes": len(payload),
            "sha256": _sha256(payload),
        }
        if path == ALL_SITES_PATH:
            details["rows"] = len(all_rows)
        elif path == COMBINED_HEAT_PATH:
            details["points"] = len(all_rows)
        else:
            category = next(key for key, value in HEAT_FILES.items() if value == path)
            details["points"] = counts[category]
        output_details[path.as_posix()] = details

    snapshot_details: dict[str, dict[str, Any]] = {}
    for path, payload in snapshot_payloads.items():
        details: dict[str, Any] = {
            "bytes": len(payload),
            "sha256": _sha256(payload),
        }
        for category, snapshot_path in SNAPSHOT_FILES.items():
            if path == snapshot_path:
                details["rows"] = source_rows[category]
                break
        snapshot_details[path.as_posix()] = details

    manifest = {
        "schema_version": 1,
        "strategy": source_metadata["strategy"],
        "dataset_version": _bundle_version(snapshot_payloads),
        "pipeline": "scripts/build_data.py",
        "provenance_note": source_metadata["provenance_note"],
        "counts_by_category": counts,
        "total_rows": len(all_rows),
        "coordinate_sanity_by_category": {
            category: _coordinate_stats(rows)
            for category, rows in rows_by_category.items()
        },
        "sources": source_metadata["sources"],
        "cleaning": source_metadata["cleaning"],
        "superfund_merge": superfund_merge,
        "snapshots": snapshot_details,
        "outputs": output_details,
    }
    artifacts[MANIFEST_PATH] = (
        json.dumps(manifest, allow_nan=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return artifacts, manifest


def validate_repository(root: Path = REPO_ROOT) -> dict[str, Any]:
    """Validate snapshots and require generated outputs to match byte-for-byte."""
    artifacts, manifest = build_artifacts(root)
    errors: list[str] = []
    for relative_path, expected in artifacts.items():
        path = root / relative_path
        if not path.is_file():
            errors.append(f"missing generated artifact: {relative_path}")
            continue
        actual = path.read_bytes()
        if actual != expected:
            errors.append(
                f"stale generated artifact: {relative_path} "
                f"(expected sha256 {_sha256(expected)}, found {_sha256(actual)})"
            )
    if errors:
        raise PipelineError("Generated data bundle is invalid:\n- " + "\n- ".join(errors))
    return manifest


def _promote_artifacts(root: Path, artifacts: Mapping[Path, bytes]) -> None:
    """Replace generated files atomically per file and roll back on promotion failure."""
    with tempfile.TemporaryDirectory(prefix=".terris-data-build-", dir=root) as temp_name:
        temp_root = Path(temp_name)
        staged_root = temp_root / "staged"
        backup_root = temp_root / "backup"

        for relative_path, payload in artifacts.items():
            staged_path = staged_root / relative_path
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            staged_path.write_bytes(payload)
            if staged_path.read_bytes() != payload:
                raise OSError(f"Failed to verify staged artifact {relative_path}")

        replaced: list[Path] = []
        had_original: dict[Path, bool] = {}
        try:
            for relative_path in artifacts:
                target = root / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                had_original[relative_path] = target.exists()
                if target.exists():
                    backup = backup_root / relative_path
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, backup)
                os.replace(staged_root / relative_path, target)
                replaced.append(relative_path)
        except BaseException:
            for relative_path in reversed(replaced):
                target = root / relative_path
                backup = backup_root / relative_path
                if had_original[relative_path]:
                    os.replace(backup, target)
                elif target.exists():
                    target.unlink()
            raise


def main() -> int:
    try:
        artifacts, _ = build_artifacts(REPO_ROOT)
        _promote_artifacts(REPO_ROOT, artifacts)
        manifest = validate_repository(REPO_ROOT)
    except (OSError, PipelineError) as exc:
        print(f"DATA BUILD FAILED\n{exc}", file=sys.stderr)
        return 1

    print(
        f"Built {manifest['dataset_version']}: {manifest['total_rows']} sites "
        f"({', '.join(f'{key}={value}' for key, value in manifest['counts_by_category'].items())})."
    )
    print(f"Manifest: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
