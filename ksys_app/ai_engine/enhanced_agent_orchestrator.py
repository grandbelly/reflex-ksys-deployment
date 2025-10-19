"""Enhanced Multi-Agent System with Clear R&R (Roles & Responsibilities)"""

import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from openai import AsyncOpenAI
from ksys_app.queries.latest import latest_snapshot
from ksys_app.queries.qc import qc_rules
from ksys_app.ai_engine.audit_agent_system import initialize_audit_system, audit_agent_performance
from ksys_app.ai_engine.response_validator import ResponseValidator, generate_validated_response
from ksys_app.ai_engine.dynamic_rag_engine import DynamicRAGEngine
from ksys_app.ai_engine.five_w1h_agent import FiveW1HAgent
# Load environment variables
def load_env():
    """Simple environment loader"""
    import os
    from pathlib import Path
    
    # .env 파일 경로 찾기
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value


@dataclass
class AgentContext:
    """Enhanced Agent Context with specific data domains"""
    query: str
    
    # Data Domains (각 에이전트별 전담 영역)
    raw_data: Dict[str, Any] = field(default_factory=dict)  # ResearchAgent 전담
    insights: Dict[str, Any] = field(default_factory=dict)  # AnalysisAgent 전담  
    quality_report: Dict[str, Any] = field(default_factory=dict)  # ReviewAgent 전담
    
    # Shared Context
    final_response: str = ""
    confidence_score: float = 0.0


class BaseAgent:
    """Base Agent with enhanced logging and specialization"""
    
    def __init__(self, name: str, role: str, specialization: str):
        self.name = name
        self.role = role
        self.specialization = specialization  # 전문 분야
        self.rag_engine = None
        
    async def initialize(self, rag_engine=None):
        self.rag_engine = rag_engine
        print(f"🔧 {self.name} 초기화 완료 - 전문분야: {self.specialization}")
        
    async def process(self, context: AgentContext) -> AgentContext:
        raise NotImplementedError("Each agent must implement process method")


