# 배포 버전 테스트 가이드

## 개요

이 문서는 Windows 환경에서 배포 버전 (Python 3.11 기반)을 테스트하는 방법을 설명합니다.

- **기존 개발 버전**: Python 3.13 (포트: 13000-13001)
- **새로운 배포 버전**: Python 3.11 (포트: 14000-14001)

두 버전을 동시에 실행할 수 있으므로 안정성 있게 테스트할 수 있습니다.

## 파일 구성

```
├── Dockerfile              # 개발 버전 (Python 3.13)
├── Dockerfile.prod         # 배포 버전 (Python 3.11) ✨ NEW
├── docker-compose.yml      # 개발 버전 설정
├── docker-compose.prod.yml # 배포 버전 설정 ✨ NEW
├── schedulers/
│   ├── Dockerfile          # 개발용 스케줄러
│   └── Dockerfile.prod     # 배포용 스케줄러 (Python 3.11) ✨ NEW
```

## 빠른 시작

### 1. 개발 버전 계속 실행 (기존)

```bash
# 개발 버전은 그대로 실행
docker-compose up -d

# 포트 13000-13001에서 액세스 가능
# - Frontend: http://localhost:13000
# - Backend: http://localhost:13001
```

### 2. 배포 버전 빌드 및 시작

```bash
# 배포 버전 이미지 빌드 (처음 한 번만)
docker-compose -f docker-compose.prod.yml build

# 배포 버전 컨테이너 시작
docker-compose -f docker-compose.prod.yml up -d

# 포트 14000-14001에서 액세스 가능
# - Frontend: http://localhost:14000
# - Backend: http://localhost:14001
```

### 3. 두 버전 동시 확인

```bash
# 모든 컨테이너 상태 확인
docker ps

# 예상 출력:
# CONTAINER ID  IMAGE                    PORTS                STATUS     NAMES
# xxx           reflex-ksys-app          0.0.0.0:13000->...  Up         reflex-ksys-app
# xxx           forecast-scheduler       ...                  Up         forecast-scheduler
# xxx           data-injector           ...                  Up         data-injector
# xxx           reflex-ksys-app-prod    0.0.0.0:14000->...  Up         reflex-ksys-app-prod
# xxx           forecast-scheduler-prod ...                  Up         forecast-scheduler-prod
```

## 테스트 체크리스트

### 배포 버전 시작 확인

```bash
# 배포 버전 로그 확인
docker logs reflex-ksys-app-prod -f

# 예상 로그:
# 2025-10-20 10:00:00 INFO Reflex app started
# 2025-10-20 10:00:05 INFO Application ready on http://0.0.0.0:13000
```

### 스케줄러 상태 확인

```bash
# 개발 버전 스케줄러
docker logs forecast-scheduler -f

# 배포 버전 스케줄러
docker logs forecast-scheduler-prod -f

# 예상 로그:
# 2025-10-20 10:00:00 INFO Starting schedulers
# 2025-10-20 10:05:00 INFO ForecastScheduler: Running predictions
# 2025-10-20 10:10:00 INFO ActualValueUpdater: Updating values
```

### 데이터베이스 연결 테스트

```bash
# 개발 버전
docker exec reflex-ksys-app python -c "
import asyncio
from ksys_app.db import get_pool
async def test():
    pool = await get_pool()
    print(f'[DEV] Connection successful! Pool: {pool.min_size}-{pool.max_size}')
asyncio.run(test())
"

# 배포 버전
docker exec reflex-ksys-app-prod python -c "
import asyncio
from ksys_app.db import get_pool
async def test():
    pool = await get_pool()
    print(f'[PROD] Connection successful! Pool: {pool.min_size}-{pool.max_size}')
asyncio.run(test())
"
```

### 웹 인터페이스 테스트

1. **개발 버전**: http://localhost:13000
   - 정상 작동하는지 확인
   - 대시보드, 알람, 학습 마법사 등 주요 기능 테스트

2. **배포 버전**: http://localhost:14000
   - Python 3.11에서 정상 작동하는지 확인
   - 개발 버전과 동일한 기능 테스트
   - 성능 비교 (필요시)

### 배포 버전 상태 확인

```bash
# 배포 버전 헬스체크 상태
docker inspect reflex-ksys-app-prod | grep -A 10 '"Health"'

# 예상 출력:
# "Health": {
#   "Status": "healthy",
#   "FailingStreak": 0,
#   "Log": [...]
# }
```

## 리소스 사용량 비교

