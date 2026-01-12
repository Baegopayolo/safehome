@echo off
chcp 65001 > nul
echo ================================================
echo 세이프홈 데이터 초기화
echo ================================================
echo.

echo [1/3] Python 서버 종료 중...
taskkill /F /IM python.exe 2>nul
timeout /t 1 /nobreak > nul
echo ✓ 서버 종료 완료
echo.

echo [2/3] 데이터베이스 초기화 중...
python reset_data.py
if %errorlevel% neq 0 (
    echo ✗ 초기화 실패!
    pause
    exit /b 1
)
echo.

echo [3/3] 샘플 데이터 생성 중...
python seed_data.py
if %errorlevel% neq 0 (
    echo ✗ 데이터 생성 실패!
    pause
    exit /b 1
)
echo.

echo ================================================
echo ✅ 초기화 완료!
echo ================================================
echo.
echo 테스트 계정 정보:
echo   아이디: test
echo   비밀번호: test123
echo.
echo 서버를 시작하려면:
echo   python app.py
echo.
pause
