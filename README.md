# PFAS Risk Scoring Data Layer (Offline)

This repository builds a **clean, reproducible offline data bundle** for a national U.S. map used in PFAS distance/risk scoring.

Processing uses manually downloaded raw data in `data/raw/` and outputs normalized CSVs in `data/processed/`.

## Quick Start

```bash
python scripts/process_all.py --overwrite
python scripts/validate.py
python scripts/export_heat_points.py
python scripts/smoke_test.py
```

If `python` is not available in your shell, use `python3`.
Place the Superfund `.gdb` in `data/raw/` (for example `data/raw/superfund_npl.gdb`).
Run `python scripts/process_all.py --overwrite` then `python scripts/validate.py` to regenerate outputs including Superfund rows.

## Option A Industrial Filtering (Recommended for API Scoring)

Use FRS National Program participation to keep higher-signal industrial facilities
(TRI, RCRA, CERCLA/Superfund-related matches):

```bash
python scripts/rebuild_industrial_filtered.py --overwrite
python scripts/validate.py
```

This reduces industrial facility volume and improves scoring signal quality.
If `NATIONAL_PROGRAM_FILE.CSV` is missing, the script falls back to facility-level
program text fields in `NATIONAL_FACILITY_FILE.CSV`.

## Industrial Reduction Without Program File

When only `NATIONAL_FACILITY_FILE.CSV` is available, run:

```bash
python scripts/rebuild_industrial_reduced_no_program.py --overwrite
python scripts/validate.py
```

Method used:
- Stage 1 high-signal proxy:
  - NAICS prefix filter if NAICS exists, else facility-name keyword proxy filter.
- Stage 2 density cap:
  - 0.05 degree grid with max 10 facilities per cell.

This is a reproducible proxy reduction for map/scoring stability, not direct PFAS confirmation.

## Folder Layout

```text
.
├── data/
│   ├── raw/              # manual downloads (not fetched by scripts)
│   └── processed/        # generated normalized outputs
├── scripts/
│   ├── rebuild_industrial_filtered.py
│   ├── process_all.py
│   ├── validate.py
│   └── smoke_test.py
├── README.md
├── SOURCES.md
└── .gitignore
```

## Data Flow

- Detect raw files in `data/raw/` (FRS facilities, military bases, LMOP landfills).
- Stream-process FRS program participation (large CSV) to build eligible REGISTRY_IDs.
- Stream-process FRS facilities (large CSV) and keep only facilities with eligible program participation.
- Process military bases from CSV or GeoJSON into unified schema.
- Process LMOP landfill XLSX (via `openpyxl`) into unified schema.
- Write:
  - `data/processed/industrial_frs.csv`
  - `data/processed/military_base.csv`
  - `data/processed/landfill.csv`
  - `data/processed/all_sites.csv`
- Validate all processed outputs and write `data/processed/summary.json`.
- Run smoke test point analyses for NYC, Chicago, and LA.

## Unified Schema

All processed CSVs use this exact column set:

| Column | Type | Description |
|---|---|---|
| `id` | string | Stable source-prefixed ID |
| `name` | string | Site/facility name |
| `category` | string | One of `industrial_frs`, `military_base`, `landfill` |
| `lat` | float | Latitude |
| `lon` | float | Longitude |
| `state` | string | 2-letter U.S. state code when available |
| `source` | string | Source identifier |
| `metadata_json` | stringified JSON | Light source-specific metadata |

## Important Notes

- Processing is fully offline; no internet is required during processing.
- Raw files are expected to be manually downloaded into `data/raw/`.
- Superfund `.gdb` ingestion uses `geopandas` plus either `fiona` or `pyogrio` in the pipeline environment (not required for backend runtime).
- Run `python scripts/export_heat_points.py` after processing/validation to refresh frontend heat-layer JSON files in `frontend/public/heat/`.
- FRS National Facility and National Program inputs are very large (multi-GB). `rebuild_industrial_filtered.py` uses streaming row-by-row logic and periodic progress logs to remain memory-safe.
- Use `--overwrite` to regenerate processed outputs cleanly.
