#!/usr/bin/env python3
"""Process EPA Superfund NPL geodatabase into unified CSV rows."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

OUTPUT_COLUMNS = [
    "id",
    "name",
    "category",
    "lat",
    "lon",
    "state",
    "source",
    "metadata_json",
    "external_id",
]

NAME_FIELD_CANDIDATES = [
    "SITE_NAME",
    "NAME",
    "SITE",
    "FACILITY",
    "DISPLAY_NAME",
]

STATE_FIELD_CANDIDATES = [
    "STATE",
    "STATE_CODE",
    "STATE_CD",
    "STATECODE",
    "STATE_ABBR",
    "ST",
    "USPS",
]

EXTERNAL_ID_CANDIDATES = [
    "SITE_ID",
    "NPL_ID",
    "EPA_ID",
    "CERCLIS_ID",
    "ID",
    "OBJECTID",
]

ADDRESS_FIELD_CANDIDATES = [
    "ADDRESS",
    "SITE_ADDRESS",
    "LOCATION",
    "CITY_STATE_ZIP",
]

US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA", "HI",
    "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD", "ME", "MI", "MN",
    "MO", "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA",
    "WI", "WV", "WY", "PR", "VI", "GU", "AS", "MP",
}


def normalize_col(name: str | None) -> str:
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]+", "", str(name).strip().lower())


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


def clean_state(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().upper()
    if len(text) == 2 and text.isalpha():
        return text
    return ""


def clean_id_fragment(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    return re.sub(r"[^A-Za-z0-9_.-]+", "", text)


def stable_hash(*parts: str) -> str:
    joined = "|".join(part.strip() for part in parts if part is not None)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]


def is_valid_coord(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def choose_column(columns: list[str], candidates: list[str]) -> str | None:
    lookup = {normalize_col(column): column for column in columns}
    for candidate in candidates:
        key = normalize_col(candidate)
        if key in lookup:
            return lookup[key]
    return None


def infer_name_column(columns: list[str]) -> str | None:
    preferred = choose_column(columns, NAME_FIELD_CANDIDATES)
    if preferred:
        return preferred

    for column in columns:
        key = normalize_col(column)
        if any(token in key for token in ("name", "site", "facility", "display", "title")):
            return column

    for column in columns:
        key = normalize_col(column)
        if "id" in key or "state" in key:
            continue
        return column
    return None


def parse_state_from_address(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().upper()
    if not text:
        return ""
    match = re.search(r",\s*([A-Z]{2})\s+\d{5}(?:-\d{4})?\b", text)
    if match:
        return match.group(1)
    return ""


def parse_state_from_external_id(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().upper()
    if len(text) < 2:
        return ""

    match = re.match(r"^([A-Z]{2})", text)
    if not match:
        return ""

    candidate = match.group(1)
    if candidate in US_STATE_CODES:
        return candidate
    return ""


def _list_layers(gdb_path: Path) -> list[str]:
    try:
        import fiona

        return [str(layer) for layer in fiona.listlayers(gdb_path)]
    except Exception:
        pass

    try:
        import pyogrio

        raw_layers = pyogrio.list_layers(gdb_path)
    except Exception as exc:
        raise RuntimeError(
            "Unable to list .gdb layers. Install geopandas with either fiona or pyogrio in the pipeline environment."
        ) from exc

    layers: list[str] = []
    if hasattr(raw_layers, "tolist"):
        raw_layers = raw_layers.tolist()
    if isinstance(raw_layers, list):
        for layer in raw_layers:
            if isinstance(layer, (list, tuple)) and layer:
                layers.append(str(layer[0]))
            elif isinstance(layer, str):
                layers.append(layer)
    return layers


def _load_geodataframe(gdb_path: Path, layer: str):
    try:
        import geopandas as gpd
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "geopandas is required for Superfund processing. Install it in the offline pipeline environment "
            "(for example: pip install geopandas pyogrio)."
        ) from exc

    return gpd.read_file(gdb_path, layer=layer)


def find_superfund_gdb(raw_dir: Path) -> Path | None:
    direct_matches = sorted(path for path in raw_dir.glob("*.gdb") if path.is_dir())
    if direct_matches:
        return direct_matches[0]

    nested_matches = sorted(path for path in raw_dir.rglob("*.gdb") if path.is_dir())
    if nested_matches:
        return nested_matches[0]
    return None


def process_superfund_gdb(source_path: Path, output_path: Path) -> dict[str, int]:
    layers = _list_layers(source_path)
    if not layers:
        raise ValueError(f"No readable layers found in {source_path}")

    layer_candidates: list[dict[str, Any]] = []
    for layer_name in layers:
        try:
            layer_gdf = _load_geodataframe(source_path, layer_name)
        except Exception:
            continue

        columns = [str(column) for column in layer_gdf.columns if str(column) != "geometry"]
        name_column = infer_name_column(columns)
        external_id_column = choose_column(columns, EXTERNAL_ID_CANDIDATES)

        unique_names = 0
        if name_column:
            name_series = layer_gdf[name_column].astype(str).str.strip()
            name_series = name_series[name_series != ""]
            unique_names = int(name_series.nunique())

        unique_ids = 0
        if external_id_column:
            id_series = layer_gdf[external_id_column].astype(str).str.strip()
            id_series = id_series[id_series != ""]
            unique_ids = int(id_series.nunique())

        geom_types = set()
        if "geometry" in layer_gdf:
            geom_types = {
                str(item).strip().lower()
                for item in layer_gdf.geometry.geom_type.dropna().tolist()
            }
        has_point_geometry = "point" in geom_types or "multipoint" in geom_types

        # Prefer point layers, but only when they also have strong unique site identity.
        # This avoids selecting point layers that represent a single site repeated many times.
        quality_score = (unique_names * 2) + unique_ids + (250 if has_point_geometry else 0)

        layer_candidates.append(
            {
                "layer_name": layer_name,
                "gdf": layer_gdf,
                "unique_names": unique_names,
                "unique_ids": unique_ids,
                "has_point_geometry": has_point_geometry,
                "row_count": int(len(layer_gdf)),
                "quality_score": quality_score,
            }
        )

    if not layer_candidates:
        raise ValueError(f"Unable to read any layer from {source_path}")

    selected = max(
        layer_candidates,
        key=lambda entry: (
            int(entry["quality_score"]),
            int(entry["unique_names"]),
            int(entry["unique_ids"]),
            int(entry["row_count"]),
        ),
    )
    selected_layer = str(selected["layer_name"])
    selected_gdf = selected["gdf"]
    use_centroid = not bool(selected["has_point_geometry"])

    gdf = selected_gdf.copy()
    if gdf.crs is not None and str(gdf.crs).upper() != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)

    geometry_series = gdf.geometry
    if use_centroid:
        projected = gdf.to_crs(epsg=3857)
        geometry_series = projected.geometry.centroid.to_crs(epsg=4326)
    else:
        non_point_mask = ~geometry_series.geom_type.eq("Point")
        if non_point_mask.any():
            geometry_series = geometry_series.copy()
            projected = gdf.loc[non_point_mask].to_crs(epsg=3857)
            geometry_series.loc[non_point_mask] = projected.geometry.centroid.to_crs(epsg=4326)

    name_column = infer_name_column([str(column) for column in gdf.columns if str(column) != "geometry"])
    state_column = choose_column([str(column) for column in gdf.columns if str(column) != "geometry"], STATE_FIELD_CANDIDATES)
    external_id_column = choose_column(
        [str(column) for column in gdf.columns if str(column) != "geometry"],
        EXTERNAL_ID_CANDIDATES,
    )
    address_column = choose_column(
        [str(column) for column in gdf.columns if str(column) != "geometry"],
        ADDRESS_FIELD_CANDIDATES,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()

        seen: set[tuple[float, float, str]] = set()
        stats = {
            "input_rows": int(len(gdf)),
            "written_rows": 0,
            "dropped_rows": 0,
            "dropped_invalid_coords": 0,
            "dropped_duplicates": 0,
        }

        for row_index, (_, row) in enumerate(gdf.iterrows(), start=1):
            geom = geometry_series.iloc[row_index - 1] if row_index - 1 < len(geometry_series) else None
            lat = parse_float(getattr(geom, "y", None))
            lon = parse_float(getattr(geom, "x", None))

            if not is_valid_coord(lat, lon):
                stats["dropped_rows"] += 1
                stats["dropped_invalid_coords"] += 1
                continue

            raw_name = row.get(name_column) if name_column else ""
            name = str(raw_name).strip() if raw_name is not None else ""

            raw_external_id = row.get(external_id_column) if external_id_column else ""
            external_id = clean_id_fragment(raw_external_id)
            if not name:
                name = f"Superfund NPL Site {external_id or stable_hash(f'{lat:.8f}', f'{lon:.8f}')[:8]}"

            dedupe_key = (round(lat, 8), round(lon, 8), name.lower())
            if dedupe_key in seen:
                stats["dropped_rows"] += 1
                stats["dropped_duplicates"] += 1
                continue
            seen.add(dedupe_key)

            state = ""
            if state_column:
                state = clean_state(row.get(state_column))
            if not state and address_column:
                state = clean_state(parse_state_from_address(row.get(address_column)))
            if not state:
                state = parse_state_from_external_id(raw_external_id)

            stable_id = external_id or stable_hash(name, f"{lat:.8f}", f"{lon:.8f}")
            metadata: dict[str, str] = {}
            if selected_layer:
                metadata["layer"] = selected_layer
            if use_centroid:
                metadata["geometry_fallback"] = "centroid"
            if external_id:
                metadata["external_id"] = external_id

            writer.writerow(
                {
                    "id": f"superfund_{stable_id}",
                    "name": name,
                    "category": "superfund_npl",
                    "lat": f"{lat:.8f}",
                    "lon": f"{lon:.8f}",
                    "state": state,
                    "source": "EPA NPL Superfund",
                    "metadata_json": json.dumps(metadata, separators=(",", ":"), ensure_ascii=True),
                    "external_id": external_id,
                }
            )
            stats["written_rows"] += 1

    print(
        f"Superfund NPL processed: loaded={stats['input_rows']} "
        f"dropped={stats['dropped_rows']} output={output_path} "
        f"layer={selected_layer} point_layer={'yes' if selected['has_point_geometry'] else 'no'} "
        f"unique_names={selected['unique_names']} unique_ids={selected['unique_ids']}"
    )
    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process EPA Superfund NPL .gdb into data/processed/superfund_npl.csv"
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Path to .gdb folder. Defaults to first *.gdb under data/raw.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(PROCESSED_DIR / "superfund_npl.csv"),
        help="Output CSV path.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output if it exists.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.source) if args.source else find_superfund_gdb(RAW_DIR)
    output = Path(args.output)

    if source is None:
        print("Superfund .gdb not found in data/raw; nothing to process.")
        return 0
    if not source.exists():
        print(f"Superfund source does not exist: {source}", file=sys.stderr)
        return 1
    if output.exists() and not args.overwrite:
        print(f"Output already exists: {output}. Use --overwrite to regenerate.", file=sys.stderr)
        return 1

    try:
        process_superfund_gdb(source_path=source, output_path=output)
    except Exception as exc:
        print(f"Superfund processing failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
