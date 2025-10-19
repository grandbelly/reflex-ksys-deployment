"""
가동범위 실시간 모니터링 시스템
TASK_007: MONITOR_IMPLEMENT_RANGE_CHECK
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import psycopg


class AlertLevel(Enum):
    """알람 레벨"""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class ThresholdConfig:
    """임계값 설정"""
    tag_name: str
    min_val: float
    max_val: float
    warn_min: float
    warn_max: float
    crit_min: float
    crit_max: float
    unit: str = ""
    description: str = ""


@dataclass
class RangeViolation:
    """범위 이탈 정보"""
    tag_name: str
    current_value: float
    threshold_type: str  # min/max
    threshold_value: float
    alert_level: AlertLevel
    deviation_percentage: float
    timestamp: datetime
    predicted_time_to_critical: Optional[float] = None  # 분 단위


class RangeMonitor:
    """가동범위 실시간 모니터링"""
    
    def __init__(self, db_dsn: str):
        self.db_dsn = db_dsn
        self.thresholds = {}  # tag_name: ThresholdConfig
        self.violation_history = []  # 이탈 이력
        self.trend_data = {}  # 트렌드 데이터 캐시
        
        # 담수화 플랜트 주요 센서 임계값 설정
        self._initialize_thresholds()
    
    def _initialize_thresholds(self):
        """임계값 초기화 - 담수화 플랜트 기준"""
        
        # TMP (Transmembrane Pressure) - bar
        self.thresholds['TMP'] = ThresholdConfig(
            tag_name='TMP',
            min_val=0.5,
            max_val=3.0,
            warn_min=0.8,
            warn_max=2.5,
            crit_min=0.5,
            crit_max=2.8,
            unit='bar',
            description='막간차압'
        )
        
        # 차압 (Differential Pressure) - bar
        self.thresholds['DP'] = ThresholdConfig(
            tag_name='DP',
            min_val=0.1,
            max_val=1.5,
            warn_min=0.2,
            warn_max=1.2,
            crit_min=0.1,
            crit_max=1.4,
            unit='bar',
            description='차압'
        )
        
        # 전도도 (Conductivity) - μS/cm
        self.thresholds['COND'] = ThresholdConfig(
            tag_name='COND',
            min_val=0,
            max_val=500,
            warn_min=0,
            warn_max=400,
            crit_min=0,
            crit_max=450,
            unit='μS/cm',
            description='전도도'
        )
        
        # 온도 - °C
        self.thresholds['TEMP'] = ThresholdConfig(
            tag_name='TEMP',
            min_val=15,
            max_val=35,
            warn_min=18,
            warn_max=32,
            crit_min=15,
            crit_max=35,
            unit='°C',
            description='온도'
        )
        
        # pH
        self.thresholds['PH'] = ThresholdConfig(
            tag_name='PH',
            min_val=6.5,
            max_val=8.5,
            warn_min=6.8,
            warn_max=8.2,
            crit_min=6.5,
            crit_max=8.5,
            unit='',
            description='pH'
        )
    
    async def check_range(self, tag_name: str, value: float) -> Tuple[AlertLevel, Optional[RangeViolation]]:
        """
        단일 센서 범위 체크
        
        Returns:
            (AlertLevel, RangeViolation or None)
        """
        if tag_name not in self.thresholds:
            return AlertLevel.NORMAL, None
        
        threshold = self.thresholds[tag_name]
        
        # Critical 체크
        if value < threshold.crit_min:
            deviation = abs((value - threshold.crit_min) / threshold.crit_min * 100)
            violation = RangeViolation(
                tag_name=tag_name,
                current_value=value,
                threshold_type='min',
                threshold_value=threshold.crit_min,
                alert_level=AlertLevel.CRITICAL,
                deviation_percentage=deviation,
                timestamp=datetime.now()
            )
            return AlertLevel.CRITICAL, violation
        
        if value > threshold.crit_max:
            deviation = abs((value - threshold.crit_max) / threshold.crit_max * 100)
            violation = RangeViolation(
                tag_name=tag_name,
                current_value=value,
                threshold_type='max',
                threshold_value=threshold.crit_max,
                alert_level=AlertLevel.CRITICAL,
                deviation_percentage=deviation,
                timestamp=datetime.now()
            )
            return AlertLevel.CRITICAL, violation
        
        # Warning 체크
        if value < threshold.warn_min:
            deviation = abs((value - threshold.warn_min) / threshold.warn_min * 100)
            violation = RangeViolation(
                tag_name=tag_name,
                current_value=value,
                threshold_type='min',
                threshold_value=threshold.warn_min,
                alert_level=AlertLevel.WARNING,
                deviation_percentage=deviation,
                timestamp=datetime.now()
            )
            return AlertLevel.WARNING, violation
        
        if value > threshold.warn_max:
            deviation = abs((value - threshold.warn_max) / threshold.warn_max * 100)
            violation = RangeViolation(
                tag_name=tag_name,
                current_value=value,
                threshold_type='max',
                threshold_value=threshold.warn_max,
                alert_level=AlertLevel.WARNING,
                deviation_percentage=deviation,
                timestamp=datetime.now()
            )
            return AlertLevel.WARNING, violation
        
        return AlertLevel.NORMAL, None
    
    async def check_all_ranges(self, sensor_data: List[Dict[str, Any]]) -> List[RangeViolation]:
        """
        모든 센서 범위 체크
        
        Args:
            sensor_data: [{'tag_name': str, 'value': float}, ...]
            
        Returns:
            위반 사항 리스트
        """
        violations = []
        
        for data in sensor_data:
            tag_name = data.get('tag_name')
            value = data.get('value')
            
            if tag_name and value is not None:
                level, violation = await self.check_range(tag_name, float(value))
                if violation:
                    violations.append(violation)
                    self.violation_history.append(violation)
        
        return violations
    
    async def predict_deviation(self, tag_name: str, history_minutes: int = 60) -> Optional[float]:
        """
        이탈 예측 - 트렌드 분석 기반
        
        Returns:
            예상 임계값 도달 시간 (분)
        """
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 최근 데이터 조회
                    await cur.execute("""
                        SELECT 
                            bucket,
                            avg_val
                        FROM influx_agg_1m
                        WHERE tag_name = %s
                        AND bucket >= NOW() - INTERVAL '%s minutes'
                        ORDER BY bucket
                    """, (tag_name, history_minutes))
                    
                    rows = await cur.fetchall()
                    
                    if len(rows) < 10:  # 최소 10개 데이터 필요
                        return None
                    
                    # 선형 회귀로 트렌드 계산
                    times = list(range(len(rows)))
                    values = [float(row[1]) for row in rows]
                    
                    # 기울기 계산 (간단한 선형 회귀)
                    n = len(times)
                    sum_x = sum(times)
                    sum_y = sum(values)
                    sum_xy = sum(x * y for x, y in zip(times, values))
                    sum_x2 = sum(x * x for x in times)
                    
                    if n * sum_x2 - sum_x * sum_x == 0:
                        return None
                    
                    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
                    current_value = values[-1]
                    
                    if tag_name not in self.thresholds:
                        return None
                    
                    threshold = self.thresholds[tag_name]
                    
                    # 예측 시간 계산
                    if slope > 0:  # 상승 추세
                        # 상한 경고값까지 시간
                        time_to_warn = (threshold.warn_max - current_value) / slope if slope != 0 else float('inf')
                        # 상한 위험값까지 시간
                        time_to_crit = (threshold.crit_max - current_value) / slope if slope != 0 else float('inf')
                    elif slope < 0:  # 하락 추세
                        # 하한 경고값까지 시간
                        time_to_warn = (threshold.warn_min - current_value) / slope if slope != 0 else float('inf')
                        # 하한 위험값까지 시간
                        time_to_crit = (threshold.crit_min - current_value) / slope if slope != 0 else float('inf')
                    else:
                        return None
                    
                    # 가장 가까운 임계값까지의 시간 반환 (분 단위)
                    if time_to_warn > 0 and time_to_warn < float('inf'):
                        return time_to_warn
                    elif time_to_crit > 0 and time_to_crit < float('inf'):
                        return time_to_crit
                    
                    return None
                    
        except Exception as e:
            print(f"[ERROR] Prediction failed for {tag_name}: {e}")
            return None
    
    async def get_current_status(self) -> Dict[str, Any]:
        """현재 모니터링 상태 조회"""
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 최신 센서 데이터 조회
                    await cur.execute("""
                        SELECT 
                            tag_name,
                            value,
                            ts
                        FROM influx_latest
                        WHERE tag_name IN %s
                    """, (tuple(self.thresholds.keys()),))
                    
                    rows = await cur.fetchall()
                    
                    status = {
                        'timestamp': datetime.now().isoformat(),
                        'sensors': [],
                        'violations': [],
                        'summary': {
                            'total': len(self.thresholds),
                            'normal': 0,
                            'warning': 0,
                            'critical': 0
                        }
                    }
                    
                    for row in rows:
                        tag_name = row[0]
                        value = float(row[1])
                        timestamp = row[2]
                        
                        level, violation = await self.check_range(tag_name, value)
                        
                        sensor_status = {
                            'tag_name': tag_name,
                            'value': value,
                            'unit': self.thresholds[tag_name].unit,
                            'status': level.value,
                            'timestamp': timestamp.isoformat() if timestamp else None
                        }
                        
                        # 예측 추가
                        prediction = await self.predict_deviation(tag_name)
                        if prediction:
                            sensor_status['prediction_minutes'] = prediction
                        
                        status['sensors'].append(sensor_status)
                        
                        # 상태별 카운트
                        if level == AlertLevel.NORMAL:
                            status['summary']['normal'] += 1
                        elif level == AlertLevel.WARNING:
                            status['summary']['warning'] += 1
                            if violation:
                                status['violations'].append({
                                    'tag_name': tag_name,
                                    'level': 'warning',
                                    'value': value,
                                    'threshold': violation.threshold_value,
                                    'deviation': f"{violation.deviation_percentage:.1f}%"
                                })
                        elif level == AlertLevel.CRITICAL:
                            status['summary']['critical'] += 1
                            if violation:
                                status['violations'].append({
                                    'tag_name': tag_name,
                                    'level': 'critical',
                                    'value': value,
                                    'threshold': violation.threshold_value,
                                    'deviation': f"{violation.deviation_percentage:.1f}%"
                                })
                    
                    return status
                    
        except Exception as e:
            print(f"[ERROR] Status check failed: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def set_custom_threshold(self, tag_name: str, config: ThresholdConfig):
        """커스텀 임계값 설정"""
        self.thresholds[tag_name] = config
    
    def get_violation_history(self, hours: int = 24) -> List[RangeViolation]:
        """이탈 이력 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [v for v in self.violation_history if v.timestamp > cutoff_time]


# 알람 트리거 설정
async def trigger_alarm(violation: RangeViolation):
    """알람 트리거"""
    print(f"[ALARM] {violation.alert_level.value.upper()}: {violation.tag_name} = {violation.current_value}")
    print(f"  Threshold: {violation.threshold_value}, Deviation: {violation.deviation_percentage:.1f}%")
    
    if violation.alert_level == AlertLevel.CRITICAL:
        print("  [ACTION] Emergency protocol activated!")
        # Emergency Stop 로직 추가 가능