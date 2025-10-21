# 배포 버전 셋업 가이드

> Windows 환경에서 배포 버전(Python 3.11)을 개발 버전(Python 3.13)과 병렬로 실행하여 테스트합니다.

## 📋 생성된 파일 목록

배포 테스트를 위해 다음 파일들이 생성되었습니다:

### 🐳 Docker 설정 파일
- `Dockerfile.prod` - 배포용 Dockerfile (Python 3.11 기반)
- `schedulers/Dockerfile.prod` - 배포용 스케줄러 Dockerfile
- `docker-compose.prod.yml` - 배포용 Docker Compose 설정

### 📖 가이드 문서
- `DEPLOYMENT_TEST_GUIDE.md` - 상세 테스트 가이드
- `PROD_DEPLOYMENT_SETUP.md` - 이 파일 (빠른 시작 가이드)

### 🔧 관리 스크립트

**Linux/WSL2:**
- `start-prod.sh` - 배포 버전 빌드 및 시작
- `compare-versions.sh` - 개발/배포 버전 비교
- `manage.sh` - 배포 버전 관리 유틸리티

**Windows:**
- `start-prod.bat` - 배포 버전 빌드 및 시작
- `manage.bat` - 배포 버전 관리 유틸리티

## 🚀 빠른 시작

### Windows에서 시작

#### 1단계: 배포 버전 빌드 및 시작

```batch
# PowerShell 또는 CMD에서 실행
start-prod.bat
```

또는 수동으로:

```batch
# 배포 버전 이미지 빌드
docker-compose -f docker-compose.prod.yml build

# 배포 버전 시작
docker-compose -f docker-compose.prod.yml up -d
```

#### 2단계: 웹 인터페이스 접속

- 개발 버전: http://localhost:13000 (Python 3.13)
- 배포 버전: http://localhost:14000 (Python 3.11) ✨ NEW

#### 3단계: 로그 확인

```batch
# 배포 버전 로그 확인
docker logs reflex-ksys-app-prod -f

# 스케줄러 로그 확인
docker logs forecast-scheduler-prod -f
```

### Linux/WSL2에서 시작

```bash
# 권한 추가 (처음 한 번만)
chmod +x *.sh

# 배포 버전 시작
./start-prod.sh

# 또는 관리 유틸리티 실행
./manage.sh
```

## 📊 버전 비교

| 항목 | 개발 버전 | 배포 버전 |
|------|---------|---------|
| **Python** | 3.13 | 3.11 ⭐ |
| **포트** | 13000-13001 | 14000-14001 |
| **설정 파일** | docker-compose.yml | docker-compose.prod.yml |
| **Dockerfile** | Dockerfile | Dockerfile.prod |
| **Environment** | development | production |
| **Hot Reload** | ✅ 지원 | ❌ 미지원 |
| **로그 경로** | ./logs | ./logs/prod |
| **Data Injector** | ✅ 활성화 | ❌ 비활성화 |
| **상태 확인** | `docker-compose ps` | `docker-compose -f docker-compose.prod.yml ps` |

## 🔍 실시간 모니터링

### 컨테이너 상태 확인

```bash
# 모든 컨테이너 확인
docker ps

# 배포 버전만 확인
docker ps --filter "name=prod"
```

### 리소스 사용량 비교

```bash
# 실시간 모니터링
docker stats reflex-ksys-app reflex-ksys-app-prod forecast-scheduler forecast-scheduler-prod
```

### 헬스 상태 확인

```bash
# 배포 버전 헬스 상태
docker inspect reflex-ksys-app-prod --format='{{.State.Health.Status}}'

# 상태: healthy / unhealthy / starting
```

## 🧪 테스트 체크리스트

배포 버전이 정상 작동하는지 확인하세요:

### 기본 기능 테스트

- [ ] **대시보드** - http://localhost:14000에서 실시간 데이터 표시
- [ ] **알람** - 알람 데이터가 올바르게 표시되는지 확인
- [ ] **학습 마법사** - 모델 학습 기능이 정상 작동하는지 확인
- [ ] **트렌드** - 시간 범위별 데이터 조회가 정상인지 확인

### 데이터베이스 연결 테스트

```bash
docker exec reflex-ksys-app-prod python -c "
import asyncio
from ksys_app.db import get_pool
async def test():
    pool = await get_pool()
    print(f'✅ 데이터베이스 연결 성공!')
    print(f'   풀 크기: {pool.min_size}-{pool.max_size}')
asyncio.run(test())
"
```

### 스케줄러 작동 확인

```bash
# 스케줄러 로그에서 예측 생성 확인
docker logs forecast-scheduler-prod -f | grep "ForecastScheduler"

# 5분마다 "Running predictions" 메시지가 나타나야 함
```

