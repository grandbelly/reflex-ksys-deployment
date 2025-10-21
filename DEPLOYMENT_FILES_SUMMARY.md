# 배포 파일 생성 완료 요약

> 2025-10-20 생성 | Windows 환경 배포 테스트 준비 완료

## 📦 생성된 파일 목록

### 1. Docker 설정 파일 (3개)

#### `Dockerfile.prod` ✨ NEW
- **목적**: 배포용 Dockerfile (Python 3.11 기반)
- **특징**:
  - Python 3.13 → 3.11로 다운그레이드 (RPI 호환성)
  - 헬스체크 추가
  - 프로덕션 최적화
- **사용**: `docker-compose -f docker-compose.prod.yml build`

#### `schedulers/Dockerfile.prod` ✨ NEW
- **목적**: 배포용 스케줄러 Dockerfile (Python 3.11 기반)
- **특징**:
  - 경량 이미지
  - 헬스체크 포함
  - 프로덕션 환경 고려
- **사용**: docker-compose.prod.yml에서 자동 참조

#### `docker-compose.prod.yml` ✨ NEW
- **목적**: 배포용 Docker Compose 설정
- **특징**:
  - 개발 버전과 병렬 실행 가능
  - 포트 14000-14001 사용 (개발: 13000-13001)
  - 로그 분리 (./logs/prod)
  - Production 환경 설정
- **서비스**:
  - `reflex-app-prod`: 배포용 Reflex 앱
  - `forecast-scheduler-prod`: 배포용 스케줄러

### 2. 가이드 문서 (2개)

#### `DEPLOYMENT_TEST_GUIDE.md` 📖 NEW
- **내용**: 상세 배포 테스트 가이드
- **포함 사항**:
  - 빠른 시작 방법
  - 테스트 체크리스트
  - 문제 해결 방법
  - 리소스 모니터링
  - 성능 비교 표
- **대상**: 테스트 담당자

#### `PROD_DEPLOYMENT_SETUP.md` 📖 NEW
- **내용**: 빠른 시작 가이드 (한글)
- **포함 사항**:
  - 5분 안에 시작하는 방법
  - 버전 비교 표
  - 테스트 체크리스트
  - 포트 충돌 해결
  - 다음 단계 안내
- **대상**: 모든 개발자

### 3. 관리 스크립트 (4개)

#### Linux/WSL2 스크립트

**`start-prod.sh`** ✨ NEW
```bash
# 배포 버전 빌드 및 시작
chmod +x start-prod.sh
./start-prod.sh
```
- 배포 이미지 자동 빌드
- 컨테이너 자동 시작
- 액세스 정보 표시
- 다음 단계 안내

**`compare-versions.sh`** ✨ NEW
```bash
./compare-versions.sh
```
- 개발/배포 버전 실시간 비교
- 리소스 사용량 비교
- 포트 상태 확인
- 웹 인터페이스 액세스 정보

**`manage.sh`** ✨ NEW
```bash
./manage.sh
```
- 9가지 관리 메뉴:
  1. 배포 버전 빌드 및 시작
  2. 배포 버전 로그 보기
  3. 배포 버전 상태 확인
  4. 배포 버전 재시작
  5. 배포 버전 종료
  6. 버전 비교
  7. 리소스 모니터링
  8. DB 연결 테스트
  9. 프로덕션 전환

#### Windows 스크립트

**`start-prod.bat`** ✨ NEW
```batch
# 배포 버전 빌드 및 시작
start-prod.bat
```
- Windows CMD/PowerShell용
- 배포 이미지 자동 빌드
- 자동 시작 및 상태 확인

**`manage.bat`** ✨ NEW
```batch
# 배포 버전 관리
manage.bat
```
- Windows CMD/PowerShell용
- 9가지 관리 메뉴 (Linux와 동일)
- 배포/개발 버전 전환

## 🎯 파일 구조

```
c:\reflex\reflex-ksys-deployment\
├── Dockerfile                    (기존: 개발용, Python 3.13)
├── Dockerfile.prod               ✨ NEW: 배포용, Python 3.11
├── docker-compose.yml            (기존: 개발 설정)
├── docker-compose.prod.yml       ✨ NEW: 배포 설정
├── DEPLOYMENT_TEST_GUIDE.md      ✨ NEW: 상세 가이드
├── PROD_DEPLOYMENT_SETUP.md      ✨ NEW: 빠른 시작 가이드
├── start-prod.sh                 ✨ NEW: 배포 시작 스크립트 (Linux)
├── start-prod.bat                ✨ NEW: 배포 시작 스크립트 (Windows)
├── compare-versions.sh           ✨ NEW: 버전 비교 스크립트
├── manage.sh                     ✨ NEW: 관리 유틸리티 (Linux)
├── manage.bat                    ✨ NEW: 관리 유틸리티 (Windows)
├── schedulers/
│   ├── Dockerfile                (기존: 개발용, Python 3.13)
│   └── Dockerfile.prod           ✨ NEW: 배포용, Python 3.11
└── ...
```

## 🚀 사용법

### 1️⃣ Windows에서 시작 (가장 간단)

