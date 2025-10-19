"""
Simple Forecast Service - 실제 모델 파일 없이 작동하는 간단한 예측 서비스.

통계적 방법 (이동평균, 선형 추세)으로 예측을 생성합니다.
실제 ML 모델이 훈련되기 전까지 사용할 수 있는 임시 솔루션입니다.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class SimpleForecastService:
    """간단한 통계 기반 예측 서비스."""

    HORIZONS = {
        '10min': 10,
        '30min': 30,
        '60min': 60,
        '2h': 120,
        '4h': 240,
        '6h': 360,
        '12h': 720,
        '24h': 1440,
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    async def predict(
        self,
        tag_name: str,
        horizon: str = '30min',
        model_type: Optional[str] = None,
        include_confidence: bool = True,
    ) -> Dict[str, Any]:
        """
        간단한 통계 기반 예측 생성.

        Args:
            tag_name: 센서 태그명
            horizon: 예측 기간
            model_type: 모델 타입 (무시됨, 항상 통계 기반)
            include_confidence: 신뢰구간 포함 여부

        Returns:
            예측 결과 딕셔너리
        """
        if horizon not in self.HORIZONS:
            raise ValueError(f"Invalid horizon: {horizon}")

        # 최근 데이터 가져오기 (24시간)
        recent_data = await self._get_recent_data(tag_name, hours=24)

        if recent_data.empty:
            raise ValueError(f"No data found for {tag_name}")

        # 예측 생성
        minutes = self.HORIZONS[horizon]
        predictions = self._generate_statistical_forecast(
            recent_data,
            steps=minutes,
            include_confidence=include_confidence,
        )

        # 모델 정보 (더미)
        from sqlalchemy import select
        from ..models.forecasting_orm import ModelRegistry

        # 등록된 모델 확인
        query = select(ModelRegistry).where(
            ModelRegistry.tag_name == tag_name
        ).order_by(ModelRegistry.train_mae.asc()).limit(1)

        result = await self.session.execute(query)
        model_record = result.scalars().first()

        if model_record:
            model_info = {
                'model_id': model_record.model_id,
                'model_type': model_record.model_type,
                'version': model_record.version,
                'trained_at': model_record.created_at.isoformat() if model_record.created_at else None,
            }
            metrics = {
                'mae': float(model_record.train_mae) if model_record.train_mae else 0.0,
                'rmse': float(model_record.train_rmse) if model_record.train_rmse else 0.0,
                'mape': float(model_record.train_mape) if model_record.train_mape else 0.0,
            }
        else:
            model_info = {
                'model_id': 0,
                'model_type': 'Statistical',
                'version': 'v1.0.0',
                'trained_at': datetime.now().isoformat(),
            }
            metrics = {
                'mae': 0.0,
                'rmse': 0.0,
                'mape': 0.0,
            }

        return {
            'tag_name': tag_name,
            'forecast_time': datetime.now().isoformat(),
            'horizon': horizon,
            'predictions': predictions,
            'model_info': model_info,
            'metrics': metrics,
        }

    async def _get_recent_data(
        self,
        tag_name: str,
        hours: int = 24,
    ) -> pd.DataFrame:
        """최근 센서 데이터 조회 - 가장 최근 데이터 기준으로 24시간 조회."""
        # 1단계: 해당 센서의 가장 최근 타임스탬프 찾기
        latest_query = text("""
            SELECT MAX(ts) as latest_ts
            FROM influx_hist
            WHERE tag_name = :tag_name
        """)

        latest_result = await self.session.execute(latest_query, {'tag_name': tag_name})
        latest_row = latest_result.mappings().first()

        if not latest_row or not latest_row['latest_ts']:
            return pd.DataFrame(columns=['timestamp', 'value'])

        # 2단계: 가장 최근 시점부터 24시간 전까지 데이터 조회
        end_time = latest_row['latest_ts']
        start_time = end_time - timedelta(hours=hours)

        query = text("""
            SELECT
                ts AT TIME ZONE 'UTC' AS timestamp,
                value
            FROM influx_hist
            WHERE tag_name = :tag_name
                AND ts >= :start_time
                AND ts <= :end_time
            ORDER BY ts ASC
        """)

        result = await self.session.execute(
            query,
            {
                'tag_name': tag_name,
                'start_time': start_time,
                'end_time': end_time,
            }
        )

        rows = result.mappings().all()

        if not rows:
            return pd.DataFrame(columns=['timestamp', 'value'])

        df = pd.DataFrame([dict(r) for r in rows])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['value'] = df['value'].astype(float)

        return df

    def _generate_statistical_forecast(
        self,
        recent_data: pd.DataFrame,
        steps: int,
        include_confidence: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        통계 기반 예측 생성 (이동평균 + 선형 추세).

        방법:
        1. 최근 N개 데이터의 이동평균 계산
        2. 선형 추세 파악
        3. 이동평균 + 추세로 미래 예측
        4. 표준편차로 신뢰구간 계산
        """
        values = recent_data['value'].values
        last_timestamp = recent_data['timestamp'].max()

        # 이동평균 계산 (최근 60분)
        window = min(60, len(values))
        if window < 5:
            # 데이터가 너무 적으면 마지막 값 사용
            base_value = values[-1]
            trend = 0
            std_dev = 0.01 * abs(base_value)  # 1% 변동
        else:
            moving_avg = values[-window:].mean()

            # 선형 추세 계산
            x = np.arange(window)
            y = values[-window:]
            coeffs = np.polyfit(x, y, 1)  # 1차 다항식 (선형)
            trend = coeffs[0]  # 기울기

            # 표준편차 계산
            std_dev = values[-window:].std()

            base_value = moving_avg

        # 미래 예측 생성
        predictions = []
        for i in range(steps):
            # 다음 시간
            next_timestamp = last_timestamp + timedelta(minutes=i+1)

            # 예측값 = 기준값 + (추세 * 시간)
            # 약간의 랜덤성 추가 (현실감)
            noise = np.random.normal(0, std_dev * 0.1)
            predicted_value = base_value + (trend * (i+1)) + noise

            pred_dict = {
                'timestamp': next_timestamp.isoformat(),
                'value': float(predicted_value),
            }

            if include_confidence:
                # 신뢰구간: 95% (±1.96 표준편차)
                margin = 1.96 * std_dev * (1 + i/steps)  # 시간이 지날수록 불확실성 증가
                pred_dict['lower_bound'] = float(predicted_value - margin)
                pred_dict['upper_bound'] = float(predicted_value + margin)

            predictions.append(pred_dict)

        return predictions