class EnhancedResearchAgent(BaseAgent):
    """🕵️ Data Collection Specialist - 데이터 수집 전문가"""
    
    def __init__(self):
        super().__init__(
            "ResearchAgent", 
            "데이터 수집 및 전처리",
            "센서 데이터, QC 규칙, 이력 데이터 수집 전문"
        )
        
    async def process(self, context: AgentContext) -> AgentContext:
        """Smart Data Collection Based on Query Analysis"""
        
        print(f"🧠 {self.name} 실행 중... 질의 분석: '{context.query[:50]}...'")
        
        # 1. Query Classification (질의 유형 분류)
        query_type = self._classify_query(context.query)
        print(f"📋 질의 유형 분류: {query_type}")
        
        # 2. Targeted Data Collection (유형별 맞춤 데이터 수집)
        if query_type == "correlation_analysis":
            await self._collect_correlation_data(context)
        elif query_type == "comparison_analysis":
            await self._collect_comparison_data(context)
        elif query_type == "current_status":
            await self._collect_current_data(context)
        elif query_type == "historical_trend":
            await self._collect_historical_data(context)
        elif query_type == "qc_violation":
            await self._collect_qc_focused_data(context)
        elif query_type == "system_overview":
            await self._collect_comprehensive_data(context)
        else:
            await self._collect_adaptive_data(context)
            
        # 3. Data Quality Assessment
        quality_score = self._assess_data_quality(context.raw_data)
        context.raw_data["quality_score"] = quality_score
        
        print(f"✅ {self.name} 완료 - 수집된 데이터: {list(context.raw_data.keys())}, 품질점수: {quality_score:.2f}")
        return context
    
    def _classify_query(self, query: str) -> str:
        """Intelligent Query Classification"""
        query_lower = query.lower()
        
        # 상관성/상관분석 질의
        if any(keyword in query_lower for keyword in ["상관", "관계", "correlation", "연관"]):
            return "correlation_analysis"
        
        # 현재 상태 질의
        elif any(keyword in query_lower for keyword in ["현재", "지금", "상태는"]):
            return "current_status"
            
        # 비교 분석 질의 (어제와 비교)
        elif any(keyword in query_lower for keyword in ["어제", "비교", "변했", "변화", "compare", "change"]):
            return "comparison_analysis"
        
        # 이력/트렌드 질의  
        elif any(keyword in query_lower for keyword in ["일주일", "트렌드", "추세"]):
            return "historical_trend"
            
        # QC 위반 질의
        elif any(keyword in query_lower for keyword in ["위반", "경고", "초과", "임계"]):
            return "qc_violation"
            
        # 시스템 전체 개요
        elif any(keyword in query_lower for keyword in ["전체", "요약", "종합", "전반적"]):
            return "system_overview"
            
        return "adaptive"
    
    async def _collect_current_data(self, context: AgentContext):
        """현재 상태 중심 데이터 수집"""
        try:
            # 여러 센서 태그 추출 (상관분석 등을 위해)
            sensor_tags = self._extract_sensor_tags(context.query)
            
            if sensor_tags:
                # 여러 센서가 있으면 모두 수집
                if len(sensor_tags) > 1:
                    context.raw_data["target_sensors"] = sensor_tags
                    all_sensor_data = []
                    for tag in sensor_tags:
                        data = await latest_snapshot(tag)
                        if data:
                            all_sensor_data.extend(data)
                    context.raw_data["focused_data"] = all_sensor_data
                    print(f"🔍 Enhanced Agent - 다중 센서 데이터 로드: {sensor_tags}")
                else:
                    # 단일 센서만 있으면 기존 로직
                    sensor_tag = sensor_tags[0]
                    sensor_data = await latest_snapshot(sensor_tag)
                    context.raw_data["target_sensor"] = sensor_tag
                    context.raw_data["focused_data"] = sensor_data
                    
                # QC 규칙 수집
                qc_data = []
                for tag in sensor_tags:
                    qc = await qc_rules(tag)
                    if qc:
                        qc_data.extend(qc)
                context.raw_data["relevant_qc"] = qc_data
            else:
                # 전체 센서 현재 상태
                sensor_data = await latest_snapshot(None)
                context.raw_data["all_sensors"] = sensor_data
                print(f"🔍 Enhanced Agent - 센서 데이터 로드됨: {len(sensor_data) if sensor_data else 0}개")
                
                # 전체 QC 규칙
                qc_data = await qc_rules(None)
                context.raw_data["relevant_qc"] = qc_data
            
        except Exception as e:
            context.raw_data["error"] = f"현재 데이터 수집 실패: {e}"
    
    async def _collect_historical_data(self, context: AgentContext):
        """이력 데이터 중심 수집"""
        try:
            from ksys_app.db import q
            
            # 시간 범위 추출
            days = self._extract_time_range(context.query)
            sensor_tag = self._extract_sensor_tag(context.query)
            
            # 이력 데이터 조회
            start_date = datetime.now() - timedelta(days=days)
            hist_query = '''
            SELECT tag_name, COUNT(*) as count, 
                   MIN(value) as min_val, MAX(value) as max_val,
                   AVG(value) as avg_val, MIN(ts) as start_time, MAX(ts) as end_time
            FROM public.influx_hist 
            WHERE ts >= %s
            ''' + (f" AND tag_name = '{sensor_tag}'" if sensor_tag else "") + '''
            GROUP BY tag_name ORDER BY count DESC LIMIT 10
            '''
            
            result = await q(hist_query, (start_date,))
            context.raw_data["historical_summary"] = result
            context.raw_data["time_range_days"] = days
            context.raw_data["target_sensor"] = sensor_tag
            
        except Exception as e:
            context.raw_data["error"] = f"이력 데이터 수집 실패: {e}"
    
    async def _collect_qc_focused_data(self, context: AgentContext):
        """QC 위반 중심 데이터 수집"""
        try:
            # 현재 센서 데이터
            sensor_data = await latest_snapshot(None)
            qc_data = await qc_rules(None)
            
            # 현재 센서 데이터 저장 (response validator에서 필요)
            context.raw_data["current_sensors"] = sensor_data
            context.raw_data["relevant_qc"] = qc_data
            
            # QC 위반 사항만 필터링
            violations = []
            for sensor in sensor_data:
                for qc in qc_data:
                    if qc.get('tag_name') == sensor.get('tag_name'):
                        value = float(sensor.get('value', 0))
                        max_val = float(qc.get('max_val', float('inf')))
                        min_val = float(qc.get('min_val', float('-inf')))
                        warn_max = float(qc.get('warn_max', max_val))
                        warn_min = float(qc.get('warn_min', min_val))
                        crit_max = float(qc.get('crit_max', max_val))
                        crit_min = float(qc.get('crit_min', min_val))
                        
                        # 위험, 경고, 위반 판단
                        if value > crit_max or value < crit_min:
                            severity = 'critical'
                            threshold = crit_max if value > crit_max else crit_min
                        elif value > warn_max or value < warn_min:
                            severity = 'warning'
                            threshold = warn_max if value > warn_max else warn_min
                        elif value > max_val or value < min_val:
                            severity = 'violation'
                            threshold = max_val if value > max_val else min_val
                        else:
                            continue
                        
                        violations.append({
                            'sensor': sensor.get('tag_name'),
                            'current_value': value,
                            'threshold': threshold,
                            'violation_type': 'max' if value > threshold else 'min',
                            'severity': severity,
                            'severity_score': abs(value - threshold)
                        })
            
            context.raw_data["violations"] = violations
            context.raw_data["total_sensors"] = len(sensor_data)
            context.raw_data["violation_rate"] = len(violations) / len(sensor_data) * 100 if sensor_data else 0
            
        except Exception as e:
            context.raw_data["error"] = f"QC 데이터 수집 실패: {e}"
    
    async def _collect_comprehensive_data(self, context: AgentContext):
        """종합적 시스템 데이터 수집"""
        try:
            # 모든 기본 데이터 수집
            await self._collect_current_data(context)
            
            # 시스템 통계 추가
            from ksys_app.db import q
            
            stats_query = '''
            SELECT 
                COUNT(DISTINCT tag_name) as total_sensors,
                COUNT(*) as total_records,
                MIN(ts) as oldest_record,
                MAX(ts) as latest_record
            FROM public.influx_latest
            '''
            
            stats = await q(stats_query)
            context.raw_data["system_stats"] = stats[0] if stats else {}
            
        except Exception as e:
            context.raw_data["error"] = f"종합 데이터 수집 실패: {e}"
    
    async def _collect_correlation_data(self, context: AgentContext):
        """상관분석용 데이터 수집"""
        try:
            # 여러 센서 태그 추출
            sensor_tags = self._extract_sensor_tags(context.query)
            
            if len(sensor_tags) >= 2:
                print(f"🔗 상관분석 데이터 수집: {sensor_tags}")
                context.raw_data["correlation_sensors"] = sensor_tags
                
                # 각 센서의 현재 데이터
                all_sensor_data = []
                for tag in sensor_tags:
                    data = await latest_snapshot(tag)
                    if data:
                        all_sensor_data.extend(data)
                context.raw_data["sensor_data"] = all_sensor_data
                
                # 30일 이력 데이터 (상관분석용)
                from ksys_app.db import q
                from datetime import datetime, timedelta
                
                start_date = datetime.now() - timedelta(days=30)
                
                # psycopg3에서 IN 절 처리
                placeholders = ', '.join(['%s'] * len(sensor_tags))
                hist_query = f'''
                SELECT tag_name, 
                       COUNT(*) as count,
                       MIN(value) as min_val, 
                       MAX(value) as max_val,
                       AVG(value) as avg_val,
                       STDDEV(value) as std_val
                FROM public.influx_hist 
                WHERE ts >= %s AND tag_name IN ({placeholders})
                GROUP BY tag_name
                '''
                
                params = [start_date] + sensor_tags
                result = await q(hist_query, tuple(params))
                context.raw_data["correlation_stats"] = result
                
                # 샘플 데이터 포인트 수집 (각 센서별 최근 10개)
                sample_points = []
                for tag in sensor_tags[:2]:  # 최대 2개 센서만
                    sample_query = '''
                    SELECT tag_name, ts, value
                    FROM public.influx_hist
                    WHERE tag_name = %s AND ts >= %s
                    ORDER BY ts DESC
                    LIMIT 10
                    '''
                    sample_result = await q(sample_query, (tag, start_date))
                    if sample_result:
                        sample_points.extend(sample_result)
                
                context.raw_data["correlation_samples"] = sample_points
                if sample_points:
                    print(f"[DATA] Collected {len(sample_points)} sample data points for correlation")
                
                # QC 규칙
                qc_data = []
                for tag in sensor_tags:
                    qc = await qc_rules(tag)
                    if qc:
                        qc_data.extend(qc)
                context.raw_data["relevant_qc"] = qc_data
                
            else:
                # 센서가 부족하면 일반 데이터 수집
                await self._collect_current_data(context)
                
        except Exception as e:
            import traceback
            error_msg = f"상관분석 데이터 수집 실패: {e}\n{traceback.format_exc()}"
            print(f"[ERROR] {error_msg}")
            context.raw_data["error"] = error_msg
    
    async def _collect_comparison_data(self, context: AgentContext):
        """비교 분석용 데이터 수집 (어제 vs 오늘)"""
        try:
            from ksys_app.db import q
            from datetime import datetime, timedelta
            
            # 시간 범위 설정
            now = datetime.now()
            yesterday_start = now - timedelta(days=2)
            yesterday_end = now - timedelta(days=1)
            today_start = now - timedelta(days=1)
            
            # 비교 쿼리
            comparison_query = """
            WITH yesterday_data AS (
                SELECT 
                    tag_name,
                    AVG(value) as yesterday_avg,
                    MIN(value) as yesterday_min,
                    MAX(value) as yesterday_max,
                    COUNT(*) as yesterday_count
                FROM influx_hist
                WHERE ts >= %s AND ts < %s
                GROUP BY tag_name
            ),
            today_data AS (
                SELECT 
                    tag_name,
                    AVG(value) as today_avg,
                    MIN(value) as today_min,
                    MAX(value) as today_max,
                    COUNT(*) as today_count
                FROM influx_hist
                WHERE ts >= %s AND ts < %s
                GROUP BY tag_name
            )
            SELECT 
                COALESCE(y.tag_name, t.tag_name) as tag_name,
                y.yesterday_avg,
                t.today_avg,
                t.today_avg - y.yesterday_avg as avg_change,
                ABS((t.today_avg - y.yesterday_avg) / NULLIF(y.yesterday_avg, 0) * 100) as pct_change,
                y.yesterday_min,
                y.yesterday_max,
                t.today_min,
                t.today_max
            FROM yesterday_data y
            FULL OUTER JOIN today_data t ON y.tag_name = t.tag_name
            WHERE y.yesterday_avg IS NOT NULL AND t.today_avg IS NOT NULL
            ORDER BY ABS((t.today_avg - y.yesterday_avg) / NULLIF(y.yesterday_avg, 0)) DESC NULLS LAST
            LIMIT 10
            """
            
            result = await q(comparison_query, (yesterday_start, yesterday_end, today_start, now))
            context.raw_data["comparison_data"] = result
            
            # 가장 큰 변화 요약
            if result:
                top_changes = []
                for row in result[:5]:  # 상위 5개
                    change_info = {
                        'tag_name': row.get('tag_name'),
                        'yesterday_avg': row.get('yesterday_avg', 0),
                        'today_avg': row.get('today_avg', 0),
                        'change': row.get('avg_change', 0),
                        'pct_change': row.get('pct_change', 0)
                    }
                    top_changes.append(change_info)
                context.raw_data["top_changes"] = top_changes
                
                # 변화율이 가장 큰 센서
                if top_changes:
                    max_change = top_changes[0]
                    context.raw_data["max_change_sensor"] = max_change
            
            # 현재 상태도 함께 수집
            from ksys_app.queries.latest import latest_snapshot
            sensor_data = await latest_snapshot(None)
            context.raw_data["current_sensors"] = sensor_data
            
            # QC 규칙
            from ksys_app.queries.qc import qc_rules
            qc_data = await qc_rules(None)
            context.raw_data["relevant_qc"] = qc_data
            
            print(f"[COMPARISON] Data collected: {len(result)} sensors compared")
            
        except Exception as e:
            import traceback
            error_msg = f"비교 분석 데이터 수집 실패: {e}\n{traceback.format_exc()}"
            print(f"[ERROR] {error_msg}")
            context.raw_data["error"] = error_msg
    
    async def _collect_adaptive_data(self, context: AgentContext):
        """적응형 데이터 수집"""
        # 키워드 기반 동적 수집
        await self._collect_current_data(context)
    
    def _extract_sensor_tag(self, query: str) -> Optional[str]:
        """센서 태그 추출 (단일)"""
        import re
        pattern = r'D\d{3}'
        match = re.search(pattern, query.upper())
        return match.group() if match else None
    
    def _extract_sensor_tags(self, query: str) -> List[str]:
        """센서 태그 추출 (복수)"""
        import re
        pattern = r'D\d{3}'
        matches = re.findall(pattern, query.upper())
        return matches if matches else []
    
    def _extract_time_range(self, query: str) -> int:
        """시간 범위 추출"""
        query_lower = query.lower()
        if '일주일' in query_lower or '1주일' in query_lower:
            return 7
        elif '어제' in query_lower:
            return 1
        elif '한달' in query_lower or '1달' in query_lower:
            return 30
        return 7  # 기본값
    
    def _assess_data_quality(self, raw_data: Dict) -> float:
        """데이터 품질 평가"""
        score = 0.0
        
        # 데이터 존재 여부
        if raw_data and not raw_data.get("error"):
            score += 0.5
            
        # 데이터 완성도
        if any(key in raw_data for key in ["all_sensors", "focused_data", "violations"]):
            score += 0.3
            
        # QC 규칙 연동
        if "relevant_qc" in raw_data:
            score += 0.2
            
        return min(score, 1.0)


