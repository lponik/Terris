# Terris Agent Context

Read this file before changing the application. It describes the working tree on branch `backend-troubleshooting` as of 2026-09-25, not a released commit.

## Product scope

Terris is a deterministic environmental-proximity map. A user selects a U.S. location and sees direct distance information for:

- EPA Superfund sites, including retained legacy records, NPL records, and SAA sites
- EPA Landfill Methane Outreach Program landfills

Terris does not calculate a risk score, exposure score, severity band, or health classification. Distances represent proximity to mapped source coordinates and do not estimate contaminants, personal exposure, health outcomes, or property safety.

Military bases, industrial facilities, reports, and the Learn route are outside the product. `/report` and `/learn` should remain absent unless the product scope changes explicitly.

Heat layers and the homepage particle background are intentional product features.

## Architecture

```text
versioned cleaned EPA snapshots + source metadata
                    |
                    v
          scripts/build_data.py
                    |
                    +--> data/processed/all_sites.csv
                    |             |
                    |             v
                    |       FastAPI /analyze
                    |       in-memory NumPy arrays
                    |
                    +--> frontend/public/heat/*.json
                                  |
                                  v
Next.js browser app ----------> Leaflet map
        |                           |
        |                           +--> OpenStreetMap raster tiles
        +--> public Nominatim search
```

There is no database, authentication, queue, object storage, server-side frontend proxy, container requirement, or AI dependency in the request path.

## Repository map

| Area | Responsibility | Important files |
|---|---|---|
| `backend/app/` | FastAPI startup, vectorized distance analysis, API schemas | `main.py`, `data_loader.py`, `geo.py`, `models.py` |
| `frontend/` | Next.js, TypeScript, Tailwind, Leaflet UI | `app/map/page.tsx`, `components/Sidebar.tsx`, `components/MapView.tsx`, `components/HeatLayer.tsx` |
| `scripts/` | Deterministic data build, read-only validation, smoke checks | `build_data.py`, `validate_data.py`, `smoke_test.py` |
| `tests/` | Spatial, API-contract, and data-pipeline regression tests | `test_spatial_data.py`, `test_data_pipeline.py` |
| `data/snapshots/` | Versioned canonical inputs and source metadata | `landfill.csv`, `superfund_legacy.csv`, `superfund_npl.csv`, `superfund_saa.csv`, `sources.json` |
| `data/processed/` | Generated backend runtime bundle | `all_sites.csv`, `manifest.json` |
| `frontend/public/heat/` | Generated static heat-point payloads | `landfill.json`, `superfund.json`, `combined.json` |

Generated local directories such as `.venv`, `backend/.venv`, `frontend/node_modules`, and `frontend/.next` are not application source.

## Backend analysis

At startup, FastAPI:

1. Reads `data/processed/all_sites.csv` or `DATA_PATH`.
2. Requires exactly the `landfill` and `superfund` categories.
3. Drops invalid coordinates.
4. Converts each category's coordinates to immutable NumPy arrays.
5. Precomputes latitude/longitude radians and latitude cosines.

For each `/analyze` request, `SpatialDataStore.analyze_point` calls `haversine_distances_miles` once for each category. Each NumPy distance array is reused for:

- nearest-site selection;
- counts within 1, 5, and 10 miles;
- selecting sites within the 5-mile nearby-results radius.

The two category lists are merged, sorted by distance with deterministic tie-breaking, and capped at 20 nearby sites. No BallTree, scikit-learn, geopy, cache, coordinate rounding, or per-request CSV read is used.

The API routes are:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Readiness, version, uptime, and startup duration |
| `HEAD` | `/health` | Lightweight readiness check |
| `GET` | `/stats` | Dataset counts and startup preparation metrics |
| `POST` | `/analyze` | Environmental proximity for `{ "lat": number, "lon": number }` |

The `/analyze` response contains:

```text
location
nearest_mapped_site
nearest_by_category.{landfill,superfund}
counts_within_miles.{landfill,superfund}.{within_1_mile,within_5_miles,within_10_miles}
nearby_sites
meta
```

Every returned site includes ID, name, category, distance in miles, latitude, longitude, state, and source. Score, signals, evidence-group, breakdown, band, and top-driver fields no longer exist.

Application errors retain the envelope:

```json
{"error":{"code":"invalid_request","message":"...","details":[]}}
```

### Backend configuration

Environment files are loaded from `backend/.env` and then root `.env` without overriding exported values.

- `ENVIRONMENT`: `development` or `production`.
- `FRONTEND_ORIGIN`: required in production and used as the sole CORS origin.
- `DEV_CORS_ORIGINS`: optional comma-separated development origins.
- `DATA_PATH`: defaults to `data/processed/all_sites.csv` relative to the launch directory.
- `APP_VERSION`.

## Frontend

The frontend uses Next.js 14.2.35, React 18, strict TypeScript, Tailwind, Leaflet, and `leaflet.heat`.

Routes:

- `/`: short landing page with the retained particle background.
- `/map`: location selection, proximity analysis, mapped-site results, and heat layers.
- `/about`: concise sources, method, and limitations.

The analysis panel is distance-first:

