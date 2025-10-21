# Cloudflare Tunnel 502 Error 해결 가이드

## 문제: 502 Bad Gateway

`ksys.idna.ai.kr` 접속 시 502 오류가 발생하는 경우, Cloudflare Tunnel은 연결되어 있지만 올바른 서비스로 라우팅되지 않는 것입니다.

## 원인

Cloudflare 대시보드의 Public Hostname 설정에서 서비스 URL이 잘못 설정되어 있습니다.

## 해결 방법

### 1. Cloudflare Zero Trust 대시보드 접속

1. https://one.dash.cloudflare.com 접속
2. 로그인
3. **Networks** → **Tunnels** 메뉴로 이동

### 2. Tunnel 선택

현재 실행 중인 터널 선택:
- Tunnel ID: `7071a55a-1039-46e1-bb65-abcfcee01991`
- Status: **HEALTHY** (초록색)

### 3. Public Hostname 설정 수정

**Public Hostname** 탭에서 `ksys.idna.ai.kr` 설정을 확인/수정합니다:

#### 올바른 설정:

```
Subdomain: ksys
Domain: idna.ai.kr
Path: (비워두기)

Service:
  Type: HTTP
  URL: reflex-app-prod:13000
```

**중요:**
- ❌ `http://reflex-app-prod:13000` (X)
- ❌ `localhost:14000` (X)
- ❌ `127.0.0.1:14000` (X)
- ✅ `reflex-app-prod:13000` (O)

#### 상세 설정:

| 필드 | 값 | 설명 |
|------|-----|------|
| **Subdomain** | `ksys` | 서브도메인 |
| **Domain** | `idna.ai.kr` | 도메인 |
| **Path** | (비우기) | 전체 경로 처리 |
| **Type** | `HTTP` | 프로토콜 타입 |
| **URL** | `reflex-app-prod:13000` | Docker 컨테이너 이름:포트 |

### 4. 추가 설정 (선택사항)

**Advanced settings**에서:
- **Connect timeout**: `30s` → `90s` (권장)
- **No TLS Verify**: OFF (기본값)
- **HTTP Host Header**: (비우기)
- **Origin Server Name**: (비우기)

### 5. 설정 저장 및 확인

1. **Save hostname** 클릭
2. 1-2분 대기 (설정 전파 시간)
3. `https://ksys.idna.ai.kr` 접속하여 확인

## 네트워크 구조 확인

현재 Docker 네트워크 구조:

```
외부 인터넷
    ↓
Cloudflare Edge (ksys.idna.ai.kr)
    ↓
cloudflared-tunnel-prod 컨테이너
    ↓ (reflex-network-prod)
reflex-app-prod:13000 컨테이너
```

## 로컬에서 연결 테스트

### 1. Docker 네트워크 내에서 테스트

```bash
# cloudflared 컨테이너에서 reflex-app-prod로 연결 테스트
docker run --rm --network reflex-ksys-deployment_reflex-network-prod \
  curlimages/curl:latest \
  curl -v http://reflex-app-prod:13000

# 정상 응답: HTTP/1.1 200 OK
```

### 2. 로컬 포트로 테스트

```bash
# 로컬에서 직접 접속
curl http://localhost:14000

# 또는 브라우저에서
http://localhost:14000
```

### 3. Cloudflare Tunnel 로그 확인

```bash
# Tunnel 로그 확인
docker logs cloudflared-tunnel-prod -f

# 정상 연결 시 표시되어야 할 메시지:
# "Registered tunnel connection"
# "connection=<UUID> ... location=icn"
```

## 트러블슈팅

### 여전히 502 오류가 발생하는 경우

#### Option 1: Tunnel 재시작

```bash
# Tunnel 컨테이너만 재시작
docker restart cloudflared-tunnel-prod

# 전체 재시작
./manage.sh restart
```

#### Option 2: 설정 확인

```bash
# 현재 실행 중인 컨테이너 확인
docker ps | grep -E "reflex-app-prod|cloudflared"

# 네트워크 확인
docker network inspect reflex-ksys-deployment_reflex-network-prod
```

