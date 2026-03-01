# Terris

Terris is a deterministic environmental exposure screening app.

It helps users explore nearby environmental site records and returns a transparent `0-10` screening score based on fixed rules. It does not detect contamination and it is not a diagnostic tool.

## What Terris Includes

- Backend: FastAPI (`backend/`)
- Frontend: Next.js 14 + TypeScript + Tailwind + Leaflet (`frontend/`)
- Data pipeline scripts: normalized U.S. site datasets (`scripts/`)

## How Scoring Works

Terris computes a deterministic score from:

- Landfill proximity (`0-3`)
- Military base proximity (`0-3`)
- Industrial density (`0-4`)
- Superfund proximity (weighted)

Total score is clamped to `0-10`, then mapped to:

- `Low`
- `Moderate`
- `High`

The same location always returns the same score for the same dataset version.

## Run Locally (Quick Start)

### 1) Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Backend URL: `http://localhost:8000`

### 2) Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Frontend URL: `http://localhost:3000`

If needed, set `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local`.

## API Endpoints

- `GET /health`
- `GET /stats`
- `POST /analyze`
- `POST /report`

## Environment Variables

### Backend (important)

- `ENVIRONMENT`: `development` or `production`
- `FRONTEND_ORIGIN`: required when `ENVIRONMENT=production`
- `DATA_PATH`: default `data/processed/all_sites.csv`
- `PORT`: default `8000`
- `CACHE_SIZE`: default `5000`
- `CACHE_ROUNDING_DECIMALS`: default `4`
- `REPORT_CACHE_TTL_SECONDS`: default `259200`
- `REPORT_CACHE_MAX_ITEMS`: default `2000`
- `APP_VERSION`: default `0.1.0`

### Frontend

- `NEXT_PUBLIC_API_BASE_URL`: backend base URL

## Data Notes

The backend expects `data/processed/all_sites.csv` at startup.

If your processed dataset is missing, regenerate data with scripts from `scripts/` (see `SOURCES.md` and script docs).

## Deploy (Recommended)

### Backend on Render

- Build command:
  - `pip install -r backend/requirements.txt`
- Start command:
  - `uvicorn backend.app.main:app --host 0.0.0.0 --port 10000`
- Env vars:
  - `ENVIRONMENT=production`
  - `FRONTEND_ORIGIN=https://<your-vercel-domain>`
  - `DATA_PATH=data/processed/all_sites.csv`
- Health check path:
  - `/health`

### Frontend on Vercel

- Set:
  - `NEXT_PUBLIC_API_BASE_URL=https://<your-render-backend-domain>`
- Redeploy frontend.

## Repo Layout

```text
.
├── backend/
├── data/
├── frontend/
├── scripts/
├── SOURCES.md
└── README.md
```

## Important Scope

Terris is a proximity-based screening signal:

- It does not measure water, soil, or air samples.
- It does not prove contamination.
- It should be used with official records and local testing.
