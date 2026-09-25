# Terris Frontend

Next.js 14, TypeScript, Tailwind, and Leaflet frontend for Terris.

## Setup

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## Environment

- `NEXT_PUBLIC_API_BASE_URL`: FastAPI origin; defaults to `http://localhost:8000`.

The map uses OpenStreetMap directly in local development and production. No map API key is required.

## Backend contract

- `GET /health`
- `GET /stats`
- `POST /analyze` with `{ "lat": number, "lon": number }`

The UI displays the nearest mapped environmental site, nearest Superfund site and landfill, a sorted list within 5 miles, and heat layers for the two datasets. Heat layers remain available at national zoom with reduced radius and opacity. The API retains 1/5/10-mile counts, but the sidebar omits the count table.

## Checks

```bash
npm run typecheck
npm run build
```
