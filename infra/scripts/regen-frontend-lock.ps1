# Regenerate frontend/package-lock.json on Linux (Docker) for CI compatibility.
$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Frontend = Join-Path $Root "frontend"
$Image = if ($env:NODE_IMAGE) { $env:NODE_IMAGE } else { "node:20-bookworm-slim" }

Write-Host "==> Regenerating frontend/package-lock.json in $Image"
docker run --rm -v "${Frontend}:/app" -w /app $Image sh -c `
  "rm -rf node_modules package-lock.json && npm install"

Write-Host "==> Verifying npm ci + test + build"
docker run --rm -v "${Frontend}:/app" -w /app $Image sh -c `
  "rm -rf node_modules && npm ci && npm test -- --run && npm run build"

Write-Host "==> Done. Commit frontend/package-lock.json (do not run npm install on Windows before commit)."
