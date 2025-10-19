"""
할루시네이션 방지 메커니즘
TASK_002: AI_FIX_HALLUCINATION
"""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import psycopg
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """검증 결과 데이터 클래스"""
    is_valid: bool
    confidence: float
    issues: List[str]
    suggestions: List[str]
    metadata: Dict[str, Any]

class HallucinationPrevention:
    """할루시네이션 방지 시스템"""
    
    def __init__(self, db_connection_string: str):
        self.db_dsn = db_connection_string
        self.fact_patterns = {
            # 센서 범위 패턴
            'sensor_range': r'[A-Z]\d{3,4}',
            # 숫자 값 패턴
            'numeric_value': r'-?\d+\.?\d*',
            # 단위 패턴
            'units': r'(°C|bar|μS/cm|m³/h|ppm|pH|%|L/min|mm/s)',
            # 날짜/시간 패턴
            'datetime': r'\d{4}-\d{2}-\d{2}|\d{2}:\d{2}',
        }
        
        # 센서 타입과 올바른 단위 매핑
        self.sensor_type_units = {
            'D100': {'type': 'temperature', 'units': ['°C', '도', 'celsius']},
            'D101': {'type': 'pressure', 'units': ['bar', '압력']},
            'D102': {'type': 'flow', 'units': ['L/min', '유량']},
            'D200': {'type': 'vibration', 'units': ['mm/s', '진동']},
            'D300': {'type': 'power', 'units': ['%', '전력', 'percent']}
        }
        
    async def validate_response(self, 
                               response: str, 
                               context: Dict[str, Any],
                               knowledge_base_ids: List[int] = None) -> ValidationResult:
        """
        AI 응답 검증
        
        Args:
            response: AI가 생성한 응답
            context: 응답 생성 시 사용된 컨텍스트
            knowledge_base_ids: 참조한 지식 베이스 ID 목록
            
        Returns:
            ValidationResult: 검증 결과
        """
        issues = []
        suggestions = []
        confidence = 1.0
        
        # 1. 팩트 체크 - 지식 베이스와 대조
        if knowledge_base_ids:
            fact_check = await self._check_against_knowledge_base(
                response, knowledge_base_ids
            )
            if not fact_check['is_consistent']:
                issues.append(f"지식 베이스와 불일치: {fact_check['mismatch']}")
                confidence *= 0.5
                suggestions.append("지식 베이스 내용을 다시 확인하세요")
        
        # 2. 숫자 일관성 검증
        numeric_check = self._validate_numeric_consistency(response)
        if not numeric_check['is_valid']:
            issues.extend(numeric_check['issues'])
            confidence *= 0.7
            suggestions.extend(numeric_check['suggestions'])
        
        # 3. 센서 범위 검증
        sensor_check = await self._validate_sensor_ranges(response)
        if not sensor_check['is_valid']:
            issues.extend(sensor_check['issues'])
            confidence *= 0.8
            suggestions.append("센서 스펙을 확인하세요")
        
        # 3.5. 센서 타입-단위 일치성 검증
        unit_check = self._validate_sensor_unit_consistency(response)
        if not unit_check['is_valid']:
            issues.extend(unit_check['issues'])
            confidence *= 0.5
            suggestions.extend(unit_check['suggestions'])
        
        # 4. 시간 정보 일관성
        time_check = self._validate_temporal_consistency(response, context)
        if not time_check['is_valid']:
            issues.append(time_check['issue'])
            confidence *= 0.9
        
        # 5. 논리적 모순 검사
        logic_check = self._check_logical_contradictions(response)
        if logic_check['has_contradiction']:
            issues.append(f"논리적 모순: {logic_check['contradiction']}")
            confidence *= 0.6
            suggestions.append("응답 내용의 논리적 일관성을 재검토하세요")
        
        # 6. 확실성 표현 검사
        certainty_check = self._check_certainty_expressions(response)
        if certainty_check['overconfident']:
            issues.append("과도한 확신 표현 감지")
            suggestions.append("불확실한 부분은 명시적으로 표현하세요")
            confidence *= 0.85
        
        is_valid = len(issues) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            issues=issues,
            suggestions=suggestions,
            metadata={
                'timestamp': datetime.now().isoformat(),
                'checks_performed': [
                    'fact_check', 'numeric_check', 'sensor_check',
                    'time_check', 'logic_check', 'certainty_check'
                ]
            }
        )
    
    async def _check_against_knowledge_base(self, 
                                           response: str, 
                                           kb_ids: List[int]) -> Dict[str, Any]:
        """지식 베이스와 응답 내용 대조"""
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 참조한 지식 베이스 내용 가져오기
                    await cur.execute("""
                        SELECT id, content, w5h1_data, metadata
                        FROM ai_knowledge_base
                        WHERE id = ANY(%s)
                    """, (kb_ids,))
                    
                    kb_contents = await cur.fetchall()
                    
                    # 응답과 지식 베이스 내용 비교
                    for kb_id, content, w5h1_data, metadata in kb_contents:
                        # 숫자 값 비교
                        kb_numbers = re.findall(self.fact_patterns['numeric_value'], content)
                        resp_numbers = re.findall(self.fact_patterns['numeric_value'], response)
                        
                        # 큰 차이가 있는지 확인
                        for kb_num in kb_numbers:
                            kb_val = float(kb_num)
                            for resp_num in resp_numbers:
                                resp_val = float(resp_num)
                                if abs(kb_val) > 0.01:  # 0이 아닌 경우
                                    diff_ratio = abs(kb_val - resp_val) / abs(kb_val)
                                    if diff_ratio > 0.5:  # 50% 이상 차이
                                        return {
                                            'is_consistent': False,
                                            'mismatch': f"값 불일치: KB({kb_val}) vs Response({resp_val})"
                                        }
                    
                    return {'is_consistent': True, 'mismatch': None}
                    
        except Exception as e:
            print(f"지식 베이스 체크 오류: {e}")
            return {'is_consistent': True, 'mismatch': None}  # 오류 시 통과
    
    def _validate_numeric_consistency(self, response: str) -> Dict[str, Any]:
        """숫자 일관성 검증"""
        issues = []
        suggestions = []
        
        # 온도 범위 체크
        temp_matches = re.findall(r'(-?\d+\.?\d*)\s*°C', response)
        for temp in temp_matches:
            temp_val = float(temp)
            if temp_val < -273.15:  # 절대영도 이하
                issues.append(f"불가능한 온도: {temp_val}°C")
                suggestions.append("온도는 -273.15°C (절대영도) 이상이어야 합니다")
            elif temp_val > 1000:  # 비현실적으로 높은 온도
                issues.append(f"비현실적인 온도: {temp_val}°C")
                suggestions.append("담수화 플랜트 운영 온도 범위를 확인하세요")
        
        # 압력 범위 체크
        pressure_matches = re.findall(r'(\d+\.?\d*)\s*bar', response)
        for pressure in pressure_matches:
            pressure_val = float(pressure)
            if pressure_val < 0:
                issues.append(f"음수 압력: {pressure_val} bar")
            elif pressure_val > 100:  # RO 시스템 일반 한계
                issues.append(f"비현실적인 압력: {pressure_val} bar")
                suggestions.append("RO 시스템 압력은 일반적으로 100 bar 이하입니다")
        
        # pH 범위 체크
        ph_matches = re.findall(r'pH\s*[:=]?\s*(\d+\.?\d*)', response)
        for ph in ph_matches:
            ph_val = float(ph)
            if ph_val < 0 or ph_val > 14:
                issues.append(f"불가능한 pH: {ph_val}")
                suggestions.append("pH는 0-14 범위여야 합니다")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'suggestions': suggestions
        }
    
    async def _validate_sensor_ranges(self, response: str) -> Dict[str, Any]:
        """센서 범위 검증"""
        issues = []
        
        # 센서 ID 추출
        sensor_ids = re.findall(self.fact_patterns['sensor_range'], response)
        
        if sensor_ids:
            try:
                async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                    async with conn.cursor() as cur:
                        # QC 룰에서 센서 범위 확인
                        for sensor_id in sensor_ids:
                            await cur.execute("""
                                SELECT min_val, max_val 
                                FROM influx_qc_rule
                                WHERE tag_name = %s
                            """, (sensor_id,))
                            
                            result = await cur.fetchone()
                            if not result:
                                issues.append(f"알 수 없는 센서: {sensor_id}")
                            
            except Exception as e:
                print(f"센서 범위 검증 오류: {e}")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues
        }
    
    def _validate_temporal_consistency(self, 
                                      response: str, 
                                      context: Dict[str, Any]) -> Dict[str, Any]:
        """시간 정보 일관성 검증"""
        # 미래 시간 참조 체크
        future_patterns = [
            r'내일', r'다음 주', r'다음 달', r'내년',
            r'will be', r'going to', r'예정'
        ]
        
        # 현재 컨텍스트가 과거 데이터인 경우
        if context.get('is_historical', False):
            for pattern in future_patterns:
                if re.search(pattern, response, re.IGNORECASE):
                    return {
                        'is_valid': False,
                        'issue': "과거 데이터에 대해 미래 시제 사용"
                    }
        
        return {'is_valid': True, 'issue': None}
    
    def _check_logical_contradictions(self, response: str) -> Dict[str, Any]:
        """논리적 모순 검사"""
        contradictions = []
        
        # 증가/감소 모순
        if '증가' in response and '감소' in response:
            # 같은 대상에 대한 모순인지 확인
            sentences = response.split('.')
            for sentence in sentences:
                if '증가' in sentence and '감소' in sentence:
                    contradictions.append("같은 문장에서 증가와 감소를 동시에 언급")
        
        # 정상/비정상 모순
        if '정상' in response and '비정상' in response:
            # 컨텍스트 확인 필요
            normal_context = response[max(0, response.find('정상')-30):response.find('정상')+30]
            abnormal_context = response[max(0, response.find('비정상')-30):response.find('비정상')+30]
            
            # 같은 대상인지 간단히 체크
            if any(word in normal_context and word in abnormal_context 
                   for word in ['센서', '압력', '온도', '유량']):
                contradictions.append("같은 항목에 대해 정상과 비정상을 동시에 언급")
        
        return {
            'has_contradiction': len(contradictions) > 0,
            'contradiction': '; '.join(contradictions) if contradictions else None
        }
    
    def _check_certainty_expressions(self, response: str) -> Dict[str, Any]:
        """확실성 표현 검사"""
        # 과도한 확신 표현
        overconfident_phrases = [
            '반드시', '절대적으로', '100%', '확실히', '의심의 여지없이',
            '무조건', '틀림없이', '분명히'
        ]
        
        # 적절한 불확실성 표현
        uncertainty_phrases = [
            '추정', '예상', '가능성', '일반적으로', '대체로',
            '약', '대략', '정도', '것으로 보임'
        ]
        
        overconfident_count = sum(1 for phrase in overconfident_phrases if phrase in response)
        uncertainty_count = sum(1 for phrase in uncertainty_phrases if phrase in response)
        
        # 과도한 확신만 있고 불확실성 표현이 없는 경우
        is_overconfident = overconfident_count > 2 and uncertainty_count == 0
        
        return {
            'overconfident': is_overconfident,
            'confidence_ratio': overconfident_count / max(uncertainty_count, 1)
        }
    
    async def enhance_response_with_disclaimer(self, 
                                              response: str,
                                              validation_result: ValidationResult) -> str:
        """검증 결과에 따라 응답에 주의사항 추가"""
        if validation_result.confidence < 0.8:
            disclaimer = "\n\n⚠️ 주의: "
            
            if validation_result.confidence < 0.5:
                disclaimer += "이 응답은 확인이 필요한 내용을 포함하고 있습니다. "
            else:
                disclaimer += "일부 내용은 추가 검증이 필요할 수 있습니다. "
            
            if validation_result.suggestions:
                disclaimer += f"참고사항: {', '.join(validation_result.suggestions[:2])}"
            
            return response + disclaimer
        
        return response
    
    def _validate_sensor_unit_consistency(self, response: str) -> Dict[str, Any]:
        """센서 타입과 단위의 일치성 검증"""
        issues = []
        suggestions = []
        
        # 각 센서에 대해 검증
        for sensor_id, info in self.sensor_type_units.items():
            if sensor_id in response:
                # 센서 언급 부분의 컨텍스트 추출 (앞뒤 50자)
                import re
                pattern = f'{sensor_id}.{{0,50}}'
                contexts = re.findall(pattern, response)
                
                for context in contexts:
                    # 잘못된 단위 사용 검출
                    wrong_units = []
                    
                    # 온도 센서인데 압력 단위 사용
                    if info['type'] == 'temperature' and 'bar' in context:
                        wrong_units.append('bar')
                    
                    # 압력 센서인데 온도 단위 사용
                    if info['type'] == 'pressure' and ('°C' in context or '도' in context):
                        wrong_units.append('°C')
                    
                    # 유량 센서인데 다른 단위 사용
                    if info['type'] == 'flow' and ('°C' in context or 'bar' in context):
                        wrong_units.append('incorrect unit')
                    
                    if wrong_units:
                        issues.append(f"{sensor_id}({info['type']})에 잘못된 단위 사용: {', '.join(wrong_units)}")
                        correct_units = ', '.join(info['units'])
                        suggestions.append(f"{sensor_id}는 {info['type']} 센서이므로 {correct_units} 단위를 사용하세요")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'suggestions': suggestions
        }
    
    def get_confidence_level(self, score: float) -> str:
        """신뢰도 점수를 레벨로 변환"""
        if score >= 0.9:
            return "매우 높음"
        elif score >= 0.7:
            return "높음"
        elif score >= 0.5:
            return "보통"
        elif score >= 0.3:
            return "낮음"
        else:
            return "매우 낮음"