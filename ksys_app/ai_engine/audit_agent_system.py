"""
🔍 AuditAgent + Reinforcement Learning System
각 에이전트의 성과를 모니터링하고 벌점/보상을 주는 시스템
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from openai import AsyncOpenAI
from ksys_app.ai_engine.real_data_audit_system import analyze_sensor_gaps


class AgentPerformanceGrade(Enum):
    """에이전트 성과 등급"""
    EXCELLENT = "A+"  # 95-100점
    GOOD = "A"        # 85-94점  
    AVERAGE = "B"     # 70-84점
    POOR = "C"        # 50-69점
    FAIL = "F"        # 0-49점


@dataclass
class AgentAuditResult:
    """에이전트 감사 결과"""
    agent_name: str
    task_id: str
    timestamp: datetime
    
    # 성과 메트릭
    data_quality_score: float = 0.0      # 데이터 품질 점수 (0-1)
    task_completion_score: float = 0.0   # 작업 완성도 점수 (0-1)
    accuracy_score: float = 0.0          # 정확성 점수 (0-1)
    efficiency_score: float = 0.0        # 효율성 점수 (0-1)
    innovation_score: float = 0.0        # 혁신성 점수 (0-1)
    
    # 종합 평가
    overall_score: float = 0.0           # 종합 점수 (0-100)
    grade: AgentPerformanceGrade = AgentPerformanceGrade.AVERAGE
    
    # 구체적 피드백
    strengths: List[str] = field(default_factory=list)      # 잘한 점
    weaknesses: List[str] = field(default_factory=list)     # 부족한 점
    penalties: List[str] = field(default_factory=list)      # 벌점 사유
    rewards: List[str] = field(default_factory=list)        # 보상 사유
    
    # 개선 방향
    improvement_suggestions: List[str] = field(default_factory=list)
    
    # 벌점/보상 점수
    penalty_points: float = 0.0          # 벌점 (-점수)
    reward_points: float = 0.0           # 보상 (+점수)


@dataclass
class AgentLearningHistory:
    """에이전트 학습 이력"""
    agent_name: str
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    
    # 성과 이력
    average_score: float = 0.0
    best_score: float = 0.0
    worst_score: float = 100.0
    
    # 학습 메트릭
    learning_rate: float = 0.1           # 학습률
    adaptation_speed: float = 0.0        # 적응 속도
    consistency_score: float = 0.0       # 일관성 점수
    
    # 벌점/보상 누적
    total_penalties: float = 0.0
    total_rewards: float = 0.0
    current_penalty_multiplier: float = 1.0  # 현재 벌점 배수
    
    # 최근 성과 트렌드
    recent_scores: List[float] = field(default_factory=list)
    improvement_trend: float = 0.0       # 개선 추세 (-1~1)


class AuditAgent:
    """🔍 감사 에이전트 - 다른 에이전트들의 성과를 감시하고 평가"""
    
    def __init__(self):
        self.name = "AuditAgent"
        self.role = "에이전트 성과 감시 및 평가"
        self.openai_client = None
        
        # 감사 기준
        self.audit_criteria = {
            "data_quality": {
                "완전성": 0.3,    # 데이터 수집 완전성
                "정확성": 0.4,    # 데이터 정확성
                "적시성": 0.3     # 적절한 시간 내 수집
            },
            "task_completion": {
                "요구사항_충족": 0.4,  # 사용자 요구사항 충족
                "작업_완성도": 0.3,    # 작업의 완성도
                "예외처리": 0.3       # 예외 상황 처리
            },
            "accuracy": {
                "결과_정확성": 0.5,    # 결과의 정확성
                "논리_일관성": 0.3,    # 논리적 일관성
                "사실_검증": 0.2      # 사실 검증
            },
            "efficiency": {
                "응답_속도": 0.3,     # 응답 속도
                "리소스_사용": 0.4,   # 리소스 효율성
                "중복_제거": 0.3      # 불필요한 중복 제거
            },
            "innovation": {
                "창의성": 0.4,        # 창의적 접근
                "문제해결": 0.3,      # 문제 해결 능력
                "개선제안": 0.3       # 개선 제안
            }
        }
        
        # 벌점 기준
        self.penalty_criteria = {
            "데이터_누락": -10,           # 중요 데이터 누락
            "잘못된_분석": -15,           # 잘못된 분석 결과
            "응답_지연": -5,             # 응답 시간 초과
            "논리_모순": -20,            # 논리적 모순
            "요구사항_미충족": -25,       # 사용자 요구사항 미충족
            "중복_작업": -8,             # 불필요한 중복
            "자원_낭비": -12,            # 컴퓨팅 자원 낭비
        }
        
        # 보상 기준
        self.reward_criteria = {
            "완벽한_데이터수집": 15,      # 완벽한 데이터 수집
            "뛰어난_인사이트": 20,        # 뛰어난 분석 인사이트
            "빠른_응답": 10,             # 빠른 응답 시간
            "창의적_접근": 25,           # 창의적 문제 해결
            "정확한_예측": 30,           # 정확한 예측
            "효율적_처리": 12,           # 효율적 처리
            "사용자_만족": 35,           # 높은 사용자 만족도
        }
    
    async def initialize(self, openai_client: AsyncOpenAI = None):
        """감사 에이전트 초기화"""
        self.openai_client = openai_client
        print(f"🔍 {self.name} 초기화 완료 - 감사 기준: {len(self.audit_criteria)}개 영역")
    
    async def audit_agent_performance(
        self, 
        agent_name: str,
        task_query: str,
        agent_context: Any,
        execution_time: float,
        user_feedback: Optional[str] = None
    ) -> AgentAuditResult:
        """에이전트 성과 종합 감사"""
        
        print(f"\n🔍 === {agent_name} 성과 감사 시작 ===")
        
        task_id = f"{agent_name}_{int(time.time())}"
        audit_result = AgentAuditResult(
            agent_name=agent_name,
            task_id=task_id,
            timestamp=datetime.now()
        )
        
        # 1. 데이터 품질 평가
        audit_result.data_quality_score = await self._evaluate_data_quality(agent_context)
        
        # 2. 작업 완성도 평가
        audit_result.task_completion_score = await self._evaluate_task_completion(
            task_query, agent_context
        )
        
        # 3. 정확성 평가
        audit_result.accuracy_score = await self._evaluate_accuracy(agent_context)
        
        # 4. 효율성 평가
        audit_result.efficiency_score = await self._evaluate_efficiency(
            execution_time, agent_context
        )
        
        # 5. 혁신성 평가
        audit_result.innovation_score = await self._evaluate_innovation(agent_context)
        
        # 6. 종합 점수 계산
        audit_result.overall_score = self._calculate_overall_score(audit_result)
        
        # 7. 등급 부여
        audit_result.grade = self._assign_grade(audit_result.overall_score)
        
        # 8. 구체적 피드백 생성
        await self._generate_detailed_feedback(audit_result, agent_context)
        
        # 9. 벌점/보상 계산
        await self._calculate_penalties_and_rewards(audit_result, agent_context)
        
        print(f"✅ {agent_name} 감사 완료 - 종합점수: {audit_result.overall_score:.1f}, 등급: {audit_result.grade.value}")
        
        return audit_result
    
    async def _evaluate_data_quality(self, agent_context: Any) -> float:
        """실제 데이터 기반 품질 평가"""
        
        try:
            # 실제 센서 데이터가 있는지 확인
            if not hasattr(agent_context, 'raw_data') or not agent_context.raw_data:
                return 0.0
            
            # 타겟 센서 추출 (ResearchAgent가 수집한 데이터에서)
            target_sensor = agent_context.raw_data.get("target_sensor")
            if not target_sensor:
                # 전체 센서 데이터에서 첫 번째 센서 추출
                all_sensors = agent_context.raw_data.get("all_sensors", [])
                if not all_sensors:
                    return 0.3  # 기본값
                target_sensor = all_sensors[0].get('tag_name', 'D101')  # 기본 센서
            
            print(f"   🔍 {target_sensor} 센서 실제 데이터 품질 평가 중...")
            
            # 실제 데이터 누락 분석 (최근 24시간)
            gap_analysis = await analyze_sensor_gaps(target_sensor, 24)
            
            # 품질 점수 = 완성도 비율
            data_quality_score = gap_analysis.completeness_ratio
            
            print(f"   📊 {target_sensor} 실제 완성도: {data_quality_score:.4f} ({gap_analysis.quality_grade})")
            print(f"   📈 누락 데이터: {gap_analysis.missing_data_points}/{gap_analysis.expected_data_points}개")
            
            return data_quality_score
            
        except Exception as e:
            print(f"   ❌ 실제 데이터 품질 평가 오류: {e}")
            return 0.2  # 오류시 낮은 점수
    
    async def _evaluate_task_completion(self, task_query: str, agent_context: Any) -> float:
        """작업 완성도 평가"""
        score = 0.0
        
        # 요구사항 충족도 (키워드 기반 간단 평가)
        query_lower = task_query.lower()
        requirements_met = 0.6  # 기본값
        
        if "현재" in query_lower and hasattr(agent_context, 'raw_data'):
            if "all_sensors" in str(agent_context.raw_data) or "focused_data" in str(agent_context.raw_data):
                requirements_met = 0.9
        
        # 작업 완성도
        completion = 0.8 if hasattr(agent_context, 'insights') else 0.4
        
        # 예외 처리
        exception_handling = 0.7 if not getattr(agent_context, 'error', None) else 0.3
        
        score = requirements_met * 0.4 + completion * 0.3 + exception_handling * 0.3
        return min(max(score, 0.0), 1.0)
    
    async def _evaluate_accuracy(self, agent_context: Any) -> float:
        """정확성 평가"""
        score = 0.7  # 기본값
        
        # 결과 정확성 (인사이트 존재 여부)
        if hasattr(agent_context, 'insights') and agent_context.insights:
            score += 0.2
            
        # 논리 일관성 (품질 보고서 확인)
        if hasattr(agent_context, 'quality_report') and agent_context.quality_report:
            logic_score = agent_context.quality_report.get('logic_validation', {}).get('score', 0.5)
            score = score * 0.7 + logic_score * 0.3
        
        return min(max(score, 0.0), 1.0)
    
    async def _evaluate_efficiency(self, execution_time: float, agent_context: Any) -> float:
        """효율성 평가"""
        # 응답 속도 평가 (5초 이하 excellent, 10초 이하 good)
        if execution_time < 5:
            speed_score = 1.0
        elif execution_time < 10:
            speed_score = 0.8
        elif execution_time < 20:
            speed_score = 0.6
        else:
            speed_score = 0.3
        
        # 리소스 사용 평가 (데이터 크기 기반)
        resource_score = 0.8  # 기본값
        
        # 중복 제거 평가
        deduplication_score = 0.7  # 기본값
        
        score = speed_score * 0.3 + resource_score * 0.4 + deduplication_score * 0.3
        return min(max(score, 0.0), 1.0)
    
    async def _evaluate_innovation(self, agent_context: Any) -> float:
        """혁신성 평가"""
        score = 0.5  # 기본값
        
        # 창의적 접근 (다양한 인사이트 생성)
        if hasattr(agent_context, 'insights') and agent_context.insights:
            insight_count = len(agent_context.insights)
            creativity_score = min(insight_count / 3.0, 1.0)
            score += creativity_score * 0.3
            
        # 문제 해결 능력
        problem_solving_score = 0.6  # 기본값
        
        # 개선 제안
        if hasattr(agent_context, 'quality_report'):
            recommendations = agent_context.quality_report.get('recommendations', [])
            improvement_score = min(len(recommendations) / 3.0, 1.0)
            score += improvement_score * 0.2
        
        return min(max(score, 0.0), 1.0)
    
    def _calculate_overall_score(self, audit_result: AgentAuditResult) -> float:
        """종합 점수 계산 (0-100)"""
        weights = {
            "data_quality": 0.25,
            "task_completion": 0.30,
            "accuracy": 0.25,
            "efficiency": 0.15,
            "innovation": 0.05
        }
        
        weighted_score = (
            audit_result.data_quality_score * weights["data_quality"] +
            audit_result.task_completion_score * weights["task_completion"] +
            audit_result.accuracy_score * weights["accuracy"] +
            audit_result.efficiency_score * weights["efficiency"] +
            audit_result.innovation_score * weights["innovation"]
        ) * 100
        
        return min(max(weighted_score, 0.0), 100.0)
    
    def _assign_grade(self, overall_score: float) -> AgentPerformanceGrade:
        """점수에 따른 등급 부여"""
        if overall_score >= 95:
            return AgentPerformanceGrade.EXCELLENT
        elif overall_score >= 85:
            return AgentPerformanceGrade.GOOD
        elif overall_score >= 70:
            return AgentPerformanceGrade.AVERAGE
        elif overall_score >= 50:
            return AgentPerformanceGrade.POOR
        else:
            return AgentPerformanceGrade.FAIL
    
    async def _generate_detailed_feedback(self, audit_result: AgentAuditResult, agent_context: Any):
        """구체적 피드백 생성"""
        # 잘한 점
        if audit_result.data_quality_score >= 0.8:
            audit_result.strengths.append("🌟 우수한 데이터 품질 관리")
        if audit_result.accuracy_score >= 0.8:
            audit_result.strengths.append("🎯 높은 정확성과 신뢰성")
        if audit_result.efficiency_score >= 0.8:
            audit_result.strengths.append("⚡ 효율적인 작업 처리")
            
        # 부족한 점
        if audit_result.data_quality_score < 0.6:
            audit_result.weaknesses.append("❌ 데이터 품질 관리 부족")
        if audit_result.task_completion_score < 0.6:
            audit_result.weaknesses.append("📋 작업 완성도 미흡")
        if audit_result.accuracy_score < 0.6:
            audit_result.weaknesses.append("🎯 정확성 개선 필요")
            
        # 개선 방향
        if audit_result.innovation_score < 0.5:
            audit_result.improvement_suggestions.append("💡 창의적 접근 방식 도입")
        if audit_result.efficiency_score < 0.7:
            audit_result.improvement_suggestions.append("⚡ 작업 효율성 개선")
    
    async def _calculate_penalties_and_rewards(self, audit_result: AgentAuditResult, agent_context: Any):
        """벌점/보상 계산"""
        # 벌점 계산
        if audit_result.data_quality_score < 0.5:
            audit_result.penalties.append("데이터_누락")
            audit_result.penalty_points += self.penalty_criteria["데이터_누락"]
            
        if audit_result.accuracy_score < 0.5:
            audit_result.penalties.append("잘못된_분석")
            audit_result.penalty_points += self.penalty_criteria["잘못된_분석"]
            
        if audit_result.task_completion_score < 0.6:
            audit_result.penalties.append("요구사항_미충족")
            audit_result.penalty_points += self.penalty_criteria["요구사항_미충족"]
        
        # 보상 계산
        if audit_result.data_quality_score >= 0.9:
            audit_result.rewards.append("완벽한_데이터수집")
            audit_result.reward_points += self.reward_criteria["완벽한_데이터수집"]
            
        if audit_result.accuracy_score >= 0.9:
            audit_result.rewards.append("뛰어난_인사이트")
            audit_result.reward_points += self.reward_criteria["뛰어난_인사이트"]
            
        if audit_result.efficiency_score >= 0.9:
            audit_result.rewards.append("효율적_처리")
            audit_result.reward_points += self.reward_criteria["효율적_처리"]


class ReinforcementLearningSystem:
    """🧠 강화학습 기반 에이전트 성과 관리 시스템"""
    
    def __init__(self):
        self.agent_histories: Dict[str, AgentLearningHistory] = {}
        self.audit_agent = AuditAgent()
        
        # 학습 파라미터
        self.learning_decay = 0.95        # 학습률 감소율
        self.penalty_amplifier = 1.2      # 벌점 증폭 계수
        self.reward_multiplier = 1.1      # 보상 배수
        self.min_learning_rate = 0.01     # 최소 학습률
        
    async def initialize(self, openai_client: AsyncOpenAI = None):
        """강화학습 시스템 초기화"""
        await self.audit_agent.initialize(openai_client)
        print("🧠 강화학습 기반 성과 관리 시스템 초기화 완료")
    
    async def evaluate_and_learn(
        self,
        agent_name: str,
        task_query: str,
        agent_context: Any,
        execution_time: float,
        user_feedback: Optional[str] = None
    ) -> Tuple[AgentAuditResult, AgentLearningHistory]:
        """에이전트 평가 및 학습"""
        
        # 1. 감사 수행
        audit_result = await self.audit_agent.audit_agent_performance(
            agent_name, task_query, agent_context, execution_time, user_feedback
        )
        
        # 2. 학습 이력 업데이트
        history = await self._update_learning_history(agent_name, audit_result)
        
        # 3. 강화학습 적용
        await self._apply_reinforcement_learning(agent_name, audit_result, history)
        
        # 4. 성과 리포트 생성
        await self._generate_performance_report(audit_result, history)
        
        return audit_result, history
    
    async def _update_learning_history(
        self, 
        agent_name: str, 
        audit_result: AgentAuditResult
    ) -> AgentLearningHistory:
        """학습 이력 업데이트"""
        
        if agent_name not in self.agent_histories:
            self.agent_histories[agent_name] = AgentLearningHistory(agent_name=agent_name)
        
        history = self.agent_histories[agent_name]
        
        # 기본 통계 업데이트
        history.total_tasks += 1
        if audit_result.overall_score >= 70:
            history.successful_tasks += 1
        else:
            history.failed_tasks += 1
            
        # 점수 이력 업데이트
        history.recent_scores.append(audit_result.overall_score)
        if len(history.recent_scores) > 10:  # 최근 10개만 유지
            history.recent_scores.pop(0)
            
        # 평균 점수 업데이트
        history.average_score = sum(history.recent_scores) / len(history.recent_scores)
        history.best_score = max(history.best_score, audit_result.overall_score)
        history.worst_score = min(history.worst_score, audit_result.overall_score)
        
        # 개선 추세 계산
        if len(history.recent_scores) >= 3:
            recent_trend = np.polyfit(range(len(history.recent_scores)), history.recent_scores, 1)[0]
            history.improvement_trend = max(-1, min(1, recent_trend / 10))  # -1~1 범위로 정규화
        
        # 벌점/보상 누적
        history.total_penalties += audit_result.penalty_points
        history.total_rewards += audit_result.reward_points
        
        return history
    
    async def _apply_reinforcement_learning(
        self,
        agent_name: str,
        audit_result: AgentAuditResult,
        history: AgentLearningHistory
    ):
        """강화학습 적용"""
        
        # 1. 학습률 조정
        if audit_result.overall_score < 60:
            # 성과가 낮으면 학습률 증가
            history.learning_rate = min(0.3, history.learning_rate * 1.2)
        elif audit_result.overall_score > 85:
            # 성과가 높으면 학습률 감소
            history.learning_rate = max(self.min_learning_rate, history.learning_rate * self.learning_decay)
        
        # 2. 벌점 배수 조정 (연속 실패시 벌점 증가)
        if audit_result.overall_score < 50:
            history.current_penalty_multiplier = min(3.0, history.current_penalty_multiplier * self.penalty_amplifier)
        elif audit_result.overall_score > 80:
            history.current_penalty_multiplier = max(1.0, history.current_penalty_multiplier * 0.9)
        
        # 3. 적응 속도 계산
        if len(history.recent_scores) >= 5:
            score_variance = np.var(history.recent_scores[-5:])
            history.adaptation_speed = 1.0 / (1.0 + score_variance / 100)  # 분산이 낮을수록 높은 적응 속도
        
        # 4. 일관성 점수 계산
        if len(history.recent_scores) >= 3:
            consistency = 1.0 - (np.std(history.recent_scores[-3:]) / 100)
            history.consistency_score = max(0, consistency)
        
        print(f"📊 {agent_name} 강화학습 적용:")
        print(f"   학습률: {history.learning_rate:.3f}")
        print(f"   벌점배수: {history.current_penalty_multiplier:.2f}")
        print(f"   적응속도: {history.adaptation_speed:.3f}")
        print(f"   일관성: {history.consistency_score:.3f}")
    
    async def _generate_performance_report(
        self, 
        audit_result: AgentAuditResult, 
        history: AgentLearningHistory
    ):
        """성과 리포트 생성"""
        
        print(f"\n📋 === {audit_result.agent_name} 성과 리포트 ===")
        print(f"🎯 종합 점수: {audit_result.overall_score:.1f}/100 ({audit_result.grade.value})")
        print(f"📊 상세 점수:")
        print(f"   - 데이터 품질: {audit_result.data_quality_score:.2f}")
        print(f"   - 작업 완성도: {audit_result.task_completion_score:.2f}")
        print(f"   - 정확성: {audit_result.accuracy_score:.2f}")
        print(f"   - 효율성: {audit_result.efficiency_score:.2f}")
        print(f"   - 혁신성: {audit_result.innovation_score:.2f}")
        
        print(f"💯 성과 이력:")
        print(f"   - 총 작업: {history.total_tasks}회")
        print(f"   - 성공률: {(history.successful_tasks/history.total_tasks*100):.1f}%")
        print(f"   - 평균 점수: {history.average_score:.1f}")
        print(f"   - 개선 추세: {history.improvement_trend:+.2f}")
        
        if audit_result.penalties:
            print(f"⚠️ 벌점 사유: {', '.join(audit_result.penalties)} ({audit_result.penalty_points:.0f}점)")
            
        if audit_result.rewards:
            print(f"🏆 보상 사유: {', '.join(audit_result.rewards)} (+{audit_result.reward_points:.0f}점)")
            
        if audit_result.improvement_suggestions:
            print(f"💡 개선 방향:")
            for suggestion in audit_result.improvement_suggestions:
                print(f"   - {suggestion}")
        
        print(f"=====================================\n")
    
    def get_agent_performance_summary(self, agent_name: str) -> Optional[Dict]:
        """에이전트 성과 요약"""
        if agent_name not in self.agent_histories:
            return None
            
        history = self.agent_histories[agent_name]
        
        return {
            "agent_name": agent_name,
            "total_tasks": history.total_tasks,
            "success_rate": (history.successful_tasks / history.total_tasks * 100) if history.total_tasks > 0 else 0,
            "average_score": history.average_score,
            "current_grade": AgentPerformanceGrade.EXCELLENT.value if history.average_score >= 95 else
                           AgentPerformanceGrade.GOOD.value if history.average_score >= 85 else
                           AgentPerformanceGrade.AVERAGE.value if history.average_score >= 70 else
                           AgentPerformanceGrade.POOR.value if history.average_score >= 50 else
                           AgentPerformanceGrade.FAIL.value,
            "improvement_trend": history.improvement_trend,
            "learning_rate": history.learning_rate,
            "penalty_multiplier": history.current_penalty_multiplier,
            "total_penalties": history.total_penalties,
            "total_rewards": history.total_rewards
        }


# 전역 강화학습 시스템
rl_system = ReinforcementLearningSystem()


async def initialize_audit_system(openai_client: AsyncOpenAI = None):
    """감사 시스템 초기화"""
    await rl_system.initialize(openai_client)


async def audit_agent_performance(
    agent_name: str,
    task_query: str,
    agent_context: Any,
    execution_time: float,
    user_feedback: Optional[str] = None
) -> Tuple[AgentAuditResult, AgentLearningHistory]:
    """에이전트 성과 감사 및 학습"""
    return await rl_system.evaluate_and_learn(
        agent_name, task_query, agent_context, execution_time, user_feedback
    )


def get_all_agents_summary() -> Dict[str, Dict]:
    """모든 에이전트 성과 요약"""
    summaries = {}
    for agent_name in rl_system.agent_histories.keys():
        summaries[agent_name] = rl_system.get_agent_performance_summary(agent_name)
    return summaries