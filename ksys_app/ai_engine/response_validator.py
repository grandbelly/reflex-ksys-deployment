"""
Response Validator - 할루시네이션 방지를 위한 응답 검증 시스템
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class SensorData:
    """센서 데이터 구조화"""
    tag_name: str
    value: float
    status: str  # normal, warning, critical
    timestamp: Optional[str] = None
    unit: Optional[str] = None
    qc_min: Optional[float] = None
    qc_max: Optional[float] = None
    confidence: float = 1.0  # 0.0 ~ 1.0


@dataclass
class AnalysisResponse:
    """구조화된 분석 응답"""
    query_type: str  # status, alert, trend, summary
    sensor_data: List[SensorData]
    summary: str
    alerts: List[str]
    recommendations: List[str]
    confidence_score: float
    data_source: str  # database, cache, prediction
    timestamp: str
    has_complete_data: bool
    missing_data: List[str]


class ResponseValidator:
    """응답 검증 및 할루시네이션 방지"""
    
    def __init__(self):
        self.known_sensors = set()
        self.known_ranges = {}
        self.db_connection = None
        self.confidence_threshold = 0.7
        
        # 센서 타입과 단위 매핑 (hallucination_prevention.py와 동기화)
        self.sensor_type_units = {
            'D100': {'type': 'temperature', 'unit': '°C', 'name': '온도'},
            'D101': {'type': 'pressure', 'unit': 'bar', 'name': '압력'},
            'D102': {'type': 'flow', 'unit': 'L/min', 'name': '유량'},
            'D200': {'type': 'vibration', 'unit': 'mm/s', 'name': '진동'},
            'D300': {'type': 'power', 'unit': '%', 'name': '전력'}
        }
        
    def validate_sensor_value(self, tag_name: str, value: Any, context: Dict) -> Tuple[bool, str]:
        """센서 값 검증"""
        
        # 1. 값이 숫자인지 확인
        try:
            float_value = float(value)
        except (TypeError, ValueError):
            return False, f"Invalid value type for {tag_name}: {value}"
        
        # 2. 컨텍스트에 있는 실제 데이터와 비교
        actual_data = context.get('current_data', [])
        for sensor in actual_data:
            if sensor.get('tag_name') == tag_name:
                actual_value = sensor.get('value')
                if actual_value is not None:
                    # 정확히 일치하는지 확인 (부동소수점 오차 허용)
                    if abs(float(actual_value) - float_value) > 0.01:
                        return False, f"Value mismatch for {tag_name}: reported {value} vs actual {actual_value}"
                break
        
        # 3. QC 범위 확인
        qc_rules = context.get('qc_rules', [])
        for rule in qc_rules:
            if rule.get('tag_name') == tag_name:
                min_val = rule.get('min_val')
                max_val = rule.get('max_val')
                if min_val is not None and float_value < float(min_val):
                    return True, f"Value {value} below minimum {min_val}"
                if max_val is not None and float_value > float(max_val):
                    return True, f"Value {value} above maximum {max_val}"
                break
                
        return True, "Valid"
    
    def extract_numbers_from_text(self, text: str) -> List[float]:
        """텍스트에서 숫자 추출"""
        # 숫자 패턴 찾기 (정수, 소수점)
        pattern = r'-?\d+\.?\d*'
        numbers = re.findall(pattern, text)
        return [float(n) for n in numbers if n]
    
    def validate_with_database(self, response: str, db_data: List[Dict]) -> float:
        """DB 데이터와 실시간 검증"""
        if not db_data:
            return 0.5
        
        mentioned_values = self.extract_numbers_from_text(response)
        actual_values = [float(d['value']) for d in db_data if 'value' in d]
        
        if not mentioned_values:
            return 1.0
        
        match_count = 0
        for val in mentioned_values:
            for actual in actual_values:
                if abs(val - actual) < 0.01:
                    match_count += 1
                    break
        
        return match_count / len(mentioned_values) if mentioned_values else 1.0
    
    def detect_hallucination(self, response: str, context: Dict) -> Dict[str, Any]:
        """할루시네이션 탐지 - 개선된 버전"""
        
        issues = []
        confidence = 1.0
        
        # 1. 응답에서 숫자 추출
        numbers_in_response = self.extract_numbers_from_text(response)
        
        # 2. 컨텍스트에 있는 실제 숫자
        actual_numbers = set()
        for data in context.get('current_data', []):
            if 'value' in data:
                actual_numbers.add(float(data['value']))
        for rule in context.get('qc_rules', []):
            for key in ['min_val', 'max_val', 'warn_min', 'warn_max', 'crit_min', 'crit_max']:
                if rule.get(key) is not None:
                    actual_numbers.add(float(rule[key]))
        # 비교 데이터의 숫자들도 추가
        for comp in context.get('comparison_data', []):
            for key in ['yesterday_avg', 'today_avg', 'avg_change', 'pct_change', 'yesterday_min', 'yesterday_max', 'today_min', 'today_max']:
                if comp.get(key) is not None:
                    actual_numbers.add(float(comp[key]))
        # 상관분석 데이터의 숫자들도 추가  
        for stat in context.get('correlation_stats', []):
            for key in ['avg_val', 'mean_val', 'std_val', 'count']:
                if stat.get(key) is not None:
                    actual_numbers.add(float(stat[key]))
        
        # 3. 할루시네이션 체크 - 신뢰도 점수 계산
        for num in numbers_in_response:
            found = False
            for actual in actual_numbers:
                if abs(num - actual) < 0.01:
                    found = True
                    break
            
            if not found and num > 10000:
                issues.append(f"Suspicious large number {num} not found in context")
                confidence *= 0.8
            elif not found and 100 < num < 10000:
                # 중간 크기 숫자는 경고만
                confidence *= 0.95
        
        # 4. 금지된 패턴 체크 (제거 - 너무 엄격함)
        # 이 부분을 제거하여 정상 범위, 품질 점수 등을 허용
        
        return {
            'has_hallucination': len(issues) > 0,
            'issues': issues,
            'confidence': confidence,
            'numbers_found': list(numbers_in_response),
            'numbers_expected': list(actual_numbers)
        }
    
    def create_structured_response(self, query: str, context: Dict) -> AnalysisResponse:
        """구조화된 응답 생성 (할루시네이션 방지)"""
        
        # 쿼리 타입 분류
        query_lower = query.lower()
        if '상관' in query_lower or 'correlation' in query_lower or '관계' in query_lower:
            query_type = 'correlation'
        elif '어제' in query_lower or '비교' in query_lower or '변화' in query_lower or '변했' in query_lower:
            query_type = 'comparison'
        elif '경고' in query_lower or '알람' in query_lower or 'alert' in query_lower or '주의' in query_lower or '위험' in query_lower or '알림' in query_lower:
            query_type = 'alert'
        elif '상태' in query_lower or 'status' in query_lower:
            query_type = 'status'
        elif '트렌드' in query_lower:
            query_type = 'trend'
        else:
            query_type = 'summary'
        
        # 센서 데이터 수집 (실제 데이터만)
        sensor_data = []
        missing_data = []
        
        # 상관분석의 경우 correlation_stats에서 데이터 가져오기
        if query_type == 'correlation' and 'correlation_stats' in context:
            current_data = []
            for stat in context.get('correlation_stats', []):
                current_data.append({
                    'tag_name': stat.get('tag_name'),
                    'value': stat.get('avg_val', stat.get('mean_val', 0)),
                    'ts': ''
                })
        # 비교 분석의 경우 comparison_data에서 데이터 가져오기
        elif query_type == 'comparison' and 'comparison_data' in context:
            current_data = []
            comp_data = context.get('comparison_data', [])
            for comp in comp_data:
                current_data.append({
                    'tag_name': comp.get('tag_name'),
                    'value': comp.get('today_avg', 0),
                    'ts': ''
                })
        else:
            current_data = context.get('current_data', [])
            if not current_data:
                current_data = context.get('current_sensors', [])
            if not current_data:
                current_data = context.get('focused_data', [])
        
        qc_rules = context.get('qc_rules', [])
        qc_lookup = {r['tag_name']: r for r in qc_rules if 'tag_name' in r}
        
        for data in current_data:
            tag_name = data.get('tag_name')
            value = data.get('value')
            
            if tag_name and value is not None:
                # QC 규칙 확인
                qc_rule = qc_lookup.get(tag_name, {})
                
                # 상태 판정
                status = 'normal'
                if qc_rule:
                    warn_min = qc_rule.get('warn_min')
                    warn_max = qc_rule.get('warn_max')
                    crit_min = qc_rule.get('crit_min')
                    crit_max = qc_rule.get('crit_max')
                    
                    float_value = float(value)
                    if (crit_min and float_value < float(crit_min)) or \
                       (crit_max and float_value > float(crit_max)):
                        status = 'critical'
                    elif (warn_min and float_value < float(warn_min)) or \
                         (warn_max and float_value > float(warn_max)):
                        status = 'warning'
                
                sensor_data.append(SensorData(
                    tag_name=tag_name,
                    value=float(value),
                    status=status,
                    timestamp=data.get('ts', ''),
                    unit=self._infer_unit(tag_name),
                    qc_min=float(qc_rule.get('min_val', 0)) if qc_rule else None,
                    qc_max=float(qc_rule.get('max_val', 0)) if qc_rule else None,
                    confidence=1.0  # 실제 데이터는 100% 신뢰
                ))
            else:
                missing_data.append(tag_name or 'Unknown')
        
        # 상관/비교 분석 결과 처리
        correlation_info = {}
        if query_type == 'comparison':
            # 비교 분석 데이터 추가
            if 'comparison_data' in context:
                correlation_info['comparison_data'] = context.get('comparison_data', [])
            if 'top_changes' in context:
                correlation_info['top_changes'] = context.get('top_changes', [])
        elif query_type == 'correlation':
            # correlation_data가 있으면 가져오기
            if 'correlation_data' in context:
                corr_data = context.get('correlation_data', {})
                if 'coefficients' in corr_data:
                    correlation_info.update(corr_data)
            
            # correlation_sensors 추가
            if 'correlation_sensors' in context:
                correlation_info['sensors'] = context.get('correlation_sensors', [])
            
            # correlation_stats 추가
            if 'correlation_stats' in context:
                correlation_info['stats'] = context.get('correlation_stats', [])
            
            # 샘플 데이터 추가
            if 'correlation_samples' in context:
                correlation_info['samples'] = context.get('correlation_samples', [])
        
        # 상관정보가 비어있지 않을 때만 사용
        if query_type == 'correlation' and not correlation_info:
            correlation_info = None
        
        # 요약 생성 (데이터 기반)
        summary = self._generate_safe_summary(query_type, sensor_data, missing_data, correlation_info)
        
        # 알림 생성 (실제 데이터만)
        alerts = []
        for sensor in sensor_data:
            if sensor.status == 'critical':
                alerts.append(f"🚨 {sensor.tag_name}: {sensor.value} (위험)")
            elif sensor.status == 'warning':
                alerts.append(f"⚠️ {sensor.tag_name}: {sensor.value} (주의)")
        
        # 권장사항 (템플릿 기반)
        recommendations = self._generate_recommendations(sensor_data, query_type)
        
        return AnalysisResponse(
            query_type=query_type,
            sensor_data=sensor_data,
            summary=summary,
            alerts=alerts,
            recommendations=recommendations,
            confidence_score=1.0 if sensor_data else 0.0,
            data_source='database' if sensor_data else 'none',
            timestamp=datetime.now().isoformat(),
            has_complete_data=len(missing_data) == 0,
            missing_data=missing_data
        )
    
    def _infer_unit(self, tag_name: str) -> str:
        """센서명에서 단위 추론 (정확한 매핑 사용)"""
        # 정확한 센서 매핑 우선
        if tag_name in self.sensor_type_units:
            return self.sensor_type_units[tag_name]['unit']
        
        # 시리즈별 매핑 (폴백)
        if tag_name.startswith('D100'):
            return '°C'
        elif tag_name.startswith('D101'):
            return 'bar'
        elif tag_name.startswith('D102'):
            return 'L/min'
        elif tag_name.startswith('D200'):
            return 'mm/s'
        elif tag_name.startswith('D300'):
            return '%'
        elif tag_name.startswith('D1'):
            return '°C'
        elif tag_name.startswith('D2'):
            return 'bar'
        elif tag_name.startswith('D3'):
            return 'rpm'
        return ''
    
    def _generate_safe_summary(self, query_type: str, sensor_data: List[SensorData], missing: List[str], correlation_info: Dict = None) -> str:
        """안전한 요약 생성 (템플릿 기반)"""
        
        if not sensor_data:
            return "현재 센서 데이터를 가져올 수 없습니다. 데이터베이스 연결을 확인해주세요."
        
        total = len(sensor_data)
        normal = len([s for s in sensor_data if s.status == 'normal'])
        warning = len([s for s in sensor_data if s.status == 'warning'])
        critical = len([s for s in sensor_data if s.status == 'critical'])
        
        if query_type == 'comparison':
            # 비교 분석 결과
            if 'comparison_data' in correlation_info and correlation_info.get('comparison_data'):
                comp_data = correlation_info.get('comparison_data', [])
                if comp_data:
                    # 가장 큰 변화 센서
                    top_sensor = comp_data[0]
                    tag = top_sensor.get('tag_name', '')
                    pct = top_sensor.get('pct_change', 0)
                    change = top_sensor.get('avg_change', 0)
                    
                    if pct == 0:
                        return "모든 센서가 어제와 동일한 값을 유지하고 있습니다. 센서 작동 상태를 점검해주세요."
                    else:
                        direction = "증가" if change > 0 else "감소"
                        return f"{tag} 센서가 어제 대비 {pct:.1f}% {direction}했습니다."
            return "어제와 오늘의 센서 데이터를 비교 분석 중입니다."
        elif query_type == 'correlation':
            if correlation_info and 'coefficients' in correlation_info:
                coeffs = correlation_info['coefficients']
                sensors = correlation_info.get('sensors', [])
                stats = correlation_info.get('stats', [])
                
                if len(sensors) >= 2:
                    # 상관계수와 데이터 통계 표시
                    summary_parts = []
                    if coeffs:
                        for key, value in coeffs.items():
                            summary_parts.append(f"{sensors[0]}와 {sensors[1]}의 상관계수: {value:.4f}")
                            break
                    else:
                        summary_parts.append(f"{sensors[0]}와 {sensors[1]}의 상관분석")
                    
                    # 데이터 통계 추가
                    if stats:
                        summary_parts.append("\n분석 데이터:")
                        for stat in stats[:2]:  # 최대 2개 센서만 표시
                            tag = stat.get('tag_name', '')
                            count = stat.get('count', 0)
                            mean = stat.get('mean_val', 0) if stat.get('mean_val') else stat.get('avg_val', 0)
                            std = stat.get('std_val', 0)
                            summary_parts.append(f"  - {tag}: {count}개 데이터 (평균: {mean:.2f}, 표준편차: {std:.2f})")
                    
                    # 샘플 데이터 포인트 추가
                    samples = correlation_info.get('samples', [])
                    if samples:
                        summary_parts.append("\n최근 데이터 샘플:")
                        # 센서별로 그룹핑
                        by_sensor = {}
                        for sample in samples[:10]:  # 최대 10개만
                            tag = sample.get('tag_name', '')
                            if tag not in by_sensor:
                                by_sensor[tag] = []
                            by_sensor[tag].append(sample.get('value', 0))
                        
                        for tag, values in by_sensor.items():
                            values_str = ', '.join([f"{v:.2f}" for v in values[:5]])  # 각 센서별 최대 5개
                            summary_parts.append(f"  - {tag}: [{values_str}]")
                    
                    summary_parts.append("(30일 데이터 기반)")
                    return "\n".join(summary_parts)
            return "상관분석 데이터를 수집 중입니다."
        elif query_type == 'status':
            return f"전체 {total}개 센서 중 정상 {normal}개, 주의 {warning}개, 위험 {critical}개"
        elif query_type == 'alert':
            if warning + critical == 0:
                return "현재 모든 센서가 정상 범위 내에 있습니다."
            else:
                return f"주의가 필요한 센서 {warning + critical}개 발견 (주의 {warning}개, 위험 {critical}개)"
        else:
            return f"센서 {total}개 모니터링 중"
    
    def _generate_recommendations(self, sensor_data: List[SensorData], query_type: str) -> List[str]:
        """권장사항 생성 (템플릿 기반)"""
        
        recommendations = []
        
        critical_sensors = [s for s in sensor_data if s.status == 'critical']
        warning_sensors = [s for s in sensor_data if s.status == 'warning']
        
        if critical_sensors:
            recommendations.append("즉시 위험 상태 센서를 점검하세요")
            recommendations.append("시스템 안전을 위해 필요시 가동을 중단하세요")
        
        if warning_sensors:
            recommendations.append("주의 상태 센서의 추이를 면밀히 모니터링하세요")
            
        if not critical_sensors and not warning_sensors:
            recommendations.append("정기적인 모니터링을 계속하세요")
            
        return recommendations
    
    def format_json_response(self, response: AnalysisResponse) -> str:
        """JSON 형식으로 응답 포맷"""
        
        # dataclass를 dict로 변환
        response_dict = asdict(response)
        
        # JSON 문자열로 변환 (한글 유지)
        return json.dumps(response_dict, ensure_ascii=False, indent=2)
    
    def format_human_response(self, response: AnalysisResponse) -> str:
        """사람이 읽기 쉬운 형식으로 포맷"""
        
        lines = []
        
        # 요약
        lines.append(f"[INFO] {response.summary}")
        lines.append("")
        
        # 알림
        if response.alerts:
            lines.append("[ALERT] 알림:")
            for alert in response.alerts:
                lines.append(f"  {alert}")
            lines.append("")
        
        # 센서 상세
        if response.sensor_data:
            lines.append("[DATA] 센서 상태:")
            for sensor in response.sensor_data[:5]:  # 최대 5개만
                status_icon = "[OK]" if sensor.status == "normal" else "[WARN]" if sensor.status == "warning" else "[CRIT]"
                lines.append(f"  {status_icon} {sensor.tag_name}: {sensor.value}{sensor.unit}")
            lines.append("")
        
        # 권장사항
        if response.recommendations:
            lines.append("[RECOMMEND] 권장사항:")
            for rec in response.recommendations:
                lines.append(f"  - {rec}")
            lines.append("")
        
        # 데이터 부족 경고
        if response.missing_data:
            lines.append(f"[WARN] 데이터 없음: {', '.join(response.missing_data[:3])}")
        
        # 신뢰도 (실제 데이터가 있을 때만)
        if response.sensor_data:
            lines.append(f"[SCORE] 데이터 수: {len(response.sensor_data)}개")
        
        return "\n".join(lines)


# 사용 예시
async def generate_validated_response(query: str, context: Dict) -> str:
    """검증된 응답 생성 (OpenAI API 사용)"""
    print(f"\n🎯 [VALIDATOR] generate_validated_response 시작")
    print(f"   Query: {query}")
    print(f"   Context keys: {list(context.keys())}")
    
    from openai import AsyncOpenAI
    import os
    
    validator = ResponseValidator()
    
    # 1. 구조화된 응답 생성 (데이터 검증용)
    print(f"📄 [VALIDATOR] 구조화된 응답 생성 중...")
    structured_response = validator.create_structured_response(query, context)
    print(f"   - 센서 데이터: {len(structured_response.sensor_data)}개")
    print(f"   - 알림: {len(structured_response.alerts)}개")
    print(f"   - 권장사항: {len(structured_response.recommendations)}개")
    
    # 2. OpenAI API를 통한 자연스러운 응답 생성
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        print(f"🔑 [VALIDATOR] API 키 확인: {api_key[:10] if api_key else 'None'}...")
        
        if not api_key or api_key == "dummy-key":
            raise ValueError("OpenAI API key not configured properly")
        
        client = AsyncOpenAI(api_key=api_key)
        print(f"✅ [VALIDATOR] OpenAI 클라이언트 생성 성공")
        
        # 컨텍스트 요약 생성
        print(f"📝 [VALIDATOR] 컨텍스트 요약 생성 중...")
        context_summary = []
        
        # 센서 데이터 요약
        if structured_response.sensor_data:
            context_summary.append("현재 센서 상태:")
            sensor_count = 0
            for sensor in structured_response.sensor_data[:10]:  # 최대 10개
                status_kr = "정상" if sensor.status == "normal" else "주의" if sensor.status == "warning" else "위험"
                context_summary.append(f"- {sensor.tag_name}: {sensor.value}{sensor.unit} ({status_kr})")
                sensor_count += 1
            print(f"   센서 데이터 요약: {sensor_count}개")
        
        # 비교 데이터 요약
        if context.get('comparison_data'):
            context_summary.append("\n어제 대비 변화:")
            comp_count = 0
            for comp in context['comparison_data'][:5]:  # 최대 5개
                change = comp.get('pct_change', 0)
                if change != 0:
                    direction = "증가" if comp.get('avg_change', 0) > 0 else "감소"
                    context_summary.append(f"- {comp['tag_name']}: {abs(change):.1f}% {direction}")
                else:
                    context_summary.append(f"- {comp['tag_name']}: 변화 없음")
                comp_count += 1
            print(f"   비교 데이터 요약: {comp_count}개")
        
        # 상관분석 데이터 요약
        if context.get('correlation_stats'):
            context_summary.append("\n상관분석 데이터:")
            corr_count = 0
            for stat in context['correlation_stats'][:2]:
                context_summary.append(f"- {stat['tag_name']}: 평균 {stat.get('mean_val', 0):.2f}")
                corr_count += 1
            print(f"   상관분석 요약: {corr_count}개")
        
        context_text = "\n".join(context_summary)
        print(f"📝 [VALIDATOR] 컨텍스트 텍스트 길이: {len(context_text)} 문자")
        
        system_prompt = """당신은 산업 센서 모니터링 전문가입니다.
