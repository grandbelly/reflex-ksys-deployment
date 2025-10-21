#!/bin/bash

# 개발 버전과 배포 버전 비교 유틸리티

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================="
echo "개발 버전 vs 배포 버전 비교"
echo "==========================================${NC}"
echo ""

# 함수: 컨테이너 정보 출력
check_container() {
    local container_name=$1
    local version=$2

    if docker ps --filter "name=^${container_name}$" --quiet | grep -q .; then
        echo -e "${GREEN}✅ ${version} 실행 중${NC}"

        local status=$(docker inspect ${container_name} --format='{{.State.Status}}')
        local health=$(docker inspect ${container_name} --format='{{.State.Health.Status}}' 2>/dev/null || echo "N/A")

        echo "   상태: ${status}"
        echo "   헬스: ${health}"

        # 리소스 사용량
        local stats=$(docker stats ${container_name} --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null)
        echo "   ${stats##*$'\n'}" # 마지막 줄만 출력
    else
        echo -e "${RED}❌ ${version} 실행 중 아님${NC}"
    fi
}

# 1. 개발 버전 상태
echo -e "${YELLOW}1️⃣  개발 버전 (Python 3.13)${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
check_container "reflex-ksys-app$" "Reflex App (Dev)"
echo ""
check_container "forecast-scheduler$" "Scheduler (Dev)"
echo ""
check_container "data-injector$" "Data Injector (Dev)"
echo ""

# 2. 배포 버전 상태
echo -e "${YELLOW}2️⃣  배포 버전 (Python 3.11)${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
check_container "reflex-ksys-app-prod$" "Reflex App (Prod)"
echo ""
check_container "forecast-scheduler-prod$" "Scheduler (Prod)"
echo ""

# 3. 포트 상태
echo -e "${YELLOW}3️⃣  포트 상태${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check_port() {
    local port=$1
    local version=$2

    if netstat -tln 2>/dev/null | grep -q ":${port} "; then
        echo -e "${GREEN}✅ 포트 ${port}${NC} 사용 중 (${version})"
    else
        echo -e "${RED}❌ 포트 ${port}${NC} 미사용"
    fi
}

check_port "13000" "Dev Frontend"
check_port "13001" "Dev Backend"
check_port "14000" "Prod Frontend"
check_port "14001" "Prod Backend"
echo ""

# 4. 이미지 정보
echo -e "${YELLOW}4️⃣  Docker 이미지${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "개발 버전 이미지:"
docker images --filter "reference=*reflex*" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep -E "reflex|REPOSITORY" || echo "찾을 수 없음"

echo ""
echo "배포 버전 이미지:"
docker images --filter "reference=*reflex-ksys-deployment*" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep -v "reflex-ksys-app$" || echo "찾을 수 없음"
echo ""

# 5. 웹 인터페이스 액세스 정보
echo -e "${YELLOW}5️⃣  웹 인터페이스 액세스${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "개발 버전 Frontend: ${BLUE}http://localhost:13000${NC}"
echo -e "개발 버전 Backend:  ${BLUE}http://localhost:13001${NC}"
echo ""
echo -e "배포 버전 Frontend: ${BLUE}http://localhost:14000${NC}"
echo -e "배포 버전 Backend:  ${BLUE}http://localhost:14001${NC}"
echo ""

# 6. 로그 확인 팁
echo -e "${YELLOW}6️⃣  로그 확인 명령어${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "개발 버전 로그:"
echo "  docker logs reflex-ksys-app -f --tail 50"
echo ""
echo "배포 버전 로그:"
echo "  docker logs reflex-ksys-app-prod -f --tail 50"
echo ""
echo "스케줄러 로그 비교:"
echo "  docker logs forecast-scheduler -f --tail 20"
echo "  docker logs forecast-scheduler-prod -f --tail 20"
echo ""

# 7. 요약
echo -e "${BLUE}=========================================="
echo "📊 요약"
echo "==========================================${NC}"

dev_running=$(docker ps --filter "name=reflex-ksys-app$" --quiet | wc -l)
prod_running=$(docker ps --filter "name=reflex-ksys-app-prod$" --quiet | wc -l)

if [ $dev_running -gt 0 ] && [ $prod_running -gt 0 ]; then
    echo -e "${GREEN}✅ 두 버전 모두 실행 중!${NC}"
    echo "   개발: http://localhost:13000"
    echo "   배포: http://localhost:14000"
elif [ $dev_running -gt 0 ]; then
    echo -e "${YELLOW}⚠️  개발 버전만 실행 중${NC}"
    echo "   배포 버전을 시작하려면: ./start-prod.sh"
elif [ $prod_running -gt 0 ]; then
    echo -e "${YELLOW}⚠️  배포 버전만 실행 중${NC}"
    echo "   개발 버전을 시작하려면: docker-compose up -d"
else
    echo -e "${RED}❌ 실행 중인 버전이 없습니다${NC}"
    echo "   개발: docker-compose up -d"
    echo "   배포: ./start-prod.sh"
fi

echo ""
