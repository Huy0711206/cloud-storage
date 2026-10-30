$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot

Write-Host 'This will expose the CloudBox portal and Nextcloud to the Internet through temporary Cloudflare URLs.' -ForegroundColor Yellow
$answer = Read-Host 'Continue? Type Y to continue'
if ($answer -notmatch '^(y|yes)$') { Write-Host 'No tunnel was started.'; exit 0 }

docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop is not ready. Open Docker Desktop, then run this script again.' }
docker compose up -d
if ($LASTEXITCODE -ne 0) { throw 'Could not start the project containers.' }

$portalTunnel = 'cloud-storage-portal-tunnel'
$nextcloudTunnel = 'cloud-storage-nextcloud-tunnel'
foreach ($name in @($portalTunnel, $nextcloudTunnel)) {
    docker inspect $name *> $null
    if ($LASTEXITCODE -eq 0) {
        docker rm -f $name *> $null
        if ($LASTEXITCODE -ne 0) { throw "Could not replace the old tunnel container: $name" }
    }
}

docker run -d --name $portalTunnel --restart=no cloudflare/cloudflared:latest tunnel --no-autoupdate --url http://host.docker.internal:8000 *> $null
if ($LASTEXITCODE -ne 0) { throw 'Could not start the portal tunnel.' }
docker run -d --name $nextcloudTunnel --restart=no cloudflare/cloudflared:latest tunnel --no-autoupdate --url http://host.docker.internal:8080 *> $null
if ($LASTEXITCODE -ne 0) { docker stop $portalTunnel *> $null; throw 'Could not start the Nextcloud tunnel.' }

function Get-QuickTunnelUrl([string]$containerName) {
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        $logText = (docker logs --tail 80 $containerName 2>&1) -join "`n"
        $match = [regex]::Match($logText, 'https://[a-z0-9-]+\.trycloudflare\.com')
        if ($match.Success) { return $match.Value }
        Start-Sleep -Seconds 2
    }
    throw "Cloudflare did not provide a URL for $containerName."
}

try {
    $portalUrl = Get-QuickTunnelUrl $portalTunnel
    $nextcloudUrl = Get-QuickTunnelUrl $nextcloudTunnel
    $nextcloudHost = ([uri]$nextcloudUrl).Host

    $envPath = Join-Path $projectRoot '.env'
    $content = [System.IO.File]::ReadAllText($envPath)
    function Set-EnvValue([string]$text, [string]$key, [string]$value) {
        $pattern = '(?m)^' + [regex]::Escape($key) + '=.*$'
        if ([regex]::IsMatch($text, $pattern)) {
            return [System.Text.RegularExpressions.Regex]::Replace($text, $pattern, "$key=$value", 1)
        }
        return $text.TrimEnd("`r", "`n") + "`r`n$key=$value`r`n"
    }
    $content = Set-EnvValue $content 'BASE_URL' $portalUrl
    $content = Set-EnvValue $content 'NEXTCLOUD_PUBLIC_URL' $nextcloudUrl
    $content = Set-EnvValue $content 'EXTRA_TRUSTED_DOMAINS' $nextcloudHost
    [System.IO.File]::WriteAllText($envPath, $content, [System.Text.UTF8Encoding]::new($false))

    docker compose exec -u www-data -T nextcloud php occ config:system:set trusted_domains 3 "--value=$nextcloudHost"
    if ($LASTEXITCODE -ne 0) { throw 'Could not add the Nextcloud trusted domain.' }
    docker compose exec -u www-data -T nextcloud php occ config:system:set overwritehost "--value=$nextcloudHost"
    if ($LASTEXITCODE -ne 0) { throw 'Could not set the Nextcloud public host.' }
    docker compose exec -u www-data -T nextcloud php occ config:system:set overwriteprotocol --value=https
    if ($LASTEXITCODE -ne 0) { throw 'Could not set the Nextcloud public protocol.' }
    docker compose exec -u www-data -T nextcloud php occ config:system:set overwrite.cli.url "--value=$nextcloudUrl"
    if ($LASTEXITCODE -ne 0) { throw 'Could not set the Nextcloud CLI URL.' }
    docker compose up -d --force-recreate portal
    if ($LASTEXITCODE -ne 0) { throw 'Could not restart the portal with the public URL.' }

    Write-Host ''
    Write-Host "Portal:    $portalUrl"
    Write-Host "Nextcloud: $nextcloudUrl"
    Write-Host 'Tunnel is active until you stop the tunnel containers or Docker Desktop.' -ForegroundColor Green
} catch {
    docker stop $portalTunnel $nextcloudTunnel *> $null
    throw
}