class EnhancedAnalysisAgent(BaseAgent):
    """🔍 Intelligence & Insight Generator - 지능형 인사이트 생성기"""
    
    def __init__(self):
        super().__init__(
            "AnalysisAgent",
            "데이터 분석 및 인사이트 도출", 
            "패턴 분석, 이상 탐지, 예측적 인사이트 전문"
        )
        
    async def process(self, context: AgentContext) -> AgentContext:
        """Intelligent Analysis & Insight Generation"""
        
        print(f"🧠 {self.name} 실행 중... 분석 대상: {list(context.raw_data.keys())}")
        
        # 1. Pattern Analysis (패턴 분석)
        await self._analyze_patterns(context)
        
        # 2. Anomaly Detection (이상 탐지)
        await self._detect_anomalies(context)
        
        # 3. Predictive Insights (예측적 인사이트)
        await self._generate_insights(context)
        
        # 4. Confidence Assessment (신뢰도 평가)
        context.confidence_score = self._calculate_confidence(context.insights)
        
        print(f"✅ {self.name} 완료 - 인사이트: {list(context.insights.keys())}, 신뢰도: {context.confidence_score:.2f}")
        return context
        
    async def _analyze_patterns(self, context: AgentContext):
        """패턴 분석"""
        patterns = {}
        
        # 센서 값 분포 패턴
        if "all_sensors" in context.raw_data:
            sensors = context.raw_data["all_sensors"]
            values = [s.get("value", 0) for s in sensors if s.get("value")]
            
            if values:
                patterns["value_distribution"] = {
                    "mean": sum(values) / len(values),
                    "range": max(values) - min(values), 
                    "outliers": len([v for v in values if abs(v - sum(values)/len(values)) > 2 * (max(values) - min(values))/len(values)])
                }
        
        # 상관분석 패턴 추가
        if "correlation_sensors" in context.raw_data:
            correlation_sensors = context.raw_data["correlation_sensors"]
            if "correlation_stats" in context.raw_data:
                stats = context.raw_data["correlation_stats"]
                patterns["correlation"] = {
                    "sensors": correlation_sensors,
                    "stats": stats,
                    "type": "correlation_analysis"
                }
                
                # PandasAnalysisEngine을 사용한 상관분석 (30일 데이터)
                from ksys_app.ai_engine.pandas_analysis_engine import PandasAnalysisEngine
                try:
                    engine = PandasAnalysisEngine()
                    result = await engine.analyze_sensor_data(
                        sensors=correlation_sensors,
                        analysis_type='correlation',
                        hours=720  # 30일
                    )
                    if result.correlations:
                        patterns["correlation"]["coefficients"] = result.correlations
                        patterns["correlation"]["heatmap"] = result.heatmap_data
                except Exception as e:
                    patterns["correlation"]["error"] = str(e)
        
        context.insights["patterns"] = patterns
    
    async def _detect_anomalies(self, context: AgentContext):
        """이상 상황 탐지"""
        anomalies = []
        
        # QC 위반 기반 이상 탐지
        if "violations" in context.raw_data:
            violations = context.raw_data["violations"]
            
            # 심각도별 분류 (문자열 기반)
            critical = [v for v in violations if v.get("severity") == "critical"]
            warning = [v for v in violations if v.get("severity") == "warning"]
            minor = [v for v in violations if v.get("severity") == "violation"]
            
            anomalies.append({
                "type": "qc_violations",
                "critical_count": len(critical),
                "warning_count": len(warning),
                "minor_count": len(minor),
                "most_severe": max(violations, key=lambda x: x.get("severity_score", 0)) if violations else None
            })
        
        context.insights["anomalies"] = anomalies
    
    async def _generate_insights(self, context: AgentContext):
        """예측적 인사이트 생성"""
        insights = []
        
        # 시스템 건강도 평가
        if "violation_rate" in context.raw_data:
            violation_rate = context.raw_data["violation_rate"]
            
            if violation_rate > 20:
                insights.append("⚠️ 높은 위반율 감지 - 시스템 점검 필요")
            elif violation_rate > 10:
                insights.append("🔍 경계 수준 위반율 - 모니터링 강화 권장") 
            else:
                insights.append("✅ 안정적인 시스템 상태 유지 중")
        
        # 특정 센서 인사이트
        if "target_sensor" in context.raw_data:
            target = context.raw_data["target_sensor"]
            insights.append(f"🎯 {target} 센서 집중 분석 완료")
        
        context.insights["predictions"] = insights
    
    def _calculate_confidence(self, insights: Dict) -> float:
        """분석 신뢰도 계산"""
        score = 0.0
        
        if insights.get("patterns"):
            score += 0.3
        if insights.get("anomalies"): 
            score += 0.4
        if insights.get("predictions"):
            score += 0.3
            
        return score


