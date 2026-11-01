param([switch]$Rebuild,[switch]$RebuildMail,[switch]$NoBrowser)
$ErrorActionPreference='Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $projectRoot
try {
    if(-not(Test-Path -LiteralPath '.env')){throw 'Chưa có .env. Xem README, không ghi đè cấu hình đang dùng.'}
    $dockerPath=(Get-Command docker.exe -ErrorAction SilentlyContinue).Source
    if(-not $dockerPath){$dockerPath=Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin\docker.exe'}
    if(-not(Test-Path -LiteralPath $dockerPath)){throw 'Chưa tìm thấy Docker Desktop.'}
    & $dockerPath info --format '{{.ServerVersion}}' 2>$null | Out-Null
    if($LASTEXITCODE -ne 0){
        $desktopPath=Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
        if(-not(Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue)){Start-Process -FilePath $desktopPath -WindowStyle Hidden}
        $deadline=(Get-Date).AddSeconds(180)
        do {
            Start-Sleep -Seconds 2
            & $dockerPath info --format '{{.ServerVersion}}' 2>$null | Out-Null
            if((Get-Date) -gt $deadline){throw 'Docker chưa sẵn sàng sau 3 phút. Mở Docker Desktop để kiểm tra.'}
        } while($LASTEXITCODE -ne 0)
    }
    $composeArgs=@('compose')
    if(Test-Path -LiteralPath '.online/compose.json'){
        foreach($tunnelName in @('cloud-storage-portal-tunnel','cloud-storage-nextcloud-tunnel')){
            $running=& $dockerPath inspect --format '{{.State.Running}}' $tunnelName 2>$null
            if($LASTEXITCODE -ne 0 -or $running -ne 'true'){throw 'Có cấu hình online nhưng tunnel đã dừng. Chạy start-online.ps1 để bật lại hoặc stop-online.ps1 để về local trước.'}
        }
        $composeArgs+=@('-f','docker-compose.yml','-f','.online/compose.json')
        Write-Host 'Giữ địa chỉ online và cấu hình phiên HTTPS đang hoạt động.' -ForegroundColor Cyan
    }
    & $dockerPath @composeArgs config --quiet
    if($LASTEXITCODE -ne 0){throw 'Cấu hình Docker không hợp lệ.'}
    if($Rebuild -or $RebuildMail){
        python scripts/sync-design.py
        if($LASTEXITCODE -ne 0){throw 'Chưa tạo được bộ nhận diện chung.'}
        $targets=if($Rebuild){@('portal','mailpit')}else{@('mailpit')}
        & $dockerPath @composeArgs build @targets
        if($LASTEXITCODE -ne 0){throw 'Build chưa thành công; xem thông báo phía trên.'}
    }
    & $dockerPath volume create cloud-storage_mailpit_data | Out-Null
    if($LASTEXITCODE -ne 0){throw 'Chưa tạo/mở được volume hộp thư.'}
    Write-Host 'Khởi động ba giao diện chính...' -ForegroundColor Cyan
    & $dockerPath @composeArgs up -d --wait --wait-timeout 180
    if($LASTEXITCODE -ne 0){throw 'Dịch vụ chưa sẵn sàng. Xem docker compose ps và logs --tail 60.'}
    if((Invoke-RestMethod 'http://localhost:8000/healthz' -TimeoutSec 10).status -ne 'ok'){throw 'CloudBox chưa sẵn sàng.'}
    $mail=Invoke-RestMethod 'http://localhost:8025/api/v1/messages?limit=1' -TimeoutSec 10
    if(-not($mail.PSObject.Properties.Name -contains 'total')){throw 'Mail chưa phản hồi đúng.'}
    $nc=Invoke-RestMethod 'http://localhost:8080/status.php' -TimeoutSec 20
    if(-not $nc.installed -or $nc.maintenance){throw 'Nextcloud chưa sẵn sàng.'}
    Write-Host 'CloudBox:       http://localhost:8000' -ForegroundColor Green
    Write-Host 'Nextcloud Files:http://localhost:8080' -ForegroundColor Green
    Write-Host 'CloudBox Mail:  http://localhost:8025 (chỉ local)' -ForegroundColor Green
    Write-Host 'Giữ Docker Desktop chạy. Nếu đang online, dùng URL HTTPS để đăng nhập CloudBox.'
    if(-not $NoBrowser){Start-Process 'http://localhost:8000/'}
} catch {Write-Host ('Không mở được CloudBox: '+$_.Exception.Message) -ForegroundColor Red;exit 1}