1. selected location in a secondary text treatment;
2. the nearest mapped environmental-site distance as the dominant result;
3. nearest Superfund and landfill rows;
4. up to 20 sites within 5 miles, sorted closest first;
5. the required exposure/health-risk disclaimer.

Selecting a result focuses its map marker without replacing the originally selected analysis coordinate. The nearest Superfund site and landfill are also shown as small category-colored circle markers after analysis. Distances at or below 0.5 mile use red text; distances above 0.5 and at or below 1 mile use yellow text. The selected-location coordinate line includes a state abbreviation when Nominatim returns one.

The map uses the standard OpenStreetMap raster tile service with a compact bottom-left OSM credit and no application API key. Leaflet's default bottom-right attribution control is disabled. Heat modes are `off`, `landfill`, `superfund`, and `combined`; military controls and payloads were removed. Heat remains available at every zoom level, with smaller, lower-opacity kernels at national zoom. Zooming does not overwrite the user's selected heat mode. Selecting a nearby site uses an immediate view change so the heat canvas and basemap redraw together instead of separating during an animated flight.

Address search calls public OpenStreetMap Nominatim directly from the browser. It is user-triggered rather than autocomplete, but public use is limited to moderate traffic and a maximum of one request per second for the entire application. Policy: <https://operations.osmfoundation.org/policies/nominatim/>

Map interaction is restricted to the contiguous U.S., while the snapshots also include Alaska, Hawaii, and territories. This remains an explicit product decision to resolve.

## Data pipeline

The shared CSV schema is:

```text
id,name,category,lat,lon,state,source,metadata_json
```

Current dataset:

| Category | Rows |
|---|---:|
| Landfill | 2,323 |
| Superfund | 1,924 |
| **Total** | **4,247** |

Run:

```bash
python scripts/build_data.py
python scripts/validate_data.py
```

`build_data.py` validates the landfill, retained legacy Superfund, NPL, and filtered SAA snapshots; merges Superfund records by EPA ID; normalizes text/metadata/order; rejects schema/category/ID/coordinate problems; and generates the backend CSV plus all three heat payloads together. Coordinate precedence is new NPL, retained legacy, then SAA. Outputs are staged and promoted with rollback on failure.

`data/processed/manifest.json` records source provenance, cleaning history, Superfund merge counts, row counts, coordinate bounds, and SHA-256 hashes. The current deterministic dataset version is `snapshot-e0b537c88e0c` (regenerate after any snapshot or source-metadata change).

`validate_data.py` is read-only. It rebuilds expected bytes in memory and requires every checked-in generated artifact to match.

The ignored `data/raw/` directory may still contain old research downloads, including a military source, but it is not part of the active build or deployed product. The canonical military snapshot and generated military heat file were deleted.

### Superfund location limitation

Superfund points are representative mapped locations. NPL coordinates come from the EPA NPL dataset, retained legacy-only points may be boundary-derived, and some SAA-only points are address-geocoded. These points do not represent contamination boundaries or exact contamination locations.

The former `NPL_Boundaries.gdb` is represented by `superfund_legacy.csv` for compatibility so legacy-only EPA IDs remain available. `superfund_npl.csv` supplies Final, Proposed, and Deleted NPL records, and `superfund_saa.csv` supplies filtered SAA sites with usable coordinates. Capture download URLs, retrieval times, relevant terms, and raw checksums on future refreshes.

## Local development

Backend, from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Frontend, in a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open <http://localhost:3000>. `NEXT_PUBLIC_API_BASE_URL` defaults to <http://localhost:8000>.

Useful checks:

```bash
python scripts/validate_data.py
python scripts/smoke_test.py
python -m unittest discover -s tests -v
cd frontend
npm run typecheck
npm run build
```

## Verification baseline

On 2026-09-25, the proximity-only working tree passed:

- 13 Python tests covering Haversine equivalence, nearest selection, 1/5/10-mile counts, nearby sorting/limits, empty-radius behavior, the score-free API contract, CSV validation, deterministic data generation, and manifest hashes;
- read-only validation of all 4,247 generated rows and three heat payloads;
- NYC, Chicago, and Los Angeles file-based smoke checks using the production NumPy path;
- Python compilation;
- frontend TypeScript checking and the Next.js production build.

Re-run checks after merging or rebasing because this baseline describes an uncommitted working tree.

## Next recommendations

Prefer explicit boundaries and deletion over new infrastructure. Do not add a database, queue, container layer, workflow orchestrator, or DVC until a measured need appears.

1. Add CI for data validation, Python tests, frontend typecheck, and frontend build.
2. Resolve `DATA_PATH` from the repository/package location rather than the caller's current working directory.
3. Teach the frontend error parser to read the backend's nested `error.message`.
4. Decide whether supported geography is contiguous U.S. only or all snapshot coverage.
5. If public Nominatim search remains, add an application-wide one-request-per-second limiter and cache repeated queries.

## Files to read first

1. `README.md`
2. `backend/app/data_loader.py`
3. `backend/app/geo.py`
4. `backend/app/models.py`
5. `backend/app/main.py`
6. `frontend/app/map/page.tsx`
7. `frontend/components/Sidebar.tsx`
8. `frontend/components/MapView.tsx`
9. `scripts/build_data.py`
10. `data/processed/manifest.json`
