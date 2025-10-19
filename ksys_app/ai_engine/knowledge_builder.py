"""
AI Knowledge Base Builder
센서 도메인 지식을 데이터베이스에 구축하는 모듈
"""

import asyncio
from typing import List, Dict, Any
from ..db import q


# 센서 도메인 지식 데이터
SENSOR_KNOWLEDGE_BASE = [
    # 센서 사양 정보 - 실제 산업용 센서 범위로 수정
    {
        "content": "D100은 온도 센서로 정상 범위는 100-200도이며, 250도 초과시 냉각 시스템 긴급 점검이 필요합니다",
        "content_type": "sensor_spec",
        "metadata": {
            "sensor_tag": "D100",
            "sensor_type": "temperature", 
            "normal_range": [100, 200],
            "unit": "celsius",
            "warning_threshold": 220,
            "critical_threshold": 250
        }
    },
    {
        "content": "D101은 압력 센서로 정상 범위는 80-150 bar이며, 급격한 압력 변화(±20 bar/min)는 누출을 의미할 수 있습니다",
        "content_type": "sensor_spec",
        "metadata": {
            "sensor_tag": "D101",
            "sensor_type": "pressure",
            "normal_range": [80, 150], 
            "unit": "bar",
            "warning_threshold": 180,
            "critical_threshold": 200,
            "warning_conditions": ["rapid_change", "leak_detection"]
        }
    },
    {
        "content": "D102는 유량 센서로 정상 범위는 0-100 L/min이며, 유량 감소시 필터 교체를 확인하세요",
        "content_type": "sensor_spec", 
        "metadata": {
            "sensor_tag": "D102",
            "sensor_type": "flow",
            "normal_range": [0, 100],
            "unit": "L/min",
            "maintenance_action": "filter_replacement"
        }
    },
    {
        "content": "D200 시리즈는 진동 센서로 0.5mm/s 이하가 정상이며, 1.0mm/s 초과시 베어링 점검이 필요합니다",
        "content_type": "sensor_spec",
        "metadata": {
            "sensor_tag": "D200",
            "sensor_type": "vibration",
            "normal_threshold": 0.5,
            "unit": "mm/s", 
            "critical_threshold": 1.0,
            "maintenance_action": "bearing_check"
        }
    },
    {
        "content": "D300 시리즈는 전력 센서로 정상 범위는 80-120%이며, 효율성 모니터링에 사용됩니다",
        "content_type": "sensor_spec",
        "metadata": {
            "sensor_tag": "D300",
            "sensor_type": "power",
            "normal_range": [80, 120],
            "unit": "percent",
            "purpose": "efficiency_monitoring"
        }
    },
    
    # 트러블슈팅 지식
    {
        "content": "센서 값이 30분 이상 변화가 없으면 통신 장애일 가능성이 높습니다. 네트워크 연결과 센서 전원을 확인하세요",
        "content_type": "troubleshooting",
        "metadata": {
            "issue_type": "communication_failure",
            "symptom": "no_data_change_30min",
            "actions": ["check_network", "check_power"]
        }
    },
    {
        "content": "온도 센서가 급격히 상승하면 냉각 시스템 고장 가능성이 있습니다. 즉시 현장 점검하세요",
        "content_type": "troubleshooting", 
        "metadata": {
            "issue_type": "cooling_system_failure",
            "sensor_type": "temperature",
            "symptom": "rapid_temperature_rise",
            "urgency": "immediate"
        }
    },
    {
        "content": "압력 센서에서 압력 강하가 지속되면 배관 누출을 의심해야 합니다. 시각적 점검을 실시하세요",
        "content_type": "troubleshooting",
        "metadata": {
            "issue_type": "pipe_leakage", 
            "sensor_type": "pressure",
            "symptom": "pressure_drop",
            "action": "visual_inspection"
        }
    },
    
    # 운영 패턴
    {
        "content": "여름철(6-8월)에는 온도 센서가 평소보다 5-10% 높게 측정되는 것이 정상입니다",
        "content_type": "operational_pattern",
        "metadata": {
            "season": "summer",
            "months": [6, 7, 8],
            "sensor_type": "temperature", 
            "expected_deviation": [5, 10],
            "unit": "percent"
        }
    },
    {
        "content": "주간 운전시간(08:00-18:00)에는 센서 값이 20-30% 높게 나타나는 것이 정상적인 운전 패턴입니다",
        "content_type": "operational_pattern",
        "metadata": {
            "time_period": "daytime",
            "hours": [8, 18],
            "expected_increase": [20, 30],
            "unit": "percent"
        }
    },
    
    # 유지보수 지침
    {
        "content": "정기 점검은 매월 첫째 주에 실시하며, D100 시리즈 온도 센서는 분기별 교정이 필요합니다",
        "content_type": "maintenance",
        "metadata": {
            "schedule": "monthly_first_week",
            "sensor_series": "D100",
            "calibration_frequency": "quarterly"
        }
    },
    {
        "content": "경고 상태가 24시간 이상 지속되면 즉시 현장 점검을 실시하고 유지보수팀에 연락하세요",
        "content_type": "maintenance", 
        "metadata": {
            "condition": "warning_24hours",
            "action": "field_inspection",
            "escalation": "maintenance_team"
        }
    },
    {
        "content": "센서 교체 후에는 2주간 모니터링 기간을 두고 정상 동작을 확인해야 합니다",
        "content_type": "maintenance",
        "metadata": {
            "post_replacement": "2weeks_monitoring",
            "verification": "normal_operation"
        }
    },
    
    # 상관관계 분석
    {
        "content": "D100 온도 센서와 D101 압력 센서는 독립적으로 작동하며, 각각 다른 공정 파라미터를 측정합니다",
        "content_type": "correlation",
        "metadata": {
            "sensor1": "D100",
            "sensor2": "D101",
            "relationship": "independent",
            "note": "온도와 압력은 서로 다른 물리량으로 직접적인 상관관계가 없습니다"
        }
    },
    {
        "content": "D101 압력 센서와 D102 유량 센서는 서로 연동되어 작동하므로 하나에 이상이 있으면 다른 센서도 확인하세요",
        "content_type": "correlation",
        "metadata": {
            "primary_sensor": "D101", 
            "secondary_sensor": "D102",
            "relationship": "pressure_flow_correlation"
        }
    },
    {
        "content": "D200 진동 센서와 D300 전력 센서는 장비 효율성과 직접적으로 연관되어 있습니다",
        "content_type": "correlation",
        "metadata": {
            "sensor1": "D200",
            "sensor2": "D300", 
            "correlation_type": "efficiency_monitoring"
        }
    }
]


