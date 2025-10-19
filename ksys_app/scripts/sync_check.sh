#!/bin/bash
# Git 동기화 상태 확인 스크립트

echo "🔍 Git 동기화 상태 확인..."

# 현재 브랜치 확인
current_branch=$(git branch --show-current)
echo "📍 현재 브랜치: $current_branch"

# 원격 저장소 최신 정보 가져오기
echo "🌐 원격 저장소 정보 업데이트 중..."
git fetch origin

# 로컬과 원격 차이 확인
behind=$(git rev-list --count HEAD..origin/$current_branch 2>/dev/null || echo "0")
ahead=$(git rev-list --count origin/$current_branch..HEAD 2>/dev/null || echo "0")

echo ""
echo "📊 동기화 상태:"
echo "   로컬이 원격보다 $behind 커밋 뒤처짐"
echo "   로컬이 원격보다 $ahead 커밋 앞섬"

# 상태에 따른 권장 조치
if [ "$behind" -gt 0 ] && [ "$ahead" -gt 0 ]; then
    echo ""
    echo "⚠️  충돌 가능성 있음!"
    echo "   권장 조치: git pull origin $current_branch (충돌 해결 필요할 수 있음)"
elif [ "$behind" -gt 0 ]; then
    echo ""
    echo "📥 원격에 새로운 변경사항 있음"
    echo "   권장 조치: git pull origin $current_branch"
elif [ "$ahead" -gt 0 ]; then
    echo ""
    echo "📤 로컬에 푸시할 변경사항 있음"
    echo "   권장 조치: git push origin $current_branch"
else
    echo ""
    echo "✅ 완전히 동기화됨"
fi

# 로컬 변경사항 확인
modified_files=$(git status --porcelain | wc -l)
if [ "$modified_files" -gt 0 ]; then
    echo ""
    echo "📝 로컬 변경사항: $modified_files 개 파일"
    echo "   수정된 파일들:"
    git status --porcelain | head -10
fi

echo ""
echo "🕒 마지막 커밋: $(git log -1 --pretty=format:'%h - %s (%ar)')"
