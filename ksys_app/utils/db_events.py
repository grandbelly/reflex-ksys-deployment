"""
Database event listener for real-time updates
PostgreSQL LISTEN/NOTIFY를 사용한 실시간 이벤트 처리
"""

import asyncio
import json
import psycopg
from typing import Callable, Optional
from ..db import _dsn
import logging

logger = logging.getLogger(__name__)

class DatabaseEventListener:
    """PostgreSQL NOTIFY 이벤트 리스너"""

    def __init__(self, channel: str = "data_update"):
        self.channel = channel
        self.connection: Optional[psycopg.AsyncConnection] = None
        self.callback: Optional[Callable] = None
        self._listening = False

    async def start(self, callback: Callable):
        """이벤트 리스너 시작"""
        self.callback = callback

        try:
            # 별도의 connection 생성 (LISTEN 전용)
            self.connection = await psycopg.AsyncConnection.connect(
                _dsn(),
                autocommit=True
            )

            # LISTEN 시작
            await self.connection.execute(f"LISTEN {self.channel}")
            self._listening = True
            logger.info(f"📡 Listening on channel: {self.channel}")

            # 이벤트 루프 시작
            await self._listen_loop()

        except Exception as e:
            logger.error(f"❌ Event listener error: {e}")
            await self.stop()

    async def _listen_loop(self):
        """NOTIFY 이벤트 대기 루프"""
        while self._listening:
            try:
                # NOTIFY 대기 (timeout 5초)
                async for notify in self.connection.notifies(timeout=5.0):
                    if notify:
                        logger.info(f"📨 Received NOTIFY: {notify.channel} - {notify.payload}")

                        # 콜백 실행
                        if self.callback:
                            try:
                                payload = json.loads(notify.payload) if notify.payload else {}
                                await self.callback(payload)
                            except json.JSONDecodeError:
                                await self.callback({"raw": notify.payload})

            except asyncio.TimeoutError:
                # 타임아웃은 정상 (연결 체크용)
                continue
            except Exception as e:
                logger.error(f"❌ Listen loop error: {e}")
                if not self._listening:
                    break
                await asyncio.sleep(1)

    async def stop(self):
        """이벤트 리스너 중지"""
        self._listening = False

        if self.connection:
            try:
                await self.connection.execute(f"UNLISTEN {self.channel}")
                await self.connection.close()
            except:
                pass

        logger.info(f"🛑 Stopped listening on channel: {self.channel}")

    async def notify(self, payload: dict):
        """다른 연결에서 NOTIFY 전송"""
        try:
            async with await psycopg.AsyncConnection.connect(_dsn(), autocommit=True) as conn:
                payload_json = json.dumps(payload)
                await conn.execute(
                    f"NOTIFY {self.channel}, %s",
                    (payload_json,)
                )
                logger.info(f"📤 Sent NOTIFY: {self.channel} - {payload_json}")
        except Exception as e:
            logger.error(f"❌ Failed to send NOTIFY: {e}")