```bash
# 실시간 모니터링
docker stats reflex-ksys-app reflex-ksys-app-prod forecast-scheduler forecast-scheduler-prod

# 예상 출력:
# CONTAINER             CPU %   MEM USAGE
# reflex-ksys-app       5-10%   800-1000MB
# reflex-ksys-app-prod  5-10%   800-1000MB
# forecast-scheduler    1-2%    300-500MB
# forecast-scheduler-prod 1-2%  300-500MB
```

## 개발 버전과 배포 버전 비교

| 항목 | 개발 버전 | 배포 버전 |
|------|---------|---------|
| Python | 3.13 | 3.11 |
| Base Image | python:3.13-slim | python:3.11-slim |
| Frontend Port | 13000 | 14000 |
| Backend Port | 13001 | 14001 |
| Logs | ./logs | ./logs/prod |
| APP_ENV | development | production |
| Hot Reload | 지원 | 미지원 |
| Data Injector | 활성화 | 비활성화 |

## 문제 해결

### 포트 이미 사용 중

```bash
# 포트 14000 사용 중인 프로세스 찾기 (Windows)
netstat -ano | findstr :14000

# 프로세스 종료 (PID: xxxx)
taskkill /PID xxxx /F

# 또는 docker-compose.prod.yml에서 포트 번호 변경
# ports:
#   - "15000:13000"  # 다른 포트 사용
#   - "15001:13001"
```

### 데이터베이스 연결 실패

```bash
# 데이터베이스 연결 확인
docker exec reflex-ksys-app-prod python -c "
import os
print('TS_DSN:', os.getenv('TS_DSN'))
print('POSTGRES_CONNECTION_STRING:', os.getenv('POSTGRES_CONNECTION_STRING'))
"

# 또는 docker-compose.prod.yml에서 환경변수 업데이트
```

### 컨테이너 시작 실패

```bash
# 배포 버전 컨테이너 로그 확인
docker logs reflex-ksys-app-prod --tail 100

# 빌드 캐시 제거 후 다시 빌드
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### Python 3.11 호환성 문제

만약 배포 버전에서 에러가 발생한다면:

1. 특정 라이브러리가 Python 3.11을 지원하지 않을 수 있음
2. `requirements.txt`의 버전 확인
3. 필요시 `requirements.txt` 업데이트

```bash
# 배포 버전에만 적용되는 requirements 생성 가능
# schedulers/requirements.prod.txt 등으로 분리 가능
```

## 배포 버전 → 프로덕션 전환

배포 버전이 안정적으로 작동하면:

1. **개발 버전 종료**
   ```bash
   docker-compose down
   ```

2. **배포 버전을 메인으로 변경**
   ```bash
   # docker-compose.prod.yml을 docker-compose.yml로 복사
   cp docker-compose.prod.yml docker-compose.yml
   ```

3. **기존 Dockerfile 백업 (선택)**
   ```bash
   mv Dockerfile Dockerfile.dev
   mv Dockerfile.prod Dockerfile
   ```

## 모니터링

### 일반적인 모니터링 명령어

```bash
# 배포 버전의 모든 로그 확인
docker-compose -f docker-compose.prod.yml logs -f

# 특정 서비스만
docker-compose -f docker-compose.prod.yml logs -f reflex-app-prod

# 마지막 100줄만
docker logs reflex-ksys-app-prod --tail 100
```

### 헬스체크 상태

배포 Dockerfile에는 헬스체크가 포함되어 있습니다:

```bash
# 헬스 상태 확인
docker inspect reflex-ksys-app-prod --format='{{.State.Health.Status}}'

# 상태 종류:
# - healthy: 정상
# - unhealthy: 비정상
# - starting: 시작 중
```

## 추가 정보

- 개발 버전 RPI 호환성 이슈: Python 3.13 → 3.11로 다운그레이드
- 배포 버전은 프로덕션 환경 고려 (헬스체크, 로그 분리, 디버깅 비활성화 등)
- 데이터베이스는 공유 (개발/배포 모두 같은 DB 사용 가능)
- 테스트 후 기존 Dockerfile도 Python 3.11로 업데이트 고려

## 다음 단계

1. ✅ 배포 버전 빌드 및 테스트
2. ✅ 기능 검증 (웹 UI, 스케줄러, DB 연결)
3. ✅ 성능 테스트 (CPU, 메모리, 응답시간)
4. ✅ RPI 환경 배포 테스트
5. ✅ 프로덕션 전환

---

생성 날짜: 2025-10-20
테스트 환경: Windows (Docker Desktop)
