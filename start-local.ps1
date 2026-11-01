param([switch]$Rebuild,[switch]$RebuildMail,[switch]$NoBrowser)
& (Join-Path $PSScriptRoot 'scripts/development/start-local.ps1') @PSBoundParameters
exit $LASTEXITCODE
