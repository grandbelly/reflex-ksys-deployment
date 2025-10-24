# Reflex 앱을 위한 Dockerfile
FROM python:3.11-slim

# 작업 디렉터리 설정
WORKDIR /app

# Docker 컨테이너 환경 표시
ENV DOCKER_CONTAINER=true

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Node.js 설치 (Reflex 프론트엔드용)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 파일 복사
COPY . .

# Reflex 초기화 (ARM64에서 crash하므로 주석 처리)
# RUN reflex init --loglevel debug || true

# 포트 노출 (14000: 프론트엔드, 14001: 백엔드)
EXPOSE 14000 14001

# 앱 실행 (포트 명시적 지정)
CMD ["reflex", "run", "--env", "prod", "--backend-host", "0.0.0.0", "--frontend-port", "14000", "--backend-port", "14001"]