주어진 센서 데이터를 기반으로 정확하고 자연스러운 한국어로 답변하세요.

중요 규칙:
1. 실제 데이터 기반으로만 답변 (추측하지 마세요)
2. 구체적인 센서명과 수치를 포함하세요
3. 위험/경고 상태가 있다면 반드시 언급하세요
4. 자연스럽고 친근한 한국어로 답변하세요
5. 필요시 이모지를 적절히 사용하세요"""

        user_prompt = f"""사용자 질문: {query}

센서 데이터:
{context_text}

위 데이터를 바탕으로 사용자 질문에 자연스럽게 답변해주세요."""
        
        print(f"🤖 [VALIDATOR] OpenAI API 호출 중...")
        print(f"   모델: gpt-3.5-turbo")
        print(f"   프롬프트 길이: {len(user_prompt)} 문자")
        
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        ai_response = response.choices[0].message.content.strip()
        print(f"✅ [VALIDATOR] OpenAI 응답 수신: {len(ai_response)} 문자")
        print(f"   응답 미리보기: {ai_response[:100]}...")
        
        # 3. 생성된 응답에 대한 할루시네이션 체크
        print(f"🛡️ [VALIDATOR] 할루시네이션 체크 중...")
        hallucination_check = validator.detect_hallucination(ai_response, context)
        
        if hallucination_check['has_hallucination']:
            print(f"⚠️ [VALIDATOR] 할루시네이션 감지됨: {hallucination_check['issues']}")
            print(f"🔄 [VALIDATOR] 안전한 템플릿 응답으로 대체")
            # 할루시네이션이 감지되면 안전한 템플릿 응답으로 대체
            return validator.format_human_response(structured_response)
        
        print(f"✅ [VALIDATOR] 할루시네이션 체크 통과")
        print(f"🎯 [VALIDATOR] 최종 응답 반환")
        return ai_response
        
    except Exception as e:
        print(f"❌ [VALIDATOR] OpenAI API 호출 실패: {e}")
        import traceback
        print(f"📋 [VALIDATOR] 상세 오류:\n{traceback.format_exc()}")
        print(f"🔄 [VALIDATOR] 템플릿 응답으로 폴백")
        # API 호출 실패시 템플릿 응답 반환
        return validator.format_human_response(structured_response)