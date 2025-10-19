"""
LlamaIndex-based RAG Engine for TimescaleDB
프레임워크 기반의 체계적인 구현
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

# LlamaIndex imports
from llama_index.core import SQLDatabase, Settings
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.llms.anthropic import Anthropic
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


class LlamaIndexRAGEngine:
    """
    LlamaIndex 기반 RAG 엔진
    TimescaleDB 시계열 데이터에 최적화
    """

    def __init__(self, db_dsn: str = None):
        """
        Args:
            db_dsn: PostgreSQL connection string
        """
        self.db_dsn = db_dsn or os.getenv(
            "TS_DSN",
            "postgresql://ecoanp_user:ecoanp_password@localhost:5432/ecoanp"
        )

        # SQLAlchemy engine with no connection pooling (for async)
        self.engine = create_engine(
            self.db_dsn,
            poolclass=NullPool,
            future=True
        )

        # Initialize LlamaIndex components
        self._setup_llama_index()

        # Cache for active tags
        self.active_tags = []
        self.last_discovery = None

    def _setup_llama_index(self):
        """LlamaIndex 컴포넌트 설정"""

        # 1. LLM 설정 (Claude 사용)
        # Note: 실제 사용시 API key 필요
        # self.llm = Anthropic(
        #     api_key=os.getenv("ANTHROPIC_API_KEY"),
        #     model="claude-3-haiku-20240307",
        #     temperature=0
        # )

        # For testing: Mock LLM
        self.llm = None  # Will implement mock for testing

        # 2. Embedding 모델 설정 (로컬 모델 사용)
        self.embed_model = HuggingFaceEmbedding(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            cache_folder="./cache"
        )

        # 3. Settings 구성
        Settings.embed_model = self.embed_model
        # Settings.llm = self.llm  # 실제 사용시

        # 4. SQL Database 설정
        self.sql_database = SQLDatabase(
            self.engine,
            include_tables=[
                "influx_latest",
                "influx_agg_1m",
                "influx_agg_10m",
                "influx_agg_1h",
                "influx_agg_1d"
            ]
        )

    def discover_tags(self) -> List[str]:
        """활성 태그 동적 발견"""

        # 캐시 확인 (5분)
        if self.last_discovery:
            elapsed = (datetime.now() - self.last_discovery).total_seconds()
            if elapsed < 300:
                return self.active_tags

        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT tag_name
                FROM influx_hist
                WHERE ts >= NOW() - INTERVAL '24 hours'
                ORDER BY tag_name
            """))

            self.active_tags = [row[0] for row in result]
            self.last_discovery = datetime.now()

        return self.active_tags

    def _select_optimal_view(self, query: str) -> str:
        """쿼리에 따른 최적 뷰 선택"""

        # 시간 키워드 매핑
        time_view_mapping = {
            # 실시간 (5분 이내)
            ('실시간', 'realtime', 'current', '현재'): 'influx_latest',
            # 1시간 이내
            ('분', 'minute', '시간', 'hour'): 'influx_agg_1m',
            # 1일 이내
            ('일', 'day', '어제', 'yesterday'): 'influx_agg_10m',
            # 1주일 이내
            ('주', 'week', '주간'): 'influx_agg_1h',
            # 1달 이상
            ('월', 'month', '달', '년', 'year'): 'influx_agg_1d',
        }

        query_lower = query.lower()

        for keywords, view in time_view_mapping.items():
            if any(keyword in query_lower for keyword in keywords):
                return view

        # 기본값: 1분 집계
        return 'influx_agg_1m'

    def _enhance_query_with_context(self, query: str) -> str:
        """쿼리에 컨텍스트 추가"""

        # 활성 태그 정보 추가
        tags = self.discover_tags()

        context = f"""
        Available tags: {', '.join(tags)}

        Table schemas:
        - influx_latest: Latest sensor values (tag_name, value, ts)
        - influx_agg_1m: 1-minute aggregates (bucket, tag_name, avg, min, max, sum)
        - influx_agg_10m: 10-minute aggregates (bucket, tag_name, avg, min, max, sum)
        - influx_agg_1h: 1-hour aggregates (bucket, tag_name, avg, min, max, sum)
        - influx_agg_1d: 1-day aggregates (bucket, tag_name, avg, min, max, sum)

        Use appropriate table based on time range in the query.
        For time filters, use: bucket >= NOW() - INTERVAL 'X hours/days/weeks'

        Query: {query}
        """

        return context

    def query_with_sql(self, sql: str) -> Dict[str, Any]:
        """직접 SQL 쿼리 실행"""

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                rows = [dict(row._mapping) for row in result]

                return {
                    'success': True,
                    'data': rows,
                    'row_count': len(rows),
                    'sql': sql
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'sql': sql
            }

    def query_natural_language(self, query: str) -> Dict[str, Any]:
        """자연어 쿼리 처리 (Mock implementation for testing)"""

        # 최적 뷰 선택
        optimal_view = self._select_optimal_view(query)

        # 태그 추출
        tags = self.discover_tags()
        detected_tags = []
        query_upper = query.upper()

        for tag in tags:
            if tag in query_upper:
                detected_tags.append(tag)

        # 모든 태그
        if any(keyword in query.lower() for keyword in ['모든', '전체', 'all']):
            detected_tags = tags

        # Mock SQL 생성 (실제로는 LLM이 생성)
        sql = self._generate_mock_sql(query, optimal_view, detected_tags)

        # 실행
        result = self.query_with_sql(sql)

        if result['success']:
            result['view_used'] = optimal_view
            result['tags_queried'] = detected_tags
            result['summary'] = self._format_summary(result['data'], query)

        return result

    def _generate_mock_sql(self, query: str, view: str, tags: List[str]) -> str:
        """Mock SQL 생성 (테스트용)"""

        # 집계 함수 결정
        if '평균' in query or 'average' in query.lower():
            agg_func = 'AVG(avg)' if view != 'influx_latest' else 'value'
            agg_label = 'average'
        elif '최대' in query or 'max' in query.lower():
            agg_func = 'MAX(max)' if view != 'influx_latest' else 'value'
            agg_label = 'maximum'
        elif '최소' in query or 'min' in query.lower():
            agg_func = 'MIN(min)' if view != 'influx_latest' else 'value'
            agg_label = 'minimum'
        else:
            agg_func = 'AVG(avg)' if view != 'influx_latest' else 'value'
            agg_label = 'value'

        # SQL 생성
        if view == 'influx_latest':
            sql = f"""
                SELECT tag_name, {agg_func} as {agg_label}, ts
                FROM {view}
            """
        else:
            sql = f"""
                SELECT tag_name, {agg_func} as {agg_label}
                FROM {view}
                WHERE bucket >= NOW() - INTERVAL '1 hour'
            """

        # 태그 필터
        if tags:
            tag_list = ','.join([f"'{t}'" for t in tags])
            if 'WHERE' in sql:
                sql += f" AND tag_name IN ({tag_list})"
            else:
                sql += f" WHERE tag_name IN ({tag_list})"

        if view != 'influx_latest':
            sql += " GROUP BY tag_name"

        sql += " ORDER BY tag_name"

        return sql

    def _format_summary(self, data: List[Dict], query: str) -> str:
        """결과 요약 생성"""

        if not data:
            return "해당 조건에 맞는 데이터가 없습니다."

        summary_lines = []
        summary_lines.append(f"{len(data)}개 센서 데이터 조회 결과:")

        for row in data[:5]:  # 처음 5개만
            tag = row.get('tag_name', 'Unknown')

            # 값 찾기 (다양한 컬럼명 처리)
            value = None
            for key in ['average', 'maximum', 'minimum', 'value']:
                if key in row and row[key] is not None:
                    value = row[key]
                    break

            if value is not None:
                summary_lines.append(f"  - {tag}: {value:.2f}")

        if len(data) > 5:
            summary_lines.append(f"  ... 외 {len(data) - 5}개")

        return '\n'.join(summary_lines)

    def create_query_engine(self, tables: List[str] = None):
        """
        LlamaIndex Query Engine 생성
        실제 LLM 사용시 활성화
        """
        if not self.llm:
            raise ValueError("LLM not configured. Use query_natural_language() for mock queries.")

        if not tables:
            tables = ["influx_latest", "influx_agg_1m"]

        query_engine = NLSQLTableQueryEngine(
            sql_database=self.sql_database,
            tables=tables,
            llm=self.llm
        )

        return query_engine


