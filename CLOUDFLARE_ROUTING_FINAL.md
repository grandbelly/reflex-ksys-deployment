# Cloudflare 최종 라우팅 설정 가이드

## 문제 분석

Reflex는 **2개 포트**를 사용합니다:
- **13000**: Frontend (정적 파일, HTML)
- **13001**: Backend (API, WebSocket)

**현재 문제:**
- 페이지는 13000에서 로드 ✅
- WebSocket은 /_event로 13001 필요 ❌
- API 호출도 13001 필요 ❌

## 해결 방법 (두 가지 옵션)

---

## 옵션 1: Path 기반 라우팅 (권장) ⭐

Cloudflare Dashboard에서 **3개 규칙** 설정:

### Public Hostname 설정 (순서 중요!)

#### 1순위: WebSocket
```yaml
Subdomain: ksys
Domain: idna.ai.kr
Path: /_event*

Service:
  Type: HTTP
  URL: reflex-app-prod:13001

Settings:
  ✅ WebSocket: ON
  Connect Timeout: 90s
```

#### 2순위: API 호출
```yaml
Subdomain: ksys
Domain: idna.ai.kr
Path: /api/*

Service:
  Type: HTTP
  URL: reflex-app-prod:13001

Settings:
  ✅ WebSocket: ON
  Connect Timeout: 90s
```

#### 3순위: Frontend (기본)
```yaml
Subdomain: ksys
Domain: idna.ai.kr
Path: (비워두기)

Service:
  Type: HTTP
  URL: reflex-app-prod:13000

Settings:
  WebSocket: OFF (또는 ON도 무방)
  Connect Timeout: 30s
```

### rxconfig.py 설정
```python
api_url = "https://ksys.idna.ai.kr"
```

### 작동 방식
```
https://ksys.idna.ai.kr/          → 13000 (페이지)
https://ksys.idna.ai.kr/api/*     → 13001 (API)
wss://ksys.idna.ai.kr/_event      → 13001 (WebSocket)
https://ksys.idna.ai.kr/logo.png  → 13000 (정적 파일)
```

---

## 옵션 2: 서브도메인 분리 (더 명확함) ⭐⭐

### Public Hostname 설정

#### Backend (별도 서브도메인)
```yaml
Subdomain: api
Domain: idna.ai.kr

Service:
  Type: HTTP
  URL: reflex-app-prod:13001

Settings:
  ✅ WebSocket: ON
  Connect Timeout: 90s
```

#### Frontend (메인 도메인)
```yaml
Subdomain: ksys
Domain: idna.ai.kr

Service:
  Type: HTTP
  URL: reflex-app-prod:13000

Settings:
  WebSocket: OFF
  Connect Timeout: 30s
```

### rxconfig.py 설정
```python
if DOCKER_ENV and APP_ENV == "production":
    api_url = "https://api.idna.ai.kr"  # 백엔드 서브도메인
else:
    api_url = "http://localhost:13001"
```

### 작동 방식
```
https://ksys.idna.ai.kr/          → 13000 (페이지)
https://api.idna.ai.kr/api/*      → 13001 (API)
wss://api.idna.ai.kr/_event       → 13001 (WebSocket)
```

---

## 옵션 3: 단일 포트 사용 (가장 간단) ⭐⭐⭐

**Reflex 기본 동작:** 13000 포트에서 모든 요청 처리 가능!

### Cloudflare Dashboard 설정

단 1개 규칙만:
```yaml
Subdomain: ksys
Domain: idna.ai.kr
Path: (비워두기)

Service:
  Type: HTTP
  URL: reflex-app-prod:13000  ← 13000만 사용!

Settings:
  ✅ WebSocket: ON  ← 중요!
  Connect Timeout: 90s
```

### rxconfig.py 설정
```python
# 기본값 사용
api_url = ""  # 빈 문자열 = 상대 경로
```

### docker-compose.prod.yml
13001 포트 매핑 제거:
```yaml
reflex-app-prod:
  ports:
    - "14000:13000"  # Frontend만
    # - "14001:13001"  # 제거 (내부에서만 사용)
```

### 작동 방식
Reflex는 **13000 포트에서**:
- HTTP 요청 처리 ✅
- WebSocket 요청 처리 ✅
- 정적 파일 서빙 ✅

```
https://ksys.idna.ai.kr/          → 13000
https://ksys.idna.ai.kr/api/*     → 13000
wss://ksys.idna.ai.kr/_event      → 13000 (WebSocket)
```

---

## 비교표

| 방식 | 규칙 수 | 복잡도 | 관리 | 추천 |
|------|---------|---------|------|------|
| **옵션 1: Path 기반** | 3개 | 중간 | 중간 | ⭐ |
| **옵션 2: 서브도메인** | 2개 | 높음 | 쉬움 | ⭐⭐ |
| **옵션 3: 단일 포트** | 1개 | 낮음 | 매우 쉬움 | ⭐⭐⭐ |

---

## 추천: 옵션 3 (단일 포트)

### 이유:
1. **Reflex 기본 동작**과 일치
2. **설정 최소화**
3. **유지보수 쉬움**
4. **WebSocket 문제 해결**

### 설정 단계:

#### 1. Cloudflare Dashboard
```
Public Hostname 1개만:
  ksys.idna.ai.kr → reflex-app-prod:13000
  ✅ WebSocket: ON
```

#### 2. rxconfig.py
```python
# 현재 그대로 유지
api_url = ""
```

#### 3. 완료!
```bash
# 재시작
docker-compose -f docker-compose.prod.yml restart

# 테스트
https://ksys.idna.ai.kr
```

---

## 현재 설정 확인

### Cloudflare Dashboard 로그인
https://one.dash.cloudflare.com

### 확인 사항
1. **Public Hostname** 섹션
2. 현재 몇 개 규칙이 있는지?
3. WebSocket 활성화되어 있는지?

### 권장 최종 설정

**단순하게 1개 규칙:**
```
ksys.idna.ai.kr → http://reflex-app-prod:13000
WebSocket: ON ✅
```

이것만으로 **모든 것이 작동**합니다!

---

## 테스트 방법

### 브라우저 개발자 도구 (F12)

#### Network 탭
```
Name          Status    Type
/             200       document
/logo.png     200       png
/_event       101       websocket  ← 이것 확인!
```

#### Console 테스트
```javascript
// WebSocket 연결 테스트
ws = new WebSocket('wss://ksys.idna.ai.kr/_event')
ws.onopen = () => console.log('✅ 연결 성공!')
ws.onerror = (e) => console.error('❌ 연결 실패:', e)
```

---

## 최종 권장 사항

**가장 간단하고 확실한 방법:**

1. Cloudflare Dashboard에서 기존 규칙 **모두 삭제**
2. **1개 규칙만** 추가:
   ```
   ksys.idna.ai.kr → reflex-app-prod:13000
   WebSocket: ON ✅
   ```
3. rxconfig.py:
   ```python
   api_url = ""  # 상대 경로
   ```
4. 재시작:
   ```bash
   docker-compose -f docker-compose.prod.yml restart
   ```

이렇게 하면 13000 포트 하나로 **모든 것이 해결**됩니다! 🎉

Reflex는 똑똑하게 설계되어서 13000에서 WebSocket도 처리할 수 있습니다!
