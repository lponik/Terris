# Terris Backend (Production-Ready Deterministic API)

FastAPI backend for deterministic environmental exposure screening.

## Core Guarantees
- Dataset is loaded once at startup from `data/processed/all_sites.csv`.
- BallTree indices are built once at startup (no per-request CSV reads).
- Scoring is deterministic and always available without AI.
- `/report` is deterministic and does not call external AI services.
- Total score is clamped to `0-10`.

## Endpoints
- `GET /health`
- `GET /stats`
- `POST /analyze`
- `POST /report`

`GET /health` now includes readiness hints:
- `ready`
- `uptime_seconds`
- `startup_total_seconds`

## Environment Variables
- `ENVIRONMENT`: `development` (default) or `production`
- `FRONTEND_ORIGIN`: required in production (example: `https://terris.vercel.app`)
- `DEV_CORS_ORIGINS`: optional comma-separated origins for development
- `DATA_PATH`: default `data/processed/all_sites.csv`
- `PORT`: default `8000`
- `CACHE_SIZE`: default `5000`
- `CACHE_ROUNDING_DECIMALS`: default `4`
- `REPORT_CACHE_TTL_SECONDS`: default `259200`
- `REPORT_CACHE_MAX_ITEMS`: default `2000`
- `APP_VERSION`: default `0.1.0`

## CORS Behavior
- Development: localhost origins are allowed by default.
- Production: only `FRONTEND_ORIGIN` is allowed.

## Local Run
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

## Render Run Command
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 10000
```

Use `ENVIRONMENT=production` in Render and set `FRONTEND_ORIGIN` to the Vercel domain.

## Deployment Verification Checklist
- Confirm backend instance tier in Render and review restart logs around timeout windows.
- Verify frontend + backend env vars are aligned:
  - Frontend: `NEXT_PUBLIC_API_BASE_URL`
  - Backend: `ENVIRONMENT=production`, `FRONTEND_ORIGIN`
- Confirm Render health check path is set to `GET /health`.
- Confirm frontend and backend are deployed in compatible regions to minimize first-request latency.

## Deterministic Report Notes
`/report` returns a structured explanation based on score breakdown and proximity signals only.

It explicitly:
- treats output as a screening signal,
- does not claim contamination detection,
- avoids speculative language.
