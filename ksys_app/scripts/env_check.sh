#!/bin/bash
echo "🔍 환경 설정 확인..."

# Python 버전 확인
echo "🐍 Python: $(python3 --version)"

# 가상환경 확인
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "❌ 가상환경이 활성화되지 않음"
    echo "   실행: source venv/bin/activate"
else
    echo "✅ 가상환경: $VIRTUAL_ENV"
fi

# 핵심 패키지 확인
echo "📦 패키지 확인:"
python3 -c "
try:
    import reflex; print('✅ Reflex:', reflex.__version__)
except: print('❌ Reflex 없음')

try:
    import psycopg; print('✅ psycopg 설치됨')
except: print('❌ psycopg 없음')

try:
    import pytest; print('✅ pytest 설치됨')
except: print('❌ pytest 없음')
"

# 환경변수 확인
if [ -f ".env" ]; then
    echo "✅ .env 파일 존재"
else
    echo "❌ .env 파일 없음"
    echo "   실행: cp .env.example .env"
fi

# DB 연결 테스트
echo "🗄️  DB 연결 테스트:"
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
dsn = os.getenv('TS_DSN')
if dsn:
    print('✅ TS_DSN 설정됨')
    try:
        import psycopg
        conn = psycopg.connect(dsn, connect_timeout=3)
        print('✅ DB 연결 성공')
        conn.close()
    except Exception as e:
        print(f'❌ DB 연결 실패: {e}')
else:
    print('❌ TS_DSN 환경변수 없음')
"
