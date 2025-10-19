"""
실시간 예측 서비스
배포된 모델을 사용하여 실시간 예측을 수행합니다.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import pickle
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.forecasting_orm import ModelRegistry, ModelArtifact, ForecastResult
from ..db_orm import get_async_session
from ..utils.logger import get_logger

logger = get_logger(__name__)


class RealtimeForecastService:
    """실시간 예측 서비스"""

    def __init__(self):
        self.deployed_models_cache: Dict[str, Any] = {}
        self.last_cache_update = None
        self.cache_ttl = 300  # 5분 캐시

    async def get_deployed_model(self, session: AsyncSession, tag_name: str) -> Optional[Dict[str, Any]]:
        """
        특정 센서의 배포된 모델 정보 가져오기

        Args:
            session: DB 세션
            tag_name: 센서 태그명

        Returns:
            배포된 모델 정보 딕셔너리
        """
        try:
            # 캐시 확인
            cache_key = f"model_{tag_name}"
            if self._is_cache_valid(cache_key):
                return self.deployed_models_cache[cache_key]

            # DB에서 배포된 모델 조회
            query = select(ModelRegistry).where(
                ModelRegistry.tag_name == tag_name,
                ModelRegistry.is_deployed == True,
                ModelRegistry.is_active == True
            )

            result = await session.execute(query)
            model = result.scalar_one_or_none()

            if not model:
                logger.info(f"No deployed model found for sensor {tag_name}")
                return None

            # 모델 아티팩트 로드
            artifact_query = select(ModelArtifact).where(
                ModelArtifact.model_id == model.model_id
            )
            artifact_result = await session.execute(artifact_query)
            artifact = artifact_result.scalar_one_or_none()

            model_info = {
                'model_id': model.model_id,
                'model_name': model.model_name,
                'model_type': model.model_type,
                'version': model.version,
                'tag_name': model.tag_name,
                'deployed_at': model.deployed_at,
                'artifact': pickle.loads(artifact.model_artifact) if artifact else None,
                'hyperparameters': model.hyperparameters
            }

            # 캐시 업데이트
            self.deployed_models_cache[cache_key] = model_info

            logger.info(f"Loaded deployed model {model.model_name} for sensor {tag_name}")
            return model_info

        except Exception as e:
            logger.error(f"Error loading deployed model for {tag_name}: {e}")
            return None

    async def predict(
        self,
        session: AsyncSession,
        tag_name: str,
        horizon: int = 24,
        confidence_level: float = 0.95
    ) -> Optional[Dict[str, Any]]:
        """
        실시간 예측 수행

        Args:
            session: DB 세션
            tag_name: 센서 태그명
            horizon: 예측 기간 (시간)
            confidence_level: 신뢰 구간 수준

        Returns:
            예측 결과 딕셔너리
        """
        try:
            # 배포된 모델 가져오기
            model_info = await self.get_deployed_model(session, tag_name)
            if not model_info or not model_info['artifact']:
                logger.warning(f"No deployed model or artifact for {tag_name}")
                return None

            # 최근 데이터 가져오기 (예측에 필요한 기간)
            historical_data = await self._get_historical_data(session, tag_name, days=30)
            if historical_data is None or historical_data.empty:
                logger.warning(f"No historical data for {tag_name}")
                return None

            # 모델 타입별 예측 수행
            model_type = model_info['model_type']
            model = model_info['artifact']

            predictions = None
            confidence_intervals = None

            if model_type == 'ARIMA':
                predictions, confidence_intervals = await self._predict_arima(
                    model, historical_data, horizon
                )
            elif model_type == 'Prophet':
                predictions, confidence_intervals = await self._predict_prophet(
                    model, historical_data, horizon
                )
            elif model_type == 'LSTM':
                predictions = await self._predict_lstm(
                    model, historical_data, horizon
                )
                # LSTM은 신뢰구간 계산이 복잡하므로 간단히 ±10% 사용
                confidence_intervals = (predictions * 0.9, predictions * 1.1)
            else:
                logger.error(f"Unknown model type: {model_type}")
                return None

            # 예측 결과 구성
            current_time = datetime.now()
            forecast_result = {
                'model_id': model_info['model_id'],
                'tag_name': tag_name,
                'forecast_time': current_time,
                'horizon': horizon,
                'predictions': predictions.tolist() if hasattr(predictions, 'tolist') else predictions,
                'confidence_lower': confidence_intervals[0].tolist() if confidence_intervals else None,
                'confidence_upper': confidence_intervals[1].tolist() if confidence_intervals else None,
                'timestamps': [(current_time + timedelta(hours=i)).isoformat()
                             for i in range(1, horizon + 1)]
            }

            # 예측 결과 저장
            await self._save_forecast_result(session, forecast_result)

            logger.info(f"Forecast completed for {tag_name}: {horizon} hours ahead")
            return forecast_result

        except Exception as e:
            logger.error(f"Error during prediction for {tag_name}: {e}", exc_info=True)
            return None

    async def _get_historical_data(
        self,
        session: AsyncSession,
        tag_name: str,
        days: int = 30
    ) -> Optional[pd.DataFrame]:
        """과거 데이터 조회"""
        try:
            query = text("""
                SELECT ts, value
                FROM influx_hist
                WHERE tag_name = :tag_name
                  AND ts > NOW() - INTERVAL :days DAY
                  AND value IS NOT NULL
                ORDER BY ts
            """)

            result = await session.execute(
                query,
                {"tag_name": tag_name, "days": days}
            )
            rows = result.fetchall()

            if not rows:
                return None

            df = pd.DataFrame(rows, columns=['ts', 'value'])
            df['ts'] = pd.to_datetime(df['ts'])
            df.set_index('ts', inplace=True)

            # 시간별 리샘플링
            df = df.resample('1H').mean().fillna(method='ffill')

            return df

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return None

    async def _predict_arima(
        self,
        model: Any,
        historical_data: pd.DataFrame,
        horizon: int
    ) -> tuple:
        """ARIMA 모델 예측"""
        try:
            # statsmodels ARIMA 모델 예측
            forecast_result = model.forecast(steps=horizon)

            # 신뢰구간 계산 (간단히 ±1.96 * std 사용)
            std_error = np.std(historical_data['value']) * np.sqrt(np.arange(1, horizon + 1))
            confidence_lower = forecast_result - 1.96 * std_error
            confidence_upper = forecast_result + 1.96 * std_error

            return forecast_result, (confidence_lower, confidence_upper)

        except Exception as e:
            logger.error(f"ARIMA prediction error: {e}")
            # 폴백: 단순 평균 예측
            mean_value = historical_data['value'].mean()
            predictions = np.full(horizon, mean_value)
            std = historical_data['value'].std()
            return predictions, (predictions - 1.96*std, predictions + 1.96*std)

    async def _predict_prophet(
        self,
        model: Any,
        historical_data: pd.DataFrame,
        horizon: int
    ) -> tuple:
        """Prophet 모델 예측"""
        try:
            # Prophet용 미래 데이터프레임 생성
            future = model.make_future_dataframe(periods=horizon, freq='H')

            # 예측 수행
            forecast = model.predict(future)

            # 마지막 horizon 개의 예측값 추출
            predictions = forecast['yhat'].iloc[-horizon:].values
            confidence_lower = forecast['yhat_lower'].iloc[-horizon:].values
            confidence_upper = forecast['yhat_upper'].iloc[-horizon:].values

            return predictions, (confidence_lower, confidence_upper)

        except Exception as e:
            logger.error(f"Prophet prediction error: {e}")
            # 폴백
            mean_value = historical_data['value'].mean()
            predictions = np.full(horizon, mean_value)
            std = historical_data['value'].std()
            return predictions, (predictions - 1.96*std, predictions + 1.96*std)

    async def _predict_lstm(
        self,
        model: Any,
        historical_data: pd.DataFrame,
        horizon: int
    ) -> np.ndarray:
        """LSTM 모델 예측"""
        try:
            # 데이터 정규화 (모델 훈련시와 동일한 방법 사용)
            from sklearn.preprocessing import MinMaxScaler
            scaler = MinMaxScaler()
            scaled_data = scaler.fit_transform(historical_data[['value']])

            # 입력 시퀀스 준비 (예: 최근 24시간)
            sequence_length = min(24, len(scaled_data))
            input_sequence = scaled_data[-sequence_length:].reshape(1, sequence_length, 1)

            # 예측
            predictions = []
            current_input = input_sequence

            for _ in range(horizon):
                pred = model.predict(current_input, verbose=0)
                predictions.append(pred[0, 0])

                # 다음 입력을 위해 시퀀스 업데이트
                current_input = np.roll(current_input, -1, axis=1)
                current_input[0, -1, 0] = pred[0, 0]

            # 역정규화
            predictions = np.array(predictions).reshape(-1, 1)
            predictions = scaler.inverse_transform(predictions).flatten()

            return predictions

        except Exception as e:
            logger.error(f"LSTM prediction error: {e}")
            # 폴백
            mean_value = historical_data['value'].mean()
            return np.full(horizon, mean_value)

    async def _save_forecast_result(
        self,
        session: AsyncSession,
        forecast_result: Dict[str, Any]
    ) -> None:
        """예측 결과 저장"""
        try:
            # ForecastResult 테이블에 저장
            result = ForecastResult(
                model_id=forecast_result['model_id'],
                tag_name=forecast_result['tag_name'],
                forecast_time=forecast_result['forecast_time'],
                horizon_hours=forecast_result['horizon'],
                predictions=forecast_result['predictions'],
                confidence_lower=forecast_result['confidence_lower'],
                confidence_upper=forecast_result['confidence_upper']
            )

            session.add(result)
            await session.commit()

            logger.info(f"Forecast result saved for {forecast_result['tag_name']}")

        except Exception as e:
            logger.error(f"Error saving forecast result: {e}")
            await session.rollback()

    def _is_cache_valid(self, cache_key: str) -> bool:
        """캐시 유효성 검사"""
        if cache_key not in self.deployed_models_cache:
            return False

        if self.last_cache_update is None:
            return False

        elapsed = (datetime.now() - self.last_cache_update).total_seconds()
        return elapsed < self.cache_ttl

    async def get_latest_forecast(
        self,
        session: AsyncSession,
        tag_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        최신 예측 결과 가져오기

        Args:
            session: DB 세션
            tag_name: 센서 태그명

        Returns:
            최신 예측 결과
        """
        try:
            query = select(ForecastResult).where(
                ForecastResult.tag_name == tag_name
            ).order_by(
                ForecastResult.forecast_time.desc()
            ).limit(1)

            result = await session.execute(query)
            forecast = result.scalar_one_or_none()

            if not forecast:
                return None

            return {
                'model_id': forecast.model_id,
                'tag_name': forecast.tag_name,
                'forecast_time': forecast.forecast_time.isoformat(),
                'horizon': forecast.horizon_hours,
                'predictions': forecast.predictions,
                'confidence_lower': forecast.confidence_lower,
                'confidence_upper': forecast.confidence_upper
            }

        except Exception as e:
            logger.error(f"Error fetching latest forecast: {e}")
            return None


# 싱글톤 인스턴스
forecast_service = RealtimeForecastService()