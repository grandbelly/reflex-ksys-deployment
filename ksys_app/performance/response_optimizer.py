"""
응답 시간 최적화 시스템
TASK_017: PERF_OPTIMIZE_RESPONSE_TIME
"""

from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio
import time
import psycopg
from psycopg.pool import AsyncConnectionPool
from functools import wraps
import hashlib
import json
from cachetools import TTLCache
import redis.asyncio as redis


class OptimizationStrategy(Enum):
    """최적화 전략"""
    QUERY_OPTIMIZATION = "query_optimization"
    CACHING = "caching"
    ASYNC_PROCESSING = "async_processing"
    BATCH_PROCESSING = "batch_processing"
    CONNECTION_POOLING = "connection_pooling"


@dataclass
class PerformanceMetrics:
    """성능 메트릭"""
    operation: str
    response_time_ms: float
    query_time_ms: float
    cache_hit: bool
    optimization_applied: List[str]
    timestamp: datetime


@dataclass
class OptimizationResult:
    """최적화 결과"""
    original_time_ms: float
    optimized_time_ms: float
    improvement_pct: float
    strategies_applied: List[OptimizationStrategy]
    bottlenecks_found: List[str]
    recommendations: List[str]


class ResponseOptimizer:
    """응답 시간 최적화"""
    
    def __init__(self, db_dsn: str):
        self.db_dsn = db_dsn
        self.target_response_time_ms = 5000  # 5초 목표
        
        # 연결 풀
        self.pool: Optional[AsyncConnectionPool] = None
        
        # 캐시 설정
        self.memory_cache = TTLCache(maxsize=1000, ttl=300)  # 5분 TTL
        self.redis_client: Optional[redis.Redis] = None
        
        # 성능 메트릭
        self.metrics: List[PerformanceMetrics] = []
        
        # 쿼리 최적화 힌트
        self.query_hints = {
            'use_index': True,
            'parallel_workers': 4,
            'enable_seqscan': False,
            'enable_hashjoin': True
        }
    
    async def initialize(self):
        """초기화"""
        # 연결 풀 생성
        self.pool = AsyncConnectionPool(
            self.db_dsn,
            min_size=5,
            max_size=20,
            timeout=10,
            max_idle=300
        )
        
        # Redis 연결 (있으면)
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=True
            )
            await self.redis_client.ping()
            print("[INFO] Redis connected for caching")
        except:
            self.redis_client = None
            print("[INFO] Redis not available, using memory cache only")
    
    async def optimize_query(self, query: str, params: tuple = None) -> Tuple[str, Dict]:
        """
        쿼리 최적화
        
        Args:
            query: SQL 쿼리
            params: 쿼리 파라미터
        
        Returns:
            최적화된 쿼리와 실행 계획
        """
        optimized_query = query
        execution_plan = {}
        
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                # EXPLAIN ANALYZE 실행
                explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
                await cur.execute(explain_query, params)
                plan_result = await cur.fetchone()
                
                if plan_result:
                    execution_plan = json.loads(plan_result[0])[0]
                    total_time = execution_plan.get('Execution Time', 0)
                    
                    # 느린 쿼리 최적화
                    if total_time > 1000:  # 1초 이상
                        # 인덱스 힌트 추가
                        if 'Seq Scan' in str(execution_plan):
                            optimized_query = self._add_index_hints(query)
                        
                        # LIMIT 추가 (없으면)
                        if 'LIMIT' not in query.upper():
                            optimized_query += " LIMIT 10000"
                        
                        # 파티션 프루닝
                        if 'influx_agg' in query:
                            optimized_query = self._add_partition_pruning(optimized_query)
        
        return optimized_query, execution_plan
    
    def _add_index_hints(self, query: str) -> str:
        """인덱스 힌트 추가"""
        # TimescaleDB 특화 최적화
        if 'influx_agg' in query:
            query = query.replace('SELECT', 'SELECT /*+ IndexScan(influx_agg) */')
        
        return query
    
    def _add_partition_pruning(self, query: str) -> str:
        """파티션 프루닝 추가"""
        # 시간 범위 제한 강제
        if 'WHERE' in query.upper() and 'bucket' in query:
            # 최근 30일로 제한
            if 'bucket >=' not in query:
                query += " AND bucket >= NOW() - INTERVAL '30 days'"
        
        return query
    
    def cache_key(self, operation: str, params: Dict = None) -> str:
        """캐시 키 생성"""
        key_data = f"{operation}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get_cached(self, key: str) -> Optional[Any]:
        """캐시 조회"""
        # Redis 우선
        if self.redis_client:
            try:
                cached = await self.redis_client.get(f"ksys:{key}")
                if cached:
                    return json.loads(cached)
            except:
                pass
        
        # 메모리 캐시
        return self.memory_cache.get(key)
    
    async def set_cached(self, key: str, value: Any, ttl: int = 300):
        """캐시 저장"""
        # Redis
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    f"ksys:{key}",
                    ttl,
                    json.dumps(value, default=str)
                )
            except:
                pass
        
        # 메모리 캐시
        self.memory_cache[key] = value
    
    def with_cache(ttl: int = 300):
        """캐싱 데코레이터"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(self, *args, **kwargs):
                # 캐시 키 생성
                cache_key = self.cache_key(func.__name__, {'args': args, 'kwargs': kwargs})
                
                # 캐시 조회
                cached = await self.get_cached(cache_key)
                if cached is not None:
                    return cached
                
                # 함수 실행
                result = await func(self, *args, **kwargs)
                
                # 캐시 저장
                await self.set_cached(cache_key, result, ttl)
                
                return result
            
            return wrapper
        return decorator
    
    def measure_time(operation: str):
        """실행 시간 측정 데코레이터"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(self, *args, **kwargs):
                start_time = time.perf_counter()
                cache_hit = False
                
                try:
                    result = await func(self, *args, **kwargs)
                    
                    # 캐시 히트 여부 확인
                    if hasattr(result, '__cached__'):
                        cache_hit = True
                    
                    return result
                    
                finally:
                    end_time = time.perf_counter()
                    response_time = (end_time - start_time) * 1000
                    
                    # 메트릭 기록
                    metric = PerformanceMetrics(
                        operation=operation,
                        response_time_ms=response_time,
                        query_time_ms=0,  # 별도 측정 필요
                        cache_hit=cache_hit,
                        optimization_applied=[],
                        timestamp=datetime.now()
                    )
                    self.metrics.append(metric)
                    
                    # 목표 시간 초과 시 경고
                    if response_time > self.target_response_time_ms:
                        print(f"[WARNING] {operation} exceeded target: {response_time:.0f}ms > {self.target_response_time_ms}ms")
            
            return wrapper
        return decorator
    
    async def batch_process(self, items: List[Any], processor: Callable, batch_size: int = 100):
        """배치 처리"""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            # 병렬 처리
            batch_tasks = [processor(item) for item in batch]
            batch_results = await asyncio.gather(*batch_tasks)
            results.extend(batch_results)
        
        return results
    
    @measure_time("dashboard_data")
    @with_cache(ttl=60)
    async def get_dashboard_data_optimized(self) -> Dict:
        """최적화된 대시보드 데이터 조회"""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                # 병렬 쿼리 실행
                tasks = [
                    self._get_latest_values(cur),
                    self._get_hourly_stats(cur),
                    self._get_alarms(cur)
                ]
                
                results = await asyncio.gather(*tasks)
                
                return {
                    'latest': results[0],
                    'stats': results[1],
                    'alarms': results[2],
                    'timestamp': datetime.now().isoformat()
                }
    
    async def _get_latest_values(self, cursor):
        """최신 값 조회 (최적화)"""
        await cursor.execute("""
            SELECT tag_name, value, ts
            FROM influx_latest
            WHERE tag_name IN (
                SELECT DISTINCT tag_name 
                FROM influx_qc_rule 
                WHERE enabled = true
            )
        """)
        return await cursor.fetchall()
    
    async def _get_hourly_stats(self, cursor):
        """시간별 통계 (최적화)"""
        await cursor.execute("""
            WITH recent_data AS (
                SELECT tag_name, avg_val, bucket
                FROM influx_agg_1h
                WHERE bucket >= NOW() - INTERVAL '24 hours'
                AND bucket <= NOW()
            )
            SELECT 
                tag_name,
                AVG(avg_val) as avg,
                MIN(avg_val) as min,
                MAX(avg_val) as max
            FROM recent_data
            GROUP BY tag_name
        """)
        return await cursor.fetchall()
    
    async def _get_alarms(self, cursor):
        """알람 조회 (최적화)"""
        await cursor.execute("""
            SELECT alarm_type, alarm_level, message, created_at
            FROM alarm_events
            WHERE created_at >= NOW() - INTERVAL '1 hour'
            ORDER BY created_at DESC
            LIMIT 10
        """)
        return await cursor.fetchall()
    
    async def analyze_performance(self) -> OptimizationResult:
        """성능 분석 및 최적화 제안"""
        if not self.metrics:
            return OptimizationResult(
                original_time_ms=0,
                optimized_time_ms=0,
                improvement_pct=0,
                strategies_applied=[],
                bottlenecks_found=[],
                recommendations=[]
            )
        
        # 메트릭 분석
        avg_response_time = sum(m.response_time_ms for m in self.metrics) / len(self.metrics)
        cache_hit_rate = sum(1 for m in self.metrics if m.cache_hit) / len(self.metrics) * 100
        slow_queries = [m for m in self.metrics if m.response_time_ms > self.target_response_time_ms]
        
        bottlenecks = []
        recommendations = []
        
        # 병목 지점 찾기
        if avg_response_time > self.target_response_time_ms:
            bottlenecks.append(f"평균 응답 시간 초과: {avg_response_time:.0f}ms")
        
        if cache_hit_rate < 50:
            bottlenecks.append(f"낮은 캐시 히트율: {cache_hit_rate:.1f}%")
            recommendations.append("캐시 TTL 증가 또는 캐시 키 최적화")
        
        if slow_queries:
            bottlenecks.append(f"느린 쿼리 {len(slow_queries)}개 발견")
            recommendations.append("쿼리 인덱스 추가 및 실행 계획 분석")
        
        # 개선율 계산
        if len(self.metrics) >= 2:
            initial_time = self.metrics[0].response_time_ms
            recent_time = sum(m.response_time_ms for m in self.metrics[-10:]) / min(10, len(self.metrics))
            improvement = ((initial_time - recent_time) / initial_time * 100) if initial_time > 0 else 0
        else:
            improvement = 0
        
        # 추가 권장사항
        if not self.redis_client:
            recommendations.append("Redis 캐시 서버 구성으로 성능 향상 가능")
        
        if not self.pool:
            recommendations.append("연결 풀 크기 조정 검토")
        
        return OptimizationResult(
            original_time_ms=self.metrics[0].response_time_ms if self.metrics else 0,
            optimized_time_ms=avg_response_time,
            improvement_pct=improvement,
            strategies_applied=[
                OptimizationStrategy.CACHING,
                OptimizationStrategy.CONNECTION_POOLING,
                OptimizationStrategy.ASYNC_PROCESSING
            ],
            bottlenecks_found=bottlenecks,
            recommendations=recommendations
        )
    
    async def run_performance_test(self) -> Dict[str, float]:
        """성능 테스트 실행"""
        test_results = {}
        
        # 테스트 1: 단순 쿼리
        start = time.perf_counter()
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT COUNT(*) FROM influx_agg_1h")
                await cur.fetchone()
        test_results['simple_query_ms'] = (time.perf_counter() - start) * 1000
        
        # 테스트 2: 복잡한 쿼리
        start = time.perf_counter()
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT 
                        tag_name,
                        AVG(avg_val),
                        MIN(min_val),
                        MAX(max_val)
                    FROM influx_agg_1h
                    WHERE bucket >= NOW() - INTERVAL '7 days'
                    GROUP BY tag_name
                """)
                await cur.fetchall()
        test_results['complex_query_ms'] = (time.perf_counter() - start) * 1000
        
        # 테스트 3: 캐시 성능
        cache_key = "test_cache"
        
        # 첫 번째 호출 (캐시 미스)
        start = time.perf_counter()
        await self.set_cached(cache_key, {"test": "data"})
        test_results['cache_write_ms'] = (time.perf_counter() - start) * 1000
        
        # 두 번째 호출 (캐시 히트)
        start = time.perf_counter()
        await self.get_cached(cache_key)
        test_results['cache_read_ms'] = (time.perf_counter() - start) * 1000
        
        # 테스트 4: 병렬 처리
        start = time.perf_counter()
        tasks = [self._dummy_async_task() for _ in range(10)]
        await asyncio.gather(*tasks)
        test_results['parallel_10_tasks_ms'] = (time.perf_counter() - start) * 1000
        
        # 목표 달성 여부
        test_results['target_achieved'] = all(
            v < self.target_response_time_ms 
            for k, v in test_results.items() 
            if k != 'target_achieved'
        )
        
        return test_results
    
    async def _dummy_async_task(self):
        """더미 비동기 작업"""
        await asyncio.sleep(0.1)
        return True
    
    async def cleanup(self):
        """정리"""
        if self.pool:
            await self.pool.close()
        
        if self.redis_client:
            await self.redis_client.close()