예상 출력:
```json
{
  "Containers": {
    "cloudflared-tunnel-prod": {...},
    "reflex-ksys-app-prod": {...},
    "forecast-scheduler-prod": {...}
  }
}
```

#### Option 3: Health Check 확인

```bash
# 애플리케이션 Health 확인
docker inspect reflex-ksys-app-prod --format='{{.State.Health.Status}}'
# 출력: healthy

# Tunnel Health 확인
docker inspect cloudflared-tunnel-prod --format='{{.State.Health.Status}}'
# 출력: healthy
```

### 애플리케이션이 응답하지 않는 경우

```bash
# 애플리케이션 로그 확인
docker logs reflex-ksys-app-prod --tail 50

# 애플리케이션 재시작
docker restart reflex-ksys-app-prod

# 2-3분 대기 후 다시 확인
```

## Alternative: Config File 사용

더 세밀한 제어가 필요한 경우, config file을 사용할 수 있습니다:

### 1. Config 파일 생성

`cloudflared-config.yml` 생성:

```yaml
tunnel: 7071a55a-1039-46e1-bb65-abcfcee01991
credentials-file: /etc/cloudflared/credentials.json

ingress:
  # Main application
  - hostname: ksys.idna.ai.kr
    service: http://reflex-app-prod:13000
    originRequest:
      connectTimeout: 90s
      noTLSVerify: false

  # API endpoint (optional)
  - hostname: ksys.idna.ai.kr
    path: /api/*
    service: http://reflex-app-prod:13001

  # Catch-all rule (required)
  - service: http_status:404
```

### 2. docker-compose.prod.yml 수정

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
```

### 3. 재시작

```bash
./manage.sh restart
```

## 체크리스트

배포 전 확인사항:

- [ ] Cloudflare Tunnel 상태: HEALTHY
- [ ] Public Hostname 설정: `reflex-app-prod:13000`
- [ ] 애플리케이션 상태: healthy
- [ ] Docker 네트워크: reflex-network-prod
- [ ] 로컬 접속 테스트: http://localhost:14000 정상
- [ ] Tunnel 로그: "Registered tunnel connection" 확인

## 설정 완료 후 테스트

```bash
# 1. 로컬 테스트
curl http://localhost:14000
# 응답: HTML 페이지

# 2. 외부 접속 테스트
curl https://ksys.idna.ai.kr
# 응답: HTML 페이지 (로컬과 동일)

# 3. API 테스트 (선택)
curl https://ksys.idna.ai.kr/ping
# 또는
curl http://localhost:14001/ping
```

## 예상 결과

### 성공 시:
- ✅ https://ksys.idna.ai.kr → 대시보드 화면 표시
- ✅ HTTPS 자동 활성화 (Cloudflare SSL)
- ✅ 빠른 로딩 속도
- ✅ DDoS 보호 활성화

### 실패 시 확인할 점:
1. Cloudflare Dashboard → Tunnels → Status가 HEALTHY인지
2. Public Hostname 설정이 정확한지
3. 애플리케이션 컨테이너가 실행 중인지
4. Docker 네트워크 연결이 정상인지

## Support

문제가 계속되는 경우:

1. **Cloudflare 로그 확인**
   ```bash
   docker logs cloudflared-tunnel-prod
   ```

2. **애플리케이션 로그 확인**
   ```bash
   docker logs reflex-ksys-app-prod
   ```

3. **네트워크 상태 확인**
   ```bash
   docker network ls
   docker network inspect reflex-ksys-deployment_reflex-network-prod
   ```

4. **Cloudflare Status 확인**
   - https://www.cloudflarestatus.com

## 요약

**핵심 해결 방법:**
1. Cloudflare Dashboard 접속
2. Public Hostname 설정 수정: `reflex-app-prod:13000`
3. 저장 후 1-2분 대기
4. https://ksys.idna.ai.kr 접속 확인

이 설정으로 502 오류가 해결됩니다! 🚀
