#!/usr/bin/env python
"""
동적 알람 체크 스케줄러
- 1분마다 QC 규칙 기반 알람 체크 실행
- 실시간 데이터 흐름 방해 없음
"""

import time
import threading
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AlarmScheduler:
    """백그라운드 알람 체크 스케줄러"""

    def __init__(self, dsn=None):
        self.dsn = dsn or os.getenv('TS_DSN',
            'postgresql://ecoanp_user:ecoanp_password@localhost:6543/ecoanp')
        self.running = False
        self.thread = None
        self.check_interval = 60  # 초 단위

    def connect_db(self):
        """데이터베이스 연결"""
        try:
            conn = psycopg2.connect(self.dsn)
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return None

    def check_alarms(self):
        """알람 체크 실행"""
        conn = self.connect_db()
        if not conn:
            return False

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 알람 체크 실행
                cur.execute("SELECT * FROM manual_alarm_schedule();")
                result = cur.fetchone()

                if result:
                    logger.info(f"알람 체크 결과: {result['manual_alarm_schedule']}")

                # 통계 조회
                cur.execute("""
                    SELECT
                        COUNT(*) as total_checks,
                        SUM(alarms_generated) as total_alarms,
                        AVG(duration_ms) as avg_duration_ms
                    FROM alarm_schedule_log
                    WHERE execution_time > NOW() - INTERVAL '1 hour'
                """)
                stats = cur.fetchone()

                if stats:
                    logger.info(
                        f"최근 1시간 통계 - "
                        f"체크: {stats['total_checks']}, "
                        f"알람: {stats['total_alarms']}, "
                        f"평균 소요시간: {stats['avg_duration_ms']:.2f}ms"
                    )

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"알람 체크 실패: {e}")
            conn.rollback()
            return False

        finally:
            conn.close()

    def run_scheduler(self):
        """스케줄러 메인 루프"""
        logger.info("알람 스케줄러 시작")

        while self.running:
            try:
                # 설정 확인
                conn = self.connect_db()
                if conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute("SELECT * FROM alarm_check_config LIMIT 1;")
                        config = cur.fetchone()

                        if config and config['enabled']:
                            self.check_interval = config['check_interval_seconds']
                            # 알람 체크 실행
                            self.check_alarms()
                        else:
                            logger.info("알람 체크가 비활성화됨")

                    conn.close()

            except Exception as e:
                logger.error(f"스케줄러 오류: {e}")

            # 대기
            time.sleep(self.check_interval)

        logger.info("알람 스케줄러 종료")

    def start(self):
        """스케줄러 시작"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run_scheduler, daemon=True)
            self.thread.start()
            logger.info("알람 스케줄러 시작됨")

    def stop(self):
        """스케줄러 중지"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
            logger.info("알람 스케줄러 중지됨")

    def status(self):
        """스케줄러 상태 확인"""
        conn = self.connect_db()
        if not conn:
            return None

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        execution_time,
                        alarms_generated,
                        duration_ms,
                        status,
                        CASE
                            WHEN execution_time > NOW() - INTERVAL '2 minutes' THEN 'ACTIVE'
                            WHEN execution_time > NOW() - INTERVAL '5 minutes' THEN 'WARNING'
                            ELSE 'INACTIVE'
                        END as scheduler_status
                    FROM alarm_schedule_log
                    ORDER BY execution_time DESC
                    LIMIT 1;
                """)
                return cur.fetchone()

        except Exception as e:
            logger.error(f"상태 확인 실패: {e}")
            return None

        finally:
            conn.close()

# 독립 실행 시
if __name__ == "__main__":
    scheduler = AlarmScheduler()

    try:
        # 즉시 한번 체크
        logger.info("초기 알람 체크 실행...")
        scheduler.check_alarms()

        # 스케줄러 시작
        scheduler.start()

        # 계속 실행
        while True:
            # 상태 확인
            status = scheduler.status()
            if status:
                logger.info(
                    f"스케줄러 상태: {status['scheduler_status']} - "
                    f"마지막 실행: {status['execution_time']}, "
                    f"알람: {status['alarms_generated']}"
                )

            # 30초 대기
            time.sleep(30)

    except KeyboardInterrupt:
        logger.info("중단 신호 받음")
        scheduler.stop()