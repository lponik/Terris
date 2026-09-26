# Terris Agent Context

Read this before changing the project. It describes branch `dev` as of 2026-09-26.

## Product boundary

Terris is a deterministic U.S. environmental-proximity map. A user chooses a location and sees distances to:

- EPA Superfund sites, including retained legacy, NPL, and SAA records;
- EPA Landfill Methane Outreach Program landfills.

Terris does **not** calculate risk, exposure, severity, health outcomes, or property safety. Keep that limitation visible. Military sites, industrial facilities, reports, and a Learn route are outside the current scope. The heat layers and homepage particle background are intentional.

## Current architecture

```text
Versioned EPA snapshots
        |
        v
scripts/build_data.py
        |-- data/processed/all_sites.csv --> FastAPI + NumPy --> /analyze
        `-- frontend/public/heat/*.json ----> Next.js + Leaflet
                                                    |
Browser <---------------- JSON ---------------------+
   |                                                |
   |-- public Nominatim search                      `-- OpenStreetMap tiles
```

The application has two Docker images and a local `compose.yaml`:

- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind, React Leaflet, and `leaflet.heat`.
- **Backend:** FastAPI, Pydantic, pandas, and NumPy on Python 3.12.
- **Data:** checked-in CSV/JSON artifacts loaded from the local filesystem.

There is no database, authentication, queue, object storage, AI dependency, or server-side frontend proxy in the current request path. The live frontend is presently linked from the README; AWS deployment is only a proposal.

## Repository map

| Path | Purpose |
|---|---|
| `backend/app/` | API, configuration, data loading, and proximity calculations |
| `frontend/app/`, `frontend/components/` | Pages and map UI |
| `scripts/` | Deterministic data build, validation, and smoke checks |
| `tests/` | API, spatial, and pipeline regression tests |
| `data/snapshots/` | Canonical versioned inputs and provenance |
| `data/processed/` | Generated backend dataset and manifest |
| `frontend/public/heat/` | Generated static heat-layer data |
| `.github/workflows/ci.yml` | Tests, builds, and Trivy image scans |

Local `.venv`, `frontend/node_modules`, `frontend/.next`, environment files, and `data/raw` research downloads are not application source.

## Backend contract

FastAPI loads `data/processed/all_sites.csv` once at startup, validates the `landfill` and `superfund` categories, and prepares immutable NumPy coordinate arrays. Each `/analyze` request runs one vectorized Haversine scan per category and reuses the results for nearest sites, radius counts, and the nearby list.

| Method | Path | Purpose |
|---|---|---|
| `GET`, `HEAD` | `/health` | Readiness and startup details |
| `GET` | `/stats` | Dataset and preparation metrics |
| `POST` | `/analyze` | Proximity for `{ "lat": number, "lon": number }` |

`/analyze` returns `location`, `nearest_mapped_site`, `nearest_by_category`, `counts_within_miles`, up to 20 `nearby_sites` within 5 miles, and `meta`. Errors use `{"error":{"code":"...","message":"..."}}`.

Configuration:

- `ENVIRONMENT`: `development` or `production`.
- `FRONTEND_ORIGIN`: required in production and used as the only CORS origin.
- `DEV_CORS_ORIGINS`: optional comma-separated local origins.
- `DATA_PATH`: defaults to `data/processed/all_sites.csv` relative to the process working directory.
- `APP_VERSION`: defaults to `0.1.0`.

## Frontend behavior

Routes are `/`, `/map`, and `/about`. The map supports location search and click selection, nearest-site results, nearby results, and landfill, Superfund, or combined heat layers.

The browser calls FastAPI through `NEXT_PUBLIC_API_BASE_URL`, which is embedded at build time and defaults to `http://localhost:8000`. It also calls public Nominatim directly. Keep Nominatim traffic user-triggered and respect its public usage policy; it is not suitable for unrestricted high-volume traffic.

Map interaction is currently limited to the contiguous U.S., although the dataset also contains Alaska, Hawaii, and territories. This is an unresolved product choice.

## Data pipeline

The shared CSV schema is:

```text
id,name,category,lat,lon,state,source,metadata_json
```

The current generated dataset has 2,323 landfill rows and 1,924 Superfund rows (4,247 total). Its version is `snapshot-e0b537c88e0c`.

`scripts/build_data.py` validates and normalizes the canonical snapshots, merges Superfund records by EPA ID, and regenerates the backend CSV, three heat payloads, and checksum manifest as one deterministic set. Coordinate precedence is NPL, retained legacy, then SAA. `scripts/validate_data.py` is read-only and verifies that every generated artifact matches the inputs.

Superfund points are representative locations, not contamination boundaries. NPL coordinates come from the EPA NPL dataset; retained legacy points may be boundary-derived; some SAA-only points are address-geocoded. Preserve provenance in `data/snapshots/sources.json` during refreshes.

## Development and verification

```bash
docker compose up --build
```

Or run the backend from the repository root and the frontend from `frontend/` as documented in the README. Important checks are:

```bash
python scripts/validate_data.py
python scripts/smoke_test.py
python -m unittest discover -s tests -v
cd frontend
npm run typecheck
npm run build
```

CI already runs validation, Python tests, frontend typechecking/building, Docker image builds, and HIGH/CRITICAL Trivy scans.

## Intentionally basic AWS plan

The first AWS version should mirror the application that already exists:

```text
Internet
   |
Route 53 + HTTPS (optional until a domain exists)
   |
Public subnet in one VPC
   |
Security group: 80/443 public; SSH restricted or disabled
   |
One small EC2 instance
   |-- lightweight reverse proxy: / -> frontend, /api -> backend
   |-- frontend container
   `-- backend container (dataset included in image)
          ^
          |
       Amazon ECR <--- CI/CD builds and pushes two images
```

Terraform should initially manage only the networking, security group, EC2 instance, IAM permissions needed to pull images, and ECR repositories. Use EC2 user data for the first Docker/Compose bootstrap. Pin image tags for repeatable deployments rather than relying on `latest`.

Suggested learning sequence:

1. Build and run both images locally with Compose.
2. Create a VPC, one public subnet, internet gateway, route table, security group, and EC2 instance in Terraform.
3. Bootstrap Docker on EC2 and deploy Compose manually once to understand the path.
4. Add ECR and push versioned images.
5. Extend GitHub Actions to test, build, push, and update the EC2 deployment using narrowly scoped credentials (prefer GitHub OIDC over long-lived AWS keys).
6. Add a domain and HTTPS when ready; add an S3 backend with state locking when collaborating or when state recovery matters.

Do not introduce ECS, Kubernetes, RDS, Auto Scaling, NAT Gateways, private-subnet tiers, a load balancer, or similar services unless a measured application requirement appears. The single EC2 host is intentionally a single point of failure and is appropriate for this learning project. The static dataset means no database is currently justified.

AWS-specific implementation details still to decide are the region, domain/DNS choice, EC2 architecture and size, reverse proxy, deployment transport, and secret handling. Do not create infrastructure until those choices are explicit.

## Near-term work

1. Fix frontend parsing of the backend's nested `error.message` envelope.
2. Resolve the default backend data path independently of the launch directory.
3. Decide whether the supported geography is the contiguous U.S. or all dataset coverage.
4. Add application-wide Nominatim rate limiting and repeated-query caching if public usage grows.
5. Add the minimal Terraform and deployment files only when AWS implementation begins.

## Read first

Start with `README.md`, `backend/app/config.py`, `backend/app/data_loader.py`, `backend/app/main.py`, `frontend/lib/api.ts`, `frontend/app/map/page.tsx`, `frontend/components/MapView.tsx`, `scripts/build_data.py`, and `data/processed/manifest.json`.
