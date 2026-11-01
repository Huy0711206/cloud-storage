$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $projectRoot
python "$PSScriptRoot\online.py" stop
exit $LASTEXITCODE
