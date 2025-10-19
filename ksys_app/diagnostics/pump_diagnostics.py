"""
펌프 고장 진단 시스템
TASK_010: DIAG_IMPLEMENT_PUMP_FAILURE
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import numpy as np
import psycopg
from ksys_app.ai_engine.w5h1_formatter import W5H1Response, W5H1Formatter


class PumpStatus(Enum):
    """펌프 상태"""
    NORMAL = "normal"
    DEGRADED = "degraded"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"


@dataclass
class PumpDiagnosisResult:
    """펌프 진단 결과"""
    pump_id: str
    status: PumpStatus
    failure_probability: float  # 0.0 ~ 1.0
    symptoms: List[str]
    root_causes: List[str]
    recommendations: List[str]
    w5h1_report: W5H1Response
    timestamp: datetime
    confidence: float


class PumpFailureDiagnostics:
    """펌프 고장 진단 시스템"""
    
    def __init__(self, db_dsn: str):
        self.db_dsn = db_dsn
        self.w5h1_formatter = W5H1Formatter()
        
        # 진단 임계값
        self.thresholds = {
            'flow_reduction': 0.8,      # 유량 80% 미만
            'pressure_increase': 1.2,    # 압력 120% 초과
            'vibration_high': 7.0,       # 진동 7mm/s 초과
            'current_deviation': 0.15,   # 전류 15% 편차
            'efficiency_low': 0.7        # 효율 70% 미만
        }
    
    async def diagnose_pump(self, pump_id: str) -> Optional[PumpDiagnosisResult]:
        """
        펌프 종합 진단
        
        Args:
            pump_id: 펌프 식별자
            
        Returns:
            진단 결과
        """
        try:
            # 펌프 관련 데이터 수집
            pump_data = await self._collect_pump_data(pump_id)
            
            if not pump_data:
                return None
            
            # 각 항목별 진단
            flow_diagnosis = self._diagnose_flow_pattern(pump_data)
            pressure_diagnosis = self._diagnose_pressure_pattern(pump_data)
            vibration_diagnosis = self._diagnose_vibration(pump_data)
            current_diagnosis = self._diagnose_current(pump_data)
            
            # 종합 진단
            symptoms = []
            root_causes = []
            failure_prob = 0.0
            
            # 유량 감소 체크
            if flow_diagnosis['reduced']:
                symptoms.append(f"유량 {flow_diagnosis['reduction_pct']:.1f}% 감소")
                failure_prob += 0.3
                
                if flow_diagnosis['sudden']:
                    root_causes.append("임펠러 손상 의심")
                else:
                    root_causes.append("임펠러 마모 진행")
            
            # 압력 이상 체크
            if pressure_diagnosis['abnormal']:
                symptoms.append(f"토출압력 {pressure_diagnosis['deviation_pct']:.1f}% 이상")
                failure_prob += 0.25
                
                if pressure_diagnosis['fluctuating']:
                    root_causes.append("캐비테이션 발생")
                else:
                    root_causes.append("배관 막힘 또는 밸브 이상")
            
            # 진동 체크
            if vibration_diagnosis['high']:
                symptoms.append(f"진동 {vibration_diagnosis['level']:.1f}mm/s")
                failure_prob += 0.25
                
                if vibration_diagnosis['bearing_freq']:
                    root_causes.append("베어링 손상")
                else:
                    root_causes.append("축 정렬 불량")
            
            # 전류 체크
            if current_diagnosis['abnormal']:
                symptoms.append(f"전류 {current_diagnosis['deviation_pct']:.1f}% 편차")
                failure_prob += 0.2
                
                if current_diagnosis['overload']:
                    root_causes.append("과부하 운전")
                else:
                    root_causes.append("모터 권선 이상")
            
            # 상태 판정
            if failure_prob >= 0.8:
                status = PumpStatus.CRITICAL
            elif failure_prob >= 0.6:
                status = PumpStatus.WARNING
            elif failure_prob >= 0.4:
                status = PumpStatus.DEGRADED
            elif failure_prob > 0:
                status = PumpStatus.DEGRADED
            else:
                status = PumpStatus.NORMAL
            
            # 권장사항 생성
            recommendations = self._generate_recommendations(
                status, symptoms, root_causes
            )
            
            # 6하원칙 리포트 생성
            w5h1_report = self._create_w5h1_report(
                pump_id, status, symptoms, root_causes, pump_data
            )
            
            # 신뢰도 계산
            confidence = self._calculate_confidence(pump_data)
            
            return PumpDiagnosisResult(
                pump_id=pump_id,
                status=status,
                failure_probability=min(failure_prob, 1.0),
                symptoms=symptoms,
                root_causes=root_causes,
                recommendations=recommendations,
                w5h1_report=w5h1_report,
                timestamp=datetime.now(),
                confidence=confidence
            )
            
        except Exception as e:
            print(f"[ERROR] Pump diagnosis failed: {e}")
            return None
    
    async def _collect_pump_data(self, pump_id: str) -> Dict[str, Any]:
        """펌프 관련 데이터 수집"""
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 최근 1시간 데이터
                    await cur.execute("""
                        SELECT 
                            tag_name,
                            AVG(avg_val) as avg_value,
                            MIN(min_val) as min_value,
                            MAX(max_val) as max_value,
                            STDDEV(avg_val) as std_dev
                        FROM influx_agg_1m
                        WHERE tag_name LIKE %s
                        AND bucket >= NOW() - INTERVAL '1 hour'
                        GROUP BY tag_name
                    """, (f"%{pump_id}%",))
                    
                    rows = await cur.fetchall()
                    
                    data = {
                        'pump_id': pump_id,
                        'timestamp': datetime.now(),
                        'metrics': {}
                    }
                    
                    for row in rows:
                        tag_name = row[0]
                        metric_type = self._extract_metric_type(tag_name)
                        
                        data['metrics'][metric_type] = {
                            'avg': float(row[1]) if row[1] else 0,
                            'min': float(row[2]) if row[2] else 0,
                            'max': float(row[3]) if row[3] else 0,
                            'std': float(row[4]) if row[4] else 0
                        }
                    
                    # 기준값 조회 (정상 운전 시)
                    await cur.execute("""
                        SELECT 
                            tag_name,
                            AVG(avg_val) as baseline
                        FROM influx_agg_1h
                        WHERE tag_name LIKE %s
                        AND bucket >= NOW() - INTERVAL '30 days'
                        AND bucket <= NOW() - INTERVAL '7 days'
                        GROUP BY tag_name
                    """, (f"%{pump_id}%",))
                    
                    baseline_rows = await cur.fetchall()
                    
                    data['baseline'] = {}
                    for row in baseline_rows:
                        tag_name = row[0]
                        metric_type = self._extract_metric_type(tag_name)
                        data['baseline'][metric_type] = float(row[1]) if row[1] else 0
                    
                    return data
                    
        except Exception as e:
            print(f"[ERROR] Data collection failed: {e}")
            return {}
    
    def _extract_metric_type(self, tag_name: str) -> str:
        """태그명에서 메트릭 타입 추출"""
        tag_lower = tag_name.lower()
        
        if 'flow' in tag_lower or 'q' in tag_lower:
            return 'flow'
        elif 'pressure' in tag_lower or 'p' in tag_lower:
            return 'pressure'
        elif 'vibration' in tag_lower or 'vib' in tag_lower:
            return 'vibration'
        elif 'current' in tag_lower or 'amp' in tag_lower:
            return 'current'
        elif 'speed' in tag_lower or 'rpm' in tag_lower:
            return 'speed'
        else:
            return tag_name
    
    def _diagnose_flow_pattern(self, pump_data: Dict) -> Dict[str, Any]:
        """유량 패턴 진단"""
        result = {
            'reduced': False,
            'reduction_pct': 0.0,
            'sudden': False
        }
        
        if 'flow' not in pump_data.get('metrics', {}):
            return result
        
        current_flow = pump_data['metrics']['flow']['avg']
        baseline_flow = pump_data.get('baseline', {}).get('flow', current_flow)
        
        if baseline_flow > 0:
            reduction_pct = (1 - current_flow / baseline_flow) * 100
            
            if reduction_pct > 20:  # 20% 이상 감소
                result['reduced'] = True
                result['reduction_pct'] = reduction_pct
                
                # 급격한 변화 체크 (표준편차 기준)
                std_dev = pump_data['metrics']['flow']['std']
                if std_dev > baseline_flow * 0.1:  # 10% 이상 변동
                    result['sudden'] = True
        
        return result
    
    def _diagnose_pressure_pattern(self, pump_data: Dict) -> Dict[str, Any]:
        """압력 패턴 진단"""
        result = {
            'abnormal': False,
            'deviation_pct': 0.0,
            'fluctuating': False
        }
        
        if 'pressure' not in pump_data.get('metrics', {}):
            return result
        
        current_pressure = pump_data['metrics']['pressure']['avg']
        baseline_pressure = pump_data.get('baseline', {}).get('pressure', current_pressure)
        
        if baseline_pressure > 0:
            deviation_pct = abs(current_pressure - baseline_pressure) / baseline_pressure * 100
            
            if deviation_pct > 15:  # 15% 이상 편차
                result['abnormal'] = True
                result['deviation_pct'] = deviation_pct
                
                # 변동성 체크
                std_dev = pump_data['metrics']['pressure']['std']
                if std_dev > baseline_pressure * 0.05:  # 5% 이상 변동
                    result['fluctuating'] = True
        
        return result
    
    def _diagnose_vibration(self, pump_data: Dict) -> Dict[str, Any]:
        """진동 진단"""
        result = {
            'high': False,
            'level': 0.0,
            'bearing_freq': False
        }
        
        if 'vibration' not in pump_data.get('metrics', {}):
            return result
        
        vibration_level = pump_data['metrics']['vibration']['avg']
        
        if vibration_level > self.thresholds['vibration_high']:
            result['high'] = True
            result['level'] = vibration_level
            
            # 베어링 주파수 패턴 체크 (간단한 판정)
            if vibration_level > 10.0:
                result['bearing_freq'] = True
        
        return result
    
    def _diagnose_current(self, pump_data: Dict) -> Dict[str, Any]:
        """전류 진단"""
        result = {
            'abnormal': False,
            'deviation_pct': 0.0,
            'overload': False
        }
        
        if 'current' not in pump_data.get('metrics', {}):
            return result
        
        current_amp = pump_data['metrics']['current']['avg']
        baseline_amp = pump_data.get('baseline', {}).get('current', current_amp)
        
        if baseline_amp > 0:
            deviation_pct = abs(current_amp - baseline_amp) / baseline_amp * 100
            
            if deviation_pct > 15:  # 15% 이상 편차
                result['abnormal'] = True
                result['deviation_pct'] = deviation_pct
                
                if current_amp > baseline_amp * 1.2:  # 20% 초과
                    result['overload'] = True
        
        return result
    
    def _generate_recommendations(self, 
                                 status: PumpStatus,
                                 symptoms: List[str],
                                 root_causes: List[str]) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        if status == PumpStatus.CRITICAL:
            recommendations.append("즉시 펌프 정지 및 점검 필요")
            recommendations.append("예비 펌프로 전환 권장")
        elif status == PumpStatus.WARNING:
            recommendations.append("24시간 내 정비 점검 필요")
            recommendations.append("운전 조건 조정 검토")
        elif status == PumpStatus.DEGRADED:
            recommendations.append("정기 점검 시 세밀한 검사 필요")
            recommendations.append("예비 부품 확보 권장")
        
        # 원인별 권장사항
        for cause in root_causes:
            if "임펠러" in cause:
                recommendations.append("임펠러 상태 육안 검사")
            elif "베어링" in cause:
                recommendations.append("베어링 교체 준비")
            elif "캐비테이션" in cause:
                recommendations.append("흡입 압력 증가 또는 유량 감소")
            elif "과부하" in cause:
                recommendations.append("운전점 확인 및 조정")
        
        return recommendations
    
    def _create_w5h1_report(self,
                           pump_id: str,
                           status: PumpStatus,
                           symptoms: List[str],
                           root_causes: List[str],
                           pump_data: Dict) -> W5H1Response:
        """6하원칙 진단 리포트 생성"""
        
        w5h1 = W5H1Response()
        
        # What - 무엇을
        w5h1.what = f"펌프 {pump_id} {status.value} 상태"
        if symptoms:
            w5h1.what += f" - {', '.join(symptoms[:2])}"
        
        # Why - 왜
        if root_causes:
            w5h1.why = f"추정 원인: {', '.join(root_causes[:2])}"
        else:
            w5h1.why = "정상 운전 중"
        
        # When - 언제
        w5h1.when = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Where - 어디서
        w5h1.where = f"펌프 {pump_id} 위치"
        
        # Who - 누가
        w5h1.who = "자동 진단 시스템"
        
        # How - 어떻게
        w5h1.how = "유량/압력/진동/전류 상관 분석을 통한 진단"
        
        return w5h1
    
    def _calculate_confidence(self, pump_data: Dict) -> float:
        """진단 신뢰도 계산"""
        confidence = 1.0
        
        # 데이터 완전성 체크
        expected_metrics = ['flow', 'pressure', 'vibration', 'current']
        available_metrics = pump_data.get('metrics', {}).keys()
        
        missing_count = sum(1 for m in expected_metrics if m not in available_metrics)
        confidence -= missing_count * 0.2
        
        # 기준값 존재 여부
        if not pump_data.get('baseline'):
            confidence -= 0.3
        
        return max(confidence, 0.3)  # 최소 30%