"""
막오염 진단 시스템
TASK_012: DIAG_IMPLEMENT_FOULING
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import psycopg
import numpy as np


class FoulingType(Enum):
    """막오염 타입"""
    ORGANIC = "organic"          # 유기물
    INORGANIC = "inorganic"      # 무기물(스케일)
    BIOLOGICAL = "biological"     # 생물막
    COLLOIDAL = "colloidal"      # 콜로이드
    MIXED = "mixed"              # 복합


@dataclass
class FoulingDiagnosisResult:
    """막오염 진단 결과"""
    membrane_id: str
    fouling_type: FoulingType
    fouling_rate: float          # %/day
    tmp_increase_rate: float     # bar/day
    cip_efficiency: float        # 0.0 ~ 1.0
    cleaning_urgency: str        # immediate/soon/scheduled
    predicted_cleaning_date: datetime
    recommendations: List[str]
    timestamp: datetime


class FoulingDiagnostics:
    """막오염 진단 시스템"""
    
    def __init__(self, db_dsn: str):
        self.db_dsn = db_dsn
        
        # 오염 진단 임계값
        self.thresholds = {
            'tmp_increase_normal': 0.1,    # bar/day
            'tmp_increase_warning': 0.2,
            'tmp_increase_critical': 0.5,
            'flux_decline_normal': 2,      # %/day
            'flux_decline_warning': 5,
            'cip_trigger_tmp': 2.5,        # bar
            'cip_trigger_flux': 0.7        # 70% of initial
        }
    
    async def diagnose_fouling(self, membrane_id: str) -> Optional[FoulingDiagnosisResult]:
        """막오염 진단"""
        try:
            # TMP 트렌드 분석
            tmp_trend = await self._analyze_tmp_trend(membrane_id)
            
            # 플럭스 감소 분석
            flux_decline = await self._analyze_flux_decline(membrane_id)
            
            # CIP 효율 계산
            cip_efficiency = await self._calculate_cip_efficiency(membrane_id)
            
            # 오염 타입 분류
            fouling_type = self._classify_fouling_type(tmp_trend, flux_decline)
            
            # 세척 시기 예측
            cleaning_date, urgency = self._predict_cleaning_schedule(
                tmp_trend['increase_rate'],
                flux_decline['decline_rate'],
                tmp_trend['current_tmp']
            )
            
            # 권장사항 생성
            recommendations = self._generate_recommendations(
                fouling_type,
                urgency,
                cip_efficiency
            )
            
            return FoulingDiagnosisResult(
                membrane_id=membrane_id,
                fouling_type=fouling_type,
                fouling_rate=flux_decline['decline_rate'],
                tmp_increase_rate=tmp_trend['increase_rate'],
                cip_efficiency=cip_efficiency,
                cleaning_urgency=urgency,
                predicted_cleaning_date=cleaning_date,
                recommendations=recommendations,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            print(f"[ERROR] Fouling diagnosis failed: {e}")
            return None
    
    async def _analyze_tmp_trend(self, membrane_id: str) -> Dict:
        """TMP 상승 트렌드 분석"""
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 최근 7일 TMP 데이터
                    await cur.execute("""
                        SELECT 
                            bucket,
                            avg_val as tmp_value
                        FROM influx_agg_1h
                        WHERE tag_name = 'TMP'
                        AND bucket >= NOW() - INTERVAL '7 days'
                        ORDER BY bucket
                    """)
                    
                    rows = await cur.fetchall()
                    
                    if len(rows) < 24:  # 최소 1일 데이터
                        return {'increase_rate': 0, 'current_tmp': 1.5}
                    
                    # 선형 회귀로 상승률 계산
                    times = np.arange(len(rows))
                    values = np.array([float(row[1]) for row in rows])
                    
                    # 선형 회귀
                    coeffs = np.polyfit(times, values, 1)
                    increase_rate = coeffs[0] * 24  # bar/day
                    
                    return {
                        'increase_rate': increase_rate,
                        'current_tmp': values[-1],
                        'initial_tmp': values[0]
                    }
                    
        except Exception as e:
            print(f"[ERROR] TMP trend analysis failed: {e}")
            return {'increase_rate': 0, 'current_tmp': 1.5}
    
    async def _analyze_flux_decline(self, membrane_id: str) -> Dict:
        """플럭스 감소 분석"""
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 플럭스 데이터
                    await cur.execute("""
                        SELECT 
                            bucket,
                            avg_val as flux_value
                        FROM influx_agg_1h
                        WHERE tag_name LIKE '%FLUX%'
                        AND bucket >= NOW() - INTERVAL '7 days'
                        ORDER BY bucket
                    """)
                    
                    rows = await cur.fetchall()
                    
                    if len(rows) < 24:
                        return {'decline_rate': 0, 'current_flux': 100}
                    
                    values = np.array([float(row[1]) for row in rows])
                    
                    # 감소율 계산
                    initial_flux = np.mean(values[:24])  # 첫날 평균
                    current_flux = np.mean(values[-24:])  # 마지막날 평균
                    
                    if initial_flux > 0:
                        decline_rate = (1 - current_flux/initial_flux) * 100 / 7  # %/day
                    else:
                        decline_rate = 0
                    
                    return {
                        'decline_rate': decline_rate,
                        'current_flux': current_flux,
                        'initial_flux': initial_flux
                    }
                    
        except Exception as e:
            print(f"[ERROR] Flux decline analysis failed: {e}")
            return {'decline_rate': 0, 'current_flux': 100}
    
    async def _calculate_cip_efficiency(self, membrane_id: str) -> float:
        """CIP 효율 계산"""
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 최근 CIP 전후 데이터
                    await cur.execute("""
                        SELECT 
                            AVG(CASE WHEN tag_name = 'TMP_BEFORE_CIP' THEN avg_val END) as tmp_before,
                            AVG(CASE WHEN tag_name = 'TMP_AFTER_CIP' THEN avg_val END) as tmp_after,
                            AVG(CASE WHEN tag_name = 'TMP_INITIAL' THEN avg_val END) as tmp_initial
                        FROM influx_agg_1h
                        WHERE tag_name IN ('TMP_BEFORE_CIP', 'TMP_AFTER_CIP', 'TMP_INITIAL')
                        AND bucket >= NOW() - INTERVAL '30 days'
                    """)
                    
                    result = await cur.fetchone()
                    
                    if result and result[0] and result[1] and result[2]:
                        tmp_before = float(result[0])
                        tmp_after = float(result[1])
                        tmp_initial = float(result[2])
                        
                        # CIP 효율 = (회복된 TMP) / (증가했던 TMP)
                        if tmp_before > tmp_initial:
                            efficiency = (tmp_before - tmp_after) / (tmp_before - tmp_initial)
                            return min(max(efficiency, 0), 1)
                    
                    return 0.8  # 기본값
                    
        except Exception as e:
            print(f"[ERROR] CIP efficiency calculation failed: {e}")
            return 0.8
    
    def _classify_fouling_type(self, tmp_trend: Dict, flux_decline: Dict) -> FoulingType:
        """오염 타입 분류"""
        tmp_rate = tmp_trend['increase_rate']
        flux_rate = flux_decline['decline_rate']
        
        # 간단한 분류 로직
        if tmp_rate > 0.3 and flux_rate > 5:
            return FoulingType.ORGANIC
        elif tmp_rate > 0.2 and flux_rate < 3:
            return FoulingType.INORGANIC
        elif tmp_rate < 0.1 and flux_rate > 3:
            return FoulingType.BIOLOGICAL
        elif tmp_rate > 0.1 and flux_rate > 2:
            return FoulingType.COLLOIDAL
        else:
            return FoulingType.MIXED
    
    def _predict_cleaning_schedule(self, tmp_rate: float, flux_rate: float, current_tmp: float) -> tuple:
        """세척 시기 예측"""
        # TMP 기준 예측
        if tmp_rate > 0:
            days_to_cip_tmp = (self.thresholds['cip_trigger_tmp'] - current_tmp) / tmp_rate
        else:
            days_to_cip_tmp = 999
        
        # 플럭스 기준 예측
        if flux_rate > 0:
            days_to_cip_flux = (30 - flux_rate * 7) / flux_rate  # 30% 감소까지
        else:
            days_to_cip_flux = 999
        
        # 더 빠른 시점 선택
        days_to_cip = min(days_to_cip_tmp, days_to_cip_flux)
        
        cleaning_date = datetime.now() + timedelta(days=max(days_to_cip, 1))
        
        # 긴급도 결정
        if days_to_cip <= 1:
            urgency = "immediate"
        elif days_to_cip <= 7:
            urgency = "soon"
        else:
            urgency = "scheduled"
        
        return cleaning_date, urgency
    
    def _generate_recommendations(self, fouling_type: FoulingType, urgency: str, cip_efficiency: float) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        # 긴급도별 권장사항
        if urgency == "immediate":
            recommendations.append("24시간 내 CIP 실시 필요")
        elif urgency == "soon":
            recommendations.append("1주일 내 CIP 일정 수립")
        
        # 오염 타입별 권장사항
        if fouling_type == FoulingType.ORGANIC:
            recommendations.append("알칼리 세정제 사용 권장")
            recommendations.append("세정 온도 40-50°C 유지")
        elif fouling_type == FoulingType.INORGANIC:
            recommendations.append("산성 세정제 사용 권장")
            recommendations.append("킬레이트제 첨가 검토")
        elif fouling_type == FoulingType.BIOLOGICAL:
            recommendations.append("살균제 투입 강화")
            recommendations.append("염소계 세정제 사용")
        
        # CIP 효율 관련
        if cip_efficiency < 0.7:
            recommendations.append("CIP 프로토콜 재검토 필요")
            recommendations.append("세정제 농도 상향 검토")
        
        return recommendations