param(
    [switch]$Mock,
    [switch]$Reset,
    [switch]$Build
)

$ErrorActionPreference = "Stop"

if ($Reset -and -not $Mock) {
    throw "-Reset can be used only together with -Mock."
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$ComposeArgs = @(
    "--env-file", ".env"
)

if ($Mock) {
    $ComposeArgs += @(
        "--env-file", "docker-compose.mock.env"
    )
}

$ComposeArgs += @(
    "-f", "docker-compose.yaml",
    "-f", "docker-compose.dev.yaml"
)

if ($Reset) {
    docker compose @ComposeArgs run --rm --no-deps backend `
        sh -c "rm -f /data/check_annotator_mock.db"

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to reset the mock database."
    }
}

$UpArgs = @(
    "up",
    "-d",
    "--force-recreate"
)

if ($Build) {
    $UpArgs += "--build"
}

$UpArgs += @(
    "backend",
    "frontend"
)

docker compose @ComposeArgs @UpArgs

if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose failed."
}

docker compose @ComposeArgs ps

if ($Mock) {
    Write-Host "Mock login: takahashi / test1"
}

Write-Host "Open: http://localhost:3000/check_annotator/login"
