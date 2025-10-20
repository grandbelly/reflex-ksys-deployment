#!/bin/bash

# 배포 버전 관리 유틸리티 스크립트

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_menu() {
    echo ""
    echo -e "${BLUE}=========================================="
    echo "배포 버전 관리 유틸리티"
    echo "==========================================${NC}"
    echo ""
    echo "1. 배포 버전 빌드 및 시작"
    echo "2. 배포 버전 로그 보기"
    echo "3. 배포 버전 상태 확인"
    echo "4. 배포 버전 재시작"
    echo "5. 배포 버전 종료"
    echo "6. 버전 비교"
    echo "7. 리소스 사용량 모니터링"
    echo "8. 데이터베이스 연결 테스트"
    echo "9. 배포 버전 → 프로덕션 전환"
    echo "0. 종료"
    echo ""
    echo -e "${YELLOW}선택 (0-9):${NC}"
}

# 1. 배포 버전 빌드 및 시작
build_and_start() {
    echo -e "${BLUE}배포 버전 빌드 중...${NC}"
    docker-compose -f docker-compose.prod.yml build

    echo -e "${BLUE}배포 버전 시작 중...${NC}"
    docker-compose -f docker-compose.prod.yml up -d

    echo -e "${GREEN}✅ 배포 버전 시작 완료${NC}"
    echo "   Frontend: http://localhost:14000"
    echo "   Backend:  http://localhost:14001"
}

# 2. 배포 버전 로그 보기
show_logs() {
    echo -e "${BLUE}로그 선택:${NC}"
    echo "1. Reflex App"
    echo "2. Scheduler"
    echo "3. 전체"
    echo ""
    read -p "선택 (1-3): " log_choice

    case $log_choice in
        1) docker logs reflex-ksys-app-prod -f --tail 100 ;;
        2) docker logs forecast-scheduler-prod -f --tail 100 ;;
        3) docker-compose -f docker-compose.prod.yml logs -f --tail 50 ;;
        *) echo "잘못된 선택" ;;
    esac
}

# 3. 배포 버전 상태 확인
check_status() {
    echo ""
    echo -e "${BLUE}배포 버전 상태:${NC}"
    docker-compose -f docker-compose.prod.yml ps

    echo ""
    echo -e "${BLUE}헬스 상태:${NC}"
    docker inspect reflex-ksys-app-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "헬스 정보 없음"

    echo ""
    echo -e "${BLUE}데이터베이스 연결 상태:${NC}"
    docker exec reflex-ksys-app-prod python -c "
import asyncio
from ksys_app.db import get_pool
async def test():
    try:
        pool = await get_pool()
        print(f'✅ 연결 성공: {pool.min_size}-{pool.max_size}')
    except Exception as e:
        print(f'❌ 연결 실패: {e}')
asyncio.run(test())
" 2>/dev/null || echo "연결 테스트 실패"
}

# 4. 배포 버전 재시작
restart_prod() {
    echo -e "${BLUE}배포 버전 재시작 중...${NC}"
    docker-compose -f docker-compose.prod.yml restart
    echo -e "${GREEN}✅ 재시작 완료${NC}"
}

# 5. 배포 버전 종료
stop_prod() {
    echo -e "${YELLOW}배포 버전을 종료하시겠습니까? (y/n):${NC}"
    read -p "> " confirm

    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        echo -e "${BLUE}배포 버전 종료 중...${NC}"
        docker-compose -f docker-compose.prod.yml down
        echo -e "${GREEN}✅ 종료 완료${NC}"
    else
        echo "취소됨"
    fi
}

# 6. 버전 비교
compare_versions() {
    if [ -f compare-versions.sh ]; then
        bash compare-versions.sh
    else
        echo -e "${RED}compare-versions.sh 파일을 찾을 수 없습니다${NC}"
    fi
}

# 7. 리소스 사용량 모니터링
monitor_resources() {
    echo -e "${BLUE}리소스 사용량 모니터링${NC}"
    echo "Ctrl+C로 종료"
    echo ""

    docker stats \
        reflex-ksys-app \
        reflex-ksys-app-prod \
        forecast-scheduler \
        forecast-scheduler-prod \
        --no-stream
}

# 8. 데이터베이스 연결 테스트
test_db_connection() {
    echo -e "${BLUE}배포 버전 데이터베이스 연결 테스트${NC}"

    docker exec reflex-ksys-app-prod python -c "
import asyncio
from ksys_app.db import get_pool
async def test():
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval('SELECT 1')
            print(f'✅ 데이터베이스 연결 성공!')
            print(f'   풀 크기: {pool.min_size}-{pool.max_size}')
            print(f'   테스트 쿼리: SELECT 1 = {result}')
    except Exception as e:
        print(f'❌ 연결 실패: {e}')
asyncio.run(test())
" 2>/dev/null || echo "테스트 중 오류 발생"
}

# 9. 배포 버전 → 프로덕션 전환
switch_to_prod() {
    echo -e "${YELLOW}주의: 이 작업은 개발 버전을 종료하고 배포 버전을 메인으로 전환합니다${NC}"
    echo ""
    echo "단계별 진행:"
    echo "1. 개발 버전 백업"
    echo "2. 개발 버전 종료"
    echo "3. 배포 버전을 메인 설정으로 변경"
    echo ""
    read -p "계속하시겠습니까? (y/n): " confirm

    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "취소됨"
        return
    fi

    echo -e "${BLUE}백업 생성 중...${NC}"
    cp docker-compose.yml docker-compose.yml.backup-$(date +%Y%m%d-%H%M%S)
    cp Dockerfile Dockerfile.dev

    echo -e "${BLUE}개발 버전 종료...${NC}"
    docker-compose down

    echo -e "${BLUE}배포 버전을 메인으로 설정...${NC}"
    cp docker-compose.prod.yml docker-compose.yml
    cp Dockerfile.prod Dockerfile

    echo -e "${BLUE}배포 버전 시작...${NC}"
    docker-compose up -d

    echo -e "${GREEN}✅ 프로덕션 전환 완료!${NC}"
    echo "   Frontend: http://localhost:13000"
    echo "   Backend:  http://localhost:13001"
    echo ""
    echo "🔄 이전 설정으로 복구하려면:"
    echo "   docker-compose down"
    echo "   cp docker-compose.yml.backup-* docker-compose.yml"
    echo "   docker-compose up -d"
}

# 메인 루프
while true; do
    show_menu
    read -p "> " choice

    case $choice in
        1) build_and_start ;;
        2) show_logs ;;
        3) check_status ;;
        4) restart_prod ;;
        5) stop_prod ;;
        6) compare_versions ;;
        7) monitor_resources ;;
        8) test_db_connection ;;
        9) switch_to_prod ;;
        0)
            echo -e "${BLUE}종료 중...${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}잘못된 선택${NC}"
            ;;
    esac
done
