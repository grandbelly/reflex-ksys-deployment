@echo off
REM 배포 버전 관리 유틸리티 (Windows)

setlocal enabledelayedexpansion

:menu
cls
echo.
echo ==========================================
echo 배포 버전 관리 유틸리티
echo ==========================================
echo.
echo 1. 배포 버전 빌드 및 시작
echo 2. 배포 버전 로그 보기
echo 3. 배포 버전 상태 확인
echo 4. 배포 버전 재시작
echo 5. 배포 버전 종료
echo 6. 버전 비교
echo 7. 리소스 사용량 모니터링
echo 8. 데이터베이스 연결 테스트
echo 9. 배포 버전 ^-> 프로덕션 전환
echo 0. 종료
echo.
set /p choice="선택 (0-9): "

if "%choice%"=="1" goto build_start
if "%choice%"=="2" goto show_logs
if "%choice%"=="3" goto check_status
if "%choice%"=="4" goto restart_prod
if "%choice%"=="5" goto stop_prod
if "%choice%"=="6" goto compare_versions
if "%choice%"=="7" goto monitor_resources
if "%choice%"=="8" goto test_db
if "%choice%"=="9" goto switch_prod
if "%choice%"=="0" goto :eof

echo 잘못된 선택입니다
timeout /t 2
goto menu

:build_start
echo.
echo 배포 버전 빌드 중...
docker-compose -f docker-compose.prod.yml build
if errorlevel 1 goto build_error

echo.
echo 배포 버전 시작 중...
docker-compose -f docker-compose.prod.yml up -d
if errorlevel 1 goto start_error

echo.
echo ✅ 배포 버전 시작 완료
echo    Frontend: http://localhost:14000
echo    Backend:  http://localhost:14001
echo.
pause
goto menu

:build_error
echo.
echo ❌ 빌드 실패
pause
goto menu

:start_error
echo.
echo ❌ 시작 실패
pause
goto menu

:show_logs
cls
echo.
echo 로그 선택:
echo 1. Reflex App
echo 2. Scheduler
echo 3. 전체
echo.
set /p log_choice="선택 (1-3): "

if "%log_choice%"=="1" (
    docker logs reflex-ksys-app-prod -f --tail 100
) else if "%log_choice%"=="2" (
    docker logs forecast-scheduler-prod -f --tail 100
) else if "%log_choice%"=="3" (
    docker-compose -f docker-compose.prod.yml logs -f --tail 50
) else (
    echo 잘못된 선택
    timeout /t 2
)
goto menu

:check_status
cls
echo.
echo 배포 버전 상태:
docker-compose -f docker-compose.prod.yml ps
echo.
echo 헬스 상태:
docker inspect reflex-ksys-app-prod --format="{{.State.Health.Status}}"
echo.
pause
goto menu

:restart_prod
echo.
echo 배포 버전 재시작 중...
docker-compose -f docker-compose.prod.yml restart
echo ✅ 재시작 완료
echo.
pause
goto menu

:stop_prod
echo.
set /p confirm="배포 버전을 종료하시겠습니까? (y/n): "
if /i "%confirm%"=="y" (
    echo 배포 버전 종료 중...
    docker-compose -f docker-compose.prod.yml down
    echo ✅ 종료 완료
) else (
    echo 취소됨
)
echo.
pause
goto menu

:compare_versions
cls
echo.
echo 개발 버전 (Python 3.13) - 포트 13000-13001
docker ps --filter "name=reflex-ksys-app$" --filter "name=forecast-scheduler$"
echo.
echo 배포 버전 (Python 3.11) - 포트 14000-14001
docker ps --filter "name=reflex-ksys-app-prod$" --filter "name=forecast-scheduler-prod$"
echo.
echo Frontend 액세스:
echo   개발: http://localhost:13000
echo   배포: http://localhost:14000
echo.
pause
goto menu

:monitor_resources
cls
echo.
echo 리소스 사용량 모니터링 (Ctrl+C로 종료)
echo.
docker stats reflex-ksys-app reflex-ksys-app-prod forecast-scheduler forecast-scheduler-prod
pause
goto menu

:test_db
echo.
echo 배포 버전 데이터베이스 연결 테스트...
echo.
docker exec reflex-ksys-app-prod python -c "import asyncio; from ksys_app.db import get_pool; asyncio.run(get_pool())" 2>nul
if errorlevel 1 (
    echo ❌ 연결 테스트 실패
) else (
    echo ✅ 데이터베이스 연결 성공
)
echo.
pause
goto menu

:switch_prod
cls
echo.
echo 주의: 이 작업은 개발 버전을 종료하고 배포 버전으로 전환합니다
echo.
echo 단계별 진행:
echo 1. 개발 버전 백업
echo 2. 개발 버전 종료
echo 3. 배포 버전을 메인 설정으로 변경
echo 4. 배포 버전 시작
echo.
set /p confirm="계속하시겠습니까? (y/n): "

if /i not "%confirm%"=="y" (
    echo 취소됨
    pause
    goto menu
)

echo.
echo 백업 생성 중...
for /f "tokens=2-4 delimiters=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delimiters=/:" %%a in ('time /t') do (set mytime=%%a%%b)
copy docker-compose.yml "docker-compose.yml.backup-%mydate%-%mytime%"

echo 개발 버전 종료 중...
docker-compose down

echo 배포 버전을 메인으로 설정 중...
copy Dockerfile Dockerfile.dev
copy Dockerfile.prod Dockerfile
copy docker-compose.prod.yml docker-compose.yml

echo 배포 버전 시작 중...
docker-compose up -d

echo.
echo ✅ 프로덕션 전환 완료!
echo    Frontend: http://localhost:13000
echo    Backend:  http://localhost:13001
echo.
echo 이전 설정으로 복구하려면:
echo   docker-compose down
echo   copy docker-compose.yml.backup-* docker-compose.yml
echo   docker-compose up -d
echo.
pause
goto menu
