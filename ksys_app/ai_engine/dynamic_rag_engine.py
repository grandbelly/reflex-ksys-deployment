"""
Dynamic RAG Engine with MCP-like Database Query Capabilities
실시간 DB 쿼리를 통한 동적 RAG 시스템
"""

import asyncio
import asyncpg
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import re
import os

class DynamicRAGEngine:
    """
    동적 RAG 엔진 - 실시간 DB 쿼리를 통해 정확한 데이터 제공
    """

    def __init__(self, db_dsn: str = None):
        self.db_dsn = db_dsn or os.getenv(
            "TS_DSN",
            "postgresql://ecoanp_user:ecoanp_password@localhost:5432/ecoanp"
        )
        self.conn = None
        self.active_tags = []
        self.tag_metadata = {}

    async def initialize(self):
        """엔진 초기화 및 태그 동적 발견"""
        self.conn = await asyncpg.connect(self.db_dsn)
        await self.discover_tags()

    async def discover_tags(self) -> List[str]:
        """현재 활성 태그를 동적으로 발견"""
        query = """
            SELECT DISTINCT tag_name
            FROM influx_hist
            WHERE ts >= NOW() - INTERVAL '24 hours'
            ORDER BY tag_name
        """

        rows = await self.conn.fetch(query)
        self.active_tags = [row['tag_name'] for row in rows]

        # 각 태그의 메타데이터도 수집
        for tag in self.active_tags:
            meta_query = """
                SELECT
                    MIN(value) as min_val,
                    MAX(value) as max_val,
                    AVG(value) as avg_val,
                    COUNT(*) as data_points,
                    MAX(ts) as latest_ts
                FROM influx_hist
                WHERE tag_name = $1
                AND ts >= NOW() - INTERVAL '24 hours'
            """

            meta = await self.conn.fetchrow(meta_query, tag)
            self.tag_metadata[tag] = dict(meta)

        return self.active_tags

    def select_optimal_view(self, time_range: str) -> str:
        """시간 범위에 따라 최적의 뷰 선택"""
        if not time_range:
            return 'influx_latest'

        # 시간 단위별 최적 뷰 매핑
        if any(x in time_range.lower() for x in ['minute', '분', '최근']):
            return 'influx_latest'
        elif any(x in time_range.lower() for x in ['hour', '시간']):
            if any(x in time_range for x in ['24', '하루']):
                return 'influx_agg_1h'
            else:
                return 'influx_agg_10m'
        elif any(x in time_range.lower() for x in ['day', '일', '어제', '오늘']):
            return 'influx_agg_1h'
        elif any(x in time_range.lower() for x in ['week', '주']):
            return 'influx_agg_1d'
        elif any(x in time_range.lower() for x in ['month', '월', '달']):
            return 'influx_agg_1d'
        else:
            return 'influx_latest'

    async def parse_time_query(self, query: str) -> Tuple[str, str, List[str]]:
        """
        자연어 시간 쿼리를 파싱하여 SQL 컴포넌트 반환
        Returns: (time_interval, aggregate_view, detected_tags)
        """

        # 시간 범위 감지 및 뷰 선택
        time_mappings = {
            # 한국어
            r'최근\s*(\d+)\s*분': ('minutes', 'influx_latest'),
            r'최근\s*(\d+)\s*시간': ('hours', 'influx_agg_1m'),
            r'지난\s*(\d+)\s*시간': ('hours', 'influx_agg_10m'),
            r'최근\s*(\d+)\s*일': ('days', 'influx_agg_1h'),
            r'지난\s*(\d+)\s*일': ('days', 'influx_agg_1h'),
            r'최근\s*(\d+)\s*주': ('weeks', 'influx_agg_1h'),
            r'최근\s*(\d+)\s*개월': ('months', 'influx_agg_1d'),
            r'어제': ('1 day', 'influx_agg_10m'),
            r'오늘': ('1 day', 'influx_agg_1m'),
            r'이번\s*주': ('1 week', 'influx_agg_1h'),
            r'이번\s*달': ('1 month', 'influx_agg_1h'),
            # 영어
            r'last\s*(\d+)\s*minute': ('minutes', 'influx_latest'),
            r'last\s*(\d+)\s*hour': ('hours', 'influx_agg_1m'),
            r'last\s*(\d+)\s*day': ('days', 'influx_agg_10m'),
            r'last\s*(\d+)\s*week': ('weeks', 'influx_agg_1h'),
            r'last\s*(\d+)\s*month': ('months', 'influx_agg_1d'),
        }

        time_interval = '1 hour'
        view = 'influx_agg_1m'

        for pattern, (unit, recommended_view) in time_mappings.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                if match.groups():
                    time_value = match.group(1)
                    time_interval = f"{time_value} {unit}"
                else:
                    time_interval = unit if unit != '1 day' else '24 hours'
                view = recommended_view
                break

        # 태그 동적 감지 - 활성 태그만 검색
        detected_tags = []
        query_upper = query.upper()
        for tag in self.active_tags:
            if tag in query_upper:
                detected_tags.append(tag)

        # "모든", "전체", "all" 키워드 감지
        if any(keyword in query.lower() for keyword in ['모든', '전체', 'all', '모두']):
            detected_tags = self.active_tags  # 모든 활성 태그

        return time_interval, view, detected_tags

    async def generate_dynamic_sql(self, query: str) -> str:
        """자연어 쿼리를 동적 SQL로 변환"""

        time_interval, view, detected_tags = await self.parse_time_query(query)

        # 집계 함수 결정
        agg_functions = []
        if '평균' in query or 'average' in query.lower() or 'avg' in query.lower():
            if view == 'influx_latest':
                agg_functions.append('AVG(value) as average')
            else:
                agg_functions.append('AVG(avg) as average')

        if '최대' in query or '최고' in query or 'max' in query.lower():
            if view == 'influx_latest':
                agg_functions.append('MAX(value) as maximum')
            else:
                agg_functions.append('MAX(max) as maximum')

        if '최소' in query or '최저' in query or 'min' in query.lower():
            if view == 'influx_latest':
                agg_functions.append('MIN(value) as minimum')
            else:
                agg_functions.append('MIN(min) as minimum')

        if '합계' in query or 'sum' in query.lower():
            if view == 'influx_latest':
                agg_functions.append('SUM(value) as total')
            else:
                agg_functions.append('SUM(sum) as total')

        # 기본 집계 함수
        if not agg_functions:
            if view == 'influx_latest':
                agg_functions = ['value as last_value', 'ts as timestamp']
            else:
                agg_functions = ['AVG(avg) as avg_value', 'MIN(min) as min_value', 'MAX(max) as max_value']

        # SQL 생성
        if view == 'influx_latest':
            # 최신 값 조회
            if detected_tags:
                tag_list = ','.join([f"'{t}'" for t in detected_tags])
                tag_condition = f"WHERE tag_name IN ({tag_list})"
            else:
                tag_condition = ""

            sql = f"""
                SELECT tag_name, {', '.join(agg_functions)}
                FROM {view}
                {tag_condition}
                ORDER BY tag_name
            """
        else:
            # 시계열 집계 조회
            if detected_tags:
                tag_list = ','.join([f"'{t}'" for t in detected_tags])
                tag_condition = f"AND tag_name IN ({tag_list})"
            else:
                tag_condition = ""

            sql = f"""
                SELECT
                    tag_name,
                    {', '.join(agg_functions)},
                    COUNT(*) as data_points,
                    MAX(bucket) as latest_bucket,
                    MIN(bucket) as earliest_bucket
                FROM {view}
                WHERE bucket >= NOW() - INTERVAL '{time_interval}'
                {tag_condition}
                GROUP BY tag_name
                ORDER BY tag_name
            """

        return sql.strip()

    async def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """SQL 쿼리 실행 및 결과 반환"""
        try:
            rows = await self.conn.fetch(sql)
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Query execution error: {e}")
            return []

    async def process_natural_language_query(self, query: str) -> Dict[str, Any]:
        """
        자연어 쿼리를 처리하여 동적 데이터와 함께 응답 생성
        """

        # 1. 태그 재발견 (최신 상태 유지)
        await self.discover_tags()

        # 2. 시간 파싱 및 뷰 선택
        time_interval, aggregate_view, detected_tags = await self.parse_time_query(query)
        time_info = {'range': time_interval, 'view': aggregate_view, 'tags': detected_tags}
        view_used = aggregate_view  # parse_time_query에서 이미 선택됨

        # 3. SQL 생성
        sql = await self.generate_dynamic_sql(query)

        # 4. 쿼리 실행
        results = await self.execute_query(sql)

        # 5. 응답 포맷팅 (표준 구조)
        response = {
            'query': query,
            'sql': sql,
            'data': results,  # 'results' → 'data'로 통일
            'metadata': {
                'active_tags': self.active_tags,
                'timestamp': datetime.now().isoformat(),
                'row_count': len(results),
                'view_used': view_used,  # 추가
                'time_range': time_info['range']  # 추가
            }
        }

        # 5. 자연어 응답 생성
        if results:
            time_interval, view, detected_tags = await self.parse_time_query(query)

            if '평균' in query:
                avg_text = []
                for row in results:
                    if 'average' in row:
                        avg_text.append(f"{row['tag_name']}: {row['average']:.2f}")
                response['summary'] = f"요청하신 {time_interval} 동안의 평균값:\n" + "\n".join(avg_text)

            elif '최대' in query or '최소' in query:
                minmax_text = []
                for row in results:
                    text = f"{row['tag_name']}: "
                    if 'maximum' in row:
                        text += f"최대 {row['maximum']:.2f}"
                    if 'minimum' in row:
                        text += f", 최소 {row['minimum']:.2f}"
                    minmax_text.append(text)
                response['summary'] = f"요청하신 {time_interval} 동안의 최대/최소값:\n" + "\n".join(minmax_text)

            else:
                # 일반 요약
                response['summary'] = f"{len(results)}개 센서의 {time_interval} 데이터를 조회했습니다."
        else:
            response['summary'] = "해당 조건에 맞는 데이터가 없습니다."

        return response

    async def close(self):
        """연결 종료"""
        if self.conn:
            await self.conn.close()


# 테스트 함수
async def test_dynamic_rag():
    """동적 RAG 테스트"""

    print("="*60)
    print("Dynamic RAG Engine Test")
    print("="*60)

    engine = DynamicRAGEngine()
    await engine.initialize()

    # 테스트 쿼리들
    test_queries = [
        "모든 센서의 최근 1시간 평균값",
        "D100과 D101의 지난 24시간 최대값",
        "전체 태그의 어제 데이터 통계",
        "최근 30분 동안 모든 센서의 최소값",
        "이번 주 D200, D201, D202의 평균",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n[Test {i}] {query}")
        print("-"*60)

        response = await engine.process_natural_language_query(query)

        print(f"SQL:\n{response['sql']}\n")
        print(f"Results: {response['metadata']['row_count']} rows")
        print(f"Summary: {response['summary']}")

        # 결과 일부 출력
        if response['results'][:2]:  # 처음 2개만
            print("\nSample Data:")
            for row in response['results'][:2]:
                print(f"  {row}")

    await engine.close()
    print("\n" + "="*60)
    print("Test completed!")


if __name__ == "__main__":
    asyncio.run(test_dynamic_rag())