def test_llamaindex_engine():
    """LlamaIndex RAG Engine 테스트"""

    print("=" * 80)
    print("LLAMAINDEX RAG ENGINE TEST")
    print("=" * 80)

    # 엔진 초기화
    engine = LlamaIndexRAGEngine()

    # 1. 태그 발견 테스트
    print("\n1. Tag Discovery Test")
    print("-" * 40)
    tags = engine.discover_tags()
    print(f"Active Tags: {tags}")

    # 2. Direct SQL 테스트
    print("\n2. Direct SQL Test")
    print("-" * 40)
    sql = "SELECT tag_name, value FROM influx_latest LIMIT 5"
    result = engine.query_with_sql(sql)
    if result['success']:
        print(f"✅ Query successful: {result['row_count']} rows")
        for row in result['data']:
            print(f"  {row}")
    else:
        print(f"❌ Query failed: {result['error']}")

    # 3. Natural Language 테스트
    print("\n3. Natural Language Query Test")
    print("-" * 40)

    test_queries = [
        "모든 센서의 최근 1시간 평균값",
        "D100 센서의 현재 값",
        "최근 24시간 최대값",
        "이번 주 D200, D201의 평균"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        result = engine.query_natural_language(query)

        if result['success']:
            print(f"✅ Success")
            print(f"  View: {result.get('view_used')}")
            print(f"  Rows: {result['row_count']}")
            print(f"  SQL: {result['sql'][:100]}...")
            print(f"  Summary:\n{result['summary']}")
        else:
            print(f"❌ Failed: {result['error']}")

    print("\n" + "=" * 80)
    print("Test completed!")


if __name__ == "__main__":
    test_llamaindex_engine()