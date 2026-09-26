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

GitHub Actions runs data validation, backend tests, frontend checks, Docker builds, and image security scans on pushes and pull requests.

## Future AWS learning deployment

The proposed first AWS deployment is intentionally small: one public EC2 instance running the existing Docker containers with Docker Compose. A lightweight reverse proxy can send browser traffic to the frontend and `/api` traffic to FastAPI. Terraform will define one VPC, one public subnet, an internet gateway, a route table, a tightly scoped security group, the EC2 instance, and its IAM role. CI/CD can build the two images, push them to ECR, and deploy the new image tags to that instance.

The dataset remains inside the backend image, so a database is not needed. S3 can be added later for Terraform remote state, and Route 53 plus HTTPS can be added when a domain is ready. This plan is meant to teach practical AWS, Terraform, Docker, networking, and deployment before introducing more infrastructure.

See [AGENT_CONTEXT.md](AGENT_CONTEXT.md) for the detailed architecture and project guardrails.
