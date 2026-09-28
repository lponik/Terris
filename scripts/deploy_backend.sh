#!/usr/bin/env bash
set -Eeuo pipefail

IMAGE_URI="${1:?Usage: deploy_backend.sh <image-uri> <aws-region>}"
AWS_REGION="${2:?Usage: deploy_backend.sh <image-uri> <aws-region>}"
CONTAINER_NAME="terris-backend"
ECR_REGISTRY="${IMAGE_URI%%/*}"

echo "Authenticating Docker to ${ECR_REGISTRY}"
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

echo "Pulling immutable backend image ${IMAGE_URI}"
docker pull "${IMAGE_URI}"

PREVIOUS_IMAGE="$(docker inspect --format '{{.Config.Image}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
if [[ -n "${PREVIOUS_IMAGE}" ]]; then
  echo "Replacing ${CONTAINER_NAME}; previous image was ${PREVIOUS_IMAGE}"
  docker rm --force "${CONTAINER_NAME}"
fi

docker run --detach \
  --name "${CONTAINER_NAME}" \
  --restart unless-stopped \
  --publish 127.0.0.1:8000:8000 \
  "${IMAGE_URI}"

echo "Waiting for direct backend health"
for attempt in {1..30}; do
  if curl --fail --silent --show-error http://127.0.0.1:8000/health >/dev/null; then
    break
  fi

  if [[ "${attempt}" -eq 30 ]]; then
    echo "Backend failed its direct health check" >&2
    docker logs "${CONTAINER_NAME}" >&2
    exit 1
  fi

  sleep 2
done

echo "Verifying nginx /api proxy health"
if ! curl --fail --silent --show-error http://127.0.0.1/api/health; then
  echo "Backend failed its proxied health check" >&2
  docker logs "${CONTAINER_NAME}" >&2
  exit 1
fi

echo
echo "Deployment healthy: ${IMAGE_URI}"
