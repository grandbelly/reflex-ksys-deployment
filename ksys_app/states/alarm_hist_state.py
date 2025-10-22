"""
알람 이력 상태 관리 - 수정된 버전
작성일: 2025-09-26
"""

import reflex as rx
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from ..db import q, execute_query

# KST 시간대
KST = timezone(timedelta(hours=9))

class AlarmHistState(rx.State):
    """알람 이력 상태 관리"""

    # 알람 이력 데이터
    alarm_history: List[Dict[str, Any]] = []
    timeline_data: List[Dict[str, Any]] = []
    sensor_distribution: List[Dict[str, Any]] = []

    # 통계
    total_alarms: int = 0
    resolved_count: int = 0
    resolution_rate: float = 0.0
    avg_level: float = 0.0
    top_sensor: str = "-"
    top_sensor_count: int = 0

    # 추가 통계 (새 페이지용)
    total_count: int = 0
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    selected_range: str = "today"
    show_critical: bool = True
    show_warning: bool = True
    show_info: bool = True
    showing_count: int = 0

    # 필터
    sensor_list: List[str] = []  # 동적으로 로드된 센서 목록
    sensor_filter: str = "전체"
    scenario_filter: str = "전체"
    level_filter: str = "전체"
    unresolved_only: bool = False

    # 날짜 범위
    start_date: str = ""
    end_date: str = ""
    date_range: str = "최근 24시간"

    # 페이지네이션
    current_page: int = 1
    total_pages: int = 1
    page_size: int = 25

    # 기타
    last_fetch: str = ""

    @rx.event
    def set_date_range(self, range_str: str):
        """날짜 범위 설정"""
        self.selected_range = range_str

    @rx.event
    def toggle_critical(self):
        """Critical 필터 토글"""
        self.show_critical = not self.show_critical

    @rx.event
    def toggle_warning(self):
        """Warning 필터 토글"""
        self.show_warning = not self.show_warning

    @rx.event
    def toggle_info(self):
        """Info 필터 토글"""
        self.show_info = not self.show_info

    @rx.event(background=True)
    async def search_alarms(self):
        """알람 검색"""
        # TODO: 실제 검색 로직 구현
        pass

    @rx.event
    def next_page(self):
        """다음 페이지"""
        if self.current_page < self.total_pages:
            self.current_page += 1

    @rx.event
    def prev_page(self):
        """이전 페이지"""
        if self.current_page > 1:
            self.current_page -= 1

    @rx.event(background=True)
    async def on_load(self):
        """페이지 로드 시 실행"""
        # 기본 날짜 설정 (최근 24시간)
        now = datetime.now(KST)
        async with self:
            self.end_date = now.strftime("%Y-%m-%dT%H:%M")
            self.start_date = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M")

        # 센서 목록 로드
        try:
            sensor_query = q("SELECT tag_name FROM influx_tag ORDER BY tag_name")
            sensors_result = await execute_query(sensor_query)
            async with self:
                self.sensor_list = [row['tag_name'] for row in sensors_result] if sensors_result else []
        except Exception as e:
            print(f"센서 목록 로드 오류: {e}")

        return AlarmHistState.fetch_history

    @rx.event(background=True)
    async def fetch_history(self):
        """알람 이력 조회"""
        async with self:
            self.last_fetch = "로딩중..."

        try:
            # 필터 조건 생성
            where_clauses = []
            params = []

            # 날짜 필터
            where_clauses.append("triggered_at >= %s")
            params.append(datetime.fromisoformat(self.start_date))

            where_clauses.append("triggered_at <= %s")
            params.append(datetime.fromisoformat(self.end_date))

            # 센서 필터
            if self.sensor_filter != "전체":
                where_clauses.append("sensor_data->>'tag_name' = %s")
                params.append(self.sensor_filter)

            # 시나리오 필터
            if self.scenario_filter != "전체":
                where_clauses.append("scenario_id = %s")
                params.append(self.scenario_filter)

            # 레벨 필터
            if self.level_filter != "전체":
                level_map = {
                    "EMERGENCY": 5,
                    "CRITICAL": 4,
                    "WARNING": 3,
                    "CAUTION": 2,
                    "INFO": 1
                }
                if self.level_filter in level_map:
                    where_clauses.append("level = %s")
                    params.append(level_map[self.level_filter])

            # 미해결 필터
            if self.unresolved_only:
                where_clauses.append("resolved = false")

            where_clause = " AND ".join(where_clauses)

            # 전체 개수 조회
            count_query = f"""
                SELECT COUNT(*) as total
                FROM alarm_history
                WHERE {where_clause}
            """
            count_result = await q(count_query, tuple(params))
            total_alarms = count_result[0]['total'] if count_result else 0
            total_pages = max(1, (total_alarms + self.page_size - 1) // self.page_size)

            # 페이지 데이터 조회
            offset = (self.current_page - 1) * self.page_size
            data_query = f"""
                SELECT
                    event_id,
                    scenario_id,
                    level,
                    TO_CHAR(triggered_at AT TIME ZONE 'Asia/Seoul', 'YYYY-MM-DD HH24:MI:SS') as triggered_at,
                    message,
                    sensor_data->>'tag_name' as tag_name,
                    (sensor_data->>'value')::numeric as value,
                    acknowledged,
                    resolved
                FROM alarm_history
                WHERE {where_clause}
                ORDER BY triggered_at DESC
                LIMIT %s OFFSET %s
            """
            params_with_limit = params.copy()
            params_with_limit.extend([self.page_size, offset])

            rows = await q(data_query, tuple(params_with_limit))
            alarm_history = rows if rows else []

            # 통계 조회
            await self._fetch_statistics(where_clause, params)

            # Update state all at once
            async with self:
                self.alarm_history = alarm_history
                self.total_alarms = total_alarms
                self.total_pages = total_pages
                self.last_fetch = datetime.now(KST).strftime("%H:%M:%S")

        except Exception as e:
            print(f"Error fetching alarm history: {e}")
            async with self:
                self.last_fetch = f"Error: {str(e)[:30]}"

    async def _fetch_statistics(self, where_clause, params):
        """통계 정보 조회"""
        stats_query = f"""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN resolved THEN 1 END) as resolved,
                AVG(level) as avg_level
            FROM alarm_history
            WHERE {where_clause}
        """
        stats = await q(stats_query, tuple(params))

        if stats and stats[0]:
            async with self:
                self.resolved_count = stats[0]['resolved']
                self.resolution_rate = (stats[0]['resolved'] / stats[0]['total'] * 100) if stats[0]['total'] > 0 else 0
                self.avg_level = float(stats[0]['avg_level']) if stats[0]['avg_level'] else 0

        # 최다 알람 센서
        top_sensor_query = f"""
            SELECT
                sensor_data->>'tag_name' as tag_name,
                COUNT(*) as count
            FROM alarm_history
            WHERE {where_clause}
            GROUP BY sensor_data->>'tag_name'
            ORDER BY count DESC
            LIMIT 1
        """
        top = await q(top_sensor_query, tuple(params))
        if top and top[0]:
            async with self:
                self.top_sensor = top[0]['tag_name']
                self.top_sensor_count = top[0]['count']

    def set_start_date(self, value: str):
        """시작 날짜 설정"""
        self.start_date = value

    def set_end_date(self, value: str):
        """종료 날짜 설정"""
        self.end_date = value

    def set_quick_range(self, value: str):
        """빠른 날짜 범위 설정"""
        now = datetime.now(KST)
        self.end_date = now.strftime("%Y-%m-%dT%H:%M")

        if value == "1시간":
            self.start_date = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
        elif value == "6시간":
            self.start_date = (now - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M")
        elif value == "24시간":
            self.start_date = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M")
        elif value == "7일":
            self.start_date = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")
        elif value == "30일":
            self.start_date = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M")

        self.date_range = value
        return AlarmHistState.fetch_history

    def set_sensor_filter(self, value: str):
        """센서 필터 설정"""
        self.sensor_filter = value
        self.current_page = 1
        return AlarmHistState.fetch_history

    def set_scenario_filter(self, value: str):
        """시나리오 필터 설정"""
        self.scenario_filter = value
        self.current_page = 1
        return AlarmHistState.fetch_history

    def set_level_filter(self, value: str):
        """레벨 필터 설정"""
        self.level_filter = value
        self.current_page = 1
        return AlarmHistState.fetch_history

    def toggle_unresolved(self):
        """미해결 필터 토글"""
        self.unresolved_only = not self.unresolved_only
        self.current_page = 1
        return AlarmHistState.fetch_history

    def reset_filters(self):
        """필터 초기화"""
        self.sensor_filter = "전체"
        self.scenario_filter = "전체"
        self.level_filter = "전체"
        self.unresolved_only = False
        self.current_page = 1
        return AlarmHistState.fetch_history

    def next_page(self):
        """다음 페이지"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            return AlarmHistState.fetch_history

    def prev_page(self):
        """이전 페이지"""
        if self.current_page > 1:
            self.current_page -= 1
            return AlarmHistState.fetch_history

    def set_page_size(self, value: str):
        """페이지 크기 설정"""
        self.page_size = int(value)
        self.current_page = 1
        return AlarmHistState.fetch_history

    async def export_excel(self):
        """Excel 내보내기"""
        # 구현 예정
        pass