### 성능 비교

```bash
# 두 버전의 CPU/메모리 사용량 비교
docker stats --no-stream
```

## ⚙️ 포트 충돌 해결

만약 포트 14000/14001이 이미 사용 중이라면:

```bash
# 포트 확인 (Windows)
netstat -ano | findstr :14000

# 포트 변경 - docker-compose.prod.yml 수정
# ports:
#   - "15000:13000"  # 14000 대신 15000 사용
#   - "15001:13001"  # 14001 대신 15001 사용

docker-compose -f docker-compose.prod.yml up -d
```

## 🔄 개발 버전과 배포 버전 동시 운영

### 개발 버전 계속 사용

개발 버전은 그대로 유지됩니다:

```bash
# 개발 버전만 다시 시작하려면
docker-compose restart reflex-ksys-app forecast-scheduler
```

### 두 버전 모두 중지

```bash
# 개발 버전 종료
docker-compose down

# 배포 버전 종료
docker-compose -f docker-compose.prod.yml down
```

## 🎯 배포 준비 체크리스트

배포 버전이 프로덕션에 준비되었는지 확인하세요:

- [ ] 데이터베이스 연결 정상
- [ ] 웹 UI 모든 기능 정상 작동
- [ ] 스케줄러 5분 주기로 예측 생성
- [ ] 로그에 에러 없음
- [ ] 헬스 상태가 `healthy`
- [ ] 리소스 사용량 정상 범위
- [ ] Python 3.11 호환성 문제 없음

## 📈 다음 단계

### 1️⃣ 배포 버전 검증 (진행 중)
- 현재 Windows에서 테스트 중
- 모든 기능 정상 확인

### 2️⃣ RPI 환경 배포 (다음 단계)
```bash
# RPI에서 배포 버전 빌드 (Python 3.11 사용)
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### 3️⃣ 개발 버전도 Python 3.11로 업그레이드 (선택)
```bash
# Dockerfile도 Python 3.11로 변경 고려
# RPI 환경 호환성 개선
FROM python:3.11-slim  # 3.13 대신 3.11 사용
```

### 4️⃣ 프로덕션 전환 (테스트 완료 후)
```bash
# 배포 버전을 메인으로 설정
manage.bat        # Windows
./manage.sh       # Linux/WSL2
# 9번 선택 (배포 버전 → 프로덕션 전환)
```

## 📞 문제 해결

### 배포 버전이 시작하지 않음

```bash
# 1. 로그 확인
docker logs reflex-ksys-app-prod --tail 50

# 2. 빌드 캐시 제거 후 다시 빌드
docker-compose -f docker-compose.prod.yml build --no-cache

# 3. 컨테이너 강제 제거 후 재시작
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d
```

### Python 3.11 호환성 문제

만약 특정 라이브러리가 Python 3.11을 지원하지 않는다면:

1. requirements.txt의 버전 확인
2. Dockerfile.prod에서 Python 버전 변경
3. 라이브러리 업데이트 시도

```bash
# Dockerfile.prod에서
FROM python:3.12-slim  # 3.11 대신 3.12 시도
```

### 데이터베이스 연결 실패

```bash
# 환경 변수 확인
docker exec reflex-ksys-app-prod python -c "
import os
print('TS_DSN:', os.getenv('TS_DSN'))
"

# 또는 docker-compose.prod.yml에서 환경 변수 확인
```

## 📚 추가 정보

자세한 내용은 다음 문서를 참조하세요:

- `DEPLOYMENT_TEST_GUIDE.md` - 상세 테스트 가이드
- `CLAUDE.md` - 프로젝트 아키텍처 및 개발 가이드
- `README.md` - 전체 시스템 개요

## 🎓 스크립트 사용 팁

### Windows에서 스크립트 권한 오류

```batch
# PowerShell에서 실행하면 권한 오류 가능
# 대신 CMD에서 실행하거나 절대 경로 사용
cmd /c manage.bat
```

### Linux/WSL2에서 권한 설정

```bash
# 스크립트에 실행 권한 부여
chmod +x *.sh

# 실행
./manage.sh
```

---

## 🎉 모든 준비가 완료되었습니다!

배포 버전 테스트를 위해 필요한 모든 파일과 스크립트가 준비되었습니다.

**다음 명령으로 바로 시작하세요:**

```bash
# Windows
start-prod.bat

# Linux/WSL2
./start-prod.sh
```

**궁금한 점이 있으면 확인하세요:**
- 이 파일 (`PROD_DEPLOYMENT_SETUP.md`)
- `DEPLOYMENT_TEST_GUIDE.md`
- `CLAUDE.md`

행운을 빕니다! 🚀
