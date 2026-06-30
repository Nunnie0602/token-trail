#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
IMAGE="${NODE_IMAGE:-node:22-bookworm-slim}"

echo "==> Backend: ruff"
(cd "$ROOT/backend" && ruff check app tests scripts)

echo "==> Backend: mypy"
(cd "$ROOT/backend" && mypy app)

echo "==> Backend: pytest"
(cd "$ROOT/backend" && pytest -q)

echo "==> Frontend: npm ci + test + build ($IMAGE)"
docker run --rm -v "$ROOT/frontend:/app" -w /app "$IMAGE" sh -c \
  "rm -rf node_modules && npm ci && npm test -- --run && npm run build"

echo "==> All local CI checks passed."
