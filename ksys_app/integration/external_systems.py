"""
외부 시스템 연동
TASK_018: INTEG_CONNECT_EXTERNAL_SYSTEMS
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio
import aiohttp
import json
import psycopg
from abc import ABC, abstractmethod


class SystemType(Enum):
    """외부 시스템 타입"""
    WEATHER_API = "weather_api"
    POWER_RATE_API = "power_rate_api"
    SCADA = "scada"
    ERP = "erp"
    MES = "mes"


@dataclass
class WeatherData:
    """날씨 데이터"""
    timestamp: datetime
    temperature: float      # 온도 (°C)
    humidity: float        # 습도 (%)
    pressure: float        # 기압 (hPa)
    wind_speed: float      # 풍속 (m/s)
    rainfall: float        # 강수량 (mm)
    uv_index: float       # 자외선 지수
    forecast: Dict[str, Any]  # 예보 데이터


@dataclass
class PowerRateData:
    """전력 요금 데이터"""
    timestamp: datetime
    time_zone: str         # 시간대 (경부하/중간부하/최대부하)
    rate_per_kwh: float    # kWh당 요금
    base_rate: float       # 기본요금
    season: str           # 계절 (여름/겨울/기타)
    peak_hours: List[int]  # 피크 시간대


@dataclass
class SCADAData:
    """SCADA 데이터"""
    timestamp: datetime
    tag_name: str
    value: float
    quality: str          # Good/Bad/Uncertain
    source: str          # PLC/RTU/HMI


class ExternalSystemConnector(ABC):
    """외부 시스템 연결 인터페이스"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """연결"""
        pass
    
    @abstractmethod
    async def fetch_data(self) -> Any:
        """데이터 조회"""
        pass
    
    @abstractmethod
    async def sync_data(self, data: Any) -> bool:
        """데이터 동기화"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """연결 해제"""
        pass


class WeatherAPIConnector(ExternalSystemConnector):
    """날씨 API 연동"""
    
    def __init__(self, api_key: str, location: str = "Seoul"):
        self.api_key = api_key
        self.location = location
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def connect(self) -> bool:
        """API 연결"""
        try:
            self.session = aiohttp.ClientSession()
            # 연결 테스트
            async with self.session.get(
                f"{self.base_url}/weather",
                params={
                    'q': self.location,
                    'appid': self.api_key,
                    'units': 'metric'
                }
            ) as response:
                return response.status == 200
        except Exception as e:
            print(f"[ERROR] Weather API connection failed: {e}")
            return False
    
    async def fetch_data(self) -> Optional[WeatherData]:
        """날씨 데이터 조회"""
        if not self.session:
            await self.connect()
        
        try:
            # 현재 날씨
            async with self.session.get(
                f"{self.base_url}/weather",
                params={
                    'q': self.location,
                    'appid': self.api_key,
                    'units': 'metric'
                }
            ) as response:
                current = await response.json()
            
            # 예보
            async with self.session.get(
                f"{self.base_url}/forecast",
                params={
                    'q': self.location,
                    'appid': self.api_key,
                    'units': 'metric',
                    'cnt': 8  # 24시간 예보 (3시간 단위)
                }
            ) as response:
                forecast = await response.json()
            
            return WeatherData(
                timestamp=datetime.now(),
                temperature=current['main']['temp'],
                humidity=current['main']['humidity'],
                pressure=current['main']['pressure'],
                wind_speed=current['wind']['speed'],
                rainfall=current.get('rain', {}).get('1h', 0),
                uv_index=current.get('uvi', 0),
                forecast=forecast
            )
            
        except Exception as e:
            print(f"[ERROR] Weather data fetch failed: {e}")
            return None
    
    async def sync_data(self, data: WeatherData) -> bool:
        """데이터 동기화 (DB 저장)"""
        # 실제 구현 시 DB 저장
        return True
    
    async def disconnect(self) -> bool:
        """연결 해제"""
        if self.session:
            await self.session.close()
        return True


class PowerRateAPIConnector(ExternalSystemConnector):
    """전력 요금 API 연동"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.kepco.co.kr/v1"  # 예시 URL
        self.session: Optional[aiohttp.ClientSession] = None
        
        # 시간대별 요금 테이블 (예시)
        self.rate_table = {
            'summer': {  # 여름 (6-8월)
                'peak': 142.3,      # 최대부하
                'mid': 105.7,       # 중간부하
                'off_peak': 68.6    # 경부하
            },
            'winter': {  # 겨울 (12-2월)
                'peak': 138.8,
                'mid': 98.1,
                'off_peak': 67.3
            },
            'other': {   # 봄/가을
                'peak': 105.8,
                'mid': 78.6,
                'off_peak': 68.2
            }
        }
    
    async def connect(self) -> bool:
        """API 연결"""
        self.session = aiohttp.ClientSession()
        return True
    
    async def fetch_data(self) -> Optional[PowerRateData]:
        """전력 요금 데이터 조회"""
        try:
            # 현재 시간 기준 요금 계산
            now = datetime.now()
            hour = now.hour
            month = now.month
            
            # 계절 판정
            if month in [6, 7, 8]:
                season = 'summer'
            elif month in [12, 1, 2]:
                season = 'winter'
            else:
                season = 'other'
            
            # 시간대 판정
            if 9 <= hour < 10 or 12 <= hour < 13 or 17 <= hour < 23:
                time_zone = 'peak'
                rate = self.rate_table[season]['peak']
            elif 10 <= hour < 12 or 13 <= hour < 17:
                time_zone = 'mid'
                rate = self.rate_table[season]['mid']
            else:
                time_zone = 'off_peak'
                rate = self.rate_table[season]['off_peak']
            
            # 피크 시간대
            peak_hours = [9, 17, 18, 19, 20, 21, 22] if season == 'summer' else [10, 11, 17, 18, 19, 20]
            
            return PowerRateData(
                timestamp=now,
                time_zone=time_zone,
                rate_per_kwh=rate,
                base_rate=6160.0,  # 기본요금 예시
                season=season,
                peak_hours=peak_hours
            )
            
        except Exception as e:
            print(f"[ERROR] Power rate fetch failed: {e}")
            return None
    
    async def sync_data(self, data: PowerRateData) -> bool:
        """데이터 동기화"""
        return True
    
    async def disconnect(self) -> bool:
        """연결 해제"""
        if self.session:
            await self.session.close()
        return True


