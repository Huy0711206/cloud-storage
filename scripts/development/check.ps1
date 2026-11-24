[CmdletBinding()]
param([string]$PythonExecutable = 'python')

$ErrorActionPreference = 'Stop'
$repoRoot = Join-Path $PSScriptRoot '../..'
$phase = 'prepare'

# Keep the default checks separate from any settings in the caller's shell.
$qaEnvironment = @{
    DATABASE_URL = 'sqlite://'
    BASE_URL = 'http://testserver'
    SECRET_KEY = 'cloudbox-local-test-only'
    STORAGE_ROOT = Join-Path ([IO.Path]::GetTempPath()) ("cloudbox-check-" + [guid]::NewGuid().ToString('N'))
    TEST_POSTGRES_URL = $null
    ADMIN_EMAIL = $null
    ADMIN_PASSWORD = $null
    SMTP_HOST = $null
    SMTP_USER = $null
    SMTP_PASSWORD = $null
    VNPAY_TMN_CODE = $null
    VNPAY_HASH_SECRET = $null
}
$previous = @{}

try {
    foreach ($name in $qaEnvironment.Keys) {
        $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $qaEnvironment[$name], 'Process')
    }

    Push-Location -LiteralPath (Join-Path $repoRoot 'apps/portal/backend')
    try {
        $phase = 'backend tests'
        Write-Host "CloudBox: $phase"
        & $PythonExecutable -m pytest -q
        if ($LASTEXITCODE -ne 0) { throw "Exit code $LASTEXITCODE" }
    } finally {
        Pop-Location
    }

    Push-Location -LiteralPath (Join-Path $repoRoot 'apps/portal/frontend')
    try {
        $phase = 'frontend install (frozen lockfile)'
        Write-Host "CloudBox: $phase"
        pnpm install --frozen-lockfile --ignore-scripts
        if ($LASTEXITCODE -ne 0) { throw "Exit code $LASTEXITCODE" }

        $phase = 'TypeScript'
        Write-Host "CloudBox: $phase"
        pnpm check
        if ($LASTEXITCODE -ne 0) { throw "Exit code $LASTEXITCODE" }

        $phase = 'frontend unit tests'
        Write-Host "CloudBox: $phase"
        node --test
        if ($LASTEXITCODE -ne 0) { throw "Exit code $LASTEXITCODE" }

        $phase = 'frontend build'
        Write-Host "CloudBox: $phase"
        pnpm build
        if ($LASTEXITCODE -ne 0) { throw "Exit code $LASTEXITCODE" }
    } finally {
        Pop-Location
    }
    Write-Host 'CloudBox checks passed.'
} catch {
    Write-Error "CloudBox check failed at ${phase}. $($_.Exception.Message)" -ErrorAction Continue
    exit 1
} finally {
    foreach ($name in $previous.Keys) {
        [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process')
    }
}
