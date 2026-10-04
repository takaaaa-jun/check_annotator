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
    "--env-file", ".env",
    "-f", "docker-compose.yaml",
    "-f", "docker-compose.dev.yaml"
)

$PreviousDataMode = $env:APP_DATA_MODE
$PreviousDatabaseUrl = $env:DATABASE_URL
$PreviousInternalApiUrl = $env:INTERNAL_API_URL

function Restore-EnvironmentVariable {
    param(
        [string]$Name,

        [AllowNull()]
        [string]$Value
    )

    if ($null -eq $Value) {
        Remove-Item `
            "Env:$Name" `
            -ErrorAction SilentlyContinue
    }
    else {
        Set-Item `
            "Env:$Name" `
            $Value
    }
}

try {
    $env:INTERNAL_API_URL = (
        "http://backend:8000"
    )

    if ($Mock) {
        $env:APP_DATA_MODE = "mock"

        $env:DATABASE_URL = (
            "sqlite:////data/" +
            "check_annotator_mock.db"
        )

        Write-Host (
            "Starting SQLite mock mode..."
        )

        if ($Reset) {
            Write-Host (
                "Resetting the SQLite " +
                "mock database..."
            )

            docker compose `
                @ComposeArgs `
                run `
                --rm `
                --no-deps `
                backend `
                sh `
                -c `
                "rm -f /data/check_annotator_mock.db"

            if ($LASTEXITCODE -ne 0) {
                throw (
                    "Failed to reset " +
                    "the mock database."
                )
            }
        }
    }
    else {
        $env:APP_DATA_MODE = "database"

        if (
            $null -eq
            $PreviousDatabaseUrl
        ) {
            Remove-Item `
                Env:DATABASE_URL `
                -ErrorAction SilentlyContinue
        }
        else {
            $env:DATABASE_URL = (
                $PreviousDatabaseUrl
            )
        }

        Write-Host (
            "Starting MySQL database mode..."
        )
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

    docker compose `
        @ComposeArgs `
        @UpArgs

    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose failed."
    }

    docker compose `
        @ComposeArgs `
        ps

    Write-Host ""

    if ($Mock) {
        Write-Host (
            "Mock login: " +
            "takahashi / test1"
        )
    }

    Write-Host (
        "Open: http://localhost:3000" +
        "/check_annotator/login"
    )
}
finally {
    Restore-EnvironmentVariable `
        -Name "APP_DATA_MODE" `
        -Value $PreviousDataMode

    Restore-EnvironmentVariable `
        -Name "DATABASE_URL" `
        -Value $PreviousDatabaseUrl

    Restore-EnvironmentVariable `
        -Name "INTERNAL_API_URL" `
        -Value $PreviousInternalApiUrl
}