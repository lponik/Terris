# Terris Agent Context

This is the current project map for maintainers and coding agents. Read it before changing the application.

It reflects the uncommitted working tree on branch `backend-troubleshooting` as of 2026-09-23, after the industrial-data, report, and Learn feature removal. It describes the working tree, not a released commit.

## Product scope

Terris is a deterministic environmental-site screening map. A user selects a U.S. location and receives a `0-10` score based only on proximity to:

- EPA Superfund National Priorities List sites
- U.S. military bases
- EPA Landfill Methane Outreach Program landfills

Terris is a screening tool. It does not measure contaminants, exposure, health outcomes, or property safety. Preserve that limitation in product copy and API behavior.

Industrial facilities are no longer part of the product. Reports and the Learn route were also removed. `/report` and `/learn` should remain absent unless the product scope changes explicitly.

## Current architecture

```text
manually downloaded public datasets
        |
        v
offline Python normalization and cleaning
        |
        +--> data/processed/all_sites.csv
        |             |
        |             v
        |       FastAPI /analyze
        |       in-memory records + BallTrees
        |
        +--> frontend/public/heat/*.json
                      |
                      v
Next.js browser app --> Leaflet map
        |                  |
        |                  +--> OpenStreetMap standard raster tiles
        +--> public Nominatim search
```

There is no database, authentication, queue, object storage, server-side frontend proxy, or AI dependency in the request path.

## Repository map

| Area | Responsibility | Important files |
|---|---|---|
| `backend/app/` | FastAPI startup, spatial lookup, scoring, API schemas | `main.py`, `data_loader.py`, `scoring.py`, `models.py` |
| `frontend/` | Next.js, TypeScript, Tailwind, Leaflet UI | `app/map/page.tsx`, `components/MapView.tsx`, `components/Sidebar.tsx`, `lib/api.ts` |
| `scripts/` | Offline processing, cleanup, validation, heat export, smoke checks | `process_all.py`, `process_superfund_npl.py`, `clean_processed_data.py`, `validate.py` |
| `data/processed/` | Versioned runtime dataset and processing metadata | `all_sites.csv`, three category CSVs, `summary.json` |
| `frontend/public/heat/` | Versioned static heat-point payloads | `manifest.json`, category JSON files |

Generated local directories such as `backend/.venv`, `frontend/node_modules`, and `frontend/.next` account for nearly all checkout disk usage. They are not application source.

## Runtime backend

At startup, FastAPI:

1. Reads `data/processed/all_sites.csv` or `DATA_PATH`.
2. Validates the shared schema and the three allowed categories.
3. Drops invalid coordinates.
4. Builds one scikit-learn haversine `BallTree` per category.
5. Stores the dataset, indexes, settings, and analysis cache in process memory.

The CSV is not read per request. Each backend worker has its own full dataset and independent cache.

The only API routes are:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Readiness, version, uptime, and startup duration |
| `HEAD` | `/health` | Lightweight readiness check |
| `GET` | `/stats` | Dataset counts and startup/cache metrics |
| `POST` | `/analyze` | Score and evidence for `{ "lat": number, "lon": number }` |

Pydantic forbids extra request fields. Application errors use this envelope:

```json
{"error":{"code":"invalid_request","message":"...","details":[]}}
```

`/analyze` finds the nearest three records in each category, calculates the nearest-category distances, counts Superfund sites within three miles, and returns the score plus evidence.

### Scoring v3

`backend/app/scoring.py` is the scoring source of truth:

- Landfill proximity: up to 3 points at `<1`, `<3`, and `<10` miles.
- Military-base proximity: up to 3 points at `<1`, `<5`, and `<15` miles.
- Superfund proximity: up to 4 points at `<1`, `<3`, `<10`, and `<25` miles.
- Bands: Low `<=3.3`, Moderate `<=6.6`, High `>6.6`.

The category maxima total exactly 10. The same coordinate and dataset produce the same score.

### Backend configuration

Environment files are loaded from `backend/.env` and then root `.env` without overriding exported values.

- `ENVIRONMENT`: `development` or `production`.
- `FRONTEND_ORIGIN`: required in production; used as the sole CORS origin.
- `DEV_CORS_ORIGINS`: optional comma-separated development origins.
- `DATA_PATH`: defaults to `data/processed/all_sites.csv` relative to the launch directory.
- `PORT`: parsed by settings but not used by FastAPI; the process launcher selects the port.
- `CACHE_SIZE`, `CACHE_ROUNDING_DECIMALS`.
- `APP_VERSION`.

The process-local LRU cache keys requests by rounded coordinates. A cache hit retains the first response's exact `location` and `timestamp_utc` for that rounded key. Treat this as an implementation flaw, not a contract to preserve.

## Frontend

The frontend uses Next.js 14.2.35, React 18, strict TypeScript, Tailwind, Leaflet, and `leaflet.heat`.

Current routes:

- `/`: short landing page.
- `/map`: coordinate/address selection, analysis, score, nearby evidence, and optional heat layers.
- `/about`: concise data sources, method, and limitations.

