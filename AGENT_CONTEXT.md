# Terris Agent Context

Read this before changing the project. This file is intentionally safe for a public repository. Never add credentials, tokens, account numbers, ARNs, resource IDs, IP addresses, DNS-provider details, private endpoints, or Terraform state values here.

## Product boundary

Terris is a deterministic U.S. environmental-proximity map. A user chooses a location and sees distances to EPA Superfund sites and EPA Landfill Methane Outreach Program landfills.

Terris reports proximity, not risk, exposure, severity, health outcomes, or property safety. Keep that limitation visible. Military sites, industrial facilities, reports, and a Learn route are outside the current scope. The heat layers and homepage particle background are intentional.

## Current architecture

```text
Versioned EPA snapshots
        |
        v
scripts/build_data.py
        |-- data/processed/all_sites.csv --> FastAPI + NumPy
        `-- frontend/public/heat/*.json ----> Next.js static export

Browser --> CloudFront
             |-- static routes --> private S3 bucket
             `-- /api/* -------> nginx on EC2 --> backend container
```

- **Frontend:** Next.js, React, TypeScript, Tailwind, React Leaflet, and `leaflet.heat`.
- **Backend:** FastAPI, Pydantic, and NumPy on Python 3.12.
- **Data:** checked-in CSV/JSON artifacts loaded from the local filesystem.
- **AWS:** Terraform-managed networking, S3, CloudFront, EC2, ECR, IAM, and SSM access.
- **CI/CD:** GitHub Actions authenticates to AWS through OIDC. It does not use long-lived AWS access keys or SSH.

There is no database, user authentication, queue, or AI dependency. Production uses a static frontend in S3 rather than a frontend container. The local `compose.yaml` remains a development convenience.

## Repository map

| Path | Purpose |
|---|---|
| `backend/app/` | API, configuration, data loading, and proximity calculations |
| `frontend/app/`, `frontend/components/` | Pages and map UI |
| `scripts/` | Data build, validation, smoke checks, and backend deployment helper |
| `tests/` | API, spatial, and pipeline regression tests |
| `data/snapshots/` | Canonical versioned inputs and provenance |
| `data/processed/` | Generated backend dataset and manifest |
| `frontend/public/heat/` | Generated static heat-layer data |
| `infra/terraform/` | AWS infrastructure and least-privilege IAM |
| `.github/workflows/ci.yml` | CI, image publishing, and AWS deployment |

Local virtual environments, dependency directories, build output, Terraform state/plan files, provider caches, environment files, and raw research downloads are not application source and must remain ignored.

## Backend contract

FastAPI loads `data/processed/all_sites.csv` once at startup, validates the supported categories, and prepares immutable NumPy coordinate arrays. Each `/analyze` request runs vectorized Haversine calculations and reuses the results for nearest sites, radius counts, and nearby results.

| Method | Path | Purpose |
|---|---|---|
| `GET`, `HEAD` | `/health` | Readiness and startup details |
| `GET` | `/stats` | Dataset and preparation metrics |
| `POST` | `/analyze` | Proximity for `{ "lat": number, "lon": number }` |

`/analyze` returns `location`, `nearest_mapped_site`, `nearest_by_category`, `counts_within_miles`, up to 20 `nearby_sites` within 5 miles, and `meta`. Errors use `{"error":{"code":"...","message":"..."}}`.

Runtime configuration is documented in `backend/README.md`. Do not add real production values to documentation or tracked environment files.

## Frontend behavior

Routes are `/`, `/map`, and `/about`. The map supports location search and click selection, nearest-site results, nearby results, and landfill, Superfund, or combined heat layers.

The frontend is a static export. In production, browser API requests use the same-origin `/api` path routed by CloudFront. Local development defaults to the local backend unless `NEXT_PUBLIC_API_BASE_URL` is explicitly set.

The browser calls public Nominatim directly. Keep requests user-triggered and respect its usage policy. The map interaction is currently limited to the contiguous U.S., although the dataset has wider coverage; treat that as an unresolved product choice.

## Data pipeline

The shared CSV schema is:

```text
id,name,category,lat,lon,state,source,metadata_json
```

`scripts/build_data.py` validates and normalizes canonical snapshots, merges Superfund records by EPA ID, and regenerates the backend CSV, heat payloads, and checksum manifest as one deterministic set. `scripts/validate_data.py` is read-only and verifies that generated artifacts match the inputs.

Superfund points are representative locations, not contamination boundaries. Preserve provenance in `data/snapshots/sources.json` during refreshes. Read the checked-in manifest when exact dataset counts or versions matter; do not duplicate those values here because they change.

## Development and verification

Use the README for local startup instructions. Important checks are:

```bash
python scripts/validate_data.py
python scripts/smoke_test.py
python -m unittest discover -s tests -v
cd frontend
npm run typecheck
npm run build
```

Before changing infrastructure, run:

```bash
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan
```

Always review the complete plan before applying. Existing cloud configuration may have been changed outside Terraform. Custom-domain aliases and certificates are intentionally protected from Terraform updates; do not remove that lifecycle guard without explicit user direction.

## CI/CD behavior

Pull requests and pushes run backend validation/tests, frontend typechecking/building, the backend Docker build, and a fixable HIGH/CRITICAL Trivy image scan.

Pushes to the configured deployment branch additionally:

1. Upload the static frontend build as a short-lived workflow artifact.
2. Assume the deployment role through GitHub OIDC.
3. Sync the frontend to S3 with separate HTML, general-asset, and immutable Next.js cache policies.
4. Invalidate CloudFront.
5. Tag the scanned backend image with the full Git commit SHA and push it to immutable ECR.
6. Discover the single running backend instance from its Terraform-managed `Name` tag.
7. Transfer and invoke `scripts/deploy_backend.sh` through SSM Run Command.
8. Fail unless both direct backend health and the nginx `/api` health path succeed.

The deployment helper is persisted on the instance under `/opt/terris` so the same path can deploy a prior immutable tag during rollback. Do not add SSH deployment, open port 22, use `latest` as the only tag, or weaken the Trivy gate.

GitHub repository variables contain only non-secret identifiers. Never copy their values into this file. Obtain current values from Terraform outputs and repository settings. Never add AWS access keys to GitHub.

## Infrastructure guardrails

- Keep the current architecture: private S3 frontend, CloudFront routing, one EC2 backend host, ECR, SSM, and Terraform.
- Do not introduce ECS, Kubernetes, RDS, Auto Scaling, NAT Gateways, load balancers, or additional tiers without a measured requirement and explicit approval.
- Keep the GitHub OIDC trust restricted to the intended repository and deployment branch.
- Keep deployment permissions scoped to the Terris resources wherever AWS supports resource-level permissions.
- EC2 discovers and pulls the exact immutable ECR tag; GitHub initiates deployment through SSM only.
- Resolve the backend instance by tag, require exactly one running match, and fail safely otherwise.
- Preserve the loopback-only backend port binding and the existing restart policy.
- Do not manage custom-domain or certificate configuration unless the user explicitly brings it into scope.

## Public-repository safety

Before committing documentation or workflow changes, check for accidental disclosure. Do not commit:

- credentials, access keys, tokens, passwords, cookies, or private keys;
- AWS account numbers, full ARNs, concrete resource IDs, public IPs, or private endpoints in documentation;
- Terraform state, saved plans, crash logs, or provider caches;
- `.env` files or copied runtime configuration;
- command output containing infrastructure identifiers when a generic example is sufficient.

Resource identifiers may be non-secret, but this project intentionally keeps them out of public documentation. Use placeholders in examples.

## Read first

Start with `README.md`, `.github/workflows/ci.yml`, `scripts/deploy_backend.sh`, `infra/terraform/github_actions.tf`, `backend/app/config.py`, `backend/app/data_loader.py`, `backend/app/main.py`, `frontend/lib/api.ts`, `frontend/app/map/page.tsx`, `frontend/components/MapView.tsx`, `scripts/build_data.py`, and `data/processed/manifest.json`.
