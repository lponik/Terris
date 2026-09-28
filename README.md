# Terris

Terris is a U.S. environmental-proximity map that shows how close a selected location is to mapped EPA Superfund sites and EPA Landfill Methane Outreach Program landfills.

**Live app:** [tryterris.org](https://tryterris.org/)

## What this project demonstrates

- Designing a cost-conscious AWS architecture around the needs of a real application
- Managing cloud infrastructure and IAM with Terraform
- Building GitHub Actions CI/CD with OIDC, immutable artifacts, vulnerability scanning, and health-gated deployments
- Operating a static Next.js frontend and containerized FastAPI backend without unnecessary platform complexity

## How it works

- A deterministic data pipeline validates versioned EPA snapshots and generates the backend dataset and static heat-layer data
- FastAPI loads the dataset into NumPy arrays at startup and calculates Haversine distances in memory
- The Next.js frontend uses Leaflet, OpenStreetMap tiles, and public Nominatim search to display results
- No database, user account, API key, or AI service is required

`POST /analyze` returns the nearest mapped site, the nearest site in each category, counts within 1, 5, and 10 miles, and up to 20 nearby sites within 5 miles.

## AWS architecture

```text
Browser
  |
CloudFront
  |-- static pages and assets --> private S3 bucket
  `-- /api/* -----------------> nginx on EC2 --> FastAPI container
                                                    ^
                                                    |
                                                   ECR
```

Terraform manages the AWS infrastructure and IAM configuration. CloudFront is the public HTTPS entry point, serves the static frontend from a private S3 bucket, and forwards `/api/*` requests to nginx on a single EC2 host.

The backend runs as a Docker container from ECR, and AWS Systems Manager is used for deployment and administration without SSH.

The architecture is intentionally simple: the frontend is fully static, the dataset is bundled with the backend, and the API performs in-memory calculations without a database. This keeps cost and operational complexity low while still providing CDN delivery, reproducible infrastructure, containerized deployment, and automated CI/CD.

## CI/CD

Every push and pull request runs:

- data validation
- backend tests
- frontend typechecking and build
- backend Docker build
- blocking Trivy scans for fixable HIGH and CRITICAL vulnerabilities

Merges to `main` trigger two deployment paths:

1. **Frontend:** reuse the validated static export, sync it to S3 with cache-control headers, then invalidate CloudFront
2. **Backend:** tag the scanned image with the full Git commit SHA, push it to ECR, and deploy that exact image to EC2 using SSM Run Command

The backend deployment fails if either the container health check or the nginx-proxied health check fails.

GitHub authenticates to AWS using short-lived OIDC credentials. The pipeline stores no AWS access keys or SSH keys, never deploys an unscanned backend image, and supports rollback by redeploying a previous commit-SHA image.

## Limitations

Terris reports proximity, not risk. Results do not estimate contamination, exposure, health outcomes, or property safety.

For authoritative information, consult official EPA records and qualified local professionals.

See [AGENT_CONTEXT.md](AGENT_CONTEXT.md) for detailed architecture, repository structure, and project guardrails.