class SCADAInterface:
    """SCADA 인터페이스 설계"""
    
    def __init__(self, db_dsn: str):
        self.db_dsn = db_dsn
        self.protocol = "OPC-UA"  # or Modbus, DNP3, IEC 61850
        self.connected = False
        
        # SCADA 태그 매핑
        self.tag_mapping = {
            # SCADA 태그 -> 내부 태그
            'PLC01.PUMP1.FLOW': 'FLOW_PUMP1',
            'PLC01.PUMP1.PRESS': 'PRESS_PUMP1',
            'PLC01.RO1.TMP': 'TMP',
            'PLC01.RO1.COND_IN': 'COND_IN',
            'PLC01.RO1.COND_OUT': 'COND_OUT',
            'RTU01.TANK1.LEVEL': 'LEVEL_TANK1',
            'RTU01.TANK1.TEMP': 'TEMP_TANK1'
        }
    
    async def connect(self, server_url: str) -> bool:
        """SCADA 서버 연결"""
        try:
            # OPC-UA 클라이언트 연결 (실제 구현 시)
            # from asyncua import Client
            # self.client = Client(server_url)
            # await self.client.connect()
            
            self.connected = True
            print(f"[INFO] Connected to SCADA server: {server_url}")
            return True
            
        except Exception as e:
            print(f"[ERROR] SCADA connection failed: {e}")
            return False
    
    async def read_tags(self, tag_list: List[str]) -> Dict[str, SCADAData]:
        """SCADA 태그 읽기"""
        data = {}
        
        for scada_tag in tag_list:
            if scada_tag in self.tag_mapping:
                # 실제 구현 시 SCADA에서 읽기
                # value = await self.client.read_node(scada_tag)
                
                # 더미 데이터
                import random
                value = random.uniform(0, 100)
                
                internal_tag = self.tag_mapping[scada_tag]
                data[internal_tag] = SCADAData(
                    timestamp=datetime.now(),
                    tag_name=internal_tag,
                    value=value,
                    quality='Good',
                    source='PLC01'
                )
        
        return data
    
    async def write_tags(self, tag_values: Dict[str, float]) -> bool:
        """SCADA 태그 쓰기"""
        try:
            for internal_tag, value in tag_values.items():
                # 역매핑
                scada_tag = None
                for st, it in self.tag_mapping.items():
                    if it == internal_tag:
                        scada_tag = st
                        break
                
                if scada_tag:
                    # 실제 구현 시 SCADA에 쓰기
                    # await self.client.write_node(scada_tag, value)
                    print(f"[INFO] Write to SCADA: {scada_tag} = {value}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] SCADA write failed: {e}")
            return False
    
    async def subscribe_changes(self, tag_list: List[str], callback):
        """태그 변경 구독"""
        # 실제 구현 시 SCADA 이벤트 구독
        # subscription = await self.client.create_subscription(500, callback)
        # for tag in tag_list:
        #     await subscription.subscribe_data_change(tag)
        pass
    
    async def sync_to_database(self, data: Dict[str, SCADAData]):
        """데이터베이스 동기화"""
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    for tag_name, scada_data in data.items():
                        # influx_latest 테이블 업데이트
                        await cur.execute("""
                            INSERT INTO influx_latest (tag_name, value, ts)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (tag_name) 
                            DO UPDATE SET value = %s, ts = %s
                        """, (
                            tag_name,
                            scada_data.value,
                            scada_data.timestamp,
                            scada_data.value,
                            scada_data.timestamp
                        ))
                    
                    await conn.commit()
                    print(f"[INFO] Synced {len(data)} tags to database")
                    
        except Exception as e:
            print(f"[ERROR] Database sync failed: {e}")
    
    async def disconnect(self):
        """연결 해제"""
        # if self.client:
        #     await self.client.disconnect()
        self.connected = False


