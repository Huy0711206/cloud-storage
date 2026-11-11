param([switch]$Rebuild,[switch]$RebuildMail,[switch]$NoBrowser)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $projectRoot
try {
    if(-not(Test-Path -LiteralPath '.env')){throw 'Chưa có .env. Xem README; không ghi đè cấu hình cũ.'}
    if($RebuildMail){throw 'Mailpit đã ngừng dùng. Hãy dùng -Rebuild để build riêng CloudBox.'}
    docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
    if($LASTEXITCODE -ne 0){throw 'Hãy mở Docker Desktop rồi chạy lại lệnh.'}
    $composeArgs=@('compose','-f','docker-compose.yml')
    if(Test-Path -LiteralPath 'docker-compose.named.yml'){$composeArgs+=@('-f','docker-compose.named.yml')}
    & docker @composeArgs config --quiet
    if($LASTEXITCODE -ne 0){throw 'Cấu hình Docker không hợp lệ.'}
    if($Rebuild){
        & docker @composeArgs build portal
        if($LASTEXITCODE -ne 0){throw 'Build chưa thành công.'}
    }
    docker volume create cloud-storage_cloudbox_data | Out-Null
    if($LASTEXITCODE -ne 0){throw 'Không mở được volume dữ liệu CloudBox.'}
    & docker @composeArgs up -d --wait --wait-timeout 180 db portal
    if($LASTEXITCODE -ne 0){throw 'CloudBox chưa sẵn sàng. Xem docker compose ps.'}
    if((Invoke-RestMethod 'http://127.0.0.1:8000/healthz' -TimeoutSec 10).status -ne 'ok'){throw 'CloudBox chưa sẵn sàng.'}
    Write-Host 'CloudBox: https://cloudbox.rachiba.top' -ForegroundColor Green
    Write-Host 'Giữ máy bật, Docker và Cloudflared hoạt động. Không tự khởi động cùng Windows.'
    if(-not $NoBrowser){Start-Process 'https://cloudbox.rachiba.top'}
} catch {Write-Host ('Không mở được CloudBox: '+$_.Exception.Message) -ForegroundColor Red;exit 1}
