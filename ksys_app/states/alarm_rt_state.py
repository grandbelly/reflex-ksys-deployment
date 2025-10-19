"""
실시간 알람 상태 관리 - 최적화 버전
작성일: 2025-10-08
"""

import reflex as rx
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from ..db import q

# KST 시간대
KST = timezone(timedelta(hours=9))

class AlarmRTState(rx.State):
    """실시간 알람 상태 관리"""

    # 실시간 알람 데이터
    realtime_alarms: List[Dict[str, Any]] = []

    # 통계
    critical_count: int = 0
    warning_count: int = 0
    normal_count: int = 0
    unacknowledged_count: int = 0

    # 추가 통계 (새 페이지용)
    total_alarm_count: int = 0
    active_alarm_count: int = 0
    acknowledged_count: int = 0
    alarms: List[Dict[str, Any]] = []
    last_update_time: str = ""

    # 전체 센서 상태 (카드 표시용)
    all_sensors: List[Dict[str, Any]] = []
    total_sensors_count: int = 0
    normal_sensors_count: int = 0
    warning_sensors_count: int = 0
    critical_sensors_count: int = 0

    # 제어 옵션
    auto_refresh: bool = False
    last_update: str = ""

    # 필터
    filter_status: str = "전체"
    filter_scenario: str = "모든 시나리오"

    def on_load(self):
        """페이지 로드 시 데이터 갱신"""
        return AlarmRTState.load_all_data

    @rx.event(background=True)
    async def load_all_data(self):
        """알람과 센서 상태 모두 로드"""
        yield AlarmRTState.load_sensor_status()
        yield AlarmRTState.refresh_realtime()

    @rx.event(background=True)
    async def load_sensor_status(self):
        """전체 센서 상태 로드 (카드 표시용)"""
        try:
            query = """
                SELECT
                    l.tag_name,
                    ROUND(l.value::numeric, 2) as value,
                    TO_CHAR(l.ts AT TIME ZONE 'Asia/Seoul', 'YYYY-MM-DD HH24:MI:SS') as timestamp,
                    COALESCE(t.description, t.meta->>'description', l.tag_name) as description,
                    COALESCE(t.unit, t.meta->>'unit', '') as unit,
                    COALESCE(q.min_val, 0.0) as min_val,
                    COALESCE(q.max_val, 100.0) as max_val,
                    COALESCE(q.warning_low, 20.0) as warning_low,
                    COALESCE(q.warning_high, 80.0) as warning_high,
                    CASE
                        WHEN l.value IS NULL OR q.min_val IS NULL THEN 'NORMAL'
                        WHEN l.value < q.min_val OR l.value > q.max_val THEN 'CRITICAL'
                        WHEN l.value < q.warning_low OR l.value > q.warning_high THEN 'WARNING'
                        ELSE 'NORMAL'
                    END as status
                FROM influx_latest l
                LEFT JOIN influx_qc_rule q ON l.tag_name = q.tag_name
                LEFT JOIN influx_tag t ON l.tag_name = t.tag_name
                WHERE l.value IS NOT NULL
                ORDER BY l.tag_name
            """

            rows = await q(query, ())

            all_sensors = []
            normal_count = 0
            warning_count = 0
            critical_count = 0

            for row in rows:
                sensor_data = {
                    "tag_name": row["tag_name"],
                    "description": row["description"],
                    "value": round(float(row["value"]), 2) if row["value"] is not None else 0.0,
                    "unit": row["unit"],
                    "timestamp": row["timestamp"],
                    "status": row["status"],
                    "min_val": round(float(row["min_val"]), 2),
                    "max_val": round(float(row["max_val"]), 2),
                    "warning_low": round(float(row["warning_low"]), 2),
                    "warning_high": round(float(row["warning_high"]), 2),
                }
                all_sensors.append(sensor_data)

                if sensor_data["status"] == "CRITICAL":
                    critical_count += 1
                elif sensor_data["status"] == "WARNING":
                    warning_count += 1
                else:
                    normal_count += 1

            async with self:
                self.all_sensors = all_sensors
                self.total_sensors_count = len(all_sensors)
                self.normal_sensors_count = normal_count
                self.warning_sensors_count = warning_count
                self.critical_sensors_count = critical_count

        except Exception as e:
            print(f"Error loading sensor status: {e}")
            async with self:
                self.all_sensors = []
                self.total_sensors_count = 0
                self.normal_sensors_count = 0
                self.warning_sensors_count = 0
                self.critical_sensors_count = 0

    @rx.event
    def toggle_auto_refresh(self):
        """자동 갱신 토글"""
        self.auto_refresh = not self.auto_refresh

    @rx.event(background=True)
    async def refresh_realtime(self):
        """실시간 알람 데이터 갱신"""
        async with self:
            self.last_update = "로딩중..."

        try:
            # Step 1: 전체 DB 통계 조회
            stats_query = """
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN level >= 4 THEN 1 END) as critical_count,
                    COUNT(CASE WHEN level = 3 THEN 1 END) as warning_count,
                    COUNT(CASE WHEN level <= 2 THEN 1 END) as info_count,
                    COUNT(CASE WHEN acknowledged = false THEN 1 END) as unacknowledged_count
                FROM alarm_history
            """
            stats_row = (await q(stats_query, ()))[0]

            # Step 2: 최근 알람 조회 (ISA-18.2 레벨 매핑)
            alarms_query = """
                SELECT
                    sensor_data->>'tag_name' as tag_name,
                    CASE
                        WHEN level = 5 THEN 'CRITICAL'
                        WHEN level = 4 THEN 'ERROR'
                        WHEN level = 3 THEN 'WARNING'
                        WHEN level = 2 THEN 'CAUTION'
                        WHEN level = 1 THEN 'INFO'
                        ELSE 'UNKNOWN'
                    END as status,
                    level,
                    (sensor_data->>'value')::numeric as current_value,
                    message,
                    TO_CHAR(triggered_at AT TIME ZONE 'Asia/Seoul', 'MM-DD HH24:MI:SS') as last_alarm_time,
                    acknowledged,
                    scenario_id as scenario
                FROM alarm_history
                ORDER BY triggered_at DESC
                LIMIT 50
            """

            rows = await q(alarms_query, ())

            realtime_alarms = []

            for row in rows:
                alarm_data = row

                # 필터 적용
                if self.filter_status != "전체":
                    if self.filter_status == "미인지" and alarm_data["acknowledged"]:
                        continue
                    elif self.filter_status != "미인지" and alarm_data["status"] != self.filter_status:
                        continue

                if self.filter_scenario != "모든 시나리오":
                    if alarm_data["scenario"] != self.filter_scenario:
                        continue

                realtime_alarms.append(alarm_data)

            # DB 통계로 상태 업데이트
            async with self:
                self.realtime_alarms = realtime_alarms
                self.total_alarm_count = stats_row["total"]
                self.critical_count = stats_row["critical_count"]
                self.warning_count = stats_row["warning_count"]
                self.normal_count = stats_row["info_count"]
                self.unacknowledged_count = stats_row["unacknowledged_count"]
                self.acknowledged_count = stats_row["total"] - stats_row["unacknowledged_count"]
                self.last_update = datetime.now(KST).strftime("%H:%M:%S")

        except Exception as e:
            print(f"Error refreshing realtime alarms: {e}")
            async with self:
                self.last_update = f"Error: {str(e)[:30]}"

    def set_filter(self, value: str):
        """필터 설정"""
        self.filter_status = value
        return AlarmRTState.refresh_realtime

    def set_scenario_filter(self, value: str):
        """시나리오 필터 설정"""
        self.filter_scenario = value
        return AlarmRTState.refresh_realtime

    @rx.event(background=True)
    async def acknowledge_alarm(self, tag_name: str):
        """알람 인지 처리"""
        try:
            from ..db import execute_query
            await execute_query("""
                UPDATE alarm_history
                SET acknowledged = true, acknowledged_at = NOW(), acknowledged_by = 'user'
                WHERE sensor_data->>'tag_name' = %s
                AND acknowledged = false
            """, (tag_name,))

            return AlarmRTState.refresh_realtime
        except Exception as e:
            print(f"Error acknowledging alarm: {e}")

    @rx.event(background=True)
    async def acknowledge_all(self):
        """모든 미인지 알람 인지 처리"""
        try:
            from ..db import execute_query
            await execute_query("""
                UPDATE alarm_history
                SET acknowledged = true, acknowledged_at = NOW(), acknowledged_by = 'bulk_acknowledge'
                WHERE acknowledged = false
            """, ())

            return AlarmRTState.refresh_realtime
        except Exception as e:
            print(f"Error acknowledging all alarms: {e}")

    @rx.event(background=True)
    async def cleanup_old_alarms(self):
        """30일 이상 인지된 알람 삭제"""
        try:
            from ..db import execute_query
            result = await execute_query("""
                DELETE FROM alarm_history
                WHERE acknowledged = true
                AND acknowledged_at < NOW() - INTERVAL '30 days'
            """, ())

            print(f"Cleaned up old alarms")
            return AlarmRTState.refresh_realtime
        except Exception as e:
            print(f"Error cleaning up alarms: {e}")

    def toggle_auto_refresh(self):
        """자동 갱신 토글"""
        self.auto_refresh = not self.auto_refresh
        if self.auto_refresh:
            return AlarmRTState.start_auto_refresh

    @rx.event(background=True)
    async def start_auto_refresh(self):
        """자동 갱신 시작"""
        while self.auto_refresh:
            return AlarmRTState.refresh_realtime
