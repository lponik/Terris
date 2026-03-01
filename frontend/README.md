# Terris Frontend (MVP)

Next.js 14 + TypeScript + Tailwind + Leaflet frontend for Terris, a national environmental exposure proxy map.

## Prerequisites

- Node.js 18+
- Backend running locally (FastAPI) at `http://localhost:8000` by default

## Setup

1. Install dependencies:

```bash
cd frontend
npm install
```

2. Configure API base URL:

```bash
cp .env.example .env.local
```

Set `NEXT_PUBLIC_API_BASE_URL` if your backend is not on `http://localhost:8000`.

3. Start dev server:

```bash
npm run dev
```

Open `http://localhost:3000` and use the Map route.

## Backend Requirement

This frontend expects these endpoints:

- `GET /health`
- `GET /stats` (optional in UI)
- `POST /analyze` with `{ "lat": number, "lon": number }`
- `POST /report` (wired as optional report action)

## Example Flow

1. Click any location on the map.
2. Click **Analyze** on the map.
3. Sidebar shows score, band, breakdown, signals, and top evidence.
4. Click **Generate Report** to call `POST /report` and render returned JSON.

## Notes

- Map defaults to continental U.S. center (`39.5, -98.35`, zoom `4`).
- Analyze requests timeout after 10 seconds.
- UI shows loading states, error states, backend health, and last-updated timestamp.