class EnhancedReviewAgent(BaseAgent):
    """🔍 Quality Assurance & Validation Expert - 품질 보증 전문가"""
    
    def __init__(self):
        super().__init__(
            "ReviewAgent",
            "품질 검증 및 최종 승인",
            "결과 검증, 정확성 확인, 개선안 제시 전문"
        )
        
    async def process(self, context: AgentContext) -> AgentContext:
        """Comprehensive Quality Review & Validation"""
        
        print(f"🧠 {self.name} 실행 중... 검토 대상: 데이터 품질 + 분석 신뢰도")
        
        # 1. Data Validity Check (데이터 유효성 검증)
        data_validation = self._validate_data_quality(context)
        
        # 2. Analysis Accuracy Review (분석 정확성 검토)
        analysis_validation = self._validate_analysis_quality(context) 
        
        # 3. Logic Consistency Check (논리 일관성 검증)
        logic_validation = self._validate_logic_consistency(context)
        
        # 4. Improvement Recommendations (개선 권고사항)
        recommendations = self._generate_recommendations(context)
        
        # 5. Final Quality Report
        context.quality_report = {
            "data_validation": data_validation,
            "analysis_validation": analysis_validation, 
            "logic_validation": logic_validation,
            "recommendations": recommendations,
            "overall_quality": (data_validation["score"] + analysis_validation["score"] + logic_validation["score"]) / 3
        }
        
        print(f"✅ {self.name} 완료 - 전체 품질점수: {context.quality_report['overall_quality']:.2f}")
        return context
    
    def _validate_data_quality(self, context: AgentContext) -> Dict:
        """데이터 품질 검증"""
        score = 0.0
        issues = []
        
        # 데이터 존재성 확인
        if context.raw_data and not context.raw_data.get("error"):
            score += 0.5
        else:
            issues.append("데이터 수집 오류 발생")
            
        # 데이터 완전성 확인
        if context.raw_data.get("quality_score", 0) > 0.7:
            score += 0.3
        else:
            issues.append("데이터 완전성 부족")
            
        # QC 규칙 연동 확인
        if "relevant_qc" in context.raw_data:
            score += 0.2
        else:
            issues.append("QC 규칙 연동 부족")
            
        return {"score": score, "issues": issues}
    
    def _validate_analysis_quality(self, context: AgentContext) -> Dict:
        """분석 품질 검증"""
        score = 0.0
        issues = []
        
        # 인사이트 존재성 확인
        if context.insights and len(context.insights) > 0:
            score += 0.4
        else:
            issues.append("의미있는 인사이트 부족")
        
        # 신뢰도 확인
        if context.confidence_score > 0.7:
            score += 0.3
        else:
            issues.append("분석 신뢰도 낮음")
            
        # 패턴 분석 확인
        if context.insights.get("patterns"):
            score += 0.3
        else:
            issues.append("패턴 분석 부족")
            
        return {"score": score, "issues": issues}
    
    def _validate_logic_consistency(self, context: AgentContext) -> Dict:
        """논리 일관성 검증"""
        score = 0.8  # 기본적으로 높은 점수 (모순 발견시 차감)
        issues = []
        
        # 데이터-결론 일관성 확인
        violations = context.raw_data.get("violations", [])
        predictions = context.insights.get("predictions", [])
        
        if violations and not any("위반" in pred for pred in predictions):
            score -= 0.3
            issues.append("위반 사항과 결론 불일치")
            
        return {"score": score, "issues": issues}
    
    def _generate_recommendations(self, context: AgentContext) -> List[str]:
        """개선 권고사항 생성"""
        recommendations = []
        
        # 데이터 품질 개선
        if context.raw_data.get("quality_score", 1.0) < 0.5:
            recommendations.append("🔧 데이터 수집 프로세스 점검 필요")
            
        # 심각한 위반 사항 대응
        violations = context.raw_data.get("violations", [])
        critical_violations = [v for v in violations if v.get("severity") == "critical"]
        
        if critical_violations:
            recommendations.append(f"🚨 {len(critical_violations)}개 심각한 위반 즉시 조치 필요")
            
        # 모니터링 강화
        if context.raw_data.get("violation_rate", 0) > 10:
            recommendations.append("📊 모니터링 주기 단축 권장")
            
        return recommendations