```batch
# 배포 버전 빌드 및 시작
start-prod.bat

# 또는 관리 메뉴 실행
manage.bat
```

### 2️⃣ Linux/WSL2에서 시작

```bash
# 권한 설정 (처음 한 번만)
chmod +x *.sh

# 배포 버전 시작
./start-prod.sh

# 또는 관리 메뉴
./manage.sh
```

### 3️⃣ 웹 인터페이스 접속

- 개발 버전: http://localhost:13000 (Python 3.13)
- 배포 버전: http://localhost:14000 (Python 3.11) ✨ NEW

## 📊 주요 변경 사항

### Python 버전
| | 개발 | 배포 |
|--|------|------|
| 버전 | 3.13 | 3.11 ⭐ |
| 호환성 | 최신 | RPI 호환 ✅ |
| 빌드 시간 | ~5분 | ~5분 |

### 포트 매핑
| 서비스 | 개발 | 배포 |
|--------|------|------|
| Frontend | 13000 | 14000 |
| Backend | 13001 | 14001 |
| 충돌 위험 | ❌ 없음 | ✅ 안전 |

### 환경 설정
| 설정 | 개발 | 배포 |
|-----|------|------|
| APP_ENV | development | production |
| Hot Reload | ✅ 지원 | ❌ 미지원 |
| Data Injector | ✅ 활성화 | ❌ 비활성화 |
| 헬스체크 | ❌ 없음 | ✅ 포함 |

## ✅ 테스트 체크리스트

배포 버전이 준비되었는지 확인하세요:

```bash
# 1. 이미지 빌드 확인
docker images | grep reflex

# 2. 컨테이너 실행 확인
docker ps | grep prod

# 3. 웹 UI 테스트
curl http://localhost:14000/

# 4. DB 연결 테스트
docker exec reflex-ksys-app-prod python -c "from ksys_app.db import get_pool; import asyncio; asyncio.run(get_pool())"

# 5. 스케줄러 작동 확인
docker logs forecast-scheduler-prod | grep "ForecastScheduler"
```

## 🔄 개발 버전과 배포 버전 동시 운영

- ✅ **가능**: 두 버전을 동시에 실행 가능
- ✅ **포트 분리**: 13000-13001 vs 14000-14001
- ✅ **로그 분리**: ./logs vs ./logs/prod
- ✅ **DB 공유**: 같은 데이터베이스 사용 가능

```bash
# 개발 버전 상태 확인
docker-compose ps

# 배포 버전 상태 확인
docker-compose -f docker-compose.prod.yml ps

# 두 버전 동시 모니터링
docker stats reflex-ksys-app reflex-ksys-app-prod
```

## 📈 다음 단계

### 1단계: Windows 배포 테스트 ✅ (준비 완료)
- 이 가이드를 따라 배포 버전 실행
- 모든 기능 정상 확인
- 성능 비교 테스트

### 2단계: RPI 환경 배포
```bash
# RPI에서 동일한 docker-compose.prod.yml 사용
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### 3단계: 기존 개발 버전도 Python 3.11로 업데이트 (선택)
- RPI 호환성 개선
- 개발 Dockerfile도 Python 3.11로 변경

### 4단계: 프로덕션 전환
- 배포 버전을 메인으로 설정
- 개발 버전은 백업으로 유지

## 📚 참고 문서

| 문서 | 내용 | 대상 |
|------|------|------|
| `PROD_DEPLOYMENT_SETUP.md` | 빠른 시작 (한글) | 모든 개발자 |
| `DEPLOYMENT_TEST_GUIDE.md` | 상세 테스트 가이드 | 테스트 담당자 |
| `CLAUDE.md` | 프로젝트 아키텍처 | 개발자 |
| `README.md` | 시스템 개요 | 모든 사람 |

## 🆘 문제 해결

### 포트 이미 사용 중

```bash
# 포트 확인 (Windows)
netstat -ano | findstr :14000

# docker-compose.prod.yml에서 포트 변경
# ports:
#   - "15000:13000"
#   - "15001:13001"
```

### 빌드 실패

```bash
# 캐시 제거 후 재빌드
docker-compose -f docker-compose.prod.yml build --no-cache
```

### 컨테이너 시작 실패

```bash
# 로그 확인
docker logs reflex-ksys-app-prod --tail 100

# 강제 재시작
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d
```

## 🎉 완료!

배포 테스트를 위한 모든 준비가 완료되었습니다.

**지금 바로 시작하세요:**

```bash
# Windows
start-prod.bat

# Linux/WSL2
chmod +x start-prod.sh
./start-prod.sh
```

궁금한 점이나 문제가 있으면 `PROD_DEPLOYMENT_SETUP.md` 또는 `DEPLOYMENT_TEST_GUIDE.md`를 참조하세요.

행운을 빕니다! 🚀

---

**생성 정보**
- 생성 날짜: 2025-10-20
- 테스트 환경: Windows (Docker Desktop)
- Python 버전: 3.13 (개발) / 3.11 (배포)
- 목적: RPI 환경 배포 전 Windows에서 호환성 테스트
