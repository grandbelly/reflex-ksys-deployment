"""
알람 상태 관리 및 이벤트 로깅
벡터 DB에 자연어 설명과 함께 저장
"""
import reflex as rx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import asyncio
import json
from ..db import q
from ..monitoring.data_logger import get_data_logger


class AlarmState(rx.State):
    """알람 상태 및 이벤트 관리"""

    # 알람 이벤트 목록
    alarm_events: List[Dict[str, Any]] = []

    # 필터링 옵션
    filter_level: str = "all"  # all, info, warning, critical, emergency
    filter_tag: str = ""
    filter_date_range: str = "24h"  # 1h, 6h, 24h, 7d, 30d

    # 통계
    total_alarms: int = 0
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    # 벡터 검색
    vector_search_query: str = ""
    is_vector_search: bool = False
    similar_alarms: list[dict] = []

    # UI 상태
    loading: bool = False
    error: Optional[str] = None
    selected_event_id: Optional[str] = None

    # 알람 모드 (rule, ai, dual)
    alarm_mode: str = "dual"

    @rx.event(background=True)
    async def load_alarm_events(self):
        """알람 이벤트 로드"""
        async with self:
            self.loading = True
            self.error = None

        try:
            # 시간 범위 계산
            hours_map = {
                "1h": 1,
                "6h": 6,
                "24h": 24,
                "7d": 168,
                "30d": 720
            }
            hours = hours_map.get(self.filter_date_range, 24)

            # 알람 이벤트 조회 쿼리
            query = """
                SELECT
                    ah.event_id,
                    ah.scenario_id,
                    ah.level,
                    ah.triggered_at,
                    ah.message,
                    ah.sensor_data,
                    ah.actions_taken,
                    ah.acknowledged,
                    ah.acknowledged_by,
                    ah.resolved,
                    -- 벡터 테이블에서 자연어 설명 가져오기
                    av.description as natural_description,
                    av.context as event_context,
                    av.recommendations as recommendations
                FROM alarm_history ah
                LEFT JOIN alarm_vectors av ON ah.event_id = av.event_id
                WHERE triggered_at >= NOW() - MAKE_INTERVAL(hours => %s)
            """

            params = [hours]

            # 레벨 필터
            if self.filter_level != "all":
                level_map = {
                    "info": 1,
                    "warning": 3,
                    "critical": 4,
                    "emergency": 5
                }
                if self.filter_level in level_map:
                    query += " AND level = %s"
                    params.append(level_map[self.filter_level])

            # 태그 필터
            if self.filter_tag:
                query += " AND sensor_data->>'tag_name' LIKE %s"
                params.append(f"%{self.filter_tag}%")

            # 알람 모드 필터 (rule, ai, dual)
            if self.alarm_mode == "rule":
                query += " AND scenario_id = 'RULE_BASE'"
            elif self.alarm_mode == "ai":
                query += " AND scenario_id = 'AI_BASE'"
            # dual 모드는 모든 알람 표시

            query += " ORDER BY triggered_at DESC LIMIT 100"

            rows = await q(query, tuple(params))

            # 결과 포맷팅
            events = []
            for row in rows:
                # sensor_data 파싱
                sensor_data = {}
                if row['sensor_data']:
                    if isinstance(row['sensor_data'], str):
                        try:
                            sensor_data = json.loads(row['sensor_data'])
                        except:
                            sensor_data = {}
                    elif isinstance(row['sensor_data'], dict):
                        sensor_data = row['sensor_data']

                # recommendations 파싱
                recommendations = []
                if row.get('recommendations'):
                    try:
                        if isinstance(row['recommendations'], str):
                            recommendations = json.loads(row['recommendations'])
                        elif isinstance(row['recommendations'], list):
                            recommendations = row['recommendations']
                        else:
                            recommendations = []
                    except:
                        recommendations = []

                events.append({
                    "event_id": row['event_id'],
                    "scenario_id": row['scenario_id'],
                    "level": self._get_level_name(row['level']),
                    "level_value": row['level'],
                    "triggered_at": row['triggered_at'].isoformat() if row['triggered_at'] else "",
                    "message": row['message'] or "",
                    "natural_description": row.get('natural_description', ''),
                    # context를 문자열로 변환
                    "context": self._format_context(row.get('event_context', {})),
                    "recommendations": recommendations,
                    "sensor_data": sensor_data,
                    "main_tag": sensor_data.get('tag_name', 'Unknown'),
                    "main_value": sensor_data.get('value', 0),
                    "actions_taken": row['actions_taken'] or [],
                    "acknowledged": row['acknowledged'] or False,
                    "resolved": row['resolved'] or False,
                    "status_color": self._get_status_color(row['level']),
                    "status_icon": self._get_status_icon(row['level'])
                })

            # 통계 계산
            critical_count = sum(1 for e in events if e['level_value'] >= 4)
            warning_count = sum(1 for e in events if e['level_value'] == 3)
            info_count = sum(1 for e in events if e['level_value'] <= 2)

            async with self:
                self.alarm_events = events
                self.total_alarms = len(events)
                self.critical_count = critical_count
                self.warning_count = warning_count
                self.info_count = info_count
                self.loading = False

        except Exception as e:
            async with self:
                self.error = f"알람 로드 실패: {str(e)}"
                self.loading = False
            print(f"❌ 알람 로드 에러: {e}")

    @rx.event(background=True)
    async def create_alarm_event(self, tag_name: str, value: float,
                                 level: str, reason: str):
        """
        새 알람 이벤트 생성 및 자연어 설명 생성

        Args:
            tag_name: 태그명
            value: 현재 값
            level: 알람 레벨 (info, warning, critical, emergency)
            reason: 알람 발생 이유
        """
        try:
            logger = await get_data_logger()

            # 이벤트 ID 생성
            event_id = f"E{datetime.now().strftime('%Y%m%d%H%M%S')}_{tag_name}"

            # 레벨 값 매핑
            level_map = {
                "info": 1,
                "notice": 2,
                "warning": 3,
                "critical": 4,
                "emergency": 5
            }
            level_value = level_map.get(level.lower(), 3)

            # 자연어 설명 생성
            natural_description = self._generate_natural_description(
                tag_name, value, level, reason
            )

            # 컨텍스트 정보 생성
            context = self._generate_context(tag_name, value)

            # 권장사항 생성
            recommendations = self._generate_recommendations(level, tag_name, value)

            # 알람 이벤트 로깅
            await logger.log_alarm_event(
                event_id=event_id,
                scenario_id="MANUAL",
                level=level_value,
                message=f"[{level.upper()}] {tag_name}: {reason}",
                sensor_data={"tag_name": tag_name, "value": value},
                actions_taken=["notification", "logging"]
            )

            # 벡터 테이블에 자연어 저장
            await self._save_alarm_vector(
                event_id, natural_description, context, recommendations
            )

            # KPI 상태 변화 로깅
            await logger.log_kpi_state_change(
                tag_name=tag_name,
                new_status=level.lower(),
                current_value=value,
                reason=reason
            )

            # 리스트 새로고침
            return AlarmState.load_alarm_events

        except Exception as e:
            print(f"❌ 알람 생성 실패: {e}")

    def _generate_natural_description(self, tag_name: str, value: float,
                                     level: str, reason: str) -> str:
        """자연어 알람 설명 생성"""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        templates = {
            "info": f"{timestamp}에 {tag_name} 센서에서 정보성 이벤트가 발생했습니다. "
                   f"현재 값은 {value:.2f}이며, {reason}",

            "warning": f"⚠️ {timestamp}에 {tag_name} 센서가 경고 수준에 도달했습니다. "
                      f"측정값 {value:.2f}은 정상 범위를 벗어났으며, {reason}",

            "critical": f"🚨 {timestamp}에 {tag_name} 센서에서 위험 상황이 감지되었습니다. "
                       f"현재 값 {value:.2f}은 즉각적인 조치가 필요한 수준입니다. {reason}",

            "emergency": f"🆘 긴급상황! {timestamp}에 {tag_name} 센서가 비상 수준을 기록했습니다. "
                        f"측정값 {value:.2f}은 시스템 안전을 위협하는 수준입니다. {reason}"
        }

        return templates.get(level.lower(), f"{tag_name}: {value:.2f} - {reason}")

    def _generate_context(self, tag_name: str, value: float) -> str:
        """이벤트 컨텍스트 생성"""
        # 실제로는 DB에서 과거 데이터를 조회하여 컨텍스트 생성
        return (f"{tag_name} 센서의 최근 24시간 평균값 대비 "
                f"현재 값 {value:.2f}의 편차를 분석한 결과입니다.")

    def _generate_recommendations(self, level: str, tag_name: str,
                                 value: float) -> List[str]:
        """권장 조치사항 생성"""
        base_recommendations = {
            "info": [
                "현재 상황을 모니터링하세요",
                "추이를 관찰하여 패턴을 파악하세요"
            ],
            "warning": [
                "운영 파라미터를 점검하세요",
                "관련 센서들의 상태를 확인하세요",
                "필요시 예방 정비를 계획하세요"
            ],
            "critical": [
                "즉시 현장을 확인하세요",
                "백업 시스템 가동을 준비하세요",
                "운영팀에 상황을 보고하세요"
            ],
            "emergency": [
                "시스템을 안전 모드로 전환하세요",
                "비상 대응 프로토콜을 실행하세요",
                "모든 관련 인원에게 즉시 통보하세요"
            ]
        }

        return base_recommendations.get(level.lower(), ["상황을 모니터링하세요"])

    async def _save_alarm_vector(self, event_id: str, description: str,
                                context: str, recommendations: List[str]):
        """벡터 테이블에 자연어 정보 저장"""
        try:
            query = """
                INSERT INTO alarm_vectors
                (event_id, description, context, recommendations, embedding)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (event_id) DO NOTHING
            """

            # 임베딩 생성 (실제로는 sentence-transformers 사용)
            # 여기서는 NULL로 저장 (나중에 별도 프로세스로 생성)
            await q(query, (
                event_id,
                description,
                context,
                json.dumps(recommendations) if recommendations else '[]',
                None  # embedding은 나중에 생성
            ))
        except:
            # 테이블이 없을 수 있으므로 무시
            pass

    def _get_level_name(self, level: int) -> str:
        """레벨 번호를 이름으로 변환"""
        names = {
            1: "INFO",
            2: "NOTICE",
            3: "WARNING",
            4: "CRITICAL",
            5: "EMERGENCY"
        }
        return names.get(level, "UNKNOWN")

    def _get_status_color(self, level: int) -> str:
        """레벨별 색상"""
        colors = {
            1: "blue",
            2: "cyan",
            3: "amber",
            4: "red",
            5: "purple"
        }
        return colors.get(level, "gray")

    def _format_context(self, context) -> str:
        """컨텍스트 딕셔너리를 읽기 쉬운 문자열로 변환"""
        if not context:
            return ""

        if isinstance(context, dict):
            parts = []
            if 'current_value' in context:
                parts.append(f"현재값: {context['current_value']}")
            if 'recent_avg' in context:
                parts.append(f"최근평균: {context['recent_avg']}")
            if 'trend' in context:
                parts.append(f"추세: {context['trend']}")
            if 'tag_name' in context:
                parts.append(f"태그: {context['tag_name']}")
            return ", ".join(parts) if parts else str(context)
        return str(context)

    def _get_status_icon(self, level: int) -> str:
        """레벨별 아이콘"""
        icons = {
            1: "info",
            2: "bell",
            3: "triangle_alert",
            4: "circle_alert",
            5: "siren"
        }
        return icons.get(level, "circle_help")

    @rx.event
    def set_filter_level(self, level: str):
        """레벨 필터 설정"""
        self.filter_level = level
        return AlarmState.load_alarm_events

    @rx.event
    def set_filter_tag(self, tag: str):
        """태그 필터 설정"""
        self.filter_tag = tag
        return AlarmState.load_alarm_events

    @rx.event
    def set_filter_date_range(self, range: str):
        """날짜 범위 필터 설정"""
        self.filter_date_range = range
        return AlarmState.load_alarm_events

    @rx.event
    def set_alarm_mode(self, mode: str):
        """알람 모드 설정 (rule, ai, dual)"""
        self.alarm_mode = mode
        return AlarmState.load_alarm_events

    @rx.event(background=True)
    async def acknowledge_alarm(self, event_id: str, user: str = "operator"):
        """알람 확인 처리"""
        try:
            query = """
                UPDATE alarm_history
                SET acknowledged = TRUE,
                    acknowledged_by = %s,
                    acknowledged_at = NOW()
                WHERE event_id = %s
            """
            await q(query, (user, event_id))

            return AlarmState.load_alarm_events

        except Exception as e:
            print(f"❌ 알람 확인 실패: {e}")

    @rx.event(background=True)
    async def resolve_alarm(self, event_id: str):
        """알람 해결 처리"""
        try:
            query = """
                UPDATE alarm_history
                SET resolved = TRUE,
                    resolved_at = NOW()
                WHERE event_id = %s
            """
            await q(query, (event_id,))

            return AlarmState.load_alarm_events

        except Exception as e:
            print(f"❌ 알람 해결 실패: {e}")

    @rx.event(background=True)
    async def search_similar_alarms(self):
        """벡터 검색으로 유사 알람 찾기"""
        async with self:
            self.loading = True
            self.error = None

        try:
            if not self.vector_search_query:
                async with self:
                    self.error = "검색어를 입력하세요"
                    self.loading = False
                return

            # 유사 알람 검색 함수 호출
            query = """
                SELECT
                    s.event_id,
                    s.description,
                    s.similarity,
                    s.triggered_at,
                    s.level,
                    s.recommendations,
                    ah.scenario_id,
                    ah.message,
                    ah.sensor_data
                FROM search_similar_alarms(%s, 10) s
                JOIN alarm_history ah ON s.event_id = ah.event_id
                ORDER BY s.similarity DESC
            """

            rows = await q(query, (self.vector_search_query,))

            # 결과 포맷팅
            events = []
            for row in rows:
                sensor_data = {}
                if row['sensor_data']:
                    if isinstance(row['sensor_data'], str):
                        try:
                            sensor_data = json.loads(row['sensor_data'])
                        except:
                            sensor_data = {}
                    elif isinstance(row['sensor_data'], dict):
                        sensor_data = row['sensor_data']

                events.append({
                    "event_id": row['event_id'],
                    "scenario_id": row.get('scenario_id', ''),
                    "level": self._get_level_name(row['level']),
                    "level_value": row['level'],
                    "triggered_at": row['triggered_at'].isoformat() if row['triggered_at'] else "",
                    "message": row.get('message', ''),
                    "natural_description": row.get('description', ''),
                    "similarity": round(row['similarity'] * 100, 1),  # 백분율로 표시
                    "recommendations": row.get('recommendations', []),
                    "sensor_data": sensor_data,
                    "main_tag": sensor_data.get('tag_name', 'Unknown'),
                    "main_value": sensor_data.get('value', 0),
                    "status_color": self._get_status_color(row['level']),
                    "status_icon": self._get_status_icon(row['level']),
                    "acknowledged": False,
                    "resolved": False,
                    "context": f"유사도: {round(row['similarity'] * 100, 1)}%",
                    "actions_taken": []
                })

            # 통계 계산
            critical_count = sum(1 for e in events if e['level_value'] >= 4)
            warning_count = sum(1 for e in events if e['level_value'] == 3)
            info_count = sum(1 for e in events if e['level_value'] <= 2)

            async with self:
                self.alarm_events = events
                self.similar_alarms = events
                self.is_vector_search = True
                self.total_alarms = len(events)
                self.critical_count = critical_count
                self.warning_count = warning_count
                self.info_count = info_count
                self.loading = False

        except Exception as e:
            async with self:
                self.error = f"검색 실패: {str(e)}"
                self.loading = False
            print(f"❌ 벡터 검색 에러: {e}")

    @rx.event
    def clear_vector_search(self):
        """벡터 검색 초기화"""
        self.vector_search_query = ""
        self.is_vector_search = False
        self.similar_alarms = []
        return AlarmState.load_alarm_events