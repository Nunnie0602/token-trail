# Simulate GitHub Actions CI locally (backend native + frontend via Docker).
$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Frontend = Join-Path $Root "frontend"
$Backend = Join-Path $Root "backend"
$Image = if ($env:NODE_IMAGE) { $env:NODE_IMAGE } else { "node:22-bookworm-slim" }

Write-Host "==> Backend: ruff"
Push-Location $Backend
try {
    ruff check app tests scripts
    Write-Host "==> Backend: mypy"
    mypy app
    Write-Host "==> Backend: pytest"
    pytest -q
} finally {
    Pop-Location
}

Write-Host "==> Frontend: npm ci + test + build ($Image)"
docker run --rm -v "${Frontend}:/app" -w /app $Image sh -c `
  "rm -rf node_modules && npm ci && npm test -- --run && npm run build"

Write-Host "==> All local CI checks passed."
