#!/bin/bash
echo "🚀 빠른 테스트 시작..."

# 가상환경 활성화 확인
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  가상환경을 먼저 활성화하세요: source venv/bin/activate"
    exit 1
fi

# 최신 코드 가져오기
echo "📥 최신 코드 가져오는 중..."
git pull origin main

# 보안 검증
echo "🛡️  보안 검증 중..."
python3 ksys_app/security.py

# 테스트 실행
echo "🧪 테스트 실행 중..."
python3 -m pytest tests/ -v --tb=short

echo "✅ 테스트 완료!"
