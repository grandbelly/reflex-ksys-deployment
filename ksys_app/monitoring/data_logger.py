"""
데이터 로깅 모듈
태그 값 변화와 KPI 상태 변화를 데이터베이스에 기록
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import asyncpg
import os


class DataLogger:
    """데이터 로깅 클래스"""

    def __init__(self, db_dsn: str = None):
        self.db_dsn = db_dsn or os.getenv("TS_DSN", "postgresql://ecoanp_user:ecoanp_password@localhost:5432/ecoanp")
        self.pool: Optional[asyncpg.Pool] = None
        self.last_values: Dict[str, float] = {}
        self.last_kpi_states: Dict[str, str] = {}

    async def initialize(self):
        """데이터베이스 연결 풀 초기화"""
        self.pool = await asyncpg.create_pool(
            self.db_dsn,
            min_size=2,
            max_size=10,
            command_timeout=10
        )

        # 테이블 생성 (존재하지 않으면)
        await self._ensure_tables()

    async def _ensure_tables(self):
        """필요한 테이블이 있는지 확인하고 없으면 생성"""
        async with self.pool.acquire() as conn:
            # 태그 값 이력 테이블
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tag_value_history (
                    id BIGSERIAL PRIMARY KEY,
                    tag_name VARCHAR(100) NOT NULL,
                    old_value DOUBLE PRECISION,
                    new_value DOUBLE PRECISION NOT NULL,
                    delta_value DOUBLE PRECISION,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)

            # KPI 상태 이력 테이블
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS kpi_state_history (
                    id BIGSERIAL PRIMARY KEY,
                    tag_name VARCHAR(100) NOT NULL,
                    old_status VARCHAR(20),
                    new_status VARCHAR(20) NOT NULL,
                    gauge_percent DOUBLE PRECISION,
                    qc_min DOUBLE PRECISION,
                    qc_max DOUBLE PRECISION,
                    current_value DOUBLE PRECISION NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    reason VARCHAR(500),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)

            # 알람 이력 테이블
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS alarm_history (
                    event_id VARCHAR(50) PRIMARY KEY,
                    scenario_id VARCHAR(20) NOT NULL,
                    level INTEGER NOT NULL,
                    triggered_at TIMESTAMPTZ NOT NULL,
                    message TEXT,
                    sensor_data JSONB,
                    actions_taken TEXT[],
                    acknowledged BOOLEAN DEFAULT FALSE,
                    acknowledged_by VARCHAR(100),
                    acknowledged_at TIMESTAMPTZ,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)

            # 인덱스 생성
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tag_value_tag_name
                ON tag_value_history(tag_name)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tag_value_timestamp
                ON tag_value_history(timestamp DESC)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_kpi_state_tag_name
                ON kpi_state_history(tag_name)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_kpi_state_timestamp
                ON kpi_state_history(timestamp DESC)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_kpi_state_status
                ON kpi_state_history(new_status)
            """)

    async def log_tag_value_change(self, tag_name: str, new_value: float,
                                   timestamp: datetime = None) -> bool:
        """
        태그 값 변화를 기록

        Args:
            tag_name: 태그 이름
            new_value: 새 값
            timestamp: 타임스탬프 (없으면 현재 시간)

        Returns:
            로깅 성공 여부
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # 이전 값 가져오기
        old_value = self.last_values.get(tag_name)

        # 변화가 없으면 기록하지 않음 (옵션)
        if old_value is not None and abs(new_value - old_value) < 0.001:
            return False

        # 델타 계산
        delta_value = new_value - old_value if old_value is not None else 0

        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO tag_value_history
                    (tag_name, old_value, new_value, delta_value, timestamp)
                    VALUES ($1, $2, $3, $4, $5)
                """, tag_name, old_value, new_value, delta_value, timestamp)

            # 캐시 업데이트
            self.last_values[tag_name] = new_value
            return True

        except Exception as e:
            print(f"❌ 태그 값 로깅 실패: {e}")
            return False

    async def log_kpi_state_change(self, tag_name: str, new_status: str,
                                   current_value: float, gauge_percent: float = None,
                                   qc_min: float = None, qc_max: float = None,
                                   reason: str = None) -> bool:
        """
        KPI 상태 변화를 기록

        Args:
            tag_name: 태그 이름
            new_status: 새 상태 ('normal', 'warning', 'critical' 등)
            current_value: 현재 값
            gauge_percent: 게이지 퍼센트
            qc_min: QC 최소값
            qc_max: QC 최대값
            reason: 상태 변경 이유

        Returns:
            로깅 성공 여부
        """
        # 이전 상태 가져오기
        old_status = self.last_kpi_states.get(tag_name)

        # 상태가 변하지 않았으면 기록하지 않음
        if old_status == new_status:
            return False

        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO kpi_state_history
                    (tag_name, old_status, new_status, gauge_percent,
                     qc_min, qc_max, current_value, reason)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, tag_name, old_status, new_status, gauge_percent,
                    qc_min, qc_max, current_value, reason)

            # 캐시 업데이트
            self.last_kpi_states[tag_name] = new_status
            return True

        except Exception as e:
            print(f"❌ KPI 상태 로깅 실패: {e}")
            return False

    async def log_alarm_event(self, event_id: str, scenario_id: str,
                             level: int, message: str,
                             sensor_data: Dict[str, Any] = None,
                             actions_taken: List[str] = None) -> bool:
        """
        알람 이벤트를 기록

        Args:
            event_id: 이벤트 ID
            scenario_id: 시나리오 ID
            level: 알람 레벨 (1-5)
            message: 알람 메시지
            sensor_data: 센서 데이터 딕셔너리
            actions_taken: 수행된 액션 리스트

        Returns:
            로깅 성공 여부
        """
        try:
            import json

            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO alarm_history
                    (event_id, scenario_id, level, triggered_at,
                     message, sensor_data, actions_taken)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (event_id) DO NOTHING
                """, event_id, scenario_id, level,
                    datetime.now(timezone.utc), message,
                    json.dumps(sensor_data) if sensor_data else None,
                    actions_taken)

            return True

        except Exception as e:
            print(f"❌ 알람 이벤트 로깅 실패: {e}")
            return False

    async def log_batch_tag_values(self, tag_values: Dict[str, float],
                                  timestamp: datetime = None) -> int:
        """
        여러 태그 값을 한 번에 기록

        Args:
            tag_values: {tag_name: value} 딕셔너리
            timestamp: 타임스탬프

        Returns:
            기록된 행 수
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        records = []
        for tag_name, new_value in tag_values.items():
            old_value = self.last_values.get(tag_name)

            # 변화가 있는 것만 기록
            if old_value is None or abs(new_value - old_value) >= 0.001:
                delta_value = new_value - old_value if old_value is not None else 0
                records.append((tag_name, old_value, new_value, delta_value, timestamp))
                self.last_values[tag_name] = new_value

        if not records:
            return 0

        try:
            async with self.pool.acquire() as conn:
                await conn.executemany("""
                    INSERT INTO tag_value_history
                    (tag_name, old_value, new_value, delta_value, timestamp)
                    VALUES ($1, $2, $3, $4, $5)
                """, records)

            return len(records)

        except Exception as e:
            print(f"❌ 배치 태그 값 로깅 실패: {e}")
            return 0

    async def get_tag_value_history(self, tag_name: str,
                                   hours: int = 24) -> List[Dict]:
        """
        태그 값 이력 조회

        Args:
            tag_name: 태그 이름
            hours: 조회할 시간 (기본 24시간)

        Returns:
            이력 리스트
        """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT tag_name, old_value, new_value, delta_value,
                           timestamp, created_at
                    FROM tag_value_history
                    WHERE tag_name = $1
                    AND timestamp >= NOW() - INTERVAL '%s hours'
                    ORDER BY timestamp DESC
                    LIMIT 1000
                """ % hours, tag_name)

                return [dict(row) for row in rows]

        except Exception as e:
            print(f"❌ 태그 값 이력 조회 실패: {e}")
            return []

    async def get_kpi_state_history(self, tag_name: str = None,
                                   hours: int = 24) -> List[Dict]:
        """
        KPI 상태 이력 조회

        Args:
            tag_name: 태그 이름 (None이면 전체)
            hours: 조회할 시간

        Returns:
            이력 리스트
        """
        try:
            async with self.pool.acquire() as conn:
                if tag_name:
                    rows = await conn.fetch("""
                        SELECT tag_name, old_status, new_status,
                               gauge_percent, current_value, reason, timestamp
                        FROM kpi_state_history
                        WHERE tag_name = $1
                        AND timestamp >= NOW() - INTERVAL '%s hours'
                        ORDER BY timestamp DESC
                        LIMIT 500
                    """ % hours, tag_name)
                else:
                    rows = await conn.fetch("""
                        SELECT tag_name, old_status, new_status,
                               gauge_percent, current_value, reason, timestamp
                        FROM kpi_state_history
                        WHERE timestamp >= NOW() - INTERVAL '%s hours'
                        ORDER BY timestamp DESC
                        LIMIT 500
                    """ % hours)

                return [dict(row) for row in rows]

        except Exception as e:
            print(f"❌ KPI 상태 이력 조회 실패: {e}")
            return []

    async def close(self):
        """연결 풀 종료"""
        if self.pool:
            await self.pool.close()


# 싱글톤 인스턴스
_logger_instance: Optional[DataLogger] = None


async def get_data_logger() -> DataLogger:
    """DataLogger 싱글톤 인스턴스 반환"""
    global _logger_instance

    if _logger_instance is None:
        _logger_instance = DataLogger()
        await _logger_instance.initialize()

    return _logger_instance


# 사용 예제
async def example_usage():
    """사용 예제"""
    logger = await get_data_logger()

    # 태그 값 변화 로깅
    await logger.log_tag_value_change("D100", 123.45)
    await logger.log_tag_value_change("D200", 67.89)

    # KPI 상태 변화 로깅
    await logger.log_kpi_state_change(
        "D100", "warning", 123.45,
        gauge_percent=75.0,
        qc_min=0, qc_max=200,
        reason="값이 경고 임계값을 초과했습니다"
    )

    # 배치 로깅
    await logger.log_batch_tag_values({
        "D100": 124.0,
        "D200": 68.5,
        "D300": 45.2
    })

    # 이력 조회
    history = await logger.get_tag_value_history("D100", hours=24)
    print(f"D100 이력: {len(history)}개")

    await logger.close()


if __name__ == "__main__":
    asyncio.run(example_usage())