#Requires -Version 7.0
[CmdletBinding()]
param(
    [switch]$PrepareOnly,
    [string]$Ec2Ip,
    [string]$KeyFile,
    [string]$KnownHostsFile,
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$')]
    [string]$HostKeyAlias,
    [string]$PythonExecutable = 'python',
    [ValidateSet('msedge','chrome','chromium')]
    [string]$BrowserChannel = 'msedge'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Executable exited with code $LASTEXITCODE."
    }
}

if (-not $PrepareOnly) {
    $address = $null
    if ($Ec2Ip -notmatch '^[0-9]{1,3}(\.[0-9]{1,3}){3}$' -or
        -not [Net.IPAddress]::TryParse($Ec2Ip,[ref]$address) -or $address.ToString() -ne $Ec2Ip) {
        throw 'Enter the current EC2 Public IPv4 with -Ec2Ip.'
    }
    foreach ($path in @($KeyFile, $KnownHostsFile)) {
        if (-not $path -or -not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw 'Provide -KeyFile and a verified -KnownHostsFile.'
        }
    }
    $sshOptions = @(
        '-o','StrictHostKeyChecking=yes','-o','BatchMode=yes',
        '-o','ConnectTimeout=12','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3',
        '-o','KexAlgorithms=curve25519-sha256',
        '-o',('UserKnownHostsFile="' + (Resolve-Path -LiteralPath $KnownHostsFile).Path + '"'),
        '-i',(Resolve-Path -LiteralPath $KeyFile).Path
    )
    if ($HostKeyAlias) { $sshOptions += @('-o',"HostKeyAlias=$HostKeyAlias") }
    $target = "ubuntu@$Ec2Ip"
}

$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$release = 'release-' + [DateTime]::UtcNow.ToString('yyyyMMddHHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8)
$image = "cloudbox-portal:$release"
$archive = Join-Path ([IO.Path]::GetTempPath()) "$release.tar"
$browserTest = Join-Path $repo 'scripts/development/check-browser.py'
$remoteScript = Join-Path $PSScriptRoot 'release-aws-portal.sh'

Push-Location -LiteralPath $repo
try {
    Invoke-Checked $PythonExecutable @('-c','import playwright')
    Invoke-Checked 'pwsh' @('-NoProfile','-File','./scripts/development/check.ps1','-PythonExecutable',$PythonExecutable)
    Invoke-Checked 'docker' @('build','--platform','linux/amd64','-t',$image,'./apps/portal')
    Invoke-Checked $PythonExecutable @('-X','utf8',$browserTest,'--image',$image,'--channel',$BrowserChannel)
    if ($PrepareOnly) {
        Write-Output "Verified local image $image. Use it for QA."
        return
    }

    Invoke-Checked 'ssh' ($sshOptions + @($target,'test -r /opt/cloudbox/compose.aws.yml && sudo -n docker info --format "{{.ServerVersion}}"'))
    $imageId = Invoke-Checked 'docker' @('image','inspect','--format','{{.Id}}',$image)
    $entry = Invoke-Checked 'docker' @('run','--rm','--network','none',$image,'python','-c','from app.shared.frontend import assets; print(assets().get("js"))')
    if ($imageId -notmatch '^sha256:[a-f0-9]{64}$' -or $entry -notmatch '^/static/ui/assets/main-[A-Za-z0-9_-]+\.js$') {
        throw 'The image ID or frontend entry did not match the expected format.'
    }

    Invoke-Checked 'docker' @('save','-o',$archive,$image)
    $checksum = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    Invoke-Checked 'scp' ($sshOptions + @($archive,"${target}:/home/ubuntu/$release.tar"))
    $remote = "tr -d '\r' | bash -s -- $release $checksum $imageId $entry"
    Get-Content -LiteralPath $remoteScript -Raw | ssh @sshOptions $target $remote
    if ($LASTEXITCODE -ne 0) { throw 'The EC2 update did not complete. Review the EC2 output.' }

    $base = 'https://cloudbox.rachiba.top'
    foreach ($path in @('/healthz','/readyz')) {
        $statusJson = (Invoke-Checked 'curl.exe' @('-fsS','--max-time','10','--retry','3',"$base$path")) -join ''
        if (($statusJson | ConvertFrom-Json).status -ne 'ok') { throw "CloudBox returned an unexpected state at $path." }
    }
    $html = (Invoke-Checked 'curl.exe' @('-fsS','--max-time','10','--retry','3',"$base/?release=$release")) -join ''
    if (-not $html.Contains($entry)) { throw 'CloudBox HTTPS has not served the expected frontend entry.' }
    Invoke-Checked 'curl.exe' @('-fsS','--max-time','10','--retry','3','-o','NUL',"$base$entry")
    Write-Output "Released $image to $base."
} finally {
    Pop-Location
    if (Test-Path -LiteralPath $archive -PathType Leaf) { Remove-Item -LiteralPath $archive }
}
