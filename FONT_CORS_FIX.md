# 웹폰트 CORS/MIME 문제 해결 가이드

## 문제 설명

프로덕션 환경에서 웹폰트가 로드되지 않고 폴백 폰트가 사용되는 문제가 발생할 수 있습니다:

- **CORS 오류**: 폰트 요청이 다른 도메인으로 가면 `Access-Control-Allow-Origin` 헤더가 없을 때 차단
- **MIME 타입 오류**: `.woff2`, `.woff` 파일의 MIME 타입이 잘못 설정되면 브라우저가 무시

## 적용된 해결 방법

### 1. 폰트 렌더링 최적화 (assets/styles.css)

```css
/* Font rendering optimization for crisp text */
* {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
  font-smooth: always;
  -webkit-text-stroke: 0.45px;
}
```

### 2. Google Fonts CORS 설정 (ksys_app/ksys_app.py)

```python
stylesheets=[
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap&crossorigin=anonymous",
    "/styles.css",
],
```

### 3. CORS 허용 도메인 추가 (rxconfig.py)

```python
cors_allowed_origins=[
    "http://localhost:13000",
    "http://localhost:13001",
    "https://ksys.idna.ai.kr",
    "https://fonts.googleapis.com",
    "https://fonts.gstatic.com",
    "*"
],
```

### 4. 커스텀 미들웨어 생성 (ksys_app/middleware.py)

폰트 파일과 정적 자산에 대한 CORS 헤더 및 올바른 MIME 타입을 설정하는 미들웨어를 생성했습니다:

- `FontCORSMiddleware`: 폰트 파일에 CORS 헤더 추가
- `StaticAssetMiddleware`: 모든 정적 자산에 대한 MIME 타입 및 캐싱 설정

**지원 MIME 타입:**
- `.woff2` → `font/woff2`
- `.woff` → `font/woff`
- `.ttf` → `font/ttf`
- `.otf` → `font/otf`
- `.eot` → `application/vnd.ms-fontobject`

### 5. Cloudflare Tunnel 설정 (cloudflared-config.yml)

Cloudflare를 통한 요청에 CORS 헤더를 추가했습니다:

```yaml
httpResponseHeaders:
  Access-Control-Allow-Origin: "*"
  Access-Control-Allow-Methods: "GET, POST, OPTIONS"
  Access-Control-Allow-Headers: "*"
  X-Font-Display: "swap"
```

## 적용 방법

### 로컬 개발 환경

1. 파일 수정 후 애플리케이션 재시작:
```bash
docker-compose restart reflex-app
```

2. 브라우저에서 확인:
   - DevTools → Network → Font 필터
   - Status 200/304 확인
   - CORS 오류 없는지 확인

### 프로덕션 환경

1. Docker 이미지 재빌드:
```bash
docker-compose -f docker-compose.prod.yml build --no-cache reflex-app-prod
```

2. 서비스 재시작:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

3. Cloudflare Tunnel 재시작:
```bash
docker-compose -f docker-compose.prod.yml restart cloudflared
```

**중요**: Token 기반 Cloudflare Tunnel을 사용하는 경우, Cloudflare Dashboard에서 직접 HTTP Response Headers를 설정해야 합니다:

1. Cloudflare Dashboard → Zero Trust → Networks → Tunnels
2. 해당 터널 선택 → Public Hostname 편집
3. Additional application settings → HTTP Settings
4. CORS Headers 섹션에서 다음 헤더 추가:
   - `Access-Control-Allow-Origin: *`
   - `Access-Control-Allow-Methods: GET, POST, OPTIONS`
   - `Access-Control-Allow-Headers: *`

## 검증 방법

### 1. 브라우저 DevTools 확인

```javascript
// Console에서 실행
document.fonts.ready.then(() => {
  console.log('Fonts loaded:', document.fonts.size);
  document.fonts.forEach(font => {
    console.log(font.family, font.status);
  });
});
```

### 2. Network 탭 확인

1. DevTools → Network → Font 필터 활성화
2. 페이지 새로고침
3. 폰트 요청 확인:
   - Status: 200 또는 304 (캐시)
   - Type: `font/woff2` 또는 `font/woff`
   - Response Headers에 `Access-Control-Allow-Origin` 존재 확인

### 3. Computed Styles 확인

1. DevTools → Elements → Computed 탭
2. `font-family` 속성 확인
3. `Inter`가 적용되었는지 확인 (폴백 폰트가 아닌지)

## 트러블슈팅

### 문제: 여전히 폰트가 로드되지 않음

**해결 방법:**
1. 브라우저 캐시 강제 새로고침 (Ctrl+Shift+R / Cmd+Shift+R)
2. 쿠키 및 캐시 완전 삭제 후 재접속
3. 시크릿 모드로 테스트

### 문제: CORS 오류가 여전히 발생

**해결 방법:**
1. Cloudflare Dashboard 설정 확인
2. `cloudflared-config.yml` 수정 후 컨테이너 재시작
3. nginx 또는 다른 리버스 프록시가 있다면 해당 설정 확인

### 문제: MIME 타입이 잘못됨

**해결 방법:**
1. Docker 이미지 재빌드 (미들웨어 적용을 위해)
2. 정적 파일 서빙 설정 확인
3. nginx 또는 웹 서버의 MIME 타입 설정 확인

## 참고 자료

- [MDN: CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [Google Fonts: Optimize Font Loading](https://developers.google.com/fonts/docs/getting_started)
- [Cloudflare: HTTP Response Headers](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/configuration/configuration-file/ingress#http-response-headers)
- [Web Font Best Practices](https://web.dev/font-best-practices/)

## 추가 최적화

### Preconnect 추가 (선택사항)

향후 더 나은 성능을 위해 HTML `<head>`에 preconnect를 추가할 수 있습니다:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
```

### 로컬 폰트 호스팅 (선택사항)

Google Fonts 의존성을 제거하려면 폰트 파일을 직접 호스팅할 수 있습니다:

1. Google Fonts에서 폰트 다운로드
2. `assets/fonts/` 디렉토리에 저장
3. `assets/styles.css`에 `@font-face` 규칙 추가:

```css
@font-face {
  font-family: 'Inter';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('/fonts/Inter-Regular.woff2') format('woff2');
}
```

이 방법을 사용하면 외부 CORS 문제를 완전히 제거할 수 있습니다.