`frontend/app/map/page.tsx` is the largest frontend file and owns most orchestration: point selection, API state, search, heat data, map focus, and evidence selection. `MapView.tsx` owns Leaflet interaction. `Sidebar.tsx` renders results.

The map always uses the standard OpenStreetMap raster tile service. There is no map key or alternate provider path. Attribution remains visible. Normal interactive browser use must follow the official tile policy: no bulk fetching or offline preloading, preserve browser caching and referrers, and do not assume an SLA. Policy: <https://operations.osmfoundation.org/policies/tiles/>

Address search calls the public OpenStreetMap Nominatim endpoint directly from the browser. It is user-triggered rather than autocomplete, but public usage is limited to moderate traffic and an absolute maximum of one request per second for the entire application. Policy: <https://operations.osmfoundation.org/policies/nominatim/>

Map interaction is restricted to the contiguous U.S., while the processed dataset also contains Alaska, Hawaii, and territories. This mismatch needs an explicit product decision.

The browser calls FastAPI directly through `NEXT_PUBLIC_API_BASE_URL`, which defaults to `http://localhost:8000`. Heat payloads are fetched as static JSON from `frontend/public/heat/`, not from the backend.

`frontend/lib/types.ts` manually mirrors the FastAPI response. The frontend error parser checks top-level `detail` and `message`, but not the backend's nested `error.message`, so some useful backend errors become generic status messages.

## Processed data

The shared CSV schema is:

```text
id,name,category,lat,lon,state,source,metadata_json
```

Allowed categories and current counts:

| Category | Rows |
|---|---:|
| Landfill | 2,323 |
| Military base | 163 |
| Superfund NPL | 1,908 |
| **Total** | **4,394** |

The cleanup pass retained all landfill and military rows. For Superfund, it collapsed 207 duplicate site IDs and removed one out-of-coverage record, reducing 2,116 input rows to 1,908 representative site points. Category CSVs and `all_sites.csv` are deterministically ordered and contain only the eight shared columns.

`summary.json` contains current counts, coordinate ranges, file counts, and cleanup results. `process_stats.json` records the earlier processing run; do not assume it alone describes the post-cleanup artifact.

## Data pipeline limitations

The processed bundle is usable, but the pipeline is not fully reproducible from the current raw directory:

- The checked-out military CSV has no usable geometry and depends on an FRS facility CSV for coordinate backfill.
- That FRS file is currently absent, so `process_all.py` cannot rebuild the military output from the available raw inputs.
- Superfund processing imports `geopandas` plus `fiona` or `pyogrio`, but those dependencies are not declared in either requirements file.
- Root `requirements.txt` contains only `openpyxl`; backend runtime requirements live separately in `backend/requirements.txt`.
- `process_all.py --overwrite` deletes processed outputs before confirming every required raw input is present.
- `clean_processed_data.py` performs a second cleanup/deduplication pass after ingestion, leaving rules split across scripts.
- `validate.py` rewrites tracked `summary.json` on every run, even when the intent is read-only validation.
- Heat JSON must be regenerated separately after processed-data changes.
- `download_all.py` only prints instructions and does not download or verify anything.

Do not run `process_all.py --overwrite` casually. Preserve the current processed bundle until the pipeline is made atomic and reproducible.

## Local development

Run the backend from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open <http://localhost:3000>. The default frontend configuration points to <http://localhost:8000>. OpenStreetMap needs no application API key.

Useful checks from the repository root:

```bash
python scripts/validate.py
python scripts/smoke_test.py
cd frontend
npm run typecheck
npm run build
```

Be aware that `validate.py` currently updates `summary.json`.

## Current verification baseline

Before this context update, the cleaned working tree passed:

- processed-file schema, category, count, ID, coordinate, and metadata validation;
- file-based and live-backend smoke checks;
- live `/stats` and `/analyze` checks;
- frontend TypeScript checking and production build;
- route checks confirming `/map` and `/about` return `200`, while `/report` and `/learn` return `404`.

Re-run the checks after merging or rebasing because this baseline describes an uncommitted working tree.

## Deletion-first simplification recommendations

These are recommendations, not completed changes. Prefer deletion before abstraction.

### 1. Remove confirmed dead code

Low risk and recommended next:

- Delete unused `frontend/components/EvidenceList.tsx`.
- Delete unused `formatLatLon`, `formatTimestamp`, and `toJsonBlock` exports from `frontend/lib/format.ts`.
- Delete `scripts/download_all.py` after source acquisition instructions are written in documentation.
- Remove the unused backend `PORT` setting and document the port only in launcher commands.

### 2. Remove decorative runtime dependencies

Delete `StarfieldBackground.tsx` and its use on the landing page, then remove `react-tsparticles` and `tsparticles-slim`. A static CSS background is enough for the product and removes two direct dependencies plus their transitive bundle/runtime surface.

### 3. Decide whether heat layers earn their complexity

The core product still works without heat layers: users can search or click, analyze, and inspect nearby evidence. Removing heat would delete:

