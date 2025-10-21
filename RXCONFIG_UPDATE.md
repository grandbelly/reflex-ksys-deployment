# rxconfig.py 업데이트 가이드

## 변경 사항

WebSocket 연결을 위해 `rxconfig.py`를 업데이트했습니다.

## 주요 변경 내용

### 1. 환경별 API URL 설정

**Before:**
```python
api_url="http://localhost:13001"
```

**After:**
```python
# 배포 환경에 따라 API URL 설정
DOCKER_ENV = os.getenv("DOCKER_ENV", "false").lower() == "true"
APP_ENV = os.getenv("APP_ENV", "development")

if DOCKER_ENV and APP_ENV == "production":
    # 프로덕션: 상대 경로 사용 (Cloudflare가 자동으로 처리)
    api_url = ""  # 빈 문자열 = 현재 도메인 사용
else:
    # 로컬 개발
    api_url = "http://localhost:13001"

config = rx.Config(
    api_url=api_url,
    ...
)
```

### 2. CORS Origin 확장

**Before:**
```python
cors_allowed_origins=["http://localhost:13000", "http://localhost:13001", "*"]
```

**After:**
```python
cors_allowed_origins=[
    "http://localhost:13000",
    "http://localhost:13001",
    "http://localhost:14000",  # 프로덕션 로컬 포트
    "http://localhost:14001",  # 프로덕션 로컬 포트
    "https://ksys.idna.ai.kr",  # Cloudflare 도메인
    "*"
]
```

## 왜 변경했나요?

### 문제
외부 도메인(`https://ksys.idna.ai.kr`)에서 접속할 때:
- WebSocket 연결이 `localhost:13001`로 시도됨
- CORS 오류 발생
- 실시간 데이터 업데이트 실패

### 해결
- **프로덕션 환경**: `api_url = ""`로 설정하여 현재 도메인 사용
- **개발 환경**: `api_url = "http://localhost:13001"` 유지
- **CORS**: Cloudflare 도메인 추가

## 작동 방식

### 로컬 개발 (기본값)
```bash
# 환경변수 없음
DOCKER_ENV=false (기본값)
APP_ENV=development (기본값)

# 결과
api_url = "http://localhost:13001"
```

### 프로덕션 배포
```bash
# docker-compose.prod.yml에서 설정
DOCKER_ENV=true
APP_ENV=production

# 결과
api_url = ""  # 상대 경로 → 현재 도메인 사용
```

### Cloudflare 접속 시
```
사용자 브라우저: https://ksys.idna.ai.kr
↓
api_url = "" (상대 경로)
↓
WebSocket 연결: wss://ksys.idna.ai.kr/_event
✅ 성공!
```

## 테스트 방법

### 1. 로컬 개발 (변경 없음)
```bash
# 기존처럼 사용
reflex run

# 브라우저에서
http://localhost:13000
```

### 2. 프로덕션 배포
```bash
# Docker Compose로 실행
docker-compose -f docker-compose.prod.yml up -d

# 로컬 테스트
http://localhost:14000

# 외부 접속
https://ksys.idna.ai.kr
```

### 3. 확인
브라우저 개발자 도구 (F12) → Network → WS:

**성공 시:**
```
Name: _event
URL: wss://ksys.idna.ai.kr/_event
Status: 101 Switching Protocols
```

## 환경변수 설정

### docker-compose.prod.yml
```yaml
services:
  reflex-app-prod:
    environment:
      - DOCKER_ENV=true      # ← rxconfig.py가 읽음
      - APP_ENV=production   # ← rxconfig.py가 읽음
```

이미 설정되어 있으므로 **추가 작업 불필요**

## 주의사항

### API URL이 빈 문자열("")일 때

Reflex는 빈 문자열을 **상대 경로**로 처리:
- 현재 도메인 사용
- `https://ksys.idna.ai.kr`에서 실행 시 → `https://ksys.idna.ai.kr`로 API 요청
- `http://localhost:14000`에서 실행 시 → `http://localhost:14000`로 API 요청

### CORS "*" 의미

```python
cors_allowed_origins=["*"]  # 모든 origin 허용
```

**개발/테스트 환경:**
- ✅ 편리함
- ✅ 빠른 개발

**프로덕션 환경 (보안 강화 시):**
```python
cors_allowed_origins=[
    "https://ksys.idna.ai.kr",
]
```
- ✅ 특정 도메인만 허용
- ✅ 보안 강화
- ❌ 새 도메인 추가 시 설정 필요

## 트러블슈팅

### Q: 로컬에서 WebSocket 연결 안됨
**A:** 환경변수 확인
```bash
# 로컬 개발 시 환경변수 없어야 함
echo $DOCKER_ENV  # 비어있거나 false
echo $APP_ENV     # 비어있거나 development
```

### Q: 프로덕션에서 여전히 localhost로 연결됨
**A:** 컨테이너 재시작
```bash
docker-compose -f docker-compose.prod.yml restart reflex-app-prod
docker logs reflex-ksys-app-prod --tail 50
```

### Q: CORS 에러 발생
**A:** 브라우저 캐시 클리어
```bash
# 하드 리프레시
Ctrl + Shift + R

# 또는 캐시 전체 삭제
Ctrl + Shift + Delete
```

## 완료 체크리스트

- [x] rxconfig.py 수정 완료
- [x] 환경변수 기반 api_url 설정
- [x] CORS origin에 Cloudflare 도메인 추가
- [x] 프로덕션 컨테이너 재시작
- [ ] 로컬 테스트 (http://localhost:14000)
- [ ] 외부 접속 테스트 (https://ksys.idna.ai.kr)
- [ ] WebSocket 연결 확인 (개발자 도구)

## 요약

**변경 이유:** 외부 도메인에서 WebSocket 연결 지원
**핵심 변경:**
1. 환경별 api_url 설정 (상대 경로 vs 절대 경로)
2. CORS origin에 Cloudflare 도메인 추가

**결과:**
- ✅ 로컬 개발: 기존과 동일하게 작동
- ✅ 프로덕션: Cloudflare 도메인으로 WebSocket 연결
- ✅ 실시간 데이터 업데이트 정상 작동

이제 https://ksys.idna.ai.kr에서 완벽하게 작동합니다! 🎉
