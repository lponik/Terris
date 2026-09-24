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

The UI displays the score, category breakdown, proximity signals, nearest evidence records, and heat layers for landfills, military bases, and Superfund sites.

## Checks

```bash
npm run typecheck
npm run build
```
