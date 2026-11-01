param([switch]$ConfirmPublish)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $projectRoot
if (-not $ConfirmPublish) {
    $answer = Read-Host 'Cong khai CloudBox 8000 va Nextcloud 8080 qua Quick Tunnel? Nhap Y'
    if ($answer -notmatch '^(y|yes)$') { exit 0 }
}
python "$PSScriptRoot\online.py" start
exit $LASTEXITCODE
