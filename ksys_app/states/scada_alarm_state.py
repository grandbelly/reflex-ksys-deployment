"""SCADA 알람 실시간 상태 관리"""

import reflex as rx
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime
from ..db import q, execute_query, _dsn
import asyncpg  # LISTEN/NOTIFY용으로만 사용
import json
import os

# Global storage for non-serializable objects to avoid pickle errors
# Use state ID as key to avoid conflicts between multiple state instances
_BACKEND_STORAGE = {}


class ScadaAlarmState(rx.State):
    """SCADA 알람 실시간 상태"""

    # 알람 로그 데이터
    alarm_logs: List[Dict[str, Any]] = []
    filtered_alarms: List[Dict[str, Any]] = []

    # 필터 설정
    severity_filter: str = "전체"
    tag_filter: str = ""

    # 통계
    total_alarms: int = 0
    critical_count: int = 0
    high_count: int = 0
    warning_count: int = 0
    low_count: int = 0
    info_count: int = 0
    critical_trend: int = 0

    # 실시간 스트리밍
    is_streaming: bool = False
    last_update: str = ""

    def _get_storage_key(self):
        """Get unique storage key for this state instance"""
        return id(self)

    def _get_listen_task(self):
        """Get listen task from global storage"""
        return _BACKEND_STORAGE.get(f"{self._get_storage_key()}_task")

    def _set_listen_task(self, task):
        """Store listen task in global storage"""
        key = f"{self._get_storage_key()}_task"
        if task is None:
            _BACKEND_STORAGE.pop(key, None)
        else:
            _BACKEND_STORAGE[key] = task

    def _get_conn(self):
        """Get connection from global storage"""
        return _BACKEND_STORAGE.get(f"{self._get_storage_key()}_conn")

    def _set_conn(self, conn):
        """Store connection in global storage"""
        key = f"{self._get_storage_key()}_conn"
        if conn is None:
            _BACKEND_STORAGE.pop(key, None)
        else:
            _BACKEND_STORAGE[key] = conn

    async def initialize(self):
        """초기화 및 데이터 로드"""
        await self.load_alarm_logs()
        await self.start_streaming()

    async def load_alarm_logs(self):
        """알람 로그 로드"""
        try:

            # 최근 100개 알람 로그 조회
            query = """
                SELECT
                    event_id,
                    to_char(triggered_at AT TIME ZONE 'Asia/Seoul',
                           'YYYY-MM-DD HH24:MI:SS.MS') as timestamp,
                    scenario_id as tag_name,
                    level as severity,
                    message as ai_description,
                    COALESCE((sensor_data->>'cause')::TEXT, '원인 분석 중...') as ai_cause,
                    COALESCE(array_to_string(actions_taken, ', '), '조치사항 확인 중...') as ai_action,
                    COALESCE((sensor_data->>'value')::FLOAT, 0.0)::FLOAT as value,
                    false as is_new
                FROM alarm_history
                ORDER BY triggered_at DESC
                LIMIT 100
            """

            self.alarm_logs = await q(query, ())

            # 통계 계산
            await self._update_statistics()

            # 필터 적용
            self.apply_filters()

            # 업데이트 시간 기록
            self.last_update = datetime.now().strftime("%H:%M:%S")

        except Exception as e:
            print(f"알람 로그 로드 실패: {e}")

    async def _update_statistics(self):
        """알람 통계 업데이트"""
        try:
            # 심각도별 카운트 (level: 1=Info, 2=Warning, 3=Critical)
            query = """
                SELECT
                    level,
                    COUNT(*) as count
                FROM alarm_history
                WHERE triggered_at >= NOW() - INTERVAL '24 hours'
                GROUP BY level
            """

            rows = await q(query, ())

            # 초기화
            self.critical_count = 0
            self.high_count = 0
            self.warning_count = 0
            self.low_count = 0
            self.info_count = 0

            for row in rows:
                if row['level'] == 5:  # Critical
                    self.critical_count = row['count']
                elif row['level'] == 4:  # High
                    self.high_count = row['count']
                elif row['level'] == 3:  # Warning
                    self.warning_count = row['count']
                elif row['level'] == 2:  # Low
                    self.low_count = row['count']
                elif row['level'] == 1:  # Info
                    self.info_count = row['count']

            self.total_alarms = len(self.alarm_logs)

            # 긴급 알람 추세 계산
            trend_query = """
                WITH hourly_counts AS (
                    SELECT
                        date_trunc('hour', triggered_at) as hour,
                        COUNT(*) as count
                    FROM alarm_history
                    WHERE level = 5
                        AND triggered_at >= NOW() - INTERVAL '2 hours'
                    GROUP BY hour
                    ORDER BY hour DESC
                    LIMIT 2
                )
                SELECT
                    COALESCE(
                        (SELECT count FROM hourly_counts LIMIT 1) -
                        (SELECT count FROM hourly_counts OFFSET 1 LIMIT 1),
                        0
                    ) as trend
            """

            trend_results = await q(trend_query, ())
            trend_result = trend_results[0]['trend'] if trend_results else 0
            self.critical_trend = trend_result or 0

        except Exception as e:
            print(f"통계 업데이트 실패: {e}")

    def apply_filters(self):
        """필터 적용"""
        filtered = self.alarm_logs.copy()

        # 심각도 필터 (level: 1=Info, 2=Low, 3=Warning, 4=High, 5=Critical)
        if self.severity_filter != "전체":
            severity_map = {
                "긴급": 5,
                "위험": 4,
                "경고": 3,
                "주의": 2,
                "정보": 1
            }
            target_severity = severity_map.get(self.severity_filter)
            if target_severity:
                filtered = [a for a in filtered if a['severity'] == target_severity]

        # 태그명 필터
        if self.tag_filter:
            filtered = [a for a in filtered
                       if self.tag_filter.lower() in a['tag_name'].lower()]

        self.filtered_alarms = filtered

    def set_severity_filter(self, value: str):
        """심각도 필터 설정"""
        self.severity_filter = value
        self.apply_filters()

    def set_tag_filter(self, value: str):
        """태그명 필터 설정"""
        self.tag_filter = value
        self.apply_filters()

    async def toggle_streaming(self):
        """실시간 스트리밍 토글"""
        if self.is_streaming:
            await self.stop_streaming()
        else:
            await self.start_streaming()

    async def start_streaming(self):
        """실시간 스트리밍 시작"""
        if self.is_streaming:
            return

        self.is_streaming = True

        try:
            # LISTEN/NOTIFY를 위한 별도 연결
            conn = await asyncpg.connect(_dsn())
            await conn.add_listener('scada_alarm', self._handle_notification)
            self._set_conn(conn)

            # 백그라운드 태스크로 리스닝 시작
            task = asyncio.create_task(self._keep_listening())
            self._set_listen_task(task)

        except Exception as e:
            print(f"스트리밍 시작 실패: {e}")
            self.is_streaming = False

    async def stop_streaming(self):
        """실시간 스트리밍 중지"""
        self.is_streaming = False

        task = self._get_listen_task()
        if task:
            task.cancel()
            self._set_listen_task(None)

        conn = self._get_conn()
        if conn:
            await conn.remove_listener('scada_alarm', self._handle_notification)
            await conn.close()
            self._set_conn(None)

    async def _keep_listening(self):
        """연결 유지 및 리스닝"""
        try:
            while self.is_streaming:
                await asyncio.sleep(1)
                # 주기적으로 알람 로그 새로고침
                if datetime.now().second % 5 == 0:
                    await self.load_alarm_logs()
        except asyncio.CancelledError:
            pass

    async def _handle_notification(self, connection, pid, channel, payload):
        """PostgreSQL NOTIFY 처리"""
        try:
            data = json.loads(payload)

            # 새 알람을 목록 맨 위에 추가
            new_alarm = {
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                'tag_name': data.get('tag', ''),
                'value': round(data.get('value', 0), 2),
                'severity': data.get('severity', 1),
                'ai_description': data.get('description', ''),
                'ai_cause': '실시간 분석 중...',
                'ai_action': '권장사항 생성 중...',
                'is_new': True  # 새 알람 표시
            }

            # 목록 업데이트
            self.alarm_logs = [new_alarm] + self.alarm_logs[:99]
            self.apply_filters()

            # 통계 업데이트
            await self._update_statistics(connection)

            # 업데이트 시간 기록
            self.last_update = datetime.now().strftime("%H:%M:%S")

        except Exception as e:
            print(f"알림 처리 실패: {e}")

    def cleanup(self):
        """정리 작업"""
        asyncio.create_task(self.stop_streaming())