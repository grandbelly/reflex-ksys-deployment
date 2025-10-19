from __future__ import annotations

import os
import sys
import asyncio
import logging
import psycopg
import psycopg_pool
from psycopg_pool import AsyncConnectionPool
from ksys_app.utils.logger import get_logger, log_function

# Initialize logger for this module
logger = get_logger(__name__)

# Windows에서 ProactorEventLoop 문제 해결 (로컬 개발 환경에서만)
# Docker 환경에서는 Linux이므로 이 설정이 필요 없음
if sys.platform == 'win32' and not os.environ.get('DOCKER_CONTAINER'):
    logger.info("Setting WindowsSelectorEventLoopPolicy for Windows environment")
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    logger.info(f"Running on platform: {sys.platform}, Docker: {os.environ.get('DOCKER_CONTAINER', 'False')}")


@log_function
def _dsn() -> str:
    dsn = os.environ.get("TS_DSN", "")
    if not dsn:
        logger.error("TS_DSN is not set in environment")
        raise RuntimeError("TS_DSN is not set in environment")
    logger.debug(f"DSN retrieved: {dsn[:30]}...")  # Log only first 30 chars for security
    return dsn


# 글로벌 풀 변수
_GLOBAL_POOL: AsyncConnectionPool | None = None
_POOL_LOCK = asyncio.Lock()


@log_function
async def get_pool() -> AsyncConnectionPool:
    """글로벌 싱글톤 풀 관리"""
    global _GLOBAL_POOL

    if _GLOBAL_POOL is None:
        async with _POOL_LOCK:
            # 다시 확인 (double-check)
            if _GLOBAL_POOL is None:
                pid = os.getpid()
                logger.info(f"Creating global pool for first access in process {pid}")
                try:
                    _GLOBAL_POOL = AsyncConnectionPool(
                        _dsn(),
                        min_size=1,  # 최소 연결 수 (줄임)
                        max_size=10,  # 최대 연결 수 (줄임)
                        max_waiting=100,  # 대기 큐 크기 (늘림)
                        timeout=5.0,  # 연결 대기 시간 (줄임)
                        kwargs={"autocommit": True},
                        open=False  # 명시적으로 open 호출
                    )
                    await _GLOBAL_POOL.open()
                    logger.info(f"Global pool created and opened successfully (PID: {pid})")
                except Exception as e:
                    logger.error(f"Failed to create global pool: {str(e)}")
                    _GLOBAL_POOL = None
                    raise

    return _GLOBAL_POOL


@log_function
async def q(sql: str, params: tuple | dict = (), timeout: float = 30.0):
    """쿼리 실행 - 글로벌 풀 사용"""
    start_time = asyncio.get_event_loop().time()

    # 직접 연결을 사용하는 폴백 메커니즘
    try:
        pool = await get_pool()

        # 풀에서 연결 가져오기
        async with pool.connection(timeout=timeout) as conn:
            await conn.execute("SET LOCAL statement_timeout = '30s'")

            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(sql, params)
                results = await cur.fetchall()

                # Log only if query took > 1 second
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > 1.0:
                    logger.warning(f"Slow query ({elapsed:.2f}s): {sql[:100]}...")
                elif logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Query completed in {elapsed:.3f}s, returned {len(results)} rows")

                return results

    except (psycopg_pool.PoolTimeout, asyncio.TimeoutError) as e:
        # 풀 타임아웃 시 직접 연결 사용
        logger.warning(f"Pool timeout, using direct connection: {str(e)}")

        try:
            async with await psycopg.AsyncConnection.connect(
                _dsn(),
                autocommit=True
            ) as conn:
                await conn.execute("SET statement_timeout = '30s'")

                async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                    await cur.execute(sql, params)
                    results = await cur.fetchall()

                    elapsed = asyncio.get_event_loop().time() - start_time
                    logger.info(f"Direct connection query completed in {elapsed:.3f}s")
                    return results

        except Exception as e2:
            logger.error(f"Direct connection also failed: {str(e2)}")
            raise

    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        logger.error(f"SQL: {sql}")
        logger.error(f"Params: {params}")
        raise


@log_function
async def execute_query(sql: str, params: tuple | dict = (), timeout: float = 30.0):
    """Execute SQL without expecting results (for INSERT, UPDATE, DELETE)"""
    start_time = asyncio.get_event_loop().time()

    try:
        pool = await get_pool()

        # 풀에서 연결 가져오기
        async with pool.connection(timeout=timeout) as conn:
            await conn.execute("SET LOCAL statement_timeout = '30s'")

            async with conn.cursor() as cur:
                await cur.execute(sql, params)

                # Log only if query took > 1 second
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > 1.0:
                    logger.warning(f"Slow execute ({elapsed:.2f}s): {sql[:100]}...")
                elif logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Execute completed in {elapsed:.3f}s")

    except (psycopg_pool.PoolTimeout, asyncio.TimeoutError) as e:
        # 풀 타임아웃 시 직접 연결 사용
        logger.warning(f"Pool timeout, using direct connection for execute: {str(e)}")

        try:
            async with await psycopg.AsyncConnection.connect(
                _dsn(),
                autocommit=True
            ) as conn:
                await conn.execute("SET statement_timeout = '30s'")

                async with conn.cursor() as cur:
                    await cur.execute(sql, params)

                    elapsed = asyncio.get_event_loop().time() - start_time
                    logger.info(f"Direct connection execute completed in {elapsed:.3f}s")

        except Exception as e2:
            logger.error(f"Direct connection execute also failed: {str(e2)}")
            raise

    except Exception as e:
        logger.error(f"Execute query failed: {str(e)}")
        logger.error(f"SQL: {sql}")
        logger.error(f"Params: {params}")
        raise


async def close_pool():
    """풀 정리"""
    global _GLOBAL_POOL

    if _GLOBAL_POOL is not None:
        try:
            await _GLOBAL_POOL.close()
            _GLOBAL_POOL = None
            logger.info("Global pool closed successfully")
        except Exception as e:
            logger.error(f"Error closing pool: {e}")