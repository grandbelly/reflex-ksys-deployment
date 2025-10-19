"""
Communication State - Refactored with Service Pattern
- Uses CommunicationService for all database operations
- Direct rx.State inheritance (not BaseState to avoid conflicts)
- Pandas operations for data transformation
"""
import reflex as rx
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime

from ksys_app.db_orm import get_async_session
from ksys_app.services.communication_service import CommunicationService
from reflex.utils import console


class CommunicationState(rx.State):
    """Communication monitoring state with service pattern"""

    # UI Controls
    selected_tag: str = "INLET_PRESSURE"  # Default to a tag that has data
    selected_days: int = 7

    # Data Storage (internal - will be transformed by computed properties)
    available_tags: List[str] = []
    _df_hourly: List[Dict] = []  # Raw hourly data
    _df_daily: List[Dict] = []   # Raw daily data
    _summary: Dict = {}          # Summary statistics

    # Loading state
    loading: bool = False
    error_message: str = ""

    # Computed Properties
    # =========================================================================

    @rx.var
    def selected_days_str(self) -> str:
        """Radio group용 문자열 변환"""
        return str(self.selected_days)

    @rx.var
    def chart_height(self) -> int:
        """Chart height based on selected days"""
        if self.selected_days <= 7:
            return 250
        elif self.selected_days <= 14:
            return 350
        else:
            return 450

    @rx.var
    def active_hours_str(self) -> str:
        """활성 시간 수"""
        return str(len(self._df_hourly))

    @rx.var
    def total_hours_str(self) -> str:
        """전체 시간 라벨"""
        return f"Out of {self.selected_days * 24} hours"

    @rx.var
    def overall_success_rate(self) -> float:
        """전체 성공률 - ALWAYS calculate from hourly data for consistency"""
        if not self._df_hourly:
            return 0.0

        df = pd.DataFrame(self._df_hourly)
        df['record_count'] = pd.to_numeric(df['record_count'], errors='coerce')
        df['expected_count'] = pd.to_numeric(df['expected_count'], errors='coerce')

        total_records = df['record_count'].sum()
        expected_records = df['expected_count'].sum()

        if expected_records > 0:
            return round(float(total_records / expected_records) * 100, 2)
        return 0.0

    @rx.var
    def total_records(self) -> int:
        """전체 레코드 수 - ALWAYS calculate from hourly data"""
        if not self._df_hourly:
            return 0

        df = pd.DataFrame(self._df_hourly)
        df['record_count'] = pd.to_numeric(df['record_count'], errors='coerce')
        return int(df['record_count'].sum())

    @rx.var
    def expected_records(self) -> int:
        """예상 레코드 수 - ALWAYS calculate from hourly data"""
        if not self._df_hourly:
            return 0

        df = pd.DataFrame(self._df_hourly)
        df['expected_count'] = pd.to_numeric(df['expected_count'], errors='coerce')
        return int(df['expected_count'].sum())

    @rx.var
    def heatmap_matrix(self) -> List[List[float]]:
        """Pandas pivot_table로 히트맵 매트릭스 생성 (KST 기준)"""
        if not self._df_hourly:
            return [[0] * 24 for _ in range(self.selected_days)]

        try:
            df = pd.DataFrame(self._df_hourly)
            console.debug(f"DataFrame columns: {df.columns.tolist()}")
            console.debug(f"DataFrame shape: {df.shape}")
            console.debug(f"First row: {df.iloc[0].to_dict() if len(df) > 0 else 'empty'}")

            df['success_rate'] = pd.to_numeric(df['success_rate'], errors='coerce')

            # Use the date and hour fields directly from the query (already in KST)
            # No need to re-parse timestamp
            if 'date' in df.columns and 'hour' in df.columns:
                console.debug(f"Before conversion - date type: {df['date'].dtype}, hour type: {df['hour'].dtype}")
                df['date'] = pd.to_datetime(df['date']).dt.date
                df['hour'] = pd.to_numeric(df['hour'], errors='coerce').astype(int)
                console.debug(f"After conversion - date sample: {df['date'].iloc[0] if len(df) > 0 else 'empty'}, hour sample: {df['hour'].iloc[0] if len(df) > 0 else 'empty'}")
                console.debug(f"Using query date/hour fields (KST): dates={df['date'].unique()}, hours={sorted(df['hour'].unique())}")
            else:
                # Fallback: parse timestamp (but this should already be KST from query)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df['date'] = df['timestamp'].dt.date
                df['hour'] = df['timestamp'].dt.hour
                console.log("Fallback: parsing timestamp for date/hour")

            # Debug: log sample data
            if len(df) > 0:
                console.debug(f"Heatmap matrix: first date={df['date'].iloc[0]}, first hour={df['hour'].iloc[0]}")

            # Pivot table로 매트릭스 생성
            pivot = df.pivot_table(
                values='success_rate',
                index='date',
                columns='hour',
                fill_value=0,
                aggfunc='mean'
            )

            console.debug(f"Pivot table shape: {pivot.shape}")
            console.debug(f"Pivot sample (first 3 cols): {pivot.iloc[:, :3].to_dict() if len(pivot) > 0 else 'empty'}")

            # 모든 시간(0-23)이 포함되도록 reindex
            pivot = pivot.reindex(columns=range(24), fill_value=0)

            result = pivot.values.tolist()
            console.debug(f"Matrix first row sample: {result[0][:5] if len(result) > 0 else 'empty'}")

            return result
        except Exception as e:
            console.error(f"Heatmap matrix calculation failed: {e}")
            return [[0] * 24 for _ in range(self.selected_days)]

    @rx.var
    def hour_labels(self) -> List[str]:
        """시간 라벨 (00-23)"""
        return [f"{i:02d}" for i in range(24)]

    @rx.var
    def date_labels(self) -> List[str]:
        """날짜 라벨 (KST) - explicitly localized"""
        if not self._df_hourly:
            return []

        df = pd.DataFrame(self._df_hourly)
        # Parse timestamp and explicitly set timezone to KST
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # Localize to KST (timestamps from DB are already in KST)
        df['timestamp'] = df['timestamp'].dt.tz_localize('Asia/Seoul')
        df['date'] = df['timestamp'].dt.date

        dates = sorted(df['date'].unique())
        result = [str(date) for date in dates]

        # Debug: log first few timestamps and dates with timezone
        if len(df) > 0:
            console.debug(f"Sample timestamps (KST): {df['timestamp'].head(3).tolist()}")
            console.debug(f"Sample dates (KST): {df['date'].head(3).tolist()}")
            console.debug(f"Date labels: {result}")

        return result

    @rx.var
    def heatmap_dates(self) -> List[str]:
        """히트맵용 날짜 리스트"""
        return self.date_labels

    @rx.var
    def daily_chart_data(self) -> List[Dict]:
        """일별 트렌드 차트 데이터"""
        if not self._df_daily:
            return []

        df = pd.DataFrame(self._df_daily)
        df = df[df['tag_name'] == self.selected_tag].copy()
        df = df.sort_values('date')

        # 날짜 포맷팅
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%m/%d')

        return df[['date', 'success_rate']].to_dict('records')

    @rx.var
    def hourly_data(self) -> List[Dict]:
        """시간대별 성공률 차트 데이터 (바 차트용)"""
        if not self._df_hourly:
            return []

        try:
            df = pd.DataFrame(self._df_hourly)
            df['success_rate'] = pd.to_numeric(df['success_rate'], errors='coerce')
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hour'] = df['timestamp'].dt.hour

            # 시간대별 평균 성공률
            hourly_avg = df.groupby('hour')['success_rate'].mean().reset_index()
            hourly_avg = hourly_avg.sort_values('hour')

            return hourly_avg.to_dict('records')

        except Exception as e:
            console.error(f"Hourly data calculation failed: {e}")
            return []

    @rx.var
    def hourly_pattern_stats(self) -> Dict[str, Any]:
        """히트맵 기반 패턴 인사이트 - 의미있는 분석"""
        if not self._df_hourly:
            return {
                "peak_hours": "N/A",
                "low_hours": "N/A",
                "consistency": "N/A",
                "trend": "N/A"
            }

        try:
            df = pd.DataFrame(self._df_hourly)
            df['success_rate'] = df['success_rate'].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hour'] = df['timestamp'].dt.hour
            df['date'] = df['timestamp'].dt.date

            # 시간대별 평균 성공률
            hourly_avg = df.groupby('hour')['success_rate'].mean()

            if hourly_avg.empty:
                return {
                    "peak_hours": "N/A",
                    "low_hours": "N/A",
                    "consistency": "N/A",
                    "trend": "N/A"
                }

            # 1. 피크 시간대 (95% 이상 유지하는 시간대)
            peak_hours = hourly_avg[hourly_avg >= 95].index.tolist()
            peak_str = f"{len(peak_hours)}시간 ({min(peak_hours):02d}-{max(peak_hours):02d}시)" if peak_hours else "없음"

            # 2. 저조 시간대 (80% 미만인 시간대)
            low_hours = hourly_avg[hourly_avg < 80].index.tolist()
            low_str = f"{len(low_hours)}시간" if low_hours else "없음"

            # 3. 시간대별 일관성 (CV: Coefficient of Variation)
            hourly_std = df.groupby('hour')['success_rate'].std()
            avg_cv = (hourly_std / hourly_avg * 100).mean()
            consistency = "높음" if avg_cv < 5 else "보통" if avg_cv < 10 else "낮음"

            # 4. 주간/야간 트렌드 비교
            df['is_daytime'] = df['hour'].between(6, 18)
            day_avg = df[df['is_daytime']]['success_rate'].mean()
            night_avg = df[~df['is_daytime']]['success_rate'].mean()

            if abs(day_avg - night_avg) < 2:
                trend = "주야 동일"
            elif day_avg > night_avg:
                trend = f"주간 우수 (+{day_avg - night_avg:.2f}%)"
            else:
                trend = f"야간 우수 (+{night_avg - day_avg:.2f}%)"

            return {
                "peak_hours": peak_str,
                "low_hours": low_str,
                "consistency": consistency,
                "trend": trend
            }

        except Exception as e:
            console.error(f"Hourly pattern stats calculation failed: {e}")
            return {
                "peak_hours": "N/A",
                "low_hours": "N/A",
                "consistency": "N/A",
                "trend": "N/A"
            }

    @rx.var
    def anomaly_detection(self) -> List[Dict]:
        """이상치 탐지 (Z-score 사용) - 현재 시간대 제외"""
        if not self._df_hourly:
            return []

        try:
            df = pd.DataFrame(self._df_hourly)
            df['success_rate'] = pd.to_numeric(df['success_rate'], errors='coerce')
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # 현재 시간 (KST) 기준으로 현재 시간대 제외
            from datetime import datetime
            import pytz
            kst = pytz.timezone('Asia/Seoul')
            now_kst = datetime.now(kst)
            current_hour = now_kst.hour
            current_date = now_kst.date()

            # 현재 시간대 데이터 제외 (오늘 날짜의 현재 시간)
            df_filtered = df[
                ~((df['timestamp'].dt.date == current_date) &
                  (df['timestamp'].dt.hour == current_hour))
            ].copy()

            if len(df_filtered) == 0:
                return []

            # Z-score 계산 (현재 시간대 제외한 데이터로)
            mean = df_filtered['success_rate'].mean()
            std = df_filtered['success_rate'].std()

            if std > 0 and not pd.isna(std):
                df_filtered['z_score'] = np.abs((df_filtered['success_rate'] - mean) / std)
                anomalies = df_filtered[df_filtered['z_score'] > 2]  # Z-score > 2는 이상치

                if not anomalies.empty:
                    anomalies = anomalies.copy()
                    anomalies['timestamp'] = anomalies['timestamp'].dt.strftime('%m/%d %H:%M')
                    anomalies['success_rate'] = anomalies['success_rate'].astype(float)
                    anomalies['z_score'] = anomalies['z_score'].astype(float)
                    return anomalies[['timestamp', 'success_rate', 'z_score']].round(2).to_dict('records')

            return []
        except Exception as e:
            console.error(f"Anomaly detection calculation failed: {e}")
            return []

    # Event Handlers
    # =========================================================================

    @rx.event(background=True)
    async def load_data(self):
        """페이지 로드 시 데이터 로드 (initialize와 동일)"""
        return await self.initialize()

    @rx.event(background=True)
    async def initialize(self):
        """초기화 - 태그 목록 로드 및 데이터 로드"""
        console.info("CommunicationState.initialize() called")

        async with self:
            self.loading = True

        try:
            # Fetch available tags
            async with get_async_session() as session:
                service = CommunicationService(session)
                tags = await service.get_available_tags()

            async with self:
                self.available_tags = tags
                if not self.selected_tag and self.available_tags:
                    self.selected_tag = self.available_tags[0]

            console.info(f"Loaded {len(self.available_tags)} tags")

            # Load initial data (call internal fetch without yield)
            await self._fetch_data()

        except Exception as e:
            console.error(f"Initialize failed: {e}")
            async with self:
                self.error_message = str(e)
        finally:
            async with self:
                self.loading = False

    async def _fetch_data(self):
        """Internal data fetch without yield (for initialize)"""
        import time

        # Get current values
        selected_tag = self.selected_tag
        selected_days = self.selected_days

        start_time = time.time()
        console.info(f"[TIMING] Starting data fetch for tag={selected_tag}, days={selected_days}")

        try:
            t_session_start = time.time()
            async with get_async_session() as session:
                console.info(f"[TIMING] Session created: {time.time() - t_session_start:.3f}s")

                service = CommunicationService(session)

                # Fetch hourly data
                t1 = time.time()
                hourly = await service.get_hourly_stats(selected_tag, selected_days)
                hourly_time = time.time() - t1
                console.info(f"[TIMING] Hourly stats ({len(hourly)} records): {hourly_time:.3f}s")

                # Fetch daily data
                t2 = time.time()
                daily = await service.get_daily_stats(selected_days)
                daily_time = time.time() - t2
                console.info(f"[TIMING] Daily stats ({len(daily)} records): {daily_time:.3f}s")

                # Fetch summary
                t3 = time.time()
                summary = await service.get_tag_summary(selected_tag, selected_days)
                summary_time = time.time() - t3
                console.info(f"[TIMING] Summary stats: {summary_time:.3f}s")

            # Update state
            t_state_update = time.time()
            async with self:
                self._df_hourly = hourly
                self._df_daily = daily
                self._summary = summary
                self.loading = False
            console.info(f"[TIMING] State update: {time.time() - t_state_update:.3f}s")

            total_time = time.time() - start_time
            console.info(f"[TIMING] Total fetch time: {total_time:.3f}s (hourly={hourly_time:.3f}s, daily={daily_time:.3f}s, summary={summary_time:.3f}s)")

        except Exception as e:
            console.error(f"Fetch data failed: {e}")
            async with self:
                self.error_message = str(e)
                self.loading = False

    @rx.event(background=True)
    async def refresh_data(self):
        """데이터 새로고침 (with yield for UI updates)"""
        # Get current values
        selected_tag = self.selected_tag
        selected_days = self.selected_days

        console.info(f"Refreshing data for tag={selected_tag}, days={selected_days}")

        async with self:
            self.loading = True

        try:
            async with get_async_session() as session:
                service = CommunicationService(session)

                # Fetch all data in parallel would be ideal, but sequential is safer
                hourly = await service.get_hourly_stats(selected_tag, selected_days)
                daily = await service.get_daily_stats(selected_days)
                summary = await service.get_tag_summary(selected_tag, selected_days)

            async with self:
                self._df_hourly = hourly
                self._df_daily = daily
                self._summary = summary
                self.loading = False
                yield  # Update UI

            console.info(f"Loaded {len(hourly)} hourly records, {len(daily)} daily records")

        except Exception as e:
            console.error(f"Refresh data failed: {e}")
            async with self:
                self.error_message = str(e)
                self.loading = False

    @rx.event(background=True)
    async def set_selected_tag(self, tag: str):
        """태그 선택 및 데이터 갱신"""
        async with self:
            self.selected_tag = tag

        return CommunicationState.refresh_data

    def set_selected_days_str(self, days: str | List[str]):
        """일수 선택 및 자동 새로고침"""
        # Segmented control returns string or list
        if isinstance(days, list):
            days = days[0] if days else "7"

        try:
            days_int = int(days)
        except (ValueError, TypeError):
            days_int = 7

        self.selected_days = days_int
        console.info(f"Selected days changed to: {days_int}")

        return CommunicationState.refresh_data