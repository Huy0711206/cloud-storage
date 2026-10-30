param(
    [switch]$Rebuild,
    [switch]$RebuildPreview,
    [switch]$RebuildMail,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
Set-Location -LiteralPath $projectRoot

function Test-DockerReady {
    try {
        & $script:dockerPath info --format '{{.ServerVersion}}' 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

try {
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot '.env'))) {
        throw 'Chưa có .env. Xem phần cài lần đầu trong README.md. Không ghi đè .env đang có.'
    }
    $dockerCommand = Get-Command docker.exe -ErrorAction SilentlyContinue
    $script:dockerPath = if ($dockerCommand) { $dockerCommand.Source } else { Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin\docker.exe' }
    if (-not (Test-Path -LiteralPath $script:dockerPath)) {
        throw 'Chưa tìm thấy Docker Desktop. Hãy cài Docker Desktop trước.'
    }

    Write-Host '[1/3] Kiểm tra Docker Desktop...' -ForegroundColor Cyan
    if (-not (Test-DockerReady)) {
        $desktopPath = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
        if (-not (Test-Path -LiteralPath $desktopPath)) { throw 'Không tìm thấy Docker Desktop. Hãy mở Docker bằng tay rồi chạy lại.' }
        $desktop = Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue
        if (-not $desktop) { Start-Process -FilePath $desktopPath -WindowStyle Hidden }
        $deadline = (Get-Date).AddSeconds(180)
        $attempt = 0
        while (-not (Test-DockerReady)) {
            if ((Get-Date) -ge $deadline) { throw 'Docker chưa sẵn sàng sau 3 phút. Mở Docker Desktop để xem thông báo WSL, rồi chạy lại.' }
            if ($attempt % 5 -eq 0) { Write-Host 'Đang đợi Docker khởi động...' }
            Start-Sleep -Seconds 2
            $attempt++
        }
    }

    & $dockerPath compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Cấu hình Docker hoặc .env không hợp lệ. Xem thông báo bên trên.' }
    if ($Rebuild) {
        Write-Host 'Đang xây dựng lại giao diện và backend...' -ForegroundColor Cyan
        & $dockerPath compose build portal
        if ($LASTEXITCODE -ne 0) { throw 'Build portal thất bại. Xem thông báo bên trên.' }
    }

    if ($RebuildPreview) {
        Write-Host 'Đang xây dựng lại giao diện thử nghiệm ở cổng 8001...' -ForegroundColor Cyan
        & $dockerPath compose build portal-preview
        if ($LASTEXITCODE -ne 0) { throw 'Build portal-preview thất bại. Xem thông báo bên trên.' }
    }

    if ($RebuildMail) {
        Write-Host 'Đang xây dựng lại hộp thư CloudBox Mail ở cổng 8026...' -ForegroundColor Cyan
        & $dockerPath compose build mail-preview
        if ($LASTEXITCODE -ne 0) { throw 'Build mail-preview thất bại. Xem thông báo bên trên.' }
    }

    Write-Host '[2/3] Khởi động và đợi các dịch vụ sẵn sàng...' -ForegroundColor Cyan
    & $dockerPath compose up -d --wait --wait-timeout 180
    if ($LASTEXITCODE -ne 0) {
        & $dockerPath compose ps
        throw 'Dịch vụ chưa sẵn sàng. Chạy docker compose logs --tail 60 portal portal-preview mail-preview mailpit nextcloud db để xem lỗi. Nếu báo cổng đã được sử dụng, xem mục xử lý cổng trong README.'
    }

    Write-Host '[3/3] Kiểm tra CloudBox và Nextcloud...' -ForegroundColor Cyan
    foreach ($port in @(8000, 8001, 8026)) {
        $uri = "http://localhost:$port/healthz"
        $result = Invoke-RestMethod -Uri $uri -TimeoutSec 10
        if ($result.status -ne 'ok') { throw "Ứng dụng chưa phản hồi đúng ở cổng $port." }
        Write-Host "OK: http://localhost:$port" -ForegroundColor Green
    }
    $mailpitResult = Invoke-RestMethod -Uri 'http://localhost:8025/api/v1/messages?limit=1' -TimeoutSec 10
    if (-not ($mailpitResult.PSObject.Properties.Name -contains 'total')) { throw 'Mailpit chưa phản hồi đúng ở cổng 8025.' }
    Write-Host 'OK: http://localhost:8025 (Mailpit gốc)' -ForegroundColor Green
    $nextcloudPage = Invoke-WebRequest -Uri 'http://localhost:8080/' -UseBasicParsing -TimeoutSec 20
    $nextcloudUri = $nextcloudPage.BaseResponse.ResponseUri
    # Windows PowerShell uses ResponseUri; PowerShell 7 uses RequestMessage.RequestUri.
    if (-not $nextcloudUri -and $nextcloudPage.BaseResponse.RequestMessage) {
        $nextcloudUri = $nextcloudPage.BaseResponse.RequestMessage.RequestUri
    }
    if ($nextcloudPage.StatusCode -ne 200 -or $nextcloudUri.Host -ne 'localhost' -or $nextcloudUri.Port -ne 8080) {
        throw 'Nextcloud chuyển hướng sai địa chỉ. Xem overwritehost trong README; địa chỉ cục bộ cần là localhost:8080.'
    }
    Write-Host 'OK: http://localhost:8080 (Nextcloud)' -ForegroundColor Green
    Write-Host 'Cổng chính (giao diện ổn định): http://localhost:8000'
    Write-Host 'Giao diện thử nghiệm: http://localhost:8001 (dùng chung backend và dữ liệu)'
    Write-Host 'Hộp thư thử nghiệm: http://localhost:8026 (dùng chung hộp thư Mailpit 8025)'
    Write-Host 'Cần giữ Docker Desktop chạy trong lúc sử dụng CloudBox.'
    if (-not $NoBrowser) { Start-Process 'http://localhost:8000/' }
    exit 0
} catch {
    Write-Host ("Không mở được CloudBox: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
