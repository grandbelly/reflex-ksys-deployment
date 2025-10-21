# WebSocket 빠른 해결 가이드 ⚡

## 현재 문제

```
Cannot connect to server: timeout
wss://ksys.idna.ai.kr/_event
```

## 1분 해결법 🚀

### Cloudflare Dashboard 설정 (필수!)

Token 기반 터널은 **Cloudflare Dashboard에서만** ingress 규칙을 설정할 수 있습니다.

#### 1단계: Dashboard 접속

https://one.dash.cloudflare.com → **Networks** → **Tunnels**

#### 2단계: 터널 선택

현재 터널 클릭 (HEALTHY 상태)

#### 3단계: Public Hostname 설정

**Configure** 탭 → **Public Hostname** 섹션

현재 1개만 있을 것입니다:
```
ksys.idna.ai.kr → http://reflex-app-prod:13000
```

#### 4단계: 백엔드 라우팅 추가 ⭐

**"Add a public hostname"** 클릭

```yaml
Public hostname:
  Subdomain: ksys
  Domain: idna.ai.kr
  Path: /_event          # 이것이 핵심!

Service:
  Type: HTTP
  URL: reflex-app-prod:13001

Additional application settings:
  ✅ Enable WebSocket support (반드시 체크!)
```

#### 5단계: 기존 규칙도 WebSocket 활성화

기존 `ksys.idna.ai.kr` 규칙 **Edit** 클릭:

```yaml
Additional application settings:
  ✅ Enable WebSocket support (체크!)
```

**Save** 클릭

#### 6단계: 순서 확인 (중요!)

Public Hostname 목록에서 **순서 확인**:

```
1순위: ksys.idna.ai.kr  Path: /_event    → reflex-app-prod:13001 ✅
2순위: ksys.idna.ai.kr  Path: (empty)    → reflex-app-prod:13000 ✅
```

순서가 잘못되었다면 드래그해서 **/_event가 위로** 이동!

#### 7단계: 완료!

1-2분 대기 후 https://ksys.idna.ai.kr 새로고침

---

## 설정 스크린샷 가이드

### Public Hostname #1 (/_event)
```
┌─────────────────────────────────────────┐
│ Public hostname                          │
├─────────────────────────────────────────┤
│ Subdomain:  ksys                         │
│ Domain:     idna.ai.kr                   │
│ Path:       /_event                      │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Service                                  │
├─────────────────────────────────────────┤
│ Type:  HTTP                              │
│ URL:   reflex-app-prod:13001             │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Additional application settings          │
├─────────────────────────────────────────┤
│ ☑ Enable WebSocket support              │
└─────────────────────────────────────────┘
```

### Public Hostname #2 (main app)
```
┌─────────────────────────────────────────┐
│ Public hostname                          │
├─────────────────────────────────────────┤
│ Subdomain:  ksys                         │
│ Domain:     idna.ai.kr                   │
│ Path:       (비워두기)                   │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Service                                  │
├─────────────────────────────────────────┤
│ Type:  HTTP                              │
│ URL:   reflex-app-prod:13000             │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Additional application settings          │
├─────────────────────────────────────────┤
│ ☑ Enable WebSocket support              │
└─────────────────────────────────────────┘
```

---

## 확인 방법

### 브라우저 개발자 도구

1. `F12` 키 누르기
2. **Network** 탭
3. **WS** (WebSocket) 필터 클릭
4. 페이지 새로고침 (`Ctrl+F5`)

**성공 시:**
```
Name: _event
Status: 101 Switching Protocols
Type: websocket
✅ 초록색 표시
```

**실패 시:**
```
Name: _event
Status: (failed)
❌ 빨간색 표시
```

### Console 테스트

개발자 도구 → **Console** 탭:

```javascript
new WebSocket('wss://ksys.idna.ai.kr/_event').onopen = () => console.log('✅ OK')
```

**성공:** `✅ OK` 출력
**실패:** 에러 메시지

---

## 체크리스트

설정 완료 후:

- [ ] Cloudflare Dashboard 접속
- [ ] Public Hostname 2개 생성
  - [ ] `/_event` → `reflex-app-prod:13001`
  - [ ] `/` → `reflex-app-prod:13000`
- [ ] 두 규칙 모두 **WebSocket 활성화**
- [ ] `/_event` 규칙이 **위에** 있는지 확인
- [ ] 저장 완료
- [ ] 1-2분 대기
- [ ] 페이지 새로고침 (`Ctrl+F5`)
- [ ] WebSocket 연결 확인 (개발자 도구)
- [ ] 에러 메시지 사라짐 확인

---

## 트러블슈팅

### Q: Dashboard에서 Path 옵션이 안 보여요
**A:** "Advanced" 또는 "Additional settings" 클릭하여 펼치기

### Q: WebSocket 옵션이 안 보여요
**A:** Service 설정에서 Type을 **HTTP** (HTTPS 아님)로 선택

### Q: 저장했는데 안 바뀌어요
**A:**
1. 브라우저 캐시 클리어 (`Ctrl+Shift+Delete`)
2. 시크릿 모드로 테스트
3. Cloudflare Dashboard에서 설정 다시 확인

### Q: 여전히 timeout 나와요
**A:**
```bash
# 터널 재시작
docker restart cloudflared-tunnel-prod

# 로그 확인
docker logs cloudflared-tunnel-prod --tail 20

# 앱 재시작
docker restart reflex-ksys-app-prod
```

---

## 왜 Config 파일이 안 먹혀요?

Token 기반 터널(`--token` 사용)은 **Cloudflare Dashboard의 설정이 우선**입니다.

Config 파일은 **Credentials 기반**에서만 완전히 작동합니다.

현재 설정:
```yaml
# Token 기반 (Dashboard 우선)
command: tunnel --token XXX

# Config는 참고용으로만 사용됨
--config /etc/cloudflared/config.yml
```

**해결:** Dashboard에서 직접 설정!

---

## 예상 결과

### Before (현재)
```
❌ Cannot connect to server: timeout
❌ wss:// 연결 실패
❌ 실시간 데이터 없음
❌ 빨간 에러 박스
```

### After (설정 후)
```
✅ WebSocket 연결 성공
✅ 실시간 데이터 업데이트
✅ 에러 메시지 사라짐
✅ 부드러운 UI 업데이트
```

---

## 핵심 요약

**3단계 해결:**

1. **Cloudflare Dashboard** 접속
2. **Public Hostname 추가:** `/_event` → `reflex-app-prod:13001`
3. **WebSocket 활성화** (두 규칙 모두)

**소요 시간:** 2-3분
**난이도:** ⭐☆☆☆☆

이제 실시간 데이터가 정상 작동합니다! 🎉
