"""
정비 스케줄 최적화 시스템
TASK_014: MAINT_OPTIMIZE_SCHEDULE
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json


class MaintenanceType(Enum):
    """정비 유형"""
    ROUTINE = "routine"          # 정기 점검
    PREVENTIVE = "preventive"    # 예방 정비
    PREDICTIVE = "predictive"    # 예지 정비
    CORRECTIVE = "corrective"    # 사후 정비
    OVERHAUL = "overhaul"        # 대정비


@dataclass
class MaintenanceTask:
    """정비 작업"""
    task_id: str
    task_name: str
    equipment_id: str
    maintenance_type: MaintenanceType
    priority: int  # 1-5 (5가 가장 높음)
    estimated_duration_hours: float
    required_parts: List[str]
    lead_time_days: int  # 부품 리드타임
    cost_estimate: float
    scheduled_date: datetime
    deadline: datetime


@dataclass
class OptimizedSchedule:
    """최적화된 정비 스케줄"""
    schedule_id: str
    start_date: datetime
    end_date: datetime
    tasks: List[MaintenanceTask]
    total_duration_hours: float
    total_cost: float
    resource_utilization: float
    optimization_score: float


class MaintenanceScheduleOptimizer:
    """정비 스케줄 최적화"""
    
    def __init__(self):
        self.operational_schedule = {}  # 운전 스케줄
        self.resource_availability = {}  # 인력 가용성
        self.part_inventory = {}  # 부품 재고
        
        # 최적화 가중치
        self.weights = {
            'cost': 0.3,
            'downtime': 0.4,
            'resource': 0.2,
            'risk': 0.1
        }
    
    def optimize_schedule(self, 
                         tasks: List[MaintenanceTask],
                         start_date: datetime,
                         end_date: datetime,
                         constraints: Dict = None) -> OptimizedSchedule:
        """
        정비 스케줄 최적화
        
        Args:
            tasks: 정비 작업 리스트
            start_date: 시작일
            end_date: 종료일
            constraints: 제약 조건
        """
        
        # 1. 우선순위 정렬
        sorted_tasks = self._sort_by_priority(tasks)
        
        # 2. 부품 리드타임 고려
        tasks_with_parts = self._check_part_availability(sorted_tasks)
        
        # 3. 운전 스케줄 연동
        scheduled_tasks = self._align_with_operations(tasks_with_parts, start_date, end_date)
        
        # 4. 자원 배분 최적화
        optimized_tasks = self._optimize_resources(scheduled_tasks)
        
        # 5. 비용 최적화
        cost_optimized = self._optimize_cost(optimized_tasks)
        
        # 6. 최종 스케줄 생성
        final_schedule = self._create_final_schedule(
            cost_optimized,
            start_date,
            end_date
        )
        
        return final_schedule
    
    def _sort_by_priority(self, tasks: List[MaintenanceTask]) -> List[MaintenanceTask]:
        """우선순위별 정렬"""
        # 우선순위, 데드라인, 유형별 정렬
        def sort_key(task):
            type_priority = {
                MaintenanceType.CORRECTIVE: 0,
                MaintenanceType.PREDICTIVE: 1,
                MaintenanceType.PREVENTIVE: 2,
                MaintenanceType.ROUTINE: 3,
                MaintenanceType.OVERHAUL: 4
            }
            return (
                -task.priority,  # 높은 우선순위 먼저
                task.deadline,   # 빠른 데드라인 먼저
                type_priority.get(task.maintenance_type, 5)
            )
        
        return sorted(tasks, key=sort_key)
    
    def _check_part_availability(self, tasks: List[MaintenanceTask]) -> List[MaintenanceTask]:
        """부품 가용성 확인 및 조정"""
        adjusted_tasks = []
        
        for task in tasks:
            # 부품 리드타임 확인
            max_lead_time = task.lead_time_days
            
            for part in task.required_parts:
                if part in self.part_inventory:
                    stock = self.part_inventory[part].get('quantity', 0)
                    lead_time = self.part_inventory[part].get('lead_time', 7)
                    
                    if stock <= 0:
                        max_lead_time = max(max_lead_time, lead_time)
            
            # 스케줄 조정
            earliest_date = datetime.now() + timedelta(days=max_lead_time)
            if task.scheduled_date < earliest_date:
                task.scheduled_date = earliest_date
            
            adjusted_tasks.append(task)
        
        return adjusted_tasks
    
    def _align_with_operations(self, 
                              tasks: List[MaintenanceTask],
                              start_date: datetime,
                              end_date: datetime) -> List[MaintenanceTask]:
        """운전 스케줄과 정렬"""
        aligned_tasks = []
        
        # 계획 정지 기간 찾기
        planned_shutdowns = self._find_shutdown_windows(start_date, end_date)
        
        for task in tasks:
            # 정지가 필요한 작업
            if task.maintenance_type in [MaintenanceType.OVERHAUL, MaintenanceType.CORRECTIVE]:
                # 가장 가까운 정지 기간에 배치
                best_window = self._find_best_shutdown_window(
                    task,
                    planned_shutdowns
                )
                if best_window:
                    task.scheduled_date = best_window
            
            aligned_tasks.append(task)
        
        return aligned_tasks
    
    def _find_shutdown_windows(self, start_date: datetime, end_date: datetime) -> List[Tuple[datetime, datetime]]:
        """계획 정지 기간 찾기"""
        windows = []
        
        # 주말 정비 시간 (토요일 오전)
        current = start_date
        while current < end_date:
            if current.weekday() == 5:  # 토요일
                window_start = current.replace(hour=6, minute=0)
                window_end = current.replace(hour=18, minute=0)
                windows.append((window_start, window_end))
            current += timedelta(days=1)
        
        # 월간 정비 시간 (매월 첫째 일요일)
        current = start_date
        while current < end_date:
            if current.day <= 7 and current.weekday() == 6:  # 첫째 일요일
                window_start = current.replace(hour=0, minute=0)
                window_end = current.replace(hour=23, minute=59)
                windows.append((window_start, window_end))
            current += timedelta(days=1)
        
        return windows
    
    def _find_best_shutdown_window(self, 
                                  task: MaintenanceTask,
                                  windows: List[Tuple[datetime, datetime]]) -> Optional[datetime]:
        """최적 정지 기간 찾기"""
        best_window = None
        min_delay = float('inf')
        
        for window_start, window_end in windows:
            # 작업 시간이 윈도우에 맞는지 확인
            window_duration = (window_end - window_start).total_seconds() / 3600
            
            if window_duration >= task.estimated_duration_hours:
                # 데드라인 전이고 가장 가까운 윈도우
                if window_start <= task.deadline:
                    delay = (window_start - task.scheduled_date).days
                    if 0 <= delay < min_delay:
                        min_delay = delay
                        best_window = window_start
        
        return best_window
    
    def _optimize_resources(self, tasks: List[MaintenanceTask]) -> List[MaintenanceTask]:
        """자원 최적화"""
        # 날짜별 작업 그룹화
        tasks_by_date = {}
        for task in tasks:
            date_key = task.scheduled_date.date()
            if date_key not in tasks_by_date:
                tasks_by_date[date_key] = []
            tasks_by_date[date_key].append(task)
        
        # 일별 작업 부하 평준화
        optimized = []
        max_daily_hours = 16  # 일 최대 작업 시간
        
        for date, daily_tasks in tasks_by_date.items():
            total_hours = sum(t.estimated_duration_hours for t in daily_tasks)
            
            if total_hours > max_daily_hours:
                # 초과 작업을 다음 날로 이동
                current_hours = 0
                deferred = []
                
                for task in daily_tasks:
                    if current_hours + task.estimated_duration_hours <= max_daily_hours:
                        optimized.append(task)
                        current_hours += task.estimated_duration_hours
                    else:
                        task.scheduled_date += timedelta(days=1)
                        deferred.append(task)
                
                optimized.extend(deferred)
            else:
                optimized.extend(daily_tasks)
        
        return optimized
    
    def _optimize_cost(self, tasks: List[MaintenanceTask]) -> List[MaintenanceTask]:
        """비용 최적화"""
        # 동일 장비 작업 병합
        equipment_groups = {}
        for task in tasks:
            if task.equipment_id not in equipment_groups:
                equipment_groups[task.equipment_id] = []
            equipment_groups[task.equipment_id].append(task)
        
        optimized = []
        
        for equipment_id, group_tasks in equipment_groups.items():
            if len(group_tasks) > 1:
                # 가까운 날짜의 작업들을 병합
                group_tasks.sort(key=lambda x: x.scheduled_date)
                
                for i in range(len(group_tasks) - 1):
                    current = group_tasks[i]
                    next_task = group_tasks[i + 1]
                    
                    days_apart = (next_task.scheduled_date - current.scheduled_date).days
                    
                    # 7일 이내면 병합 고려
                    if days_apart <= 7:
                        # 병합 시 비용 절감 (고정비 10% 절감)
                        current.cost_estimate *= 0.95
                        next_task.cost_estimate *= 0.95
                        
                        # 날짜 조정 (중간 날짜로)
                        mid_date = current.scheduled_date + timedelta(days=days_apart//2)
                        current.scheduled_date = mid_date
                        next_task.scheduled_date = mid_date
            
            optimized.extend(group_tasks)
        
        return optimized
    
    def _create_final_schedule(self,
                              tasks: List[MaintenanceTask],
                              start_date: datetime,
                              end_date: datetime) -> OptimizedSchedule:
        """최종 스케줄 생성"""
        
        # 기간 내 작업만 필터링
        scheduled_tasks = [
            t for t in tasks 
            if start_date <= t.scheduled_date <= end_date
        ]
        
        # 날짜순 정렬
        scheduled_tasks.sort(key=lambda x: x.scheduled_date)
        
        # 통계 계산
        total_duration = sum(t.estimated_duration_hours for t in scheduled_tasks)
        total_cost = sum(t.cost_estimate for t in scheduled_tasks)
        
        # 자원 활용률 계산
        total_days = (end_date - start_date).days
        available_hours = total_days * 8  # 일 8시간 기준
        utilization = min(total_duration / available_hours, 1.0) if available_hours > 0 else 0
        
        # 최적화 점수 계산
        optimization_score = self._calculate_optimization_score(
            scheduled_tasks,
            total_cost,
            utilization
        )
        
        return OptimizedSchedule(
            schedule_id=f"SCH_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            start_date=start_date,
            end_date=end_date,
            tasks=scheduled_tasks,
            total_duration_hours=total_duration,
            total_cost=total_cost,
            resource_utilization=utilization,
            optimization_score=optimization_score
        )
    
    def _calculate_optimization_score(self,
                                     tasks: List[MaintenanceTask],
                                     total_cost: float,
                                     utilization: float) -> float:
        """최적화 점수 계산"""
        score = 0.0
        
        # 비용 효율성 (낮을수록 좋음)
        cost_efficiency = min(10000 / (total_cost + 1), 1.0)
        score += cost_efficiency * self.weights['cost']
        
        # 가동률 (높을수록 좋음)
        uptime_score = 1.0 - utilization  # 정비 시간이 적을수록 좋음
        score += uptime_score * self.weights['downtime']
        
        # 자원 활용률 (적정 수준이 좋음)
        resource_score = 1.0 - abs(utilization - 0.7)  # 70%가 최적
        score += resource_score * self.weights['resource']
        
        # 위험도 (우선순위 높은 작업 완료율)
        high_priority_completed = sum(1 for t in tasks if t.priority >= 4)
        total_high_priority = len([t for t in tasks if t.priority >= 4])
        risk_score = high_priority_completed / total_high_priority if total_high_priority > 0 else 1.0
        score += risk_score * self.weights['risk']
        
        return score
    
    def generate_calendar_view(self, schedule: OptimizedSchedule) -> Dict[str, List[Dict]]:
        """캘린더 뷰 생성"""
        calendar = {}
        
        for task in schedule.tasks:
            date_key = task.scheduled_date.strftime('%Y-%m-%d')
            
            if date_key not in calendar:
                calendar[date_key] = []
            
            calendar[date_key].append({
                'time': task.scheduled_date.strftime('%H:%M'),
                'task': task.task_name,
                'equipment': task.equipment_id,
                'duration': f"{task.estimated_duration_hours}h",
                'priority': task.priority,
                'type': task.maintenance_type.value
            })
        
        return calendar