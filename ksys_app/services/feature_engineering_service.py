"""
Feature Engineering Service for Time-Series Forecasting

This service generates engineered features from raw time-series data:
- Lag features (1h, 3h, 6h, 12h, 24h)
- Rolling window statistics (mean, std, min, max, median)
- Time-based features (hour, day, month, seasonality)
- Seasonal decomposition (trend, seasonal, residual)

Uses pandas for efficient feature calculation and stores results
in the feature_store table.

Task: 32 - Feature Engineering Service Layer
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import pytz
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from reflex.utils import console

try:
    from statsmodels.tsa.seasonal import STL
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    console.warn("statsmodels not available - seasonal decomposition disabled")


class FeatureEngineeringService:
    """
    Service for generating time-series features from sensor data.

    Follows the async pattern from sensor_service.py:
    - Raw SQL queries with statement_timeout
    - Returns plain dicts (no ORM objects)
    - Timezone-aware datetime handling (UTC → KST)
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.kst = pytz.timezone('Asia/Seoul')

    # ============================================================================
    # 1. Lag Features
    # ============================================================================

    async def generate_lag_features(
        self,
        tag_name: str,
        start_time: datetime,
        end_time: datetime,
        lags: List[int] = [1, 3, 6, 12, 24]  # Hours
    ) -> pd.DataFrame:
        """
        Generate lag features for a given tag.

        Args:
            tag_name: Sensor tag name
            start_time: Start of time range (UTC)
            end_time: End of time range (UTC)
            lags: List of lag periods in hours

        Returns:
            DataFrame with columns: ts, value, lag_1h, lag_3h, lag_6h, ...
        """
        try:
            # Set query timeout
            await self.session.execute(text("SET LOCAL statement_timeout = '10s'"))

            # Fetch historical data
            # Extend start time to get enough history for lags
            max_lag = max(lags) if lags else 24
            extended_start = start_time - timedelta(hours=max_lag + 1)

            query = text("""
                SELECT
                    ts,
                    value
                FROM influx_hist
                WHERE tag_name = :tag_name
                AND ts >= :start_time
                AND ts <= :end_time
                ORDER BY ts
            """)

            result = await self.session.execute(
                query,
                {
                    "tag_name": tag_name,
                    "start_time": extended_start,
                    "end_time": end_time
                }
            )
            rows = result.mappings().all()

            if not rows:
                console.warn(f"No data found for {tag_name}")
                return pd.DataFrame()

            # Convert to pandas DataFrame
            df = pd.DataFrame([dict(row) for row in rows])
            df['ts'] = pd.to_datetime(df['ts'], utc=True)
            df = df.set_index('ts').sort_index()

            # Generate lag features
            for lag_hours in lags:
                df[f'lag_{lag_hours}h'] = df['value'].shift(lag_hours)

            # Filter to requested time range
            df = df[start_time:end_time]

            console.info(f"Generated {len(lags)} lag features for {tag_name}: {len(df)} rows")
            return df.reset_index()

        except Exception as e:
            console.error(f"Error generating lag features for {tag_name}: {e}")
            return pd.DataFrame()

    # ============================================================================
    # 2. Rolling Window Statistics
    # ============================================================================

    async def generate_rolling_features(
        self,
        tag_name: str,
        start_time: datetime,
        end_time: datetime,
        windows: List[int] = [6, 24, 168]  # Hours: 6h, 24h, 1 week
    ) -> pd.DataFrame:
        """
        Generate rolling window statistics.

        Args:
            tag_name: Sensor tag name
            start_time: Start of time range (UTC)
            end_time: End of time range (UTC)
            windows: List of window sizes in hours

        Returns:
            DataFrame with rolling_mean_6h, rolling_std_6h, etc.
        """
        try:
            # Set query timeout
            await self.session.execute(text("SET LOCAL statement_timeout = '10s'"))

            # Extend start time to get enough history for windows
            max_window = max(windows) if windows else 168
            extended_start = start_time - timedelta(hours=max_window + 1)

            query = text("""
                SELECT
                    ts,
                    value
                FROM influx_hist
                WHERE tag_name = :tag_name
                AND ts >= :start_time
                AND ts <= :end_time
                ORDER BY ts
            """)

            result = await self.session.execute(
                query,
                {
                    "tag_name": tag_name,
                    "start_time": extended_start,
                    "end_time": end_time
                }
            )
            rows = result.mappings().all()

            if not rows:
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame([dict(row) for row in rows])
            df['ts'] = pd.to_datetime(df['ts'], utc=True)
            df = df.set_index('ts').sort_index()

            # Generate rolling statistics
            for window_hours in windows:
                # Rolling mean
                df[f'rolling_mean_{window_hours}h'] = df['value'].rolling(
                    window=window_hours, min_periods=1
                ).mean()

                # Rolling std
                df[f'rolling_std_{window_hours}h'] = df['value'].rolling(
                    window=window_hours, min_periods=1
                ).std()

                # Rolling min/max
                df[f'rolling_min_{window_hours}h'] = df['value'].rolling(
                    window=window_hours, min_periods=1
                ).min()

                df[f'rolling_max_{window_hours}h'] = df['value'].rolling(
                    window=window_hours, min_periods=1
                ).max()

                # Rolling median
                df[f'rolling_median_{window_hours}h'] = df['value'].rolling(
                    window=window_hours, min_periods=1
                ).median()

            # Filter to requested range
            df = df[start_time:end_time]

            console.info(f"Generated rolling features for {tag_name}: {len(df)} rows")
            return df.reset_index()

        except Exception as e:
            console.error(f"Error generating rolling features for {tag_name}: {e}")
            return pd.DataFrame()

    # ============================================================================
    # 3. Time-Based Features
    # ============================================================================

    def generate_time_features(self, df: pd.DataFrame, ts_column: str = 'ts') -> pd.DataFrame:
        """
        Generate time-based features from datetime index.

        Args:
            df: DataFrame with datetime column
            ts_column: Name of timestamp column

        Returns:
            DataFrame with added time features
        """
        try:
            if df.empty:
                return df

            # Ensure datetime
            if ts_column not in df.columns:
                console.error(f"Column {ts_column} not found in DataFrame")
                return df

            df[ts_column] = pd.to_datetime(df[ts_column], utc=True)

            # Convert to KST for local time features
            df_kst = df[ts_column].dt.tz_convert(self.kst)

            # Extract time components
            df['hour_of_day'] = df_kst.dt.hour
            df['day_of_week'] = df_kst.dt.dayofweek  # 0=Monday, 6=Sunday
            df['day_of_month'] = df_kst.dt.day
            df['month'] = df_kst.dt.month
            df['quarter'] = df_kst.dt.quarter

            # Binary features
            df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)  # Saturday, Sunday
            df['is_business_hour'] = ((df['hour_of_day'] >= 9) & (df['hour_of_day'] < 18)).astype(int)

            console.info(f"Generated time-based features: {len(df)} rows")
            return df

        except Exception as e:
            console.error(f"Error generating time features: {e}")
            return df

    # ============================================================================
    # 4. Seasonal Decomposition
    # ============================================================================

    def generate_seasonal_features(
        self,
        df: pd.DataFrame,
        value_column: str = 'value',
        period: int = 24,  # Daily seasonality
        seasonal_model: str = 'additive'
    ) -> pd.DataFrame:
        """
        Generate seasonal decomposition features using STL.

        Args:
            df: DataFrame with time series data
            value_column: Column name containing values
            period: Seasonal period (24 for daily, 168 for weekly)
            seasonal_model: 'additive' or 'multiplicative'

        Returns:
            DataFrame with trend, seasonal, and residual components
        """
        try:
            if not STATSMODELS_AVAILABLE:
                console.warn("statsmodels not available - skipping seasonal decomposition")
                return df

            if df.empty or len(df) < period * 2:
                console.warn(f"Insufficient data for seasonal decomposition (need >= {period * 2} points)")
                return df

            # Ensure we have a numeric column
            if value_column not in df.columns:
                console.error(f"Column {value_column} not found")
                return df

            # Handle missing values
            series = df[value_column].fillna(method='ffill').fillna(method='bfill')

            # Perform STL decomposition
            stl = STL(series, seasonal=period + 1, robust=True)
            result = stl.fit()

            # Add components to DataFrame
            df['trend_component'] = result.trend
            df['seasonal_component'] = result.seasonal
            df['residual_component'] = result.resid

            console.info(f"Generated seasonal decomposition features: {len(df)} rows")
            return df

        except Exception as e:
            console.error(f"Error in seasonal decomposition: {e}")
            # Return original df without seasonal features
            df['trend_component'] = np.nan
            df['seasonal_component'] = np.nan
            df['residual_component'] = np.nan
            return df

    # ============================================================================
    # 5. Advanced Features
    # ============================================================================

    def generate_advanced_features(self, df: pd.DataFrame, value_column: str = 'value') -> pd.DataFrame:
        """
        Generate advanced derived features.

        Args:
            df: DataFrame with time series data
            value_column: Column name containing values

        Returns:
            DataFrame with advanced features
        """
        try:
            if df.empty or value_column not in df.columns:
                return df

            # Rate of change (first derivative)
            df['rate_of_change'] = df[value_column].pct_change()

            # Acceleration (second derivative)
            df['acceleration'] = df['rate_of_change'].diff()

            # Replace infinities with NaN
            df['rate_of_change'] = df['rate_of_change'].replace([np.inf, -np.inf], np.nan)
            df['acceleration'] = df['acceleration'].replace([np.inf, -np.inf], np.nan)

            console.info(f"Generated advanced features: {len(df)} rows")
            return df

        except Exception as e:
            console.error(f"Error generating advanced features: {e}")
            return df

    # ============================================================================
    # 6. Complete Feature Pipeline
    # ============================================================================

    async def generate_all_features(
        self,
        tag_name: str,
        start_time: datetime,
        end_time: datetime,
        lag_periods: List[int] = [1, 3, 6, 12, 24],
        rolling_windows: List[int] = [6, 24, 168],
        include_seasonal: bool = True,
        seasonal_period: int = 24
    ) -> pd.DataFrame:
        """
        Generate complete feature set for a tag.

        This is the main method to call for comprehensive feature engineering.

        Args:
            tag_name: Sensor tag name
            start_time: Start time (UTC)
            end_time: End time (UTC)
            lag_periods: Lag periods in hours
            rolling_windows: Rolling window sizes in hours
            include_seasonal: Whether to include seasonal decomposition
            seasonal_period: Period for seasonal decomposition

        Returns:
            DataFrame with all engineered features
        """
        try:
            console.info(f"Starting feature engineering for {tag_name}")

            # Step 1: Generate lag features
            df = await self.generate_lag_features(tag_name, start_time, end_time, lag_periods)
            if df.empty:
                console.warn(f"No lag features generated for {tag_name}")
                return df

            # Step 2: Generate rolling features
            df_rolling = await self.generate_rolling_features(tag_name, start_time, end_time, rolling_windows)
            if not df_rolling.empty:
                # Merge rolling features
                df = pd.merge(df, df_rolling, on='ts', how='left', suffixes=('', '_roll'))
                # Keep only non-duplicate columns
                df = df.loc[:, ~df.columns.duplicated()]

            # Step 3: Time-based features
            df = self.generate_time_features(df, 'ts')

            # Step 4: Seasonal decomposition
            if include_seasonal and len(df) >= seasonal_period * 2:
                df = self.generate_seasonal_features(df, 'value', seasonal_period)

            # Step 5: Advanced features
            df = self.generate_advanced_features(df, 'value')

            console.info(f"Feature engineering complete for {tag_name}: {len(df)} rows, {len(df.columns)} features")
            return df

        except Exception as e:
            console.error(f"Error in complete feature pipeline for {tag_name}: {e}")
            return pd.DataFrame()

    # ============================================================================
    # 7. Save Features to Database
    # ============================================================================

    async def save_features_to_db(
        self,
        tag_name: str,
        features_df: pd.DataFrame,
        feature_version: str = "1.0"
    ) -> int:
        """
        Save engineered features to feature_store table.

        Args:
            tag_name: Sensor tag name
            features_df: DataFrame with features
            feature_version: Version string for tracking

        Returns:
            Number of rows inserted
        """
        try:
            if features_df.empty:
                console.warn(f"No features to save for {tag_name}")
                return 0

            # Prepare data for insertion
            records = []
            for _, row in features_df.iterrows():
                record = {
                    'feature_time': row.get('ts'),
                    'tag_name': tag_name,
                    'lag_1h': row.get('lag_1h'),
                    'lag_3h': row.get('lag_3h'),
                    'lag_6h': row.get('lag_6h'),
                    'lag_12h': row.get('lag_12h'),
                    'lag_24h': row.get('lag_24h'),
                    'rolling_mean_6h': row.get('rolling_mean_6h'),
                    'rolling_std_6h': row.get('rolling_std_6h'),
                    'rolling_min_6h': row.get('rolling_min_6h'),
                    'rolling_max_6h': row.get('rolling_max_6h'),
                    'rolling_median_6h': row.get('rolling_median_6h'),
                    'rolling_mean_24h': row.get('rolling_mean_24h'),
                    'rolling_std_24h': row.get('rolling_std_24h'),
                    'rolling_min_24h': row.get('rolling_min_24h'),
                    'rolling_max_24h': row.get('rolling_max_24h'),
                    'rolling_mean_1w': row.get('rolling_mean_168h'),
                    'rolling_std_1w': row.get('rolling_std_168h'),
                    'hour_of_day': row.get('hour_of_day'),
                    'day_of_week': row.get('day_of_week'),
                    'day_of_month': row.get('day_of_month'),
                    'month': row.get('month'),
                    'quarter': row.get('quarter'),
                    'is_weekend': bool(row.get('is_weekend', 0)),
                    'is_business_hour': bool(row.get('is_business_hour', 0)),
                    'trend_component': row.get('trend_component'),
                    'seasonal_component': row.get('seasonal_component'),
                    'residual_component': row.get('residual_component'),
                    'rate_of_change': row.get('rate_of_change'),
                    'acceleration': row.get('acceleration'),
                    'feature_version': feature_version
                }

                # Convert NaN to None for database insertion
                record = {k: (None if pd.isna(v) else v) for k, v in record.items()}
                records.append(record)

            # Batch insert with UPSERT (ON CONFLICT DO UPDATE)
            if records:
                # Set timeout for insert
                await self.session.execute(text("SET LOCAL statement_timeout = '30s'"))

                insert_query = text("""
                    INSERT INTO feature_store (
                        feature_time, tag_name, lag_1h, lag_3h, lag_6h, lag_12h, lag_24h,
                        rolling_mean_6h, rolling_std_6h, rolling_min_6h, rolling_max_6h, rolling_median_6h,
                        rolling_mean_24h, rolling_std_24h, rolling_min_24h, rolling_max_24h,
                        rolling_mean_1w, rolling_std_1w,
                        hour_of_day, day_of_week, day_of_month, month, quarter,
                        is_weekend, is_business_hour,
                        trend_component, seasonal_component, residual_component,
                        rate_of_change, acceleration, feature_version
                    ) VALUES (
                        :feature_time, :tag_name, :lag_1h, :lag_3h, :lag_6h, :lag_12h, :lag_24h,
                        :rolling_mean_6h, :rolling_std_6h, :rolling_min_6h, :rolling_max_6h, :rolling_median_6h,
                        :rolling_mean_24h, :rolling_std_24h, :rolling_min_24h, :rolling_max_24h,
                        :rolling_mean_1w, :rolling_std_1w,
                        :hour_of_day, :day_of_week, :day_of_month, :month, :quarter,
                        :is_weekend, :is_business_hour,
                        :trend_component, :seasonal_component, :residual_component,
                        :rate_of_change, :acceleration, :feature_version
                    )
                    ON CONFLICT (feature_time, tag_name)
                    DO UPDATE SET
                        lag_1h = EXCLUDED.lag_1h,
                        lag_3h = EXCLUDED.lag_3h,
                        lag_6h = EXCLUDED.lag_6h,
                        lag_12h = EXCLUDED.lag_12h,
                        lag_24h = EXCLUDED.lag_24h,
                        rolling_mean_6h = EXCLUDED.rolling_mean_6h,
                        rolling_std_6h = EXCLUDED.rolling_std_6h,
                        rolling_min_6h = EXCLUDED.rolling_min_6h,
                        rolling_max_6h = EXCLUDED.rolling_max_6h,
                        rolling_median_6h = EXCLUDED.rolling_median_6h,
                        rolling_mean_24h = EXCLUDED.rolling_mean_24h,
                        rolling_std_24h = EXCLUDED.rolling_std_24h,
                        rolling_min_24h = EXCLUDED.rolling_min_24h,
                        rolling_max_24h = EXCLUDED.rolling_max_24h,
                        rolling_mean_1w = EXCLUDED.rolling_mean_1w,
                        rolling_std_1w = EXCLUDED.rolling_std_1w,
                        hour_of_day = EXCLUDED.hour_of_day,
                        day_of_week = EXCLUDED.day_of_week,
                        day_of_month = EXCLUDED.day_of_month,
                        month = EXCLUDED.month,
                        quarter = EXCLUDED.quarter,
                        is_weekend = EXCLUDED.is_weekend,
                        is_business_hour = EXCLUDED.is_business_hour,
                        trend_component = EXCLUDED.trend_component,
                        seasonal_component = EXCLUDED.seasonal_component,
                        residual_component = EXCLUDED.residual_component,
                        rate_of_change = EXCLUDED.rate_of_change,
                        acceleration = EXCLUDED.acceleration,
                        feature_version = EXCLUDED.feature_version
                """)

                # Execute batch insert
                await self.session.execute(insert_query, records)
                await self.session.commit()

                console.info(f"Saved {len(records)} feature records for {tag_name}")
                return len(records)

        except Exception as e:
            console.error(f"Error saving features to database: {e}")
            await self.session.rollback()
            return 0
