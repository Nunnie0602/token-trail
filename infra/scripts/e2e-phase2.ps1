# Phase 2 E2E: docker compose (redis + backend) then frontend API integration tests.
$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$ComposeFile = Join-Path $Root "infra\docker\docker-compose.yml"
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$ApiBase = if ($env:E2E_API_BASE_URL) { $env:E2E_API_BASE_URL } else { "http://localhost:8000" }

function Wait-BackendHealth {
    param([string]$Url, [int]$Retries = 40)
    for ($i = 1; $i -le $Retries; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "$Url/health" -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200) {
                Write-Host "Backend healthy at $Url"
                return
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    throw "Backend did not become healthy at $Url"
}

Write-Host "==> Building backend image (required after code changes)"
docker compose -f $ComposeFile build backend

Write-Host "==> Starting redis + backend (docker compose)"
Push-Location $Root
try {
    docker compose -f $ComposeFile up -d redis backend
    Wait-BackendHealth -Url $ApiBase
} finally {
    Pop-Location
}

Write-Host "==> Backend pytest (fakeredis E2E flow)"
Push-Location $Backend
try {
    pytest -q tests/test_e2e_game_flow.py
} finally {
    Pop-Location
}

Write-Host "==> Frontend API E2E (P2-T22 / P2-T23)"
$env:E2E_API_BASE_URL = $ApiBase
Push-Location $Frontend
try {
    npm run test:e2e
} finally {
    Pop-Location
}

Write-Host "==> Phase 2 E2E passed."
