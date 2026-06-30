#!/usr/bin/env bash
# Phase 2 E2E: docker compose (redis + backend) then frontend API integration tests.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE_FILE="$ROOT/infra/docker/docker-compose.yml"
API_BASE="${E2E_API_BASE_URL:-http://localhost:8000}"

wait_backend() {
  local url="$1"
  local retries="${2:-40}"
  for ((i = 1; i <= retries; i++)); do
    if curl -sf "$url/health" >/dev/null; then
      echo "Backend healthy at $url"
      return 0
    fi
    sleep 2
  done
  echo "Backend did not become healthy at $url" >&2
  return 1
}

echo "==> Building backend image (required after code changes)"
docker compose -f "$COMPOSE_FILE" build backend

echo "==> Starting redis + backend (docker compose)"
docker compose -f "$COMPOSE_FILE" up -d redis backend
wait_backend "$API_BASE"

echo "==> Backend pytest (fakeredis E2E flow)"
(
  cd "$ROOT/backend"
  pytest -q tests/test_e2e_game_flow.py
)

echo "==> Frontend API E2E (P2-T22 / P2-T23)"
export E2E_API_BASE_URL="$API_BASE"
(
  cd "$ROOT/frontend"
  npm run test:e2e
)

echo "==> Phase 2 E2E passed."
