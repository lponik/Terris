# Terris

Terris is a deterministic environmental-proximity map. Select a U.S. location to compare its distance to two public environmental-site categories:

- EPA Superfund sites, including retained legacy records, NPL records, and SAA sites
- EPA Landfill Methane Outreach Program landfills

Distances represent proximity to mapped environmental sites. They do not estimate contaminants, personal exposure, or health risk and should not replace official records or local testing.

## Live app

https://terris-theta.vercel.app/

## How it works

1. One offline builder validates the versioned landfill, legacy Superfund, NPL, and filtered SAA snapshots, merges Superfund records by EPA ID, and generates the shared runtime bundle.
2. FastAPI loads `data/processed/all_sites.csv` once and prepares one set of NumPy coordinate arrays per category.
3. `POST /analyze` performs one vectorized Haversine scan per category and reuses each distance array for nearest-site selection and radius counts.
4. The Next.js app displays direct proximity results and static heat layers, including a reduced-density national overview.

```text
id,name,category,lat,lon,state,source,metadata_json
```

The supported category values are `landfill` and `superfund`.

## Proximity results

`POST /analyze` returns:

- the nearest mapped environmental site overall;
- the nearest Superfund site and nearest landfill;
- category counts within 1, 5, and 10 miles;
- up to 20 sites within 5 miles, sorted by distance.

Superfund points are representative mapped locations. NPL coordinates come from the EPA NPL dataset, retained legacy-only points may be boundary-derived, and some SAA-only points are address-geocoded. These points do not represent contamination boundaries or exact contamination locations.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness and readiness |
| `GET` | `/stats` | Dataset counts and startup metrics |
| `POST` | `/analyze` | Proximity results for `{ "lat": number, "lon": number }` |

## Data workflow

Terris uses a snapshot-first pipeline. The cleaned, versioned inputs live under `data/snapshots/`; raw downloads under `data/raw/` are local research material and are not part of the active build.

```bash
python scripts/build_data.py
python scripts/validate_data.py
python scripts/smoke_test.py
python -m unittest discover -s tests -v
```

`build_data.py` validates and normalizes the canonical snapshots, merges legacy, NPL, and SAA records by EPA ID, then regenerates `all_sites.csv`, three heat payloads, and one checksum manifest. Coordinate precedence is new NPL, retained legacy, then SAA. Outputs are staged before promotion, and a failed promotion rolls back files already replaced. The build is deterministic: unchanged snapshots produce byte-identical outputs and the same dataset version.

`validate_data.py` is read-only. It applies the same snapshot checks and requires every generated artifact to match the expected bytes and checksums.

The active data layout is:

```text
data/snapshots/landfill.csv
data/snapshots/superfund_legacy.csv
data/snapshots/superfund_npl.csv
data/snapshots/superfund_saa.csv
data/snapshots/sources.json
data/processed/all_sites.csv
data/processed/manifest.json
frontend/public/heat/{landfill,superfund,combined}.json
```

Edit or replace snapshots only as an intentional dataset refresh. Update `sources.json` with provenance and cleaning counts, run the builder, review the manifest and diff, then run validation and tests. The retired raw-ingestion scripts are not required to run or deploy the application.

## Local development

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

`NEXT_PUBLIC_API_BASE_URL` defaults to `http://localhost:8000`. The map uses OpenStreetMap directly and does not require a map API key.