class ExternalSystemIntegrator:
    """외부 시스템 통합 관리자"""
    
    def __init__(self, db_dsn: str):
        self.db_dsn = db_dsn
        self.connectors: Dict[SystemType, ExternalSystemConnector] = {}
        self.scada_interface: Optional[SCADAInterface] = None
        self.sync_intervals = {
            SystemType.WEATHER_API: 3600,      # 1시간
            SystemType.POWER_RATE_API: 900,    # 15분
            SystemType.SCADA: 10               # 10초
        }
        self.sync_tasks = {}
    
    async def register_connector(self, 
                                system_type: SystemType,
                                connector: ExternalSystemConnector):
        """커넥터 등록"""
        self.connectors[system_type] = connector
        
        # 연결 테스트
        if await connector.connect():
            print(f"[INFO] {system_type.value} connected successfully")
            
            # 자동 동기화 시작
            if system_type in self.sync_intervals:
                self.sync_tasks[system_type] = asyncio.create_task(
                    self._auto_sync(system_type)
                )
        else:
            print(f"[ERROR] {system_type.value} connection failed")
    
    async def _auto_sync(self, system_type: SystemType):
        """자동 동기화"""
        connector = self.connectors[system_type]
        interval = self.sync_intervals[system_type]
        
        while True:
            try:
                # 데이터 조회
                data = await connector.fetch_data()
                
                if data:
                    # DB 동기화
                    await connector.sync_data(data)
                    
                    # 특별 처리
                    if system_type == SystemType.WEATHER_API:
                        await self._process_weather_data(data)
                    elif system_type == SystemType.POWER_RATE_API:
                        await self._process_power_rate(data)
                
                # 대기
                await asyncio.sleep(interval)
                
            except Exception as e:
                print(f"[ERROR] Auto sync failed for {system_type.value}: {e}")
                await asyncio.sleep(60)  # 에러 시 1분 대기
    
    async def _process_weather_data(self, weather: WeatherData):
        """날씨 데이터 처리"""
        # 온도가 수처리에 미치는 영향 분석
        if weather.temperature < 5:
            print("[WARNING] Low temperature - RO efficiency may decrease")
        elif weather.temperature > 35:
            print("[WARNING] High temperature - Cooling system check required")
        
        # 강수량 영향
        if weather.rainfall > 50:
            print("[INFO] Heavy rainfall - Raw water quality may change")
    
    async def _process_power_rate(self, rate: PowerRateData):
        """전력 요금 데이터 처리"""
        # 피크 시간대 운전 최적화
        current_hour = datetime.now().hour
        
        if current_hour in rate.peak_hours:
            print(f"[INFO] Peak hours - Current rate: {rate.rate_per_kwh} KRW/kWh")
            # 비필수 장비 운전 중지 권고
        else:
            print(f"[INFO] Off-peak hours - Current rate: {rate.rate_per_kwh} KRW/kWh")
            # 에너지 집약 작업 수행 권고
    
    async def initialize_scada(self, server_url: str):
        """SCADA 초기화"""
        self.scada_interface = SCADAInterface(self.db_dsn)
        
        if await self.scada_interface.connect(server_url):
            # 주기적 데이터 수집
            asyncio.create_task(self._scada_polling())
    
    async def _scada_polling(self):
        """SCADA 폴링"""
        while self.scada_interface and self.scada_interface.connected:
            try:
                # 모든 태그 읽기
                tags = list(self.scada_interface.tag_mapping.keys())
                data = await self.scada_interface.read_tags(tags)
                
                # DB 동기화
                await self.scada_interface.sync_to_database(data)
                
                await asyncio.sleep(10)  # 10초 주기
                
            except Exception as e:
                print(f"[ERROR] SCADA polling failed: {e}")
                await asyncio.sleep(30)
    
    async def get_integrated_data(self) -> Dict[str, Any]:
        """통합 데이터 조회"""
        integrated = {
            'timestamp': datetime.now().isoformat(),
            'systems': {}
        }
        
        for system_type, connector in self.connectors.items():
            try:
                data = await connector.fetch_data()
                if data:
                    integrated['systems'][system_type.value] = data.__dict__ if hasattr(data, '__dict__') else data
            except:
                integrated['systems'][system_type.value] = None
        
        return integrated
    
    async def shutdown(self):
        """종료"""
        # 동기화 작업 취소
        for task in self.sync_tasks.values():
            task.cancel()
        
        # 커넥터 연결 해제
        for connector in self.connectors.values():
            await connector.disconnect()
        
        # SCADA 연결 해제
        if self.scada_interface:
            await self.scada_interface.disconnect()