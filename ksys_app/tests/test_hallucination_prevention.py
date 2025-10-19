"""
할루시네이션 방지 시스템 테스트
TASK_002 검증
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ksys_app.ai_engine.hallucination_prevention import HallucinationPrevention, ValidationResult


# pytest 없이 작동하도록 주석 처리
# class TestHallucinationPrevention는 pytest 필요 시 사용


# 실행 테스트
async def run_manual_test():
    """수동 테스트 실행"""
    print("=" * 50)
    print("할루시네이션 방지 시스템 수동 테스트")
    print("=" * 50)
    
    db_dsn = "postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable"
    prevention = HallucinationPrevention(db_dsn)
    
    test_responses = [
        "온도가 -400°C로 측정되었습니다",
        "pH가 7.2로 정상 범위입니다",
        "압력이 증가하면서 동시에 감소하고 있습니다",
        "반드시 100% 절대적으로 고장입니다",
        "약 25°C 정도로 추정되며, 대체로 정상 범위로 보입니다"
    ]
    
    for i, response in enumerate(test_responses, 1):
        print(f"\n테스트 {i}: {response[:50]}...")
        result = await prevention.validate_response(response, {})
        
        print(f"  유효성: {result.is_valid}")
        print(f"  신뢰도: {result.confidence:.2f} ({prevention.get_confidence_level(result.confidence)})")
        
        if result.issues:
            print(f"  이슈: {', '.join(result.issues)}")
        
        if result.suggestions:
            print(f"  제안: {', '.join(result.suggestions)}")
        
        if result.confidence < 0.7:
            enhanced = await prevention.enhance_response_with_disclaimer(response, result)
            disclaimer = enhanced[len(response):]
            print(f"  보정된 응답: {disclaimer.encode('utf-8', 'ignore').decode('cp949', 'ignore')}")
    
    print("\n" + "=" * 50)
    print("테스트 완료")


if __name__ == "__main__":
    # 수동 테스트 실행
    asyncio.run(run_manual_test())