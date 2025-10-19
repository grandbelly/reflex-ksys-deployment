"""
막파손 진단 시스템
TASK_011: DIAG_IMPLEMENT_MEMBRANE_DAMAGE
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import psycopg


class MembraneStatus(Enum):
    """막 상태"""
    INTACT = "intact"
    MINOR_DAMAGE = "minor_damage"
    MODERATE_DAMAGE = "moderate_damage"
    SEVERE_DAMAGE = "severe_damage"
    FAILED = "failed"


@dataclass
class MembraneDiagnosisResult:
    """막파손 진단 결과"""
    membrane_id: str
    status: MembraneStatus
    damage_probability: float
    location_estimate: str
    conductivity_spike: float
    turbidity_change: float
    salt_rejection_rate: float
    recommendations: List[str]
    timestamp: datetime


class MembraneDamageDiagnostics:
    """막파손 진단 시스템"""
    
    def __init__(self, db_dsn: str):
        self.db_dsn = db_dsn
        
        # 진단 임계값
        self.thresholds = {
            'conductivity_normal': 500,     # μS/cm
            'conductivity_warning': 600,
            'conductivity_critical': 800,
            'turbidity_normal': 0.5,        # NTU
            'turbidity_warning': 1.0,
            'salt_rejection_min': 0.95,     # 95%
            'spike_rate': 1.5               # 150% 급증
        }
    
    async def diagnose_membrane(self, membrane_id: str) -> Optional[MembraneDiagnosisResult]:
        """막파손 진단"""
        try:
            # 수질 데이터 수집
            water_quality = await self._collect_water_quality_data(membrane_id)
            
            if not water_quality:
                return None
            
            # 전도도 급변 감지
            cond_spike = self._detect_conductivity_spike(water_quality)
            
            # 탁도 변화 감지
            turb_change = self._detect_turbidity_change(water_quality)
            
            # 염제거율 계산
            salt_rejection = self._calculate_salt_rejection(water_quality)
            
            # 파손 위치 추정
            location = self._estimate_damage_location(water_quality)
            
            # 종합 진단
            status, damage_prob = self._determine_membrane_status(
                cond_spike, turb_change, salt_rejection
            )
            
            # 권장사항
            recommendations = self._generate_recommendations(status, location)
            
            return MembraneDiagnosisResult(
                membrane_id=membrane_id,
                status=status,
                damage_probability=damage_prob,
                location_estimate=location,
                conductivity_spike=cond_spike,
                turbidity_change=turb_change,
                salt_rejection_rate=salt_rejection,
                recommendations=recommendations,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            print(f"[ERROR] Membrane diagnosis failed: {e}")
            return None
    
    async def _collect_water_quality_data(self, membrane_id: str) -> Dict[str, Any]:
        """수질 데이터 수집"""
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 최근 데이터 조회
                    await cur.execute("""
                        SELECT 
                            tag_name,
                            AVG(avg_val) as current_avg,
                            MAX(max_val) as peak_value,
                            MIN(min_val) as min_value
                        FROM influx_agg_1m
                        WHERE tag_name IN ('COND_IN', 'COND_OUT', 'TURB_IN', 'TURB_OUT', 'TDS_IN', 'TDS_OUT')
                        AND bucket >= NOW() - INTERVAL '1 hour'
                        GROUP BY tag_name
                    """)
                    
                    rows = await cur.fetchall()
                    
                    data = {}
                    for row in rows:
                        tag = row[0]
                        data[tag] = {
                            'avg': float(row[1]) if row[1] else 0,
                            'peak': float(row[2]) if row[2] else 0,
                            'min': float(row[3]) if row[3] else 0
                        }
                    
                    # 이전 기준값 조회
                    await cur.execute("""
                        SELECT 
                            tag_name,
                            AVG(avg_val) as baseline
                        FROM influx_agg_1h
                        WHERE tag_name IN ('COND_OUT', 'TURB_OUT')
                        AND bucket >= NOW() - INTERVAL '7 days'
                        AND bucket <= NOW() - INTERVAL '1 day'
                        GROUP BY tag_name
                    """)
                    
                    baseline_rows = await cur.fetchall()
                    
                    for row in baseline_rows:
                        tag = row[0]
                        if tag in data:
                            data[tag]['baseline'] = float(row[1]) if row[1] else 0
                    
                    return data
                    
        except Exception as e:
            print(f"[ERROR] Data collection failed: {e}")
            return {}
    
    def _detect_conductivity_spike(self, data: Dict) -> float:
        """전도도 급변 감지"""
        if 'COND_OUT' not in data:
            return 0.0
        
        current = data['COND_OUT']['avg']
        baseline = data['COND_OUT'].get('baseline', current)
        peak = data['COND_OUT']['peak']
        
        # 급증률 계산
        if baseline > 0:
            spike_rate = peak / baseline
            if spike_rate > self.thresholds['spike_rate']:
                return spike_rate
        
        return current / self.thresholds['conductivity_normal'] if current > self.thresholds['conductivity_normal'] else 0.0
    
    def _detect_turbidity_change(self, data: Dict) -> float:
        """탁도 변화 감지"""
        if 'TURB_OUT' not in data:
            return 0.0
        
        current = data['TURB_OUT']['avg']
        baseline = data['TURB_OUT'].get('baseline', 0.5)
        
        if baseline > 0:
            change_rate = current / baseline
            return change_rate if change_rate > 1.5 else 0.0
        
        return current / self.thresholds['turbidity_normal'] if current > self.thresholds['turbidity_normal'] else 0.0
    
    def _calculate_salt_rejection(self, data: Dict) -> float:
        """염제거율 계산"""
        if 'TDS_IN' not in data or 'TDS_OUT' not in data:
            if 'COND_IN' in data and 'COND_OUT' in data:
                # 전도도로 대체 계산
                cond_in = data['COND_IN']['avg']
                cond_out = data['COND_OUT']['avg']
                if cond_in > 0:
                    return 1 - (cond_out / cond_in)
            return 0.95  # 기본값
        
        tds_in = data['TDS_IN']['avg']
        tds_out = data['TDS_OUT']['avg']
        
        if tds_in > 0:
            return 1 - (tds_out / tds_in)
        
        return 0.95
    
    def _estimate_damage_location(self, data: Dict) -> str:
        """막파손 위치 추정"""
        # 간단한 로직: 전도도 패턴으로 추정
        if 'COND_OUT' in data:
            peak = data['COND_OUT']['peak']
            avg = data['COND_OUT']['avg']
            
            if peak > avg * 2:
                return "1단 막 모듈 전단부"
            elif peak > avg * 1.5:
                return "1단 막 모듈 중앙부"
            else:
                return "2단 막 모듈"
        
        return "위치 추정 불가"
    
    def _determine_membrane_status(self, cond_spike: float, turb_change: float, salt_rejection: float) -> tuple:
        """막 상태 판정"""
        damage_prob = 0.0
        
        # 전도도 기준
        if cond_spike > 2.0:
            damage_prob += 0.5
        elif cond_spike > 1.5:
            damage_prob += 0.3
        elif cond_spike > 1.2:
            damage_prob += 0.1
        
        # 탁도 기준
        if turb_change > 2.0:
            damage_prob += 0.3
        elif turb_change > 1.5:
            damage_prob += 0.2
        
        # 염제거율 기준
        if salt_rejection < 0.90:
            damage_prob += 0.4
        elif salt_rejection < 0.95:
            damage_prob += 0.2
        
        # 상태 결정
        if damage_prob >= 0.8:
            status = MembraneStatus.SEVERE_DAMAGE
        elif damage_prob >= 0.5:
            status = MembraneStatus.MODERATE_DAMAGE
        elif damage_prob >= 0.2:
            status = MembraneStatus.MINOR_DAMAGE
        else:
            status = MembraneStatus.INTACT
        
        return status, min(damage_prob, 1.0)
    
    def _generate_recommendations(self, status: MembraneStatus, location: str) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        if status == MembraneStatus.SEVERE_DAMAGE:
            recommendations.append("즉시 해당 막 모듈 격리")
            recommendations.append("예비 막 모듈로 교체")
            recommendations.append(f"파손 위치 확인: {location}")
        elif status == MembraneStatus.MODERATE_DAMAGE:
            recommendations.append("운전 압력 감소")
            recommendations.append("수질 모니터링 강화")
            recommendations.append("24시간 내 정비 점검")
        elif status == MembraneStatus.MINOR_DAMAGE:
            recommendations.append("수질 추이 관찰")
            recommendations.append("다음 정비 시 상세 점검")
        
        return recommendations