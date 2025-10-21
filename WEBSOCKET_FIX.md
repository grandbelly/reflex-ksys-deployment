# WebSocket 연결 오류 해결 가이드

## 문제 증상

```
Cannot connect to server: timeout
Check if server is reachable at wss://ksys.idna.ai.kr/_event
```

화면은 로드되지만 **실시간 데이터가 업데이트되지 않고** WebSocket 연결 오류가 발생합니다.

## 원인

Reflex는 **두 가지 연결**이 필요합니다:
1. **HTTP(S)**: 페이지 로드 (현재 작동 중 ✅)
2. **WebSocket(WSS)**: 실시간 데이터 업데이트 (현재 실패 ❌)

Cloudflare Tunnel 설정에서 **WebSocket 지원이 활성화되지 않았거나**, 백엔드 포트(13001)가 라우팅되지 않고 있습니다.

## 해결 방법

### 방법 1: Cloudflare Dashboard 설정 수정 (권장)

#### 1단계: Public Hostname 확인/수정

Cloudflare Dashboard (https://one.dash.cloudflare.com):

**현재 설정:**
```
Subdomain: ksys
Domain: idna.ai.kr
Service: reflex-app-prod:13000
```

**이것만으로는 부족합니다!** Reflex는 **백엔드 포트(13001)**도 필요합니다.

#### 2단계: 백엔드 WebSocket 라우팅 추가

Cloudflare Dashboard에서 **두 번째 Public Hostname 추가**:

```
방법 A: Path 기반 라우팅 (권장)
────────────────────────────────
1번 규칙:
  Subdomain: ksys
  Domain: idna.ai.kr
  Path: /_event*
  Service: http://reflex-app-prod:13001

2번 규칙:
  Subdomain: ksys
  Domain: idna.ai.kr
  Path: (비우기)
  Service: http://reflex-app-prod:13000
```

**중요:** Path 순서가 중요합니다!
- `/_event*` 규칙이 **먼저** 와야 합니다
- 기본 규칙은 **나중**에 배치

#### 3단계: WebSocket 활성화

각 Public Hostname의 **Advanced settings**:

```yaml
✅ Enable WebSocket: ON (체크)
✅ Connect timeout: 90s
✅ No TLS Verify: OFF
```

### 방법 2: Config File 사용 (더 정확한 제어)

#### 1단계: Config 파일 생성

`cloudflared-config.yml` 파일 생성:

```yaml
tunnel: 7071a55a-1039-46e1-bb65-abcfcee01991
credentials-file: /etc/cloudflared/credentials.json

# Ingress 규칙 (순서 중요!)
ingress:
  # WebSocket endpoint (/_event)
  - hostname: ksys.idna.ai.kr
    path: /_event*
    service: http://reflex-app-prod:13001
    originRequest:
      noTLSVerify: false
      connectTimeout: 90s

  # Main application
  - hostname: ksys.idna.ai.kr
    service: http://reflex-app-prod:13000
    originRequest:
      noTLSVerify: false
      connectTimeout: 90s

  # Catch-all (필수)
  - service: http_status:404
```

#### 2단계: Credentials 파일 가져오기

Cloudflare Dashboard에서:
1. Tunnels → 터널 선택
2. Configure → Download credentials.json

또는 기존 토큰 사용.

#### 3단계: docker-compose.prod.yml 수정

```yaml
cloudflared:
  image: cloudflare/cloudflared:latest
  container_name: cloudflared-tunnel-prod
  command: tunnel --config /etc/cloudflared/config.yml run
  volumes:
    - ./cloudflared-config.yml:/etc/cloudflared/config.yml:ro
  networks:
    - reflex-network-prod
  restart: unless-stopped
  depends_on:
    - reflex-app-prod
  environment:
    - TZ=Asia/Seoul
```

#### 4단계: 재시작

```bash
./manage.sh restart

# 또는
docker-compose -f docker-compose.prod.yml restart
```

### 방법 3: 단일 포트 사용 (간단한 방법)

Reflex 설정을 변경하여 단일 포트만 사용:

#### rxconfig.py 수정

```python
config = rx.Config(
    app_name="ksys_app",
    backend_port=13000,  # 백엔드도 13000 사용
    frontend_port=13000,  # 프론트엔드도 13000 사용
    backend_host="0.0.0.0",
    # ... 기타 설정
)
```

이 방법은 **단일 포트**로 HTTP와 WebSocket을 모두 처리합니다.

그러나 **권장하지 않습니다** - 기존 구조가 더 견고합니다.

## 빠른 해결 (추천)

Cloudflare Dashboard에서 **가장 간단한 설정**:

### Option A: 백엔드 포트를 별도 서브도메인으로

```
1번 Public Hostname:
  Subdomain: ksys
  Domain: idna.ai.kr
  Service: http://reflex-app-prod:13000

2번 Public Hostname:
  Subdomain: ksys-api  (또는 ksys-ws)
  Domain: idna.ai.kr
  Service: http://reflex-app-prod:13001
  ✅ Enable WebSocket: ON
```

그런 다음 **환경변수 설정**:

```yaml
# docker-compose.prod.yml
environment:
  - REFLEX_BACKEND_URL=https://ksys-api.idna.ai.kr
```

### Option B: 모든 트래픽을 13000으로 (가장 간단)

Reflex는 기본적으로 **13000 포트에서 WebSocket도 처리**할 수 있습니다.

Cloudflare Dashboard:
```
Subdomain: ksys
Domain: idna.ai.kr
Service: http://reflex-app-prod:13000
✅ Enable WebSocket: ON (중요!)
```

**이것만 해도 작동합니다!**

## 테스트

### 1. 로컬 WebSocket 테스트

```bash
# wscat 설치 (없으면)
npm install -g wscat

# WebSocket 연결 테스트
wscat -c ws://localhost:14001/_event
# 또는
wscat -c ws://localhost:14000/_event
```

### 2. 외부 WebSocket 테스트

브라우저 개발자 도구 → Console:

```javascript
// WebSocket 연결 테스트
const ws = new WebSocket('wss://ksys.idna.ai.kr/_event');
ws.onopen = () => console.log('✅ Connected!');
ws.onerror = (e) => console.error('❌ Error:', e);
ws.onclose = () => console.log('Closed');
```

성공 시: `✅ Connected!` 출력

### 3. Cloudflare 설정 확인

```bash
# Tunnel 로그 확인
docker logs cloudflared-tunnel-prod | grep -i websocket

# 또는 전체 로그
docker logs cloudflared-tunnel-prod --tail 50
```

## 최종 권장 설정

가장 안정적인 구성:

### Cloudflare Dashboard 설정

```
Public Hostname 1:
──────────────────
Hostname: ksys.idna.ai.kr
Path: /_event*
Service: http://reflex-app-prod:13001
✅ WebSocket: ON
Timeout: 90s

Public Hostname 2:
──────────────────
Hostname: ksys.idna.ai.kr
Path: (empty)
Service: http://reflex-app-prod:13000
✅ WebSocket: ON
Timeout: 90s
```

**핵심:**
- 두 규칙 모두 **WebSocket ON**
- `/_event*` 규칙이 **먼저**
- 백엔드(13001)와 프론트엔드(13000) **분리**

## 확인 체크리스트

설정 후 확인:

- [ ] Cloudflare Dashboard → WebSocket 활성화
- [ ] Public Hostname에 `/_event*` 규칙 추가
- [ ] 백엔드 포트(13001) 라우팅 설정
- [ ] Tunnel 재시작 완료
- [ ] 브라우저에서 https://ksys.idna.ai.kr 접속
- [ ] 개발자 도구에서 WebSocket 연결 확인
- [ ] 실시간 데이터 업데이트 확인
- [ ] 에러 메시지 사라짐 확인

## 트러블슈팅

### 여전히 연결 안되는 경우

#### 1. 백엔드 포트 확인

```bash
# 백엔드가 13001에서 실행 중인지 확인
docker exec reflex-ksys-app-prod netstat -tlnp | grep 13001

# 또는
curl http://localhost:14001/ping
```

#### 2. Reflex 설정 확인

```bash
# rxconfig.py 확인
cat rxconfig.py | grep -A5 "rx.Config"
```

출력 예시:
```python
config = rx.Config(
    app_name="ksys_app",
    backend_port=13001,  # ← 이것 확인
    frontend_port=13000,
```

#### 3. 컨테이너 재시작

```bash
# 전체 재시작
./manage.sh restart

# 로그 확인
docker logs reflex-ksys-app-prod -f
```

#### 4. Cloudflare 캐시 클리어

Cloudflare Dashboard:
1. Caching → Configuration
2. Purge Everything

또는 브라우저 캐시 클리어: `Ctrl+Shift+R`

## 상태별 해결 방법

### 상황 1: 페이지는 로드되지만 데이터가 안 나옴
→ **WebSocket 연결 실패**
→ Cloudflare에서 WebSocket 활성화

### 상황 2: "Cannot connect to server: timeout"
→ **백엔드 포트 미연결**
→ `/_event*` → `13001` 라우팅 추가

### 상황 3: 간헐적으로 끊김
→ **Timeout 부족**
→ Connect timeout을 60s → 90s로 증가

### 상황 4: CORS 에러
→ **Origin 불일치**
→ rxconfig.py에서 `cors_allowed_origins` 설정

## 예상 결과

### 성공 시:
```
✅ 페이지 로드: https://ksys.idna.ai.kr
✅ WebSocket 연결: wss://ksys.idna.ai.kr/_event
✅ 실시간 데이터 업데이트
✅ 에러 메시지 없음
✅ 개발자 도구 Console 깨끗함
```

### 실패 시:
```
❌ "Cannot connect to server: timeout"
❌ wss:// 연결 실패
❌ 데이터 업데이트 안됨
❌ 빨간 에러 메시지
```

## 빠른 체크 스크립트

```bash
#!/bin/bash
# websocket-check.sh

echo "WebSocket 연결 상태 확인..."

# 1. 백엔드 포트 확인
echo "1. 백엔드 포트(13001) 확인..."
docker exec reflex-ksys-app-prod curl -s http://localhost:13001/ping && echo "✅ 백엔드 OK" || echo "❌ 백엔드 없음"

# 2. 프론트엔드 포트 확인
echo "2. 프론트엔드 포트(13000) 확인..."
docker exec reflex-ksys-app-prod curl -s http://localhost:13000 > /dev/null && echo "✅ 프론트엔드 OK" || echo "❌ 프론트엔드 없음"

# 3. Cloudflare Tunnel 상태
echo "3. Cloudflare Tunnel 상태..."
docker ps | grep cloudflared | grep -q "Up" && echo "✅ Tunnel 실행 중" || echo "❌ Tunnel 중지됨"

# 4. 로그에서 에러 확인
echo "4. 최근 에러 확인..."
docker logs reflex-ksys-app-prod --tail 20 | grep -i error || echo "✅ 에러 없음"

echo ""
echo "외부 테스트: https://ksys.idna.ai.kr"
echo "WebSocket: wss://ksys.idna.ai.kr/_event"
```

## 핵심 요약

**문제:** WebSocket 연결 timeout
**원인:** Cloudflare Tunnel에서 WebSocket 미지원
**해결:**
1. Cloudflare Dashboard → Public Hostname → **WebSocket ON**
2. `/_event*` 경로를 `reflex-app-prod:13001`로 라우팅
3. Tunnel 재시작

**시간:** 5분 내 해결 가능

이렇게 설정하면 실시간 데이터가 정상적으로 업데이트됩니다! 🚀
