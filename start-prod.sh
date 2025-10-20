#!/bin/bash

# 배포 버전 빌드 및 시작 스크립트
# Windows WSL2 또는 Linux에서 사용 가능

set -e

echo "=========================================="
echo "배포 버전 (Python 3.11) 빌드 및 시작"
echo "=========================================="
echo ""

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 기존 컨테이너 상태 확인
echo -e "${BLUE}1️⃣  기존 컨테이너 상태 확인${NC}"
echo "개발 버전 (Python 3.13) - 포트 13000-13001"
docker ps --filter "name=reflex-ksys-app$" --filter "name=forecast-scheduler$" || true
echo ""

# 2. 배포 버전 이미지 빌드
echo -e "${BLUE}2️⃣  배포 버전 이미지 빌드 (Python 3.11)${NC}"
docker-compose -f docker-compose.prod.yml build

echo -e "${GREEN}✅ 이미지 빌드 완료${NC}"
echo ""

# 3. 배포 버전 컨테이너 시작
echo -e "${BLUE}3️⃣  배포 버전 컨테이너 시작${NC}"
docker-compose -f docker-compose.prod.yml up -d

echo -e "${GREEN}✅ 컨테이너 시작 완료${NC}"
echo ""

# 4. 상태 확인
echo -e "${BLUE}4️⃣  배포 버전 서비스 상태 확인${NC}"
docker-compose -f docker-compose.prod.yml ps
echo ""

# 5. 웹 인터페이스 정보 표시
echo -e "${YELLOW}=========================================="
echo "📋 배포 버전 액세스 정보"
echo "=========================================="
echo -e "Frontend: ${GREEN}http://localhost:14000${NC}"
echo -e "Backend:  ${GREEN}http://localhost:14001${NC}"
echo -e "Environment: ${YELLOW}production (Python 3.11)${NC}"
echo -e "Logs:     ./logs/prod/"
echo ""

# 6. 기존 개발 버전 정보
echo -e "${YELLOW}=========================================="
echo "📋 개발 버전 정보 (계속 실행 중)"
echo "=========================================="
echo -e "Frontend: ${GREEN}http://localhost:13000${NC}"
echo -e "Backend:  ${GREEN}http://localhost:13001${NC}"
echo -e "Environment: ${YELLOW}development (Python 3.13)${NC}"
echo -e "Logs:     ./logs/"
echo ""

# 7. 다음 단계 안내
echo -e "${BLUE}📌 다음 단계${NC}"
echo "1. 배포 버전 로그 확인:"
echo "   docker logs reflex-ksys-app-prod -f"
echo ""
echo "2. 배포 버전 헬스 상태 확인:"
echo "   docker inspect reflex-ksys-app-prod | grep -A 5 Health"
echo ""
echo "3. 두 버전 비교:"
echo "   docker stats reflex-ksys-app reflex-ksys-app-prod"
echo ""
echo "4. 배포 버전 종료 (필요시):"
echo "   docker-compose -f docker-compose.prod.yml down"
echo ""
echo -e "${GREEN}=========================================="
echo "✨ 배포 버전 준비 완료!"
echo "=========================================="
