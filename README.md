# Terris

Terris is an environmental-proximity map for the United States. Choose a location to see its distance from mapped EPA Superfund sites and EPA Landfill Methane Outreach Program landfills.

**Live app:** [terris-theta.vercel.app](https://terris-theta.vercel.app/)

Terris reports proximity, not risk. Results do not estimate contamination, exposure, health outcomes, or property safety. Always consult official records and qualified local professionals when those questions matter.

## How it works

- A deterministic data pipeline validates versioned EPA snapshots and generates one backend CSV plus static map heat layers.
- FastAPI loads the CSV into NumPy arrays once at startup and calculates Haversine distances in memory.
- The Next.js frontend uses Leaflet, OpenStreetMap tiles, and public Nominatim search to display the results.
- No database, user account, API key, or AI service is required.

`POST /analyze` returns the nearest mapped site, the nearest site in each category, counts within 1, 5, and 10 miles, and up to 20 sites within 5 miles.

## Run locally

The easiest option is Docker:

```bash
docker compose up --build
```

Open <http://localhost:3000>. The API is available at <http://localhost:8000>; useful endpoints are `GET /health`, `GET /stats`, and `POST /analyze`.

To run without Docker, start the services in separate terminals:

```bash
# Backend, from the repository root
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

```bash
# Frontend
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

`NEXT_PUBLIC_API_BASE_URL` defaults to `http://localhost:8000`.

## Data and checks

Canonical inputs live in `data/snapshots/`. Generated files are checked in under `data/processed/` and `frontend/public/heat/` so the deployed app does not fetch or rebuild source data at runtime.

```bash
python scripts/build_data.py       # regenerate outputs after an intentional snapshot update
python scripts/validate_data.py    # confirm generated files match the snapshots
python scripts/smoke_test.py
python -m unittest discover -s tests -v
cd frontend && npm run typecheck && npm run build
```

GitHub Actions runs data validation, backend tests, frontend checks, the backend Docker build, and a HIGH/CRITICAL Trivy image scan on pushes and pull requests.

## CI/CD

Pushes to `main` deploy through GitHub Actions using short-lived AWS credentials from GitHub OIDC. No AWS access keys or SSH keys are stored in GitHub.

The frontend job typechecks and builds the static Next.js export once, passes it to the deployment job as a short-lived artifact, syncs it to the private S3 bucket with cache-control headers, and invalidates CloudFront. HTML revalidates on every request, general assets use a one-hour cache, and hashed files under `_next/static/` use a one-year immutable cache.

The backend job runs the tests, builds the Docker image, and blocks on fixable HIGH or CRITICAL Trivy findings. Successful images are tagged with the full Git commit SHA and pushed to the immutable ECR repository. A separate deployment job discovers the single running `Name=terris-backend` EC2 instance, invokes `scripts/deploy_backend.sh` through SSM Run Command, and fails unless both the direct container and nginx-proxied health checks pass.

The deployment workflow uses these non-sensitive GitHub repository variables:

- `AWS_ROLE_ARN`
- `AWS_REGION`
- `FRONTEND_BUCKET_NAME`
- `CLOUDFRONT_DISTRIBUTION_ID`
- `BACKEND_ECR_REPOSITORY_URL`

To roll back the backend, run the persisted `/opt/terris/deploy_backend.sh` through SSM with a previously published ECR commit-SHA tag. The same pull, replacement, and health-check path is used for forward deployments and rollbacks.

See [AGENT_CONTEXT.md](AGENT_CONTEXT.md) for the detailed architecture and project guardrails.
