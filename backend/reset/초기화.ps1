# 세이프홈 데이터 초기화 스크립트

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "세이프홈 데이터 초기화" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# 현재 디렉토리 확인
$backendPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $backendPath

Write-Host "[1/3] Python 서버 종료 중..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Write-Host "✓ 서버 종료 완료" -ForegroundColor Green
Write-Host ""

Write-Host "[2/3] 데이터베이스 초기화 중..." -ForegroundColor Yellow
python reset_data.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ 초기화 실패!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

Write-Host "[3/3] 샘플 데이터 생성 중..." -ForegroundColor Yellow
python seed_data.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ 데이터 생성 실패!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

Write-Host "================================================" -ForegroundColor Green
Write-Host "✅ 초기화 완료!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "테스트 계정 정보:" -ForegroundColor White
Write-Host "  아이디: test" -ForegroundColor Cyan
Write-Host "  비밀번호: test123" -ForegroundColor Cyan
Write-Host ""
Write-Host "서버를 시작하려면:" -ForegroundColor White
Write-Host "  python app.py" -ForegroundColor Yellow
Write-Host ""

Read-Host "Press Enter to continue"
