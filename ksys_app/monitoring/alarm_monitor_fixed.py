"""
실시간 알람 모니터링 엔진 (ISA-18.2 준수)
타임스탬프 기반으로 센서 데이터를 감시하고 알람 이벤트를 생성
"""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import asyncpg
from ..db import get_pool

class AlarmMonitor:
    """실시간 알람 모니터링 엔진 (ISA-18.2 준수)"""

    def __init__(self):
        self.pool = None
        self.rules = {}
        self.monitoring = False
        self.check_interval = 10  # 10초마다 체크

    async def initialize(self):
        """모니터 초기화"""
        self.pool = await get_pool()
        await self.load_alarm_rules()

    async def load_alarm_rules(self):
        """
        알람 규칙 로드 (ISA-18.2 준수)

        QC Rule 컬럼:
        - min_val, max_val: 정상 운전 범위
        - warning_low, warning_high: Level 3 (WARNING) 임계값
        - critical_low, critical_high: Level 5 (CRITICAL) 임계값
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT tag_name, min_val, max_val,
                       warning_low, warning_high,
                       critical_low, critical_high
                FROM influx_qc_rule
                WHERE enabled = true
            """)

            for row in rows:
                self.rules[row['tag_name']] = {
                    'normal': (row['min_val'], row['max_val']),
                    'warning': (row['warning_low'], row['warning_high']),
                    'critical': (row['critical_low'], row['critical_high'])
                }

    async def check_sensor_values(self):
        """센서 값 체크 및 알람 생성"""
        async with self.pool.acquire() as conn:
            # 최근 데이터 조회
            rows = await conn.fetch("""
                SELECT DISTINCT ON (tag_name)
                    tag_name, value, ts
                FROM influx_hist
                WHERE ts >= NOW() - INTERVAL '1 minute'
                ORDER BY tag_name, ts DESC
            """)

            for row in rows:
                await self.evaluate_alarm_condition(
                    conn,
                    row['tag_name'],
                    row['value'],
                    row['ts']
                )

    async def evaluate_alarm_condition(self, conn, tag_name: str, value: float, ts: datetime):
        """
        알람 조건 평가 (ISA-18.2 알람 레벨 매핑)

        Level 5 (CRITICAL): critical_low < value < critical_high 초과 → 즉시 조치
        Level 4 (ERROR): min_val < value < max_val 초과 → 긴급 조치
        Level 3 (WARNING): warning_low < value < warning_high 초과 → 모니터링
        Level 2 (INFO): 정상 범위 접근 (10% margin)
        Level 1 (CAUTION): 정상 범위 접근 (20% margin)
        """
        if tag_name not in self.rules:
            return

        rules = self.rules[tag_name]
        alarm_level = None
        message = None

        # Level 5: CRITICAL - Critical threshold 초과 (ISA-18.2)
        if rules['critical']:
            crit_min, crit_max = rules['critical']
            if crit_min is not None and value < crit_min:
                alarm_level = 5  # CRITICAL
                message = f"{tag_name} 위험 하한 초과: {value:.2f} < {crit_min}"
            elif crit_max is not None and value > crit_max:
                alarm_level = 5  # CRITICAL
                message = f"{tag_name} 위험 상한 초과: {value:.2f} > {crit_max}"

        # Level 4: ERROR - Operating range 초과
        if not alarm_level and rules['normal']:
            min_val, max_val = rules['normal']
            if min_val is not None and value < min_val:
                alarm_level = 4  # ERROR
                message = f"{tag_name} 정상 하한 초과: {value:.2f} < {min_val}"
            elif max_val is not None and value > max_val:
                alarm_level = 4  # ERROR
                message = f"{tag_name} 정상 상한 초과: {value:.2f} > {max_val}"

        # Level 3: WARNING - Warning threshold 초과
        if not alarm_level and rules['warning']:
            warn_min, warn_max = rules['warning']
            if warn_min is not None and value < warn_min:
                alarm_level = 3  # WARNING
                message = f"{tag_name} 경고 하한 초과: {value:.2f} < {warn_min}"
            elif warn_max is not None and value > warn_max:
                alarm_level = 3  # WARNING
                message = f"{tag_name} 경고 상한 초과: {value:.2f} > {warn_max}"

        # Level 2: INFO - 정상 범위 접근 (warning threshold의 10% margin)
        if not alarm_level and rules['warning']:
            warn_min, warn_max = rules['warning']
            if warn_min is not None:
                margin_min = warn_min * 1.1  # 10% below warning_low
                if value < margin_min:
                    alarm_level = 2  # INFO
                    message = f"{tag_name} 경고 범위 접근 (하한): {value:.2f}"
            if warn_max is not None:
                margin_max = warn_max * 0.9  # 10% above warning_high
                if value > margin_max:
                    alarm_level = 2  # INFO
                    message = f"{tag_name} 경고 범위 접근 (상한): {value:.2f}"

        # 알람 생성
        if alarm_level:
            await self.create_alarm_event(conn, tag_name, value, ts, alarm_level, message)

    async def create_alarm_event(self, conn, tag_name: str, value: float,
                                 ts: datetime, level: int, message: str):
        """알람 이벤트 생성 및 저장"""

        # 중복 체크 (같은 태그, 레벨로 최근 5분내 알람이 있는지)
        existing = await conn.fetchval("""
            SELECT COUNT(*) FROM alarm_history
            WHERE sensor_data->>'tag_name' = $1
            AND level = $2
            AND triggered_at > NOW() - INTERVAL '5 minutes'
        """, tag_name, level)

        if existing > 0:
            return  # 중복 알람 방지

        # 알람 이벤트 생성
        event_id = f"ALM-{datetime.now().strftime('%Y%m%d%H%M%S')}-{tag_name}"
        scenario_id = self._get_scenario_id(tag_name, level)

        sensor_data = {
            "tag_name": tag_name,
            "value": value,
            "timestamp": ts.isoformat()
        }

        # alarm_history에 저장
        await conn.execute("""
            INSERT INTO alarm_history
            (event_id, scenario_id, level, triggered_at, message, sensor_data, actions_taken)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, event_id, scenario_id, level, ts, message,
            json.dumps(sensor_data), ["알람 생성", "모니터링"])

        # NOTIFY 이벤트 발생
        await conn.execute(f"NOTIFY alarm_event, '{event_id}'")

        print(f"✅ 알람 생성: {event_id} - {message}")

    def _get_scenario_id(self, tag_name: str, level: int) -> str:
        """시나리오 ID 생성 (ISA-18.2 레벨 매핑)"""
        tag_prefix = tag_name[:4] if len(tag_name) >= 4 else tag_name
        level_names = {
            1: "CAUTION",   # Level 1
            2: "INFO",      # Level 2
            3: "WARNING",   # Level 3
            4: "ERROR",     # Level 4
            5: "CRITICAL"   # Level 5
        }
        return f"{tag_prefix}_{level_names.get(level, 'UNKN')}"

    async def start_monitoring(self):
        """모니터링 시작"""
        self.monitoring = True
        print("🚀 알람 모니터링 시작 (ISA-18.2 준수)")

        while self.monitoring:
            try:
                await self.check_sensor_values()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                print(f"❌ 모니터링 에러: {e}")
                await asyncio.sleep(5)

    async def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring = False
        print("🛑 알람 모니터링 중지")

# 싱글톤 인스턴스
alarm_monitor = AlarmMonitor()

async def start_alarm_monitoring():
    """알람 모니터링 시작"""
    await alarm_monitor.initialize()
    await alarm_monitor.start_monitoring()
