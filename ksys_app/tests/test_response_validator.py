"""
ResponseValidator 테스트 케이스
TASK_002: 할루시네이션 방지 메커니즘 테스트
"""

import pytest
import asyncio
from typing import Dict, Any
from datetime import datetime

# 상위 디렉토리의 모듈 import
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from ksys_app.ai_engine.response_validator import (
    ResponseValidator, 
    SensorData, 
    AnalysisResponse
)


class TestResponseValidator:
    """ResponseValidator 테스트 클래스"""
    
    @pytest.fixture
    def validator(self):
        """테스트용 validator 인스턴스"""
        return ResponseValidator()
    
    @pytest.fixture
    def sample_context(self):
        """테스트용 샘플 컨텍스트 데이터"""
        return {
            'current_data': [
                {'tag_name': 'D101', 'value': 25.5, 'ts': '2024-01-15T10:00:00'},
                {'tag_name': 'D201', 'value': 3.2, 'ts': '2024-01-15T10:00:00'},
                {'tag_name': 'D301', 'value': 1500, 'ts': '2024-01-15T10:00:00'}
            ],
            'qc_rules': [
                {
                    'tag_name': 'D101',
                    'min_val': 0,
                    'max_val': 100,
                    'warn_min': 10,
                    'warn_max': 80,
                    'crit_min': 5,
                    'crit_max': 90
                },
                {
                    'tag_name': 'D201',
                    'min_val': 0,
                    'max_val': 10,
                    'warn_min': 1,
                    'warn_max': 8,
                    'crit_min': 0.5,
                    'crit_max': 9
                }
            ],
            'comparison_data': [
                {
                    'tag_name': 'D101',
                    'yesterday_avg': 24.0,
                    'today_avg': 25.5,
                    'avg_change': 1.5,
                    'pct_change': 6.25
                }
            ]
        }
    
    def test_sensor_value_validation_valid(self, validator, sample_context):
        """TEST 1: 정상 센서 값 검증"""
        # 실제 데이터와 일치하는 값
        is_valid, message = validator.validate_sensor_value('D101', 25.5, sample_context)
        assert is_valid == True
        assert message == "Valid"
        
        print("[OK] TEST 1: 정상 센서 값 검증 통과")
    
    def test_sensor_value_validation_mismatch(self, validator, sample_context):
        """TEST 2: 불일치 센서 값 검증"""
        # 실제 데이터와 다른 값
        is_valid, message = validator.validate_sensor_value('D101', 30.0, sample_context)
        assert is_valid == False
        assert "mismatch" in message.lower()
        
        print("[OK] TEST 2: 불일치 센서 값 검증 통과")
    
    def test_hallucination_detection_clean(self, validator, sample_context):
        """TEST 3: 할루시네이션 없는 응답 검증"""
        # 실제 데이터 기반 응답
        response = "센서 D101의 현재 온도는 25.5도이고, D201의 압력은 3.2 bar입니다."
        
        result = validator.detect_hallucination(response, sample_context)
        
        assert result['has_hallucination'] == False
        assert result['confidence'] >= 0.9
        assert 25.5 in result['numbers_found']
        assert 3.2 in result['numbers_found']
        
        print("[OK] TEST 3: 깨끗한 응답 검증 통과")
    
    def test_hallucination_detection_with_fake_data(self, validator, sample_context):
        """TEST 4: 할루시네이션 있는 응답 검증"""
        # 존재하지 않는 큰 숫자 포함
        response = "센서 D101의 온도는 25.5도이며, 시스템 효율은 99999%입니다."
        
        result = validator.detect_hallucination(response, sample_context)
        
        assert result['has_hallucination'] == True
        assert result['confidence'] < 1.0
        assert len(result['issues']) > 0
        assert 99999 in result['numbers_found']
        
        print("[OK] TEST 4: 할루시네이션 감지 통과")
    
    def test_structured_response_creation(self, validator, sample_context):
        """TEST 5: 구조화된 응답 생성"""
        query = "현재 센서 상태를 알려주세요"
        
        response = validator.create_structured_response(query, sample_context)
        
        assert isinstance(response, AnalysisResponse)
        assert response.query_type == 'status'
        assert len(response.sensor_data) == 3
        assert response.has_complete_data == True
        assert response.confidence_score == 1.0
        
        # 센서 데이터 검증
        d101 = next((s for s in response.sensor_data if s.tag_name == 'D101'), None)
        assert d101 is not None
        assert d101.value == 25.5
        assert d101.status == 'normal'
        
        print("[OK] TEST 5: 구조화된 응답 생성 통과")
    
    def test_database_validation(self, validator):
        """TEST 6: DB 데이터 실시간 검증"""
        response = "센서 값은 25.5, 3.2, 1500입니다."
        db_data = [
            {'value': 25.5},
            {'value': 3.2},
            {'value': 1500}
        ]
        
        confidence = validator.validate_with_database(response, db_data)
        
        assert confidence == 1.0  # 모든 값이 일치
        
        # 일부만 일치하는 경우
        response2 = "센서 값은 25.5, 999, 1500입니다."
        confidence2 = validator.validate_with_database(response2, db_data)
        
        assert confidence2 < 1.0  # 일부 불일치
        assert confidence2 > 0.5  # 그래도 일부는 일치
        
        print("[OK] TEST 6: DB 실시간 검증 통과")
    
    def test_comparison_analysis(self, validator, sample_context):
        """TEST 7: 비교 분석 응답 생성"""
        query = "어제와 오늘의 센서 값 변화를 알려줘"
        
        response = validator.create_structured_response(query, sample_context)
        
        assert response.query_type == 'comparison'
        assert "어제 대비" in response.summary or "변화" in response.summary
        
        print("[OK] TEST 7: 비교 분석 통과")
    
    def test_alert_generation(self, validator):
        """TEST 8: 경고 생성 테스트"""
        context = {
            'current_data': [
                {'tag_name': 'D101', 'value': 95, 'ts': '2024-01-15T10:00:00'},  # Critical
                {'tag_name': 'D201', 'value': 8.5, 'ts': '2024-01-15T10:00:00'}  # Warning
            ],
            'qc_rules': [
                {
                    'tag_name': 'D101',
                    'min_val': 0,
                    'max_val': 100,
                    'warn_min': 10,
                    'warn_max': 80,
                    'crit_min': 5,
                    'crit_max': 90
                },
                {
                    'tag_name': 'D201',
                    'min_val': 0,
                    'max_val': 10,
                    'warn_min': 1,
                    'warn_max': 8,
                    'crit_min': 0.5,
                    'crit_max': 9
                }
            ]
        }
        
        query = "경고나 알람 상태인 센서가 있나요?"
        response = validator.create_structured_response(query, context)
        
        assert response.query_type == 'alert'
        assert len(response.alerts) == 2
        assert any('D101' in alert for alert in response.alerts)
        assert any('위험' in alert for alert in response.alerts)
        assert any('주의' in alert for alert in response.alerts)
        
        print("[OK] TEST 8: 경고 생성 통과")
    
    def test_confidence_threshold(self, validator):
        """TEST 9: 신뢰도 임계값 테스트"""
        # 신뢰도 임계값 설정
        assert validator.confidence_threshold == 0.7
        
        # 낮은 신뢰도 응답
        context = {'current_data': []}  # 빈 데이터
        response = validator.create_structured_response("센서 상태", context)
        
        assert response.confidence_score == 0.0  # 데이터 없음
        assert response.data_source == 'none'
        
        print("[OK] TEST 9: 신뢰도 임계값 통과")
    
    def test_number_extraction(self, validator):
        """TEST 10: 숫자 추출 기능 테스트"""
        text1 = "온도는 25.5도, 압력은 -3.2 bar입니다."
        numbers1 = validator.extract_numbers_from_text(text1)
        assert 25.5 in numbers1
        assert -3.2 in numbers1
        
        text2 = "센서 D101: 100%, D201: 50.25"
        numbers2 = validator.extract_numbers_from_text(text2)
        assert 101 in numbers2  # D101의 101
        assert 100 in numbers2
        assert 201 in numbers2  # D201의 201
        assert 50.25 in numbers2
        
        print("[OK] TEST 10: 숫자 추출 통과")


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("ResponseValidator 테스트 시작")
    print("=" * 60)
    
    # pytest 실행
    pytest.main([__file__, '-v', '--tb=short'])
    
    print("\n" + "=" * 60)
    print("모든 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()