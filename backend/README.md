# Terris Backend

FastAPI backend for deterministic proximity analysis across landfills and Superfund sites.

## Runtime behavior

- Loads `data/processed/all_sites.csv` once at startup.
- Precomputes immutable NumPy coordinate arrays for each category.
- Uses one vectorized NumPy Haversine scan per category and request.
- Reuses each distance array for nearest-site selection and 1, 5, and 10-mile counts.
- Performs no per-request CSV reads.
- Performs no coordinate rounding or response caching.
- Returns the nearest mapped site in each category.
- Returns up to 20 sites within 5 miles, sorted by distance.

## Endpoints

- `GET /health`
- `HEAD /health`
- `GET /stats`
- `POST /analyze`

## Environment variables

- `ENVIRONMENT`: `development` (default) or `production`
- `FRONTEND_ORIGIN`: required in production
- `DEV_CORS_ORIGINS`: optional comma-separated development origins
- `DATA_PATH`: defaults to `data/processed/all_sites.csv`
- `APP_VERSION`: defaults to `0.1.0`

## Run locally

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Run the backend regression tests from the repository root:

```bash
python -m unittest discover -s tests -v
```

Render should run from the repository root so the default relative `DATA_PATH` resolves correctly.
