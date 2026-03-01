#!/usr/bin/env python3
"""Export heatmap point JSON files from processed all_sites.csv."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = REPO_ROOT / "data" / "processed" / "all_sites.csv"
OUTPUT_DIR = REPO_ROOT / "frontend" / "public" / "heat"

CATEGORY_TO_OUTPUT = {
    "industrial_frs": "industrial.json",
    "landfill": "landfill.json",
    "military_base": "military.json",
    "superfund_npl": "superfund.json",
}


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


def valid_coordinate(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def main() -> int:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Missing processed dataset: {INPUT_CSV}. Run scripts/process_all.py and scripts/validate.py first."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    points_by_category: dict[str, list[list[float]]] = {
        category: [] for category in CATEGORY_TO_OUTPUT
    }
    combined_points: list[list[float]] = []

    with INPUT_CSV.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required_columns = {"category", "lat", "lon"}
        missing_columns = sorted(required_columns - set(reader.fieldnames or []))
        if missing_columns:
            raise ValueError(
                f"Input CSV missing required columns: {missing_columns}. Found: {reader.fieldnames}"
            )

        for row in reader:
            category = str(row.get("category", "")).strip()
            if category not in points_by_category:
                continue

            lat = parse_float(row.get("lat"))
            lon = parse_float(row.get("lon"))
            if not valid_coordinate(lat, lon):
                continue

            point = [lat, lon]
            points_by_category[category].append(point)
            combined_points.append(point)

    file_map = {
        "industrial": "/heat/industrial.json",
        "landfill": "/heat/landfill.json",
        "military": "/heat/military.json",
        "superfund": "/heat/superfund.json",
        "combined": "/heat/combined.json",
    }

    write_json(OUTPUT_DIR / "industrial.json", points_by_category["industrial_frs"])
    write_json(OUTPUT_DIR / "landfill.json", points_by_category["landfill"])
    write_json(OUTPUT_DIR / "military.json", points_by_category["military_base"])
    write_json(OUTPUT_DIR / "superfund.json", points_by_category["superfund_npl"])
    write_json(OUTPUT_DIR / "combined.json", combined_points)

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_csv": str(INPUT_CSV.relative_to(REPO_ROOT)),
        "counts": {
            "industrial": len(points_by_category["industrial_frs"]),
            "landfill": len(points_by_category["landfill"]),
            "military": len(points_by_category["military_base"]),
            "superfund": len(points_by_category["superfund_npl"]),
            "combined": len(combined_points),
        },
        "files": file_map,
    }
    write_json(OUTPUT_DIR / "manifest.json", manifest)

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
