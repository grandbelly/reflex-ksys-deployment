"""
수질 기준 모니터링 시스템
TASK_015: WATER_MONITOR_QUALITY
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import psycopg
import asyncio


class ComplianceStatus(Enum):
    """준수 상태"""
    COMPLIANT = "compliant"          # 기준 준수
    WARNING = "warning"              # 경고 수준
    VIOLATION = "violation"          # 기준 위반
    CRITICAL = "critical"           # 심각한 위반


@dataclass
class WaterQualityStandard:
    """수질 기준"""
    parameter: str              # 수질 항목
    unit: str                  # 단위
    standard_min: float        # 최소 기준값
    standard_max: float        # 최대 기준값
    warning_min: float         # 경고 최소값
    warning_max: float         # 경고 최대값
    regulation: str            # 규정명
    effective_date: datetime   # 시행일


@dataclass
class WaterQualityResult:
    """수질 모니터링 결과"""
    parameter: str
    value: float
    unit: str
    status: ComplianceStatus
    standard_min: float
    standard_max: float
    deviation_pct: float       # 기준 대비 이탈률
    message: str
    timestamp: datetime


@dataclass
class ComplianceReport:
    """준수율 보고서"""
    monitoring_period: Tuple[datetime, datetime]
    total_samples: int
    compliant_samples: int
    warning_samples: int
    violation_samples: int
    compliance_rate: float     # 준수율 %
    parameters: Dict[str, float]  # 항목별 준수율
    critical_events: List[Dict]


class WaterQualityMonitor:
    """수질 기준 모니터링 시스템"""
    
    def __init__(self, db_dsn: str):
        self.db_dsn = db_dsn
        
        # 먹는물 수질 기준 (한국 기준)
        self.standards = {
            'pH': WaterQualityStandard(
                parameter='pH',
                unit='',
                standard_min=5.8,
                standard_max=8.5,
                warning_min=6.0,
                warning_max=8.3,
                regulation='먹는물 수질기준',
                effective_date=datetime(2024, 1, 1)
            ),
            'turbidity': WaterQualityStandard(
                parameter='turbidity',
                unit='NTU',
                standard_min=0,
                standard_max=0.5,
                warning_min=0,
                warning_max=0.4,
                regulation='먹는물 수질기준',
                effective_date=datetime(2024, 1, 1)
            ),
            'residual_chlorine': WaterQualityStandard(
                parameter='residual_chlorine',
                unit='mg/L',
                standard_min=0.1,
                standard_max=4.0,
                warning_min=0.2,
                warning_max=3.5,
                regulation='먹는물 수질기준',
                effective_date=datetime(2024, 1, 1)
            ),
            'tds': WaterQualityStandard(
                parameter='tds',
                unit='mg/L',
                standard_min=0,
                standard_max=500,
                warning_min=0,
                warning_max=450,
                regulation='먹는물 수질기준',
                effective_date=datetime(2024, 1, 1)
            ),
            'conductivity': WaterQualityStandard(
                parameter='conductivity',
                unit='μS/cm',
                standard_min=0,
                standard_max=800,
                warning_min=0,
                warning_max=700,
                regulation='먹는물 수질기준',
                effective_date=datetime(2024, 1, 1)
            ),
            'temperature': WaterQualityStandard(
                parameter='temperature',
                unit='°C',
                standard_min=4,
                standard_max=25,
                warning_min=5,
                warning_max=23,
                regulation='먹는물 수질기준',
                effective_date=datetime(2024, 1, 1)
            )
        }
    
    async def check_water_quality(self, 
                                 parameter: str, 
                                 value: float) -> WaterQualityResult:
        """
        수질 항목 체크
        
        Args:
            parameter: 수질 항목명
            value: 측정값
        """
        if parameter not in self.standards:
            return WaterQualityResult(
                parameter=parameter,
                value=value,
                unit='',
                status=ComplianceStatus.WARNING,
                standard_min=0,
                standard_max=0,
                deviation_pct=0,
                message=f"기준 없음: {parameter}",
                timestamp=datetime.now()
            )
        
        standard = self.standards[parameter]
        
        # 상태 판정
        status = ComplianceStatus.COMPLIANT
        deviation_pct = 0.0
        message = "정상 범위"
        
        if value < standard.standard_min:
            status = ComplianceStatus.VIOLATION
            deviation_pct = ((standard.standard_min - value) / standard.standard_min) * 100
            message = f"최소 기준 미달: {value:.2f} < {standard.standard_min:.2f}"
            
            if value < standard.warning_min:
                status = ComplianceStatus.CRITICAL
                message = f"심각한 미달: {value:.2f} << {standard.standard_min:.2f}"
                
        elif value > standard.standard_max:
            status = ComplianceStatus.VIOLATION
            deviation_pct = ((value - standard.standard_max) / standard.standard_max) * 100
            message = f"최대 기준 초과: {value:.2f} > {standard.standard_max:.2f}"
            
            if value > standard.warning_max * 1.2:
                status = ComplianceStatus.CRITICAL
                message = f"심각한 초과: {value:.2f} >> {standard.standard_max:.2f}"
                
        elif value < standard.warning_min or value > standard.warning_max:
            status = ComplianceStatus.WARNING
            if value < standard.warning_min:
                deviation_pct = ((standard.warning_min - value) / standard.warning_min) * 100
                message = f"경고 수준: {value:.2f} (최소 권장: {standard.warning_min:.2f})"
            else:
                deviation_pct = ((value - standard.warning_max) / standard.warning_max) * 100
                message = f"경고 수준: {value:.2f} (최대 권장: {standard.warning_max:.2f})"
        
        return WaterQualityResult(
            parameter=parameter,
            value=value,
            unit=standard.unit,
            status=status,
            standard_min=standard.standard_min,
            standard_max=standard.standard_max,
            deviation_pct=abs(deviation_pct),
            message=message,
            timestamp=datetime.now()
        )
    
    async def monitor_realtime(self) -> List[WaterQualityResult]:
        """실시간 수질 모니터링"""
        results = []
        
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 최신 수질 데이터 조회
                    await cur.execute("""
                        SELECT 
                            tag_name,
                            value
                        FROM influx_latest
                        WHERE tag_name IN ('PH', 'TURB', 'CL2', 'TDS', 'COND_OUT', 'TEMP')
                    """)
                    
                    rows = await cur.fetchall()
                    
                    # 태그명 매핑
                    tag_mapping = {
                        'PH': 'pH',
                        'TURB': 'turbidity',
                        'CL2': 'residual_chlorine',
                        'TDS': 'tds',
                        'COND_OUT': 'conductivity',
                        'TEMP': 'temperature'
                    }
                    
                    for row in rows:
                        tag_name = row[0]
                        value = float(row[1]) if row[1] else 0
                        
                        if tag_name in tag_mapping:
                            parameter = tag_mapping[tag_name]
                            result = await self.check_water_quality(parameter, value)
                            results.append(result)
                            
                            # 위반 시 알람 발생
                            if result.status in [ComplianceStatus.VIOLATION, ComplianceStatus.CRITICAL]:
                                await self._trigger_alarm(result)
        
        except Exception as e:
            print(f"[ERROR] Realtime monitoring failed: {e}")
        
        return results
    
    async def calculate_compliance_rate(self, 
                                       start_date: datetime,
                                       end_date: datetime) -> ComplianceReport:
        """준수율 계산"""
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 기간 내 수질 데이터 조회
                    await cur.execute("""
                        SELECT 
                            tag_name,
                            COUNT(*) as total,
                            AVG(avg_val) as avg_value,
                            MIN(min_val) as min_value,
                            MAX(max_val) as max_value
                        FROM influx_agg_1h
                        WHERE tag_name IN ('PH', 'TURB', 'CL2', 'TDS', 'COND_OUT', 'TEMP')
                        AND bucket >= %s AND bucket <= %s
                        GROUP BY tag_name
                    """, (start_date, end_date))
                    
                    rows = await cur.fetchall()
                    
                    total_samples = 0
                    compliant_samples = 0
                    warning_samples = 0
                    violation_samples = 0
                    critical_events = []
                    parameter_compliance = {}
                    
                    tag_mapping = {
                        'PH': 'pH',
                        'TURB': 'turbidity',
                        'CL2': 'residual_chlorine',
                        'TDS': 'tds',
                        'COND_OUT': 'conductivity',
                        'TEMP': 'temperature'
                    }
                    
                    for row in rows:
                        tag_name = row[0]
                        count = row[1]
                        avg_val = float(row[2]) if row[2] else 0
                        min_val = float(row[3]) if row[3] else 0
                        max_val = float(row[4]) if row[4] else 0
                        
                        if tag_name in tag_mapping:
                            parameter = tag_mapping[tag_name]
                            standard = self.standards.get(parameter)
                            
                            if standard:
                                # 준수 판정
                                param_compliant = 0
                                param_warning = 0
                                param_violation = 0
                                
                                # 최소/최대값 체크
                                if min_val < standard.standard_min or max_val > standard.standard_max:
                                    param_violation = count * 0.2  # 추정
                                    
                                    if min_val < standard.warning_min or max_val > standard.warning_max * 1.2:
                                        critical_events.append({
                                            'parameter': parameter,
                                            'value': min_val if min_val < standard.standard_min else max_val,
                                            'timestamp': datetime.now(),
                                            'message': f'{parameter} 심각한 기준 위반'
                                        })
                                
                                elif min_val < standard.warning_min or max_val > standard.warning_max:
                                    param_warning = count * 0.1  # 추정
                                
                                param_compliant = count - param_warning - param_violation
                                
                                # 누적
                                total_samples += count
                                compliant_samples += param_compliant
                                warning_samples += param_warning
                                violation_samples += param_violation
                                
                                # 항목별 준수율
                                if count > 0:
                                    parameter_compliance[parameter] = (param_compliant / count) * 100
                    
                    # 전체 준수율
                    compliance_rate = (compliant_samples / total_samples * 100) if total_samples > 0 else 0
                    
                    return ComplianceReport(
                        monitoring_period=(start_date, end_date),
                        total_samples=int(total_samples),
                        compliant_samples=int(compliant_samples),
                        warning_samples=int(warning_samples),
                        violation_samples=int(violation_samples),
                        compliance_rate=compliance_rate,
                        parameters=parameter_compliance,
                        critical_events=critical_events
                    )
                    
        except Exception as e:
            print(f"[ERROR] Compliance calculation failed: {e}")
            return ComplianceReport(
                monitoring_period=(start_date, end_date),
                total_samples=0,
                compliant_samples=0,
                warning_samples=0,
                violation_samples=0,
                compliance_rate=0,
                parameters={},
                critical_events=[]
            )
    
    async def _trigger_alarm(self, result: WaterQualityResult):
        """수질 위반 알람 발생"""
        alarm_level = "WARNING"
        if result.status == ComplianceStatus.CRITICAL:
            alarm_level = "CRITICAL"
        elif result.status == ComplianceStatus.VIOLATION:
            alarm_level = "ERROR"
        
        print(f"[ALARM] [{alarm_level}] {result.parameter}: {result.message}")
        
        # DB에 알람 기록 (필요시)
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        INSERT INTO alarm_events (
                            alarm_type, 
                            alarm_level, 
                            parameter, 
                            value, 
                            message, 
                            created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        'WATER_QUALITY',
                        alarm_level,
                        result.parameter,
                        result.value,
                        result.message,
                        datetime.now()
                    ))
                    await conn.commit()
        except:
            pass  # 테이블 없으면 무시
    
    async def load_regulations_from_db(self):
        """DB에서 법규 기준값 로드"""
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT 
                            parameter,
                            unit,
                            standard_min,
                            standard_max,
                            warning_min,
                            warning_max,
                            regulation,
                            effective_date
                        FROM water_quality_standards
                        WHERE effective_date <= NOW()
                        ORDER BY effective_date DESC
                    """)
                    
                    rows = await cur.fetchall()
                    
                    for row in rows:
                        parameter = row[0]
                        if parameter not in self.standards:
                            self.standards[parameter] = WaterQualityStandard(
                                parameter=parameter,
                                unit=row[1],
                                standard_min=float(row[2]) if row[2] else 0,
                                standard_max=float(row[3]) if row[3] else float('inf'),
                                warning_min=float(row[4]) if row[4] else 0,
                                warning_max=float(row[5]) if row[5] else float('inf'),
                                regulation=row[6],
                                effective_date=row[7]
                            )
                    
                    print(f"[INFO] Loaded {len(rows)} water quality standards from DB")
                    
        except Exception as e:
            print(f"[INFO] Using default standards (DB table not found): {e}")