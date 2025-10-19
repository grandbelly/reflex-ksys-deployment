"""Dashboard Model - Clean ORM style data access"""
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
import psycopg
from psycopg.rows import dict_row
from ..db import get_pool


@dataclass
class SensorData:
    """센서 데이터 모델"""
    tag_name: str
    value: float
    timestamp: datetime
    min_val: float
    max_val: float
    status: int
    unit: str = ""

    @property
    def status_color(self) -> str:
        """상태별 색상"""
        if self.status == 2:
            return "red"
        elif self.status == 1:
            return "amber"
        return "green"

    @property
    def gauge_percent(self) -> float:
        """게이지 퍼센트 계산"""
        if self.max_val > self.min_val:
            pct = ((self.value - self.min_val) / (self.max_val - self.min_val)) * 100
            return max(0, min(100, pct))
        return 50.0


@dataclass
class ChartPoint:
    """차트 포인트 모델"""
    time: str
    value: float


class DashboardModel:
    """Dashboard 데이터 접근 계층"""

    @staticmethod
    async def get_latest_sensor_data() -> List[SensorData]:
        """최신 센서 데이터 조회"""
        query = """
            SELECT
                il.tag_name,
                il.value,
                il.ts as timestamp,
                COALESCE(iqr.min_val, 0) as min_val,
                COALESCE(iqr.max_val, 100) as max_val,
                CASE
                    WHEN il.value > iqr.max_val OR il.value < iqr.min_val THEN 2
                    WHEN il.value > COALESCE(iqr.warning_high, iqr.max_val * 0.9)
                      OR il.value < COALESCE(iqr.warning_low, iqr.min_val * 1.1) THEN 1
                    ELSE 0
                END as status,
                '' as unit
            FROM influx_latest il
            LEFT JOIN influx_qc_rule iqr ON il.tag_name = iqr.tag_name
            WHERE il.value IS NOT NULL
            ORDER BY il.tag_name
            LIMIT 20
        """

        pool = await get_pool()
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query)
                rows = await cur.fetchall()

                return [
                    SensorData(
                        tag_name=row['tag_name'],
                        value=float(row['value']),
                        timestamp=row['timestamp'],
                        min_val=float(row['min_val']),
                        max_val=float(row['max_val']),
                        status=row['status'],
                        unit=row['unit']
                    )
                    for row in rows
                ]

    @staticmethod
    async def get_chart_data(tag_names: List[str]) -> Dict[str, List[ChartPoint]]:
        """차트 데이터 일괄 조회"""
        if not tag_names:
            return {}

        query = """
            WITH ranked_data AS (
                SELECT
                    tag_name,
                    bucket,
                    avg as value,
                    ROW_NUMBER() OVER (PARTITION BY tag_name ORDER BY bucket DESC) as rn
                FROM influx_agg_1h
                WHERE tag_name = ANY(%s)
            )
            SELECT tag_name, bucket, value
            FROM ranked_data
            WHERE rn <= 8
            ORDER BY tag_name, bucket
        """

        pool = await get_pool()
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, (tag_names,))
                rows = await cur.fetchall()

                # Group by tag_name
                chart_data = {}
                for row in rows:
                    tag = row['tag_name']
                    if tag not in chart_data:
                        chart_data[tag] = []

                    chart_data[tag].append(ChartPoint(
                        time=row['bucket'].strftime("%H:%M"),
                        value=float(row['value'])
                    ))

                return chart_data

    @staticmethod
    async def get_sensor_stats() -> Dict[str, int]:
        """센서 상태 통계"""
        query = """
            SELECT
                COUNT(*) FILTER (WHERE status = 0) as normal,
                COUNT(*) FILTER (WHERE status = 1) as warning,
                COUNT(*) FILTER (WHERE status = 2) as critical
            FROM (
                SELECT
                    CASE
                        WHEN il.value > iqr.max_val OR il.value < iqr.min_val THEN 2
                        WHEN il.value > COALESCE(iqr.warning_high, iqr.max_val * 0.9)
                          OR il.value < COALESCE(iqr.warning_low, iqr.min_val * 1.1) THEN 1
                        ELSE 0
                    END as status
                FROM influx_latest il
                LEFT JOIN influx_qc_rule iqr ON il.tag_name = iqr.tag_name
                WHERE il.value IS NOT NULL
            ) t
        """

        pool = await get_pool()
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query)
                row = await cur.fetchone()

                return {
                    'normal': row['normal'] or 0,
                    'warning': row['warning'] or 0,
                    'critical': row['critical'] or 0
                }