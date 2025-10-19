"""
데이터베이스 통합 테스트
실제 DB 연결 및 쿼리 검증
"""
import pytest
import os
from dotenv import load_dotenv
import psycopg
from unittest.mock import patch


class TestDatabaseIntegration:
    """데이터베이스 통합 테스트"""
    
    @classmethod
    def setup_class(cls):
        """테스트 클래스 설정"""
        load_dotenv()
        cls.dsn = os.getenv('TS_DSN')
        if not cls.dsn:
            pytest.skip("TS_DSN 환경변수가 설정되지 않았습니다")
    
    def test_database_connection(self):
        """DB 연결 테스트"""
        try:
            conn = psycopg.connect(self.dsn, connect_timeout=5)
            cursor = conn.cursor()
            cursor.execute('SELECT 1;')
            result = cursor.fetchone()[0]
            assert result == 1
            cursor.close()
            conn.close()
        except Exception as e:
            pytest.fail(f"DB 연결 실패: {e}")
    
    def test_timescaledb_extension(self):
        """TimescaleDB 확장 확인"""
        conn = psycopg.connect(self.dsn, connect_timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'timescaledb';")
        result = cursor.fetchone()
        assert result is not None, "TimescaleDB 확장이 설치되지 않았습니다"
        assert result[0] == 'timescaledb'
        cursor.close()
        conn.close()
    
    def test_required_tables_exist(self):
        """필수 테이블 존재 확인"""
        required_tables = [
            'influx_agg_1m', 'influx_agg_10m', 'influx_agg_1h', 
            'influx_latest', 'influx_qc_rule'
        ]
        
        conn = psycopg.connect(self.dsn, connect_timeout=5)
        cursor = conn.cursor()
        
        for table in required_tables:
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = %s;
            """, (table,))
            result = cursor.fetchone()
            assert result is not None, f"필수 테이블 {table}이 존재하지 않습니다"
        
        cursor.close()
        conn.close()
    
    def test_influx_latest_schema(self):
        """influx_latest 스키마 확인"""
        expected_columns = ['tag_name', 'value', 'ts']
        
        conn = psycopg.connect(self.dsn, connect_timeout=5)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'influx_latest'
            ORDER BY ordinal_position;
        """)
        columns = [row[0] for row in cursor.fetchall()]
        
        for expected_col in expected_columns:
            assert expected_col in columns, f"influx_latest에 {expected_col} 컬럼이 없습니다"
        
        cursor.close()
        conn.close()
    
    def test_influx_agg_schema(self):
        """influx_agg_1m 스키마 확인"""
        expected_columns = ['bucket', 'tag_name', 'count', 'avg', 'min', 'max', 'last', 'first']  # n → count, sum 제거
        
        conn = psycopg.connect(self.dsn, connect_timeout=5)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'influx_agg_1m'
            ORDER BY ordinal_position;
        """)
        columns = [row[0] for row in cursor.fetchall()]
        
        for expected_col in expected_columns:
            assert expected_col in columns, f"influx_agg_1m에 {expected_col} 컬럼이 없습니다"
        
        cursor.close()
        conn.close()
    
    def test_sample_data_query(self):
        """샘플 데이터 쿼리 테스트"""
        conn = psycopg.connect(self.dsn, connect_timeout=5)
        cursor = conn.cursor()
        
        # Latest 데이터 조회
        cursor.execute("SELECT tag_name, value, ts FROM public.influx_latest LIMIT 5;")
        latest_rows = cursor.fetchall()
        
        # 데이터가 있으면 스키마 검증
        if latest_rows:
            for row in latest_rows:
                assert len(row) == 3, "influx_latest 행의 컬럼 수가 올바르지 않습니다"
                assert isinstance(row[0], str), "tag_name은 문자열이어야 합니다"
                assert isinstance(row[1], (int, float)), "value는 숫자여야 합니다"
        
        # Aggregate 데이터 조회
        cursor.execute("""
            SELECT bucket, tag_name, count, avg, min, max, last, first
            FROM public.influx_agg_1m
            WHERE bucket >= now() - interval '1 hour'
            LIMIT 5;
        """)
        agg_rows = cursor.fetchall()
        
        # 데이터가 있으면 스키마 검증
        if agg_rows:
            for row in agg_rows:
                assert len(row) == 8, "influx_agg_1m 행의 컬럼 수가 올바르지 않습니다"
                assert isinstance(row[1], str), "tag_name은 문자열이어야 합니다"
                assert isinstance(row[2], int), "count는 정수여야 합니다"
        
        cursor.close()
        conn.close()
    
    def test_qc_rule_schema(self):
        """QC 규칙 테이블 스키마 확인"""
        expected_columns = [
            'tag_name', 'min_val', 'max_val', 'warning_low',
            'warning_high', 'critical_low', 'critical_high'  # warn_min/max → warning_low/high로 변경
        ]
        
        conn = psycopg.connect(self.dsn, connect_timeout=5)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'influx_qc_rule'
            ORDER BY ordinal_position;
        """)
        columns = [row[0] for row in cursor.fetchall()]
        
        for expected_col in expected_columns:
            assert expected_col in columns, f"influx_qc_rule에 {expected_col} 컬럼이 없습니다"
        
        cursor.close()
        conn.close()
    
    @pytest.mark.slow
    def test_query_performance(self):
        """쿼리 성능 테스트 (24시간 윈도우)"""
        import time
        
        conn = psycopg.connect(self.dsn, connect_timeout=5)
        cursor = conn.cursor()
        
        # 24시간 윈도우 쿼리 (PRD 목표: <300ms)
        start_time = time.time()
        cursor.execute("""
            SELECT bucket, tag_name, avg, min, max, last, first, count
            FROM public.influx_agg_1m
            WHERE bucket >= now() - interval '24 hours'
            ORDER BY bucket
            LIMIT 10000;
        """)
        rows = cursor.fetchall()
        elapsed_ms = (time.time() - start_time) * 1000
        
        print(f"24시간 쿼리: {elapsed_ms:.1f}ms, {len(rows)}행")
        assert elapsed_ms < 2000, f"24시간 쿼리가 너무 느립니다: {elapsed_ms:.1f}ms"  # 개발환경 여유
        
        cursor.close()
        conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])