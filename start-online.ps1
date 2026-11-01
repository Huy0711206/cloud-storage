param([switch]$ConfirmPublish)
& (Join-Path $PSScriptRoot 'scripts/operations/start-online.ps1') @PSBoundParameters
exit $LASTEXITCODE