async def build_knowledge_base() -> int:
    """지식베이스를 데이터베이스에 구축"""
    
    # 기존 데이터 삭제 (재구축) - DELETE는 결과를 반환하지 않으므로 execute 사용
    from ..db import execute_query
    await execute_query("DELETE FROM ai_engine.knowledge_base", ())
    
    inserted_count = 0
    
    for knowledge in SENSOR_KNOWLEDGE_BASE:
        try:
            import json
            sql = """
                INSERT INTO ai_engine.knowledge_base (content, content_type, metadata) 
                VALUES (%s, %s, %s)
            """
            params = (
                knowledge["content"],
                knowledge["content_type"], 
                json.dumps(knowledge["metadata"])
            )
            
            await execute_query(sql, params)
            inserted_count += 1
            
        except Exception as e:
            print(f"지식 삽입 실패: {knowledge['content'][:50]}... - {e}")
            continue
    
    print(f"[OK] 지식베이스 구축 완료: {inserted_count}개 항목")
    return inserted_count


async def search_knowledge(query: str, content_types: List[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """지식베이스에서 텍스트 검색 (전체 텍스트 검색)"""
    
    where_clause = "to_tsvector('english', content) @@ plainto_tsquery('english', %s)"
    params = [query]
    
    if content_types:
        placeholders = ','.join(['%s'] * len(content_types))
        where_clause += f" AND content_type IN ({placeholders})"
        params.extend(content_types)
    
    sql = f"""
        SELECT 
            id, content, content_type, metadata, created_at,
            ts_rank(to_tsvector('english', content), plainto_tsquery('english', %s)) as relevance
        FROM ai_engine.knowledge_base 
        WHERE {where_clause}
        ORDER BY relevance DESC, created_at DESC
        LIMIT %s
    """
    
    params = [query] + params + [limit]
    
    try:
        results = await q(sql, params)
        return results or []
    except Exception as e:
        print(f"지식 검색 실패: {e}")
        return []


async def get_sensor_knowledge(sensor_tag: str) -> List[Dict[str, Any]]:
    """특정 센서에 대한 지식 조회"""
    print(f"\n[KNOWLEDGE] get_sensor_knowledge: sensor_tag='{sensor_tag}'")
    sql = """
        SELECT id, sensor_tag, sensor_type, content, normal_range, thresholds, maintenance_info, created_at
        FROM ai_engine.sensor_knowledge
        WHERE sensor_tag = %s
        ORDER BY created_at DESC
    """
    
    params = [sensor_tag]
    print(f"   검색 파라미터: {sensor_tag}")
    
    try:
        results = await q(sql, params)
        print(f"   결과: {len(results) if results else 0}개")
        if results:
            for r in results[:2]:  # 처음 2개만 로그
                print(f"   - ID {r['id']}: {r['content_type']}, {r['content'][:50]}...")
        return results or []
    except Exception as e:
        print(f"[ERROR] [KNOWLEDGE] get_sensor_knowledge 실패: {e}")
        return []


if __name__ == "__main__":
    # 지식베이스 구축 실행
    asyncio.run(build_knowledge_base())