class EnhancedMultiAgentOrchestrator:
    """Enhanced Multi-Agent System with AuditAgent & Reinforcement Learning"""
    
    def __init__(self):
        self.research_agent = EnhancedResearchAgent()
        self.analysis_agent = EnhancedAnalysisAgent()
        self.review_agent = EnhancedReviewAgent()
        self.dynamic_rag = None  # Dynamic RAG Engine 추가
        self.five_w1h_agent = FiveW1HAgent()  # 5W1H Agent 추가
        self.openai_client = None
        self.audit_system_initialized = False
        
    async def initialize(self, rag_engine=None):
        """시스템 초기화"""
        print("🚀 Enhanced Multi-Agent System 초기화 중...")
        
        # OpenAI 클라이언트 초기화
        load_env()
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            self.openai_client = AsyncOpenAI(api_key=api_key)
            print("✅ Enhanced OpenAI 클라이언트 초기화 완료")
            
        # Dynamic RAG Engine 초기화
        try:
            self.dynamic_rag = DynamicRAGEngine()
            await self.dynamic_rag.initialize()
            print("✅ Dynamic RAG Engine 초기화 완료")
        except Exception as e:
            print(f"⚠️ Dynamic RAG Engine 초기화 실패: {e}")
            self.dynamic_rag = None

        # 각 에이전트 초기화
        await self.research_agent.initialize(rag_engine)
        await self.analysis_agent.initialize(rag_engine)
        await self.review_agent.initialize(rag_engine)
        
        # AuditAgent 시스템 초기화
        if not self.audit_system_initialized:
            await initialize_audit_system(self.openai_client)
            self.audit_system_initialized = True
            print("🔍 AuditAgent + 강화학습 시스템 초기화 완료")
        
        print("🎯 Enhanced Multi-Agent System with Audit 준비 완료")
    
    async def process_query(self, query: str) -> str:
        """Enhanced Multi-Agent Processing Pipeline"""
        
        print(f"\n{'='*60}")
        print(f"🧠 Enhanced Multi-Agent Processing 시작")
        print(f"📝 Query: {query}")
        print(f"{'='*60}")
        
        # 컨텍스트 초기화
        context = AgentContext(query=query)
        
        try:
            total_start_time = time.time()
            
            # 1단계: 전문 데이터 수집 + 감사
            print(f"\n🔍 1단계: 전문 데이터 수집")
            start_time = time.time()
            context = await self.research_agent.process(context)
            execution_time = time.time() - start_time
            
            # ResearchAgent 감사
            if self.audit_system_initialized:
                audit_result, learning_history = await audit_agent_performance(
                    "ResearchAgent", query, context, execution_time
                )
            
            # 2단계: 지능형 분석 + 감사
            print(f"\n📊 2단계: 지능형 분석")
            start_time = time.time()
            context = await self.analysis_agent.process(context)
            execution_time = time.time() - start_time
            
            # AnalysisAgent 감사
            if self.audit_system_initialized:
                audit_result, learning_history = await audit_agent_performance(
                    "AnalysisAgent", query, context, execution_time
                )
            
            # 3단계: 품질 검증 + 감사
            print(f"\n🔍 3단계: 품질 검증")
            start_time = time.time()
            context = await self.review_agent.process(context)
            execution_time = time.time() - start_time
            
            # ReviewAgent 감사
            if self.audit_system_initialized:
                audit_result, learning_history = await audit_agent_performance(
                    "ReviewAgent", query, context, execution_time
                )
            
            # 4단계: Dynamic RAG로 실시간 데이터 조회
            print(f"\n🔄 4단계: Dynamic RAG로 실시간 데이터 조회")
            if self.dynamic_rag:
                try:
                    rag_response = await self.dynamic_rag.process_natural_language_query(query)
                    context.raw_data["dynamic_rag_data"] = rag_response.get('data', [])
                    context.raw_data["dynamic_rag_sql"] = rag_response.get('sql', '')
                    context.raw_data["dynamic_rag_metadata"] = rag_response.get('metadata', {})
                    print(f"✅ Dynamic RAG 조회 완료: {rag_response['metadata'].get('row_count', 0)}개 데이터")
                except Exception as e:
                    print(f"⚠️ Dynamic RAG 조회 실패: {e}")

            # 5단계: 5W1H 구조화
            print(f"\n📋 5단계: 5W1H 원칙으로 구조화")
            result = await self.five_w1h_agent.process(context)

            # 6단계: 최종 응답 생성 (할루시네이션 검증 적용)
            print(f"\n🤖 6단계: 최종 응답 생성 (검증 적용)")
            
            # 컨텍스트를 딕셔너리로 변환
            context_dict = {
                'current_data': context.raw_data.get('focused_data', context.raw_data.get('all_sensors', [])),
                'current_sensors': context.raw_data.get('current_sensors', []),
                'qc_rules': context.raw_data.get('relevant_qc', []),
                'query': query,
                'correlation_data': context.insights.get('patterns', {}).get('correlation', {}),
                'correlation_sensors': context.raw_data.get('correlation_sensors', []),
                'correlation_stats': context.raw_data.get('correlation_stats', []),
                'correlation_samples': context.raw_data.get('correlation_samples', []),
                'comparison_data': context.raw_data.get('comparison_data', []),
                'top_changes': context.raw_data.get('top_changes', []),
                'max_change_sensor': context.raw_data.get('max_change_sensor', {})
            }
            
            # 검증된 응답 생성 시도
            try:
                validated_response = await generate_validated_response(query, context_dict)
                print("✅ 할루시네이션 검증 통과")
                
                # 시각화 데이터와 함께 반환
                if hasattr(context, 'visualizations') and context.visualizations:
                    return {
                        'text': validated_response,
                        'visualizations': context.visualizations
                    }
                return validated_response
            except Exception as e:
                print(f"⚠️ 검증 실패, 기존 방식 사용: {e}")
                final_response = await self._generate_enhanced_response(query, context)
            
            total_execution_time = time.time() - total_start_time
            
            print(f"\n✅ Enhanced Multi-Agent Processing 완료")
            print(f"📋 품질점수: {context.quality_report.get('overall_quality', 0):.2f}")
            print(f"🎯 신뢰도: {context.confidence_score:.2f}")
            print(f"⏱️ 총 실행시간: {total_execution_time:.2f}초")
            print(f"{'='*60}\n")
            
            # final_response가 딕셔너리이면 그대로 리턴 (시각화 데이터 포함)
            return final_response
            
        except Exception as e:
            error_msg = f"❌ Enhanced Multi-Agent 처리 오류: {str(e)}"
            print(error_msg)
            return error_msg
    
    async def _generate_enhanced_response(self, query: str, context: AgentContext) -> str:
        """Dynamic RAG + 5W1H 기반 최종 응답 생성"""

        # 5W1H 구조화된 응답이 있으면 우선 사용
        if hasattr(context, 'five_w1h'):
            return self._format_5w1h_response(context)

        
        if not self.openai_client:
            return self._generate_fallback_response(context)
            
        try:
            # 전문화된 시스템 프롬프트 - 환각 방지 강화
            system_prompt = """당신은 산업용 센서 모니터링 시스템의 전문 AI 어시스턴트입니다.

중요 규칙 (절대 준수):
1. Multi-Agent가 제공한 데이터만 사용하세요
2. 제공되지 않은 수치, 임계값, 품질점수를 절대 창작하지 마세요
3. 데이터가 없으면 "데이터 없음"이라고 명확히 표시하세요
4. 모든 숫자는 제공된 값 그대로 사용하세요 (추정 금지)

응답 원칙:
1. 사용자 질문에 직접적으로 답변
2. 실제 데이터 기반 구체적인 수치와 상태 제시
3. 발견된 이상 사항이나 패턴을 명확히 설명
4. 실행 가능한 권장사항 제공
5. 한국어로 전문적이면서도 이해하기 쉽게 설명

분석 결과의 신뢰도와 품질 점수를 투명하게 공개하세요."""

            # 컨텍스트 조합
            context_summary = self._build_context_summary(context)
            
            user_prompt = f"""사용자 질문: {query}

Multi-Agent 분석 결과:
{context_summary}

위 전문 분석 결과를 바탕으로 사용자에게 정확하고 유용한 답변을 제공해주세요."""

            # OpenAI API 호출
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,  # 환각 방지를 위해 0.7 → 0.2로 낮춤
                max_tokens=1000
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # 시각화 데이터 추가
            from ksys_app.ai_engine.visualization_generator import generate_visualization_data, format_visualization_response
            
            sensor_data = context.raw_data.get("all_sensors", [])
            qc_data = context.raw_data.get("relevant_qc", [])
            print(f"🎨 시각화 생성기에 전달되는 데이터: 센서 {len(sensor_data)}개, QC {len(qc_data)}개")
            
            viz_data = await generate_visualization_data(
                query,
                sensor_data,
                qc_data,
                context.raw_data.get("historical_summary")
            )
            
            if viz_data:
                return format_visualization_response(ai_response, viz_data)
            
            return ai_response
            
        except Exception as e:
            print(f"❌ OpenAI 응답 생성 실패: {e}")
            return self._generate_fallback_response(context)
    
    def _build_context_summary(self, context: AgentContext) -> str:
        """컨텍스트 요약 생성"""
        summary_parts = []
        
        # 데이터 수집 결과
        summary_parts.append("🔍 **데이터 수집 결과**:")
        if context.raw_data:
            for key, value in context.raw_data.items():
                if key != "error":
                    summary_parts.append(f"- {key}: {str(value)[:100]}...")
        
        # 분석 인사이트
        summary_parts.append("\n📊 **분석 인사이트**:")
        if context.insights:
            for key, value in context.insights.items():
                summary_parts.append(f"- {key}: {str(value)[:100]}...")
        
        # 품질 보고서
        summary_parts.append(f"\n🔍 **품질 검증**: {context.quality_report.get('overall_quality', 0):.2f}/1.0")
        if context.quality_report.get("recommendations"):
            summary_parts.append("권고사항:")
            for rec in context.quality_report["recommendations"]:
                summary_parts.append(f"- {rec}")
        
        return "\n".join(summary_parts)
    
    def _format_5w1h_response(self, context: AgentContext) -> str:
        """5W1H 원칙에 따른 응답 포맷팅"""
        w1h = context.five_w1h

        # Dynamic RAG 데이터에서 타임스탬프 추출
        timestamp_info = ""
        if "dynamic_rag_data" in context.raw_data:
            rag_data = context.raw_data["dynamic_rag_data"]
            if rag_data and len(rag_data) > 0:
                # 첫 번째 데이터의 타임스탬프 사용
                first_data = rag_data[0]
                if 'timestamp' in first_data:
                    timestamp_info = f" [{first_data['timestamp']}]"
                elif 'latest_bucket' in first_data:
                    timestamp_info = f" [{first_data['latest_bucket']}]"

        response = f"""## 🎯 6하원칙 기반 정확한 분석 결과{timestamp_info}

### 📍 WHO (누가/무엇이)
{w1h.who}

### 📌 WHAT (무엇을)
{w1h.what}

### 🗺️ WHERE (어디서)
{w1h.where}

### ⏰ WHEN (언제)
{w1h.when}

### 💡 WHY (왜)
{w1h.why}

### 🔧 HOW (어떻게)
{w1h.how}

---
📊 **데이터 신뢰도**: Dynamic RAG Engine 실시간 조회
🔍 **분석 신뢰도**: {context.confidence_score:.2f}
📋 **품질 점수**: {context.quality_report.get('overall_quality', 0):.2f}"""

        return response

    def _generate_fallback_response(self, context: AgentContext) -> str:
        """Fallback 응답 생성"""
        # 5W1H 구조화된 응답이 있으면 사용
        if hasattr(context, 'five_w1h'):
            return self._format_5w1h_response(context)

        return f"""🤖 **Enhanced Multi-Agent 분석 결과**

📊 데이터 수집: {len(context.raw_data)} 개 영역
🔍 분석 신뢰도: {context.confidence_score:.2f}
📋 품질 점수: {context.quality_report.get('overall_quality', 0):.2f}

{self._build_context_summary(context)}"""


# 전역 인스턴스 
enhanced_orchestrator = EnhancedMultiAgentOrchestrator()


async def initialize_enhanced_multi_agent_system(rag_engine=None):
    """Enhanced Multi-Agent 시스템 초기화"""
    await enhanced_orchestrator.initialize(rag_engine)


async def get_enhanced_multi_agent_response(query: str) -> str:
    """Enhanced Multi-Agent 응답 생성"""
    return await enhanced_orchestrator.process_query(query)