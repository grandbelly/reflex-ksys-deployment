"""
RO 멤브레인 수명 예측 시스템
TASK_013: MAINT_PREDICT_RO_LIFETIME
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import psycopg
import numpy as np


@dataclass
class ROLifetimePrediction:
    """RO 수명 예측 결과"""
    membrane_id: str
    installation_date: datetime
    operating_hours: float
    cip_count: int
    current_performance: float    # 0.0 ~ 1.0
    tmp_increase_rate: float     # bar/month
    estimated_lifetime_days: int
    remaining_days: int
    replacement_date: datetime
    confidence: float
    factors: Dict[str, float]    # 영향 요인별 점수


class ROLifetimePredictor:
    """RO 멤브레인 수명 예측"""
    
    def __init__(self, db_dsn: str):
        self.db_dsn = db_dsn
        
        # 수명 영향 계수
        self.lifetime_factors = {
            'base_lifetime_days': 1095,  # 3년 기준
            'cip_impact': -10,           # CIP 1회당 -10일
            'tmp_impact': -5,            # TMP 0.1bar 증가당 -5일
            'quality_impact': 2,         # 수질 양호시 +2일/월
            'temp_impact': -3            # 고온 운전시 -3일/°C
        }
    
    async def predict_lifetime(self, membrane_id: str) -> Optional[ROLifetimePrediction]:
        """RO 멤브레인 수명 예측"""
        try:
            # 운전 데이터 수집
            operation_data = await self._collect_operation_data(membrane_id)
            
            if not operation_data:
                return None
            
            # 운전 시간 계산
            operating_hours = self._calculate_operating_hours(operation_data)
            
            # CIP 횟수 계산
            cip_count = await self._count_cip_cycles(membrane_id)
            
            # TMP 증가율 분석
            tmp_rate = await self._analyze_tmp_trend(membrane_id)
            
            # 현재 성능 평가
            current_performance = await self._evaluate_performance(membrane_id)
            
            # 수명 계산
            lifetime_days, factors = self._calculate_lifetime(
                operating_hours,
                cip_count,
                tmp_rate,
                current_performance,
                operation_data
            )
            
            # 잔여 수명
            installation_date = operation_data.get('installation_date', 
                                                  datetime.now() - timedelta(days=365))
            days_used = (datetime.now() - installation_date).days
            remaining_days = max(lifetime_days - days_used, 0)
            
            replacement_date = datetime.now() + timedelta(days=remaining_days)
            
            return ROLifetimePrediction(
                membrane_id=membrane_id,
                installation_date=installation_date,
                operating_hours=operating_hours,
                cip_count=cip_count,
                current_performance=current_performance,
                tmp_increase_rate=tmp_rate,
                estimated_lifetime_days=lifetime_days,
                remaining_days=remaining_days,
                replacement_date=replacement_date,
                confidence=self._calculate_confidence(operation_data),
                factors=factors
            )
            
        except Exception as e:
            print(f"[ERROR] Lifetime prediction failed: {e}")
            return None
    
    async def _collect_operation_data(self, membrane_id: str) -> Dict:
        """운전 데이터 수집"""
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 운전 이력 조회
                    await cur.execute("""
                        SELECT 
                            MIN(bucket) as start_date,
                            MAX(bucket) as end_date,
                            COUNT(DISTINCT DATE(bucket)) as operating_days,
                            AVG(avg_val) as avg_tmp,
                            MAX(max_val) as max_tmp
                        FROM influx_agg_1h
                        WHERE tag_name = 'TMP'
                        AND bucket >= NOW() - INTERVAL '3 years'
                    """)
                    
                    result = await cur.fetchone()
                    
                    if result:
                        return {
                            'installation_date': result[0] if result[0] else datetime.now() - timedelta(days=365),
                            'last_date': result[1],
                            'operating_days': result[2] if result[2] else 0,
                            'avg_tmp': float(result[3]) if result[3] else 1.5,
                            'max_tmp': float(result[4]) if result[4] else 2.5
                        }
                    
                    return {}
                    
        except Exception as e:
            print(f"[ERROR] Data collection failed: {e}")
            return {}
    
    def _calculate_operating_hours(self, operation_data: Dict) -> float:
        """운전 시간 계산"""
        operating_days = operation_data.get('operating_days', 0)
        # 일평균 20시간 운전 가정
        return operating_days * 20
    
    async def _count_cip_cycles(self, membrane_id: str) -> int:
        """CIP 횟수 카운트"""
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # CIP 이벤트 카운트 (간단한 로직)
                    await cur.execute("""
                        SELECT COUNT(*)
                        FROM influx_agg_1h
                        WHERE tag_name = 'CIP_EVENT'
                        AND avg_val > 0
                    """)
                    
                    result = await cur.fetchone()
                    return result[0] if result and result[0] else 10  # 기본값 10회
                    
        except Exception as e:
            # 예상값으로 대체
            return 10
    
    async def _analyze_tmp_trend(self, membrane_id: str) -> float:
        """TMP 증가율 분석 (bar/month)"""
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 월별 TMP 평균
                    await cur.execute("""
                        SELECT 
                            DATE_TRUNC('month', bucket) as month,
                            AVG(avg_val) as monthly_avg
                        FROM influx_agg_1h
                        WHERE tag_name = 'TMP'
                        AND bucket >= NOW() - INTERVAL '6 months'
                        GROUP BY month
                        ORDER BY month
                    """)
                    
                    rows = await cur.fetchall()
                    
                    if len(rows) >= 3:
                        values = [float(row[1]) for row in rows]
                        # 선형 회귀
                        x = np.arange(len(values))
                        coeffs = np.polyfit(x, values, 1)
                        return coeffs[0]  # bar/month
                    
                    return 0.05  # 기본값
                    
        except Exception as e:
            return 0.05
    
    async def _evaluate_performance(self, membrane_id: str) -> float:
        """현재 성능 평가 (0.0 ~ 1.0)"""
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 염제거율 조회
                    await cur.execute("""
                        SELECT 
                            AVG(CASE WHEN tag_name = 'COND_IN' THEN avg_val END) as cond_in,
                            AVG(CASE WHEN tag_name = 'COND_OUT' THEN avg_val END) as cond_out
                        FROM influx_agg_1h
                        WHERE tag_name IN ('COND_IN', 'COND_OUT')
                        AND bucket >= NOW() - INTERVAL '24 hours'
                    """)
                    
                    result = await cur.fetchone()
                    
                    if result and result[0] and result[1]:
                        cond_in = float(result[0])
                        cond_out = float(result[1])
                        
                        if cond_in > 0:
                            rejection = 1 - (cond_out / cond_in)
                            # 95% 이상이면 1.0, 90% 이하면 0.0
                            performance = min(max((rejection - 0.90) / 0.05, 0), 1)
                            return performance
                    
                    return 0.8  # 기본값
                    
        except Exception as e:
            return 0.8
    
    def _calculate_lifetime(self, 
                           operating_hours: float,
                           cip_count: int,
                           tmp_rate: float,
                           performance: float,
                           operation_data: Dict) -> tuple:
        """수명 계산"""
        
        # 기본 수명
        base_lifetime = self.lifetime_factors['base_lifetime_days']
        
        factors = {
            'base': base_lifetime,
            'cip_impact': 0,
            'tmp_impact': 0,
            'performance_impact': 0,
            'operation_impact': 0
        }
        
        # CIP 영향
        cip_impact = cip_count * self.lifetime_factors['cip_impact']
        factors['cip_impact'] = cip_impact
        
        # TMP 증가율 영향
        tmp_impact = tmp_rate * 12 * self.lifetime_factors['tmp_impact'] * 10  # 연간 영향
        factors['tmp_impact'] = tmp_impact
        
        # 성능 영향
        if performance < 0.9:
            performance_impact = (0.9 - performance) * 1000  # 성능 저하시 수명 감소
            factors['performance_impact'] = -performance_impact
        else:
            factors['performance_impact'] = 0
        
        # 운전 조건 영향
        avg_tmp = operation_data.get('avg_tmp', 1.5)
        if avg_tmp > 2.0:
            operation_impact = (avg_tmp - 2.0) * 100
            factors['operation_impact'] = -operation_impact
        else:
            factors['operation_impact'] = 0
        
        # 총 수명 계산
        total_lifetime = base_lifetime + sum([
            factors['cip_impact'],
            factors['tmp_impact'],
            factors['performance_impact'],
            factors['operation_impact']
        ])
        
        # 최소 180일, 최대 1825일(5년)
        total_lifetime = min(max(total_lifetime, 180), 1825)
        
        return int(total_lifetime), factors
    
    def _calculate_confidence(self, operation_data: Dict) -> float:
        """예측 신뢰도 계산"""
        confidence = 1.0
        
        # 데이터 기간이 짧으면 신뢰도 감소
        operating_days = operation_data.get('operating_days', 0)
        if operating_days < 30:
            confidence -= 0.5
        elif operating_days < 90:
            confidence -= 0.3
        elif operating_days < 180:
            confidence -= 0.1
        
        return max(confidence, 0.3)