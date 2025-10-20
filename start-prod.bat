@echo off
REM 배포 버전 (Python 3.11) 빌드 및 시작 스크립트
REM Windows CMD / PowerShell에서 사용 가능

setlocal enabledelayedexpansion

echo.
echo ==========================================
echo 배포 버전 (Python 3.11) 빌드 및 시작
echo ==========================================
echo.

REM 1. 기존 컨테이너 상태 확인
echo 1️⃣  기존 컨테이너 상태 확인
echo 개발 버전 (Python 3.13) - 포트 13000-13001
docker ps --filter "name=reflex-ksys-app$" --filter "name=forecast-scheduler$"
echo.

REM 2. 배포 버전 이미지 빌드
echo 2️⃣  배포 버전 이미지 빌드 (Python 3.11)
docker-compose -f docker-compose.prod.yml build

if errorlevel 1 (
    echo.
    echo ❌ 이미지 빌드 실패!
    pause
    exit /b 1
)

echo.
echo ✅ 이미지 빌드 완료
echo.

REM 3. 배포 버전 컨테이너 시작
echo 3️⃣  배포 버전 컨테이너 시작
docker-compose -f docker-compose.prod.yml up -d

if errorlevel 1 (
    echo.
    echo ❌ 컨테이너 시작 실패!
    pause
    exit /b 1
)

echo.
echo ✅ 컨테이너 시작 완료
echo.

REM 4. 상태 확인
echo 4️⃣  배포 버전 서비스 상태 확인
docker-compose -f docker-compose.prod.yml ps
echo.

REM 5. 웹 인터페이스 정보 표시
echo.
echo ==========================================
echo 📋 배포 버전 액세스 정보
echo ==========================================
echo Frontend: http://localhost:14000
echo Backend:  http://localhost:14001
echo Environment: production (Python 3.11)
echo Logs: ./logs/prod/
echo.

REM 6. 기존 개발 버전 정보
echo ==========================================
echo 📋 개발 버전 정보 (계속 실행 중)
echo ==========================================
echo Frontend: http://localhost:13000
echo Backend:  http://localhost:13001
echo Environment: development (Python 3.13)
echo Logs: ./logs/
echo.

REM 7. 다음 단계 안내
echo 📌 다음 단계
echo.
echo 1. 배포 버전 로그 확인:
echo    docker logs reflex-ksys-app-prod -f
echo.
echo 2. 배포 버전 헬스 상태 확인:
echo    docker inspect reflex-ksys-app-prod --format="{{.State.Health.Status}}"
echo.
echo 3. 두 버전 리소스 비교:
echo    docker stats reflex-ksys-app reflex-ksys-app-prod
echo.
echo 4. 배포 버전 종료 (필요시):
echo    docker-compose -f docker-compose.prod.yml down
echo.
echo.
echo ==========================================
echo ✨ 배포 버전 준비 완료!
echo ==========================================
echo.

pause
