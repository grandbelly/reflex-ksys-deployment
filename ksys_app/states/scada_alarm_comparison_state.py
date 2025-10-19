"""SCADA 알람 비교 상태 관리"""

import reflex as rx
from typing import List, Dict, Any
import asyncio
from datetime import datetime
from ..db import q
import os


class ScadaAlarmComparisonState(rx.State):
    """SCADA 알람 비교 상태"""

    # 비교 데이터
    comparison_data: List[Dict[str, Any]] = []

    # 통계
    total_pairs: int = 0
    rule_count: int = 0
    ai_count: int = 0
    match_rate: float = 0.0
    avg_ai_response: float = 0.0
    avg_rule_length: int = 0
    avg_ai_length: int = 0

    async def initialize(self):
        """초기화"""
        await self.load_comparison_data()

    async def load_comparison_data(self):
        """비교 데이터 로드"""
        try:

            # 비교 데이터 조회
            query = """
                WITH paired_alarms AS (
                    SELECT
                        r.event_id as rule_event_id,
                        a.event_id as ai_event_id,
                        to_char(r.triggered_at AT TIME ZONE 'Asia/Seoul',
                               'YYYY-MM-DD HH24:MI:SS') as timestamp,
                        r.sensor_data->>'tag_name' as tag_name,
                        COALESCE(r.sensor_data->>'value', '0')::FLOAT as value,
                        COALESCE(r.sensor_data->>'unit', '') as unit,
                        COALESCE(r.sensor_data->>'sensor_type', '미지정') as sensor_type,
                        r.level,
                        r.message as rule_message,
                        COALESCE(a.message, 'AI 분석 대기중...') as ai_message,
                        COALESCE(r.sensor_data->>'cause', '분석 중') as rule_cause,
                        COALESCE(a.sensor_data->>'cause', 'AI 분석 중') as ai_cause,
                        COALESCE(r.actions_taken[1], '조치 필요') as rule_action,
                        COALESCE(a.actions_taken[1], 'AI 권장 대기') as ai_action,
                        COALESCE((a.sensor_data->>'ai_response_time')::FLOAT, 0.0) as ai_response_time,
                        r.triggered_at,
                        false as is_new
                    FROM (
                        SELECT * FROM alarm_history
                        WHERE scenario_id = 'RULE_BASE'
                        AND triggered_at >= NOW() - INTERVAL '24 hours'
                    ) r
                    LEFT JOIN (
                        SELECT * FROM alarm_history
                        WHERE scenario_id = 'AI_BASE'
                        AND triggered_at >= NOW() - INTERVAL '24 hours'
                    ) a
                    ON r.sensor_data->>'tag_name' = a.sensor_data->>'tag_name'
                    AND ABS(EXTRACT(EPOCH FROM (r.triggered_at - a.triggered_at))) < 5
                )
                SELECT * FROM paired_alarms
                ORDER BY triggered_at DESC
                LIMIT 50
            """

            rows = await q(query, ())
            self.comparison_data = []

            for row in rows:
                self.comparison_data.append({
                    'timestamp': row['timestamp'],
                    'tag_name': row['tag_name'],
                    'value': row['value'],
                    'unit': row['unit'],
                    'sensor_type': row['sensor_type'],
                    'level': row['level'],
                    'rule_message': row['rule_message'][:150] if row['rule_message'] else '',
                    'ai_message': row['ai_message'][:150] if row['ai_message'] else '',
                    'rule_cause': row['rule_cause'],
                    'ai_cause': row['ai_cause'],
                    'rule_action': row['rule_action'],
                    'ai_action': row['ai_action'],
                    'ai_response_time': f"{row['ai_response_time']:.2f}" if row['ai_response_time'] > 0 else "",
                    'is_new': row['is_new']
                })

            # 통계 계산
            await self._calculate_statistics(conn)

            # Connection handled by pool

        except Exception as e:
            print(f"비교 데이터 로드 실패: {e}")

    async def _calculate_statistics(self, conn):
        """통계 계산"""
        try:
            # 카운트 조회
            count_query = """
                SELECT
                    scenario_id,
                    COUNT(*) as count,
                    AVG(LENGTH(message)) as avg_length
                FROM alarm_history
                WHERE triggered_at >= NOW() - INTERVAL '24 hours'
                GROUP BY scenario_id
            """

            rows = await q(count_query, ())
            for row in rows:
                if row['scenario_id'] == 'RULE_BASE':
                    self.rule_count = row['count']
                    self.avg_rule_length = int(row['avg_length'] or 0)
                elif row['scenario_id'] == 'AI_BASE':
                    self.ai_count = row['count']
                    self.avg_ai_length = int(row['avg_length'] or 0)

            # AI 응답시간 평균
            ai_time_query = """
                SELECT AVG((sensor_data->>'ai_response_time')::FLOAT) as avg_time
                FROM alarm_history
                WHERE scenario_id = 'AI_BASE'
                AND sensor_data->>'ai_response_time' IS NOT NULL
            """

            result = await q(ai_time_query, ())
            result = result[0]['avg'] if result and result[0] else None
            self.avg_ai_response = round(result or 0, 2)

            # 일치율 계산
            self.total_pairs = len(self.comparison_data)
            if self.total_pairs > 0:
                # 같은 레벨인 경우의 비율
                match_count = sum(1 for item in self.comparison_data
                                if item['level'] == item.get('ai_level', item['level']))
                self.match_rate = round((match_count / self.total_pairs) * 100, 1)
            else:
                self.match_rate = 0

        except Exception as e:
            print(f"통계 계산 실패: {e}")

    async def generate_test_data(self):
        """테스트 데이터 생성"""
        # Docker 환경 체크
        is_docker = os.getenv('DOCKER_ENV', 'false').lower() == 'true'
        if is_docker:
            dsn = 'postgresql://ecoanp_user:ecoanp_password@pgai-db:5432/ecoanp'
        else:
            dsn = os.getenv('TS_DSN', 'postgresql://ecoanp_user:ecoanp_password@localhost:6543/ecoanp')

        try:
            conn = await asyncpg.connect(dsn)

            # 테스트 데이터 생성 함수 호출
            from ..db import execute_query
            await execute_query("SELECT generate_test_alarms()", ())

            # Connection handled by pool

            # 데이터 새로고침
            await asyncio.sleep(2)  # AI 처리 대기
            await self.load_comparison_data()

        except Exception as e:
            print(f"테스트 데이터 생성 실패: {e}")