# WebSocket 간단 해결법 (최종)

## 결론: /_event 하나만 추가하면 됩니다!

### Cloudflare Dashboard 설정

**2개 규칙만 필요:**

#### 규칙 1 (우선순위 높음)
```
Subdomain: ksys
Domain: idna.ai.kr
Path: /_event

Service:
  Type: HTTP
  URL: reflex-app-prod:13001

Settings:
  ✅ WebSocket: ON
  Connect Timeout: 90s
```

#### 규칙 2 (기본)
```
Subdomain: ksys
Domain: idna.ai.kr
Path: (비워두기)

Service:
  Type: HTTP
  URL: reflex-app-prod:13000

Settings:
  ✅ WebSocket: ON (켜두면 좋음)
  Connect Timeout: 30s
```

## 왜 이것만으로 충분한가?

Reflex 13000 포트는 **스마트 프록시**입니다:
- `/` → 13000에서 직접 처리 (HTML, 정적 파일)
- `/api/*` → 13000이 자동으로 13001로 프록시
- **`/_event`만** 직접 13001로 연결 필요!

## 작동 방식

```
사용자 → Cloudflare → 컨테이너

https://ksys.idna.ai.kr/
  → 13000 (페이지 로드)
  → 13000이 내부에서 13001 호출

wss://ksys.idna.ai.kr/_event
  → 13001 (WebSocket 직접 연결) ← 이것만 설정!
```

## 설정 단계

1. **Cloudflare Dashboard** 접속
2. **Public Hostname** 추가:
   - `/_event` → `reflex-app-prod:13001`
   - WebSocket ON
3. 저장
4. 완료!

## rxconfig.py

```python
api_url = "https://ksys.idna.ai.kr"
```

이것만으로 충분합니다!

## 요약

❌ `/api/*` 라우팅 **불필요** (13000이 알아서 처리)
✅ `/_event` 라우팅 **필수** (WebSocket 직접 연결)

**설정할 것: 딱 1개 (/_event)**

이게 전부입니다! 🎉
