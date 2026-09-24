# Terris Backend

FastAPI backend for deterministic proximity screening across landfills, military bases, and Superfund NPL sites.

## Runtime behavior

- Loads `data/processed/all_sites.csv` once at startup.
- Builds one haversine `BallTree` per category.
- Performs no per-request CSV reads.
- Returns the same score for the same coordinate and dataset.
- Clamps the score to `0–10`.

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
- `PORT`: defaults to `8000`
- `CACHE_SIZE`: defaults to `5000`
- `CACHE_ROUNDING_DECIMALS`: defaults to `4`
- `APP_VERSION`: defaults to `0.1.0`

## Run locally

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Render should run from the repository root so the default relative `DATA_PATH` resolves correctly.
