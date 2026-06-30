#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FRONTEND="$ROOT/frontend"
IMAGE="${NODE_IMAGE:-node:20-bookworm-slim}"

echo "==> Regenerating frontend/package-lock.json in $IMAGE"
docker run --rm -v "$FRONTEND:/app" -w /app "$IMAGE" sh -c \
  "rm -rf node_modules package-lock.json && npm install"

echo "==> Verifying npm ci + test + build"
docker run --rm -v "$FRONTEND:/app" -w /app "$IMAGE" sh -c \
  "rm -rf node_modules && npm ci && npm test -- --run && npm run build"

echo "==> Done. Commit frontend/package-lock.json from this Linux-generated lockfile."
