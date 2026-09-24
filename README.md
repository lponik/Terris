# Terris

Terris is a deterministic environmental-site screening map. Select a U.S. location to compare its proximity to three public record categories:

- EPA Superfund National Priorities List sites
- U.S. military bases
- EPA Landfill Methane Outreach Program landfills

Terris is a screening tool. It does not measure contaminants, exposure, or health risk and should not replace official records or local testing.

## Live app

https://terris-theta.vercel.app/

## How it works

1. Offline scripts normalize the three source datasets into the shared schema below.
2. FastAPI loads `data/processed/all_sites.csv` once and builds one haversine `BallTree` per category.
3. `POST /analyze` finds nearby records and applies fixed proximity thresholds.
4. The Next.js app displays the score, signals, evidence, and static heat layers.

```text
id,name,category,lat,lon,state,source,metadata_json
```

The supported category values are `landfill`, `military_base`, and `superfund_npl`.

## Scoring v3

The category contributions add to a maximum score of 10:

- Landfill proximity, up to 3 points: `<1`, `<3`, and `<10` miles.
- Military-base proximity, up to 3 points: `<1`, `<5`, and `<15` miles.
- Superfund proximity, up to 4 points: `<1`, `<3`, `<10`, and `<25` miles.

Bands are Low (`<=3.3`), Moderate (`<=6.6`), and High (`>6.6`). The same coordinate and dataset always produce the same score.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness and readiness |
| `GET` | `/stats` | Dataset counts and startup metrics |
| `POST` | `/analyze` | Score and evidence for `{ "lat": number, "lon": number }` |

## Data workflow

Raw downloads stay local under `data/raw/`. Processed artifacts are versioned under `data/processed/`.

```bash
python scripts/process_all.py --overwrite
python scripts/clean_processed_data.py
python scripts/validate.py
python scripts/export_heat_points.py
python scripts/smoke_test.py
```

`clean_processed_data.py` enforces the shared schema, required fields, valid coordinates and coverage, unique site IDs, and deterministic ordering. It also collapses duplicate Superfund boundary records into one representative site point.

The retained processed files are:

```text
data/processed/landfill.csv
data/processed/military_base.csv
data/processed/superfund_npl.csv
data/processed/all_sites.csv
data/processed/process_stats.json
data/processed/summary.json
```

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
