#!/bin/bash

# Cloudflare Tunnel 연결 테스트 스크립트

echo "========================================="
echo "Cloudflare Tunnel 연결 테스트"
echo "========================================="
echo ""

# 1. Docker 컨테이너 상태 확인
echo "1. Docker 컨테이너 상태 확인..."
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "NAME|prod"
echo ""

# 2. 애플리케이션 로컬 테스트
echo "2. 애플리케이션 로컬 접속 테스트 (localhost:14000)..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:14000 | grep -q "200"; then
    echo "✅ 로컬 접속 성공 (HTTP 200)"
else
    echo "❌ 로컬 접속 실패"
fi
echo ""

# 3. 컨테이너 간 연결 테스트
echo "3. Docker 네트워크 내부 연결 테스트..."
docker run --rm --network reflex-ksys-deployment_reflex-network-prod \
    curlimages/curl:latest \
    curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" \
    http://reflex-app-prod:13000
echo ""

# 4. Cloudflare Tunnel 상태 확인
echo "4. Cloudflare Tunnel 로그 (최근 10줄)..."
docker logs cloudflared-tunnel-prod --tail 10
echo ""

# 5. Health Check 상태
echo "5. Health Check 상태..."
echo -n "reflex-app-prod: "
docker inspect reflex-ksys-app-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "No health check"
echo -n "cloudflared: "
docker inspect cloudflared-tunnel-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "No health check"
echo ""

# 6. 네트워크 확인
echo "6. Docker 네트워크 확인..."
docker network ls | grep reflex-network-prod
echo ""

echo "========================================="
echo "테스트 완료"
echo "========================================="
echo ""
echo "외부 접속 URL: https://ksys.idna.ai.kr"
echo ""
echo "Cloudflare Dashboard 설정 확인:"
echo "1. https://one.dash.cloudflare.com 접속"
echo "2. Networks → Tunnels 선택"
echo "3. Public Hostname 설정:"
echo "   - Service URL: reflex-app-prod:13000"
echo ""