- `HeatLayer.tsx` and Leaflet heat integration;
- `leaflet.heat` and `@types/leaflet.heat`;
- static heat JSON and `scripts/export_heat_points.py`;
- heat fetch/cache/downsampling state from the 637-line map page;
- heat controls and zoom-coupled behavior from `MapView.tsx`.

This is the largest safe optional feature deletion. Keep it only if the overview visualization is central to the product.

### 4. Make a deliberate address-search choice

Keeping search is useful, but public Nominatim adds policy, availability, privacy, and rate-limit dependencies. The smallest product is click/coordinate-only. If search stays, add an application-wide one-request-per-second limiter, cache repeated queries, show attribution, and keep the provider URL configurable without a code release.

### 5. Simplify the backend after benchmarking

With only 4,394 rows, the analysis cache may cost more clarity than it saves. Benchmark uncached `/analyze`, then consider deleting `AnalysisCache`, `CACHE_SIZE`, and coordinate rounding. That removes stale-location/timestamp behavior and makes debugging deterministic.

`pandas` is currently used for CSV loading. Replacing it with the standard `csv` module plus NumPy would remove a large runtime dependency. A vectorized NumPy haversine scan may also be fast enough at this dataset size to replace scikit-learn `BallTree`; measure p50/p95 latency before removing scikit-learn.

### 6. Pick one honest data strategy

Do not keep a half-reproducible pipeline. Choose one:

- **Snapshot-first, recommended for the current demo:** treat cleaned processed CSVs as versioned inputs, keep validation and provenance, and move raw ingestion tooling out of the runtime repo.
- **Fully reproducible pipeline:** obtain a geometry-bearing military source or preserve the required FRS input, pin source URLs/versions/checksums, declare geospatial dependencies, merge cleanup into each source processor, and write outputs to a temporary directory before atomically replacing the old bundle.

In either case, make validation read-only by default and add an explicit `--write-summary` option.

### 7. Resolve the geography mismatch

Choose either contiguous-U.S. coverage and filter the processed dataset accordingly, or expand/remove the map bounds so Alaska, Hawaii, and territories are reachable. Contiguous-only data is smaller and matches the present UI; national-plus-territories coverage is more faithful to the sources.

## Suggested migration for cleaner code and debugging

The recommended target is still a small browser app plus a small deterministic API. Avoid introducing databases, queues, containers, or extra services until they solve a measured problem.

### Phase 1: freeze behavior

- Add a small `pytest` suite for scoring thresholds, loader/category validation, `/analyze` response shape, nested error envelopes, and the intentional absence of `/report`.
- Add frontend tests only around API error parsing and search normalization.
- Add CI that runs processed-data validation, Python tests, frontend typecheck, and frontend build.

Tests add some code, but they make later deletion and dependency removal safe and make failures local rather than deployment-only.

### Phase 2: delete optional surface

- Remove the confirmed dead code and unused configuration.
- Remove the particle background.
- Decide on heat layers, address search, and geographic scope.
- Fix frontend parsing of `{ "error": { "message": "..." } }`.

### Phase 3: make data reproducible or explicitly snapshot-based

- Select one of the two data strategies above.
- Consolidate Python dependencies into `pyproject.toml` with separate runtime and pipeline extras, or into clearly named pinned requirements files.
- Record source versions/checksums and output checksums.
- Make processing atomic so a failed run cannot destroy known-good artifacts.

### Phase 4: simplify runtime dependencies

- Remove the analysis cache if benchmarks support it.
- Replace pandas with standard-library CSV loading.
- Benchmark a NumPy-only spatial scan before deciding whether BallTree/scikit-learn is still justified.
- Resolve the default data path from the repository/package location instead of the shell working directory.

### Phase 5: establish two clean frontend boundaries

After feature deletion, extract only the stable seams from `app/map/page.tsx`, such as `useAnalysis` and `useLocationSearch` or a single reducer. Avoid a large component hierarchy.

Next.js is currently acting as a client-side SPA. A later migration to Vite can reduce framework surface and make local debugging more direct, but it should be a separate, behavior-preserving change after tests and deletions. Keeping Next.js is also reasonable if Vercel deployment convenience matters more than framework size.

An even larger option is moving the 4,394-row dataset and scoring into the browser to delete FastAPI and backend hosting entirely. That would ship all evidence data to every user, increase client payload/work, and remove centralized scoring/version control. Treat it as an architecture decision, not an automatic simplification.

Containerization and hosting migration come after these phases, per the current project direction.

## Files to read first

1. `README.md`
2. `backend/app/main.py`
3. `backend/app/data_loader.py`
4. `backend/app/scoring.py`
5. `backend/app/models.py`
6. `frontend/app/map/page.tsx`
7. `frontend/components/MapView.tsx`
8. `frontend/lib/api.ts` and `frontend/lib/types.ts`
9. `scripts/clean_processed_data.py`
10. `scripts/process_all.py`
11. `data/processed/summary.json`
