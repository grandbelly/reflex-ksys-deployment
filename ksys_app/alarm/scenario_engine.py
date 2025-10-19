"""
알람 시나리오 엔진
TASK_009: ALARM_CREATE_SCENARIO_ENGINE
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import psycopg


class AlarmLevel(Enum):
    """알람 레벨 정의"""
    INFO = 1      # 정보
    NOTICE = 2    # 주의 
    WARNING = 3   # 경고
    CRITICAL = 4  # 위험
    EMERGENCY = 5 # 긴급


class ActionType(Enum):
    """대응 액션 타입"""
    LOG = "log"                    # 로그 기록
    NOTIFY = "notify"              # 알림 발송
    ADJUST = "adjust"              # 파라미터 조정
    STOP = "stop"                  # 운전 정지
    EMERGENCY_STOP = "emergency"   # 비상 정지
    MAINTENANCE = "maintenance"    # 정비 요청


@dataclass
class AlarmCondition:
    """알람 발생 조건"""
    tag_name: str
    operator: str  # '>', '<', '>=', '<=', '==', '!='
    threshold: float
    duration_seconds: int = 0  # 지속 시간 조건
    description: str = ""


@dataclass
class AlarmAction:
    """알람 대응 액션"""
    action_type: ActionType
    parameters: Dict[str, Any] = field(default_factory=dict)
    delay_seconds: int = 0  # 액션 지연 시간
    description: str = ""


@dataclass
class AlarmScenario:
    """알람 시나리오"""
    scenario_id: str
    name: str
    level: AlarmLevel
    conditions: List[AlarmCondition]  # AND 조건
    actions: List[AlarmAction]
    cooldown_seconds: int = 300  # 재발생 방지 시간
    enabled: bool = True
    description: str = ""
    last_triggered: Optional[datetime] = None


@dataclass
class AlarmEvent:
    """알람 이벤트"""
    event_id: str
    scenario_id: str
    level: AlarmLevel
    triggered_at: datetime
    conditions_met: List[Dict[str, Any]]
    actions_taken: List[str]
    sensor_values: Dict[str, float]
    message: str


class AlarmScenarioEngine:
    """알람 시나리오 엔진"""
    
    def __init__(self, db_dsn: str):
        self.db_dsn = db_dsn
        self.scenarios: Dict[str, AlarmScenario] = {}
        self.alarm_history: List[AlarmEvent] = []
        self.condition_cache: Dict[str, Dict] = {}  # 조건 상태 캐시
        self.action_handlers: Dict[ActionType, Callable] = {}
        
        # 기본 시나리오 초기화
        self._initialize_scenarios()
        
        # 액션 핸들러 등록
        self._register_action_handlers()
    
    def _initialize_scenarios(self):
        """기본 알람 시나리오 정의"""
        
        # 시나리오 1: 막압력 이상
        self.scenarios['S001'] = AlarmScenario(
            scenario_id='S001',
            name='막압력 이상',
            level=AlarmLevel.WARNING,
            conditions=[
                AlarmCondition(
                    tag_name='TMP',
                    operator='>',
                    threshold=2.5,
                    duration_seconds=60,
                    description='TMP가 2.5 bar 초과 1분 지속'
                )
            ],
            actions=[
                AlarmAction(
                    action_type=ActionType.NOTIFY,
                    parameters={'target': 'operator', 'method': 'sms'},
                    description='운영자 SMS 알림'
                ),
                AlarmAction(
                    action_type=ActionType.ADJUST,
                    parameters={'pump_speed': -10},
                    delay_seconds=30,
                    description='펌프 속도 10% 감소'
                )
            ],
            cooldown_seconds=600,
            description='막압력이 경고 수준 초과'
        )
        
        # 시나리오 2: 전도도 급상승 (막파손 의심)
        self.scenarios['S002'] = AlarmScenario(
            scenario_id='S002',
            name='전도도 급상승',
            level=AlarmLevel.CRITICAL,
            conditions=[
                AlarmCondition(
                    tag_name='COND',
                    operator='>',
                    threshold=450,
                    duration_seconds=0,
                    description='전도도 450 μS/cm 초과'
                )
            ],
            actions=[
                AlarmAction(
                    action_type=ActionType.NOTIFY,
                    parameters={'target': 'all', 'method': 'emergency'},
                    description='전체 비상 알림'
                ),
                AlarmAction(
                    action_type=ActionType.STOP,
                    parameters={'system': 'RO'},
                    delay_seconds=60,
                    description='RO 시스템 정지'
                )
            ],
            cooldown_seconds=1800,
            description='막파손 의심 - 전도도 급상승'
        )
        
        # 시나리오 3: 복합 조건 - 차압 & 유량 이상
        self.scenarios['S003'] = AlarmScenario(
            scenario_id='S003',
            name='펌프 이상 징후',
            level=AlarmLevel.WARNING,
            conditions=[
                AlarmCondition(
                    tag_name='DP',
                    operator='>',
                    threshold=1.2,
                    description='차압 1.2 bar 초과'
                ),
                AlarmCondition(
                    tag_name='FLOW',
                    operator='<',
                    threshold=80,
                    description='유량 80% 미만'
                )
            ],
            actions=[
                AlarmAction(
                    action_type=ActionType.LOG,
                    parameters={'severity': 'warning'},
                    description='경고 로그 기록'
                ),
                AlarmAction(
                    action_type=ActionType.MAINTENANCE,
                    parameters={'type': 'pump_inspection'},
                    delay_seconds=300,
                    description='펌프 점검 요청'
                )
            ],
            cooldown_seconds=900,
            description='펌프 성능 저하 의심'
        )
        
        # 시나리오 4: 비상 정지
        self.scenarios['S004'] = AlarmScenario(
            scenario_id='S004',
            name='비상 정지 조건',
            level=AlarmLevel.EMERGENCY,
            conditions=[
                AlarmCondition(
                    tag_name='PRESSURE',
                    operator='>',
                    threshold=100,
                    duration_seconds=0,
                    description='압력 100 bar 초과'
                )
            ],
            actions=[
                AlarmAction(
                    action_type=ActionType.EMERGENCY_STOP,
                    parameters={'all_systems': True},
                    delay_seconds=0,
                    description='전체 시스템 비상 정지'
                ),
                AlarmAction(
                    action_type=ActionType.NOTIFY,
                    parameters={'target': 'emergency_team', 'method': 'all'},
                    description='비상팀 전체 알림'
                )
            ],
            cooldown_seconds=3600,
            description='압력 초과 - 비상 정지 필요'
        )
    
    def _register_action_handlers(self):
        """액션 핸들러 등록"""
        self.action_handlers[ActionType.LOG] = self._action_log
        self.action_handlers[ActionType.NOTIFY] = self._action_notify
        self.action_handlers[ActionType.ADJUST] = self._action_adjust
        self.action_handlers[ActionType.STOP] = self._action_stop
        self.action_handlers[ActionType.EMERGENCY_STOP] = self._action_emergency_stop
        self.action_handlers[ActionType.MAINTENANCE] = self._action_maintenance
    
    async def check_scenarios(self, sensor_data: Dict[str, float]) -> List[AlarmEvent]:
        """
        모든 시나리오 체크
        
        Args:
            sensor_data: {'tag_name': value, ...}
            
        Returns:
            발생한 알람 이벤트 리스트
        """
        events = []
        current_time = datetime.now()
        
        for scenario in self.scenarios.values():
            if not scenario.enabled:
                continue
            
            # 쿨다운 체크
            if scenario.last_triggered:
                cooldown_elapsed = (current_time - scenario.last_triggered).seconds
                if cooldown_elapsed < scenario.cooldown_seconds:
                    continue
            
            # 조건 체크
            conditions_met = await self._check_conditions(
                scenario.conditions, sensor_data
            )
            
            if all(conditions_met.values()):
                # 알람 발생
                event = await self._trigger_alarm(scenario, sensor_data, conditions_met)
                events.append(event)
                
                # 시나리오 업데이트
                scenario.last_triggered = current_time
        
        return events
    
    async def _check_conditions(self, 
                               conditions: List[AlarmCondition], 
                               sensor_data: Dict[str, float]) -> Dict[str, bool]:
        """조건 체크"""
        results = {}
        
        for condition in conditions:
            tag_name = condition.tag_name
            
            if tag_name not in sensor_data:
                results[tag_name] = False
                continue
            
            value = sensor_data[tag_name]
            
            # 연산자별 체크
            if condition.operator == '>':
                met = value > condition.threshold
            elif condition.operator == '<':
                met = value < condition.threshold
            elif condition.operator == '>=':
                met = value >= condition.threshold
            elif condition.operator == '<=':
                met = value <= condition.threshold
            elif condition.operator == '==':
                met = abs(value - condition.threshold) < 0.01
            elif condition.operator == '!=':
                met = abs(value - condition.threshold) >= 0.01
            else:
                met = False
            
            # 지속 시간 체크
            if met and condition.duration_seconds > 0:
                cache_key = f"{tag_name}_{condition.operator}_{condition.threshold}"
                
                if cache_key in self.condition_cache:
                    first_met = self.condition_cache[cache_key]['first_met']
                    duration = (datetime.now() - first_met).seconds
                    met = duration >= condition.duration_seconds
                else:
                    self.condition_cache[cache_key] = {
                        'first_met': datetime.now()
                    }
                    met = False
            elif not met:
                # 조건 미충족시 캐시 제거
                cache_key = f"{tag_name}_{condition.operator}_{condition.threshold}"
                self.condition_cache.pop(cache_key, None)
            
            results[tag_name] = met
        
        return results
    
    async def _trigger_alarm(self, 
                           scenario: AlarmScenario,
                           sensor_data: Dict[str, float],
                           conditions_met: Dict[str, bool]) -> AlarmEvent:
        """알람 트리거"""
        
        event_id = f"E{datetime.now().strftime('%Y%m%d%H%M%S')}_{scenario.scenario_id}"
        
        # 액션 실행
        actions_taken = []
        for action in scenario.actions:
            if action.delay_seconds > 0:
                # 지연 액션은 비동기로 실행
                asyncio.create_task(
                    self._execute_delayed_action(action, action.delay_seconds)
                )
                actions_taken.append(f"{action.action_type.value} (delayed {action.delay_seconds}s)")
            else:
                # 즉시 실행
                await self._execute_action(action)
                actions_taken.append(action.action_type.value)
        
        # 이벤트 생성
        event = AlarmEvent(
            event_id=event_id,
            scenario_id=scenario.scenario_id,
            level=scenario.level,
            triggered_at=datetime.now(),
            conditions_met=[
                {'tag': k, 'met': v} for k, v in conditions_met.items()
            ],
            actions_taken=actions_taken,
            sensor_values=sensor_data.copy(),
            message=f"[{scenario.level.name}] {scenario.name}: {scenario.description}"
        )
        
        # 이력 저장
        self.alarm_history.append(event)
        
        # DB 저장
        await self._save_event_to_db(event)
        
        print(f"[ALARM] {event.message}")
        
        return event
    
    async def _execute_action(self, action: AlarmAction):
        """액션 실행"""
        handler = self.action_handlers.get(action.action_type)
        if handler:
            await handler(action.parameters)
    
    async def _execute_delayed_action(self, action: AlarmAction, delay: int):
        """지연 액션 실행"""
        await asyncio.sleep(delay)
        await self._execute_action(action)
    
    # 액션 핸들러들
    async def _action_log(self, params: Dict):
        """로그 기록"""
        print(f"[LOG] Severity: {params.get('severity', 'info')}")
    
    async def _action_notify(self, params: Dict):
        """알림 발송"""
        target = params.get('target', 'operator')
        method = params.get('method', 'email')
        print(f"[NOTIFY] Sending {method} to {target}")
    
    async def _action_adjust(self, params: Dict):
        """파라미터 조정"""
        print(f"[ADJUST] Parameters: {params}")
    
    async def _action_stop(self, params: Dict):
        """시스템 정지"""
        system = params.get('system', 'unknown')
        print(f"[STOP] Stopping {system} system")
    
    async def _action_emergency_stop(self, params: Dict):
        """비상 정지"""
        print("[EMERGENCY] EMERGENCY STOP ACTIVATED!")
        if params.get('all_systems'):
            print("[EMERGENCY] All systems shutting down")
    
    async def _action_maintenance(self, params: Dict):
        """정비 요청"""
        maint_type = params.get('type', 'general')
        print(f"[MAINTENANCE] Request: {maint_type}")
    
    async def _save_event_to_db(self, event: AlarmEvent):
        """이벤트 DB 저장"""
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        INSERT INTO alarm_history 
                        (event_id, scenario_id, level, triggered_at, message, sensor_data)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (event_id) DO NOTHING
                    """, (
                        event.event_id,
                        event.scenario_id,
                        event.level.value,
                        event.triggered_at,
                        event.message,
                        json.dumps(event.sensor_values)
                    ))
                    await conn.commit()
        except Exception as e:
            # 테이블이 없을 수 있음
            pass
    
    def get_alarm_history(self, hours: int = 24) -> List[AlarmEvent]:
        """알람 이력 조회"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [e for e in self.alarm_history if e.triggered_at > cutoff]