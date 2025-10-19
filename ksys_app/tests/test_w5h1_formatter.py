"""
6하원칙 포맷터 테스트
TASK_004 검증
"""

import asyncio
import sys
import os

# Windows asyncio 이벤트 루프 문제 해결
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ksys_app.ai_engine.w5h1_formatter import W5H1Formatter, W5H1Response
from ksys_app.ai_engine.w5h1_knowledge_retriever import W5H1KnowledgeRetriever


async def test_w5h1_formatter():
    """6하원칙 포맷터 테스트"""
    
    print("=" * 50)
    print("6하원칙 포맷터 테스트")
    print("=" * 50)
    
    formatter = W5H1Formatter()
    
    # 테스트 1: 질문 분석
    print("\n1. 질문 분석 테스트:")
    test_questions = [
        "온도 센서 D101의 현재 값은 무엇인가요?",
        "왜 압력이 높아졌나요?",
        "언제 정비를 해야 하나요?",
        "어디서 문제가 발생했나요?",
        "누가 담당자인가요?",
        "어떻게 해결해야 하나요?"
    ]
    
    for question in test_questions:
        needs = formatter.analyze_question(question)
        active_needs = [k for k, v in needs.items() if v]
        print(f"   Q: {question[:30]}...")
        print(f"      필요한 요소: {', '.join(active_needs)}")
    
    # 테스트 2: W5H1Response 생성
    print("\n2. W5H1Response 생성 테스트:")
    response = W5H1Response(
        what="온도 센서 D101의 현재 값은 25.3°C입니다",
        why="정상 작동 범위 내에 있습니다",
        when="2025-09-08 01:00:00",
        where="RO 시스템 입구",
        who="시스템 자동 모니터링",
        how="RTD 센서를 통한 실시간 측정",
        confidence=0.95,
        sources=["센서 데이터", "QC 규칙"]
    )
    
    print("   JSON 형식:")
    print(response.to_json()[:200] + "...")
    
    print("\n   텍스트 형식:")
    print(response.to_text()[:200] + "...")
    
    # 테스트 3: 텍스트에서 추출
    print("\n3. 텍스트에서 6하원칙 정보 추출:")
    test_text = """
    센서 D101의 온도가 25.3°C를 기록했습니다.
    이는 정상 범위입니다.
    2025-09-08 01:00:00에 측정되었습니다.
    RO 시스템 입구에 위치한 센서입니다.
    RTD 방식으로 측정합니다.
    """
    
    extracted = formatter.extract_from_text(test_text)
    print(f"   추출된 What: {extracted.what[:50] if extracted.what else 'None'}")
    print(f"   추출된 When: {extracted.when[:50] if extracted.when else 'None'}")
    print(f"   추출된 Where: {extracted.where[:50] if extracted.where else 'None'}")
    
    # 테스트 4: 템플릿 적용
    print("\n4. 도메인 템플릿 적용:")
    sensor_data = {
        'tag_name': 'D101',
        'value': '25.3',
        'unit': '°C',
        'purpose': '입구 온도 모니터링',
        'timestamp': '2025-09-08 01:00:00',
        'location': 'RO 시스템 입구',
        'method': 'RTD'
    }
    
    templated = formatter.apply_template('sensor', sensor_data)
    print(f"   What: {templated.what}")
    print(f"   Why: {templated.why}")
    print(f"   How: {templated.how}")
    
    # 테스트 5: 응답 병합
    print("\n5. 응답 병합 테스트:")
    response1 = W5H1Response(what="센서 값 25°C", when="01:00")
    response2 = W5H1Response(what="센서 값 26°C", where="RO 입구")
    
    merged = formatter.merge_responses(response1, response2)
    print(f"   병합된 What: {merged.what}")
    print(f"   병합된 When: {merged.when}")
    print(f"   병합된 Where: {merged.where}")
    
    print("\n" + "=" * 50)
    print("포맷터 테스트 완료")


async def test_w5h1_retriever():
    """6하원칙 지식 검색 테스트"""
    
    print("\n" + "=" * 50)
    print("6하원칙 지식 검색 테스트")
    print("=" * 50)
    
    db_dsn = "postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable"
    retriever = W5H1KnowledgeRetriever(db_dsn)
    
    # 테스트 1: 일반 검색
    print("\n1. 일반 검색 테스트:")
    results = await retriever.get_w5h1_knowledge(query="온도", limit=3)
    
    for i, result in enumerate(results, 1):
        print(f"\n   결과 {i}:")
        print(f"      Content: {result['content'][:50]}...")
        print(f"      Type: {result['content_type']}")
        w5h1 = result.get('w5h1_data', {})
        if w5h1:
            print(f"      What: {w5h1.get('what', 'N/A')[:30]}...")
    
    # 테스트 2: 태그 검색
    print("\n2. 태그 검색 테스트:")
    tag_results = await retriever.get_w5h1_by_tags(['temperature', 'sensor'], limit=2)
    
    for i, result in enumerate(tag_results, 1):
        print(f"\n   결과 {i}:")
        print(f"      Tags: {', '.join(result['tags'])}")
        print(f"      Priority: {result['priority']}")
    
    # 테스트 3: 데이터 병합
    print("\n3. 6하원칙 데이터 병합:")
    if results:
        merged = await retriever.merge_w5h1_data(results)
        print(f"   병합된 What: {merged.get('what', 'N/A')[:50] if merged.get('what') else 'N/A'}...")
        print(f"   병합된 Why: {merged.get('why', 'N/A')[:50] if merged.get('why') else 'N/A'}...")
    
    print("\n" + "=" * 50)
    print("검색 테스트 완료")


async def main():
    """메인 테스트 실행"""
    
    # 포맷터 테스트
    await test_w5h1_formatter()
    
    # 검색기 테스트
    try:
        await test_w5h1_retriever()
    except Exception as e:
        print(f"\n검색기 테스트 실패 (DB 연결 문제일 수 있음): {e}")
    
    print("\n" + "=" * 50)
    print("모든 테스트 완료!")


if __name__ == "__main__":
    asyncio.run(main())