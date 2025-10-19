"""
Drift Detection - Monitor data and model drift in production.

This module implements drift detection methods to identify when:
1. Data Drift: Input data distribution changes over time
2. Model Drift: Model performance degrades over time

Methods:
- PSI (Population Stability Index): Measures distribution shift
- KS Test (Kolmogorov-Smirnov): Statistical test for distribution change
- JS Divergence (Jensen-Shannon): Symmetric measure of distribution difference
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial.distance import jensenshannon
from sqlalchemy import select, text, insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.forecasting_orm import DriftMonitoring

logger = logging.getLogger(__name__)


class DriftSeverity(str, Enum):
    """Drift severity levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DriftType(str, Enum):
    """Types of drift."""
    DATA_DRIFT = "data_drift"
    PREDICTION_DRIFT = "prediction_drift"
    PERFORMANCE_DRIFT = "performance_drift"


class DriftDetector:
    """Drift detection system for monitoring model and data drift."""

    # PSI thresholds (industry standard)
    PSI_THRESHOLDS = {
        DriftSeverity.NONE: 0.0,
        DriftSeverity.LOW: 0.1,      # < 0.1: No significant change
        DriftSeverity.MEDIUM: 0.2,   # 0.1-0.2: Moderate change
        DriftSeverity.HIGH: 0.25,    # > 0.2: Significant change
        DriftSeverity.CRITICAL: 0.3, # > 0.25: Severe drift
    }

    # KS test p-value thresholds
    KS_THRESHOLDS = {
        DriftSeverity.NONE: 1.0,
        DriftSeverity.LOW: 0.1,
        DriftSeverity.MEDIUM: 0.05,
        DriftSeverity.HIGH: 0.01,
        DriftSeverity.CRITICAL: 0.001,
    }

    # JS Divergence thresholds (0-1 scale)
    JS_THRESHOLDS = {
        DriftSeverity.NONE: 0.0,
        DriftSeverity.LOW: 0.1,
        DriftSeverity.MEDIUM: 0.2,
        DriftSeverity.HIGH: 0.3,
        DriftSeverity.CRITICAL: 0.4,
    }

    def __init__(self, session: AsyncSession):
        """
        Initialize drift detector.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def calculate_psi(
        self,
        reference_data: np.ndarray,
        current_data: np.ndarray,
        bins: int = 10,
    ) -> Tuple[float, DriftSeverity]:
        """
        Calculate Population Stability Index (PSI).

        PSI measures the change in distribution between two datasets.
        PSI = Σ (actual% - expected%) * ln(actual% / expected%)

        Args:
            reference_data: Reference (baseline) distribution
            current_data: Current (production) distribution
            bins: Number of bins for discretization

        Returns:
            Tuple of (PSI value, severity level)
        """
        # Create bins based on reference data
        _, bin_edges = np.histogram(reference_data, bins=bins)

        # Calculate distributions
        ref_hist, _ = np.histogram(reference_data, bins=bin_edges)
        curr_hist, _ = np.histogram(current_data, bins=bin_edges)

        # Convert to percentages
        ref_pct = ref_hist / len(reference_data)
        curr_pct = curr_hist / len(current_data)

        # Avoid log(0) by adding small epsilon
        epsilon = 1e-10
        ref_pct = np.maximum(ref_pct, epsilon)
        curr_pct = np.maximum(curr_pct, epsilon)

        # Calculate PSI
        psi = np.sum((curr_pct - ref_pct) * np.log(curr_pct / ref_pct))

        # Determine severity
        severity = self._classify_severity(psi, self.PSI_THRESHOLDS)

        logger.info(f"PSI calculated: {psi:.4f} (severity: {severity})")

        return float(psi), severity

    async def kolmogorov_smirnov_test(
        self,
        reference_data: np.ndarray,
        current_data: np.ndarray,
    ) -> Tuple[float, float, DriftSeverity]:
        """
        Perform Kolmogorov-Smirnov test.

        KS test is a non-parametric test that compares the cumulative
        distributions of two datasets.

        Args:
            reference_data: Reference distribution
            current_data: Current distribution

        Returns:
            Tuple of (KS statistic, p-value, severity level)
        """
        # Run KS test
        statistic, p_value = stats.ks_2samp(reference_data, current_data)

        # Lower p-value = more drift (distributions are different)
        severity = self._classify_severity_inverse(p_value, self.KS_THRESHOLDS)

        logger.info(
            f"KS Test: statistic={statistic:.4f}, p-value={p_value:.4f}, "
            f"severity={severity}"
        )

        return float(statistic), float(p_value), severity

    async def jensen_shannon_divergence(
        self,
        reference_data: np.ndarray,
        current_data: np.ndarray,
        bins: int = 10,
    ) -> Tuple[float, DriftSeverity]:
        """
        Calculate Jensen-Shannon Divergence.

        JS divergence is a symmetric measure of similarity between two
        probability distributions. It's based on KL divergence.

        Args:
            reference_data: Reference distribution
            current_data: Current distribution
            bins: Number of bins for discretization

        Returns:
            Tuple of (JS divergence, severity level)
        """
        # Create bins based on combined data range
        combined_data = np.concatenate([reference_data, current_data])
        _, bin_edges = np.histogram(combined_data, bins=bins)

        # Calculate distributions
        ref_hist, _ = np.histogram(reference_data, bins=bin_edges)
        curr_hist, _ = np.histogram(current_data, bins=bin_edges)

        # Normalize to probabilities
        ref_prob = ref_hist / np.sum(ref_hist)
        curr_prob = curr_hist / np.sum(curr_hist)

        # Calculate JS divergence
        js_div = jensenshannon(ref_prob, curr_prob, base=2)

        # Determine severity
        severity = self._classify_severity(js_div, self.JS_THRESHOLDS)

        logger.info(f"JS Divergence: {js_div:.4f} (severity: {severity})")

        return float(js_div), severity

    async def detect_drift(
        self,
        tag_name: str,
        model_id: int,
        reference_start: datetime,
        reference_end: datetime,
        current_start: datetime,
        current_end: datetime,
        drift_type: DriftType = DriftType.DATA_DRIFT,
    ) -> Dict[str, Any]:
        """
        Detect drift by comparing reference and current data distributions.

        Args:
            tag_name: Sensor tag name
            model_id: Model ID for tracking
            reference_start: Start time for reference period
            reference_end: End time for reference period
            current_start: Start time for current period
            current_end: End time for current period
            drift_type: Type of drift to detect

        Returns:
            Dictionary with drift metrics and severity
        """
        # Fetch reference data
        ref_data = await self._fetch_data(tag_name, reference_start, reference_end)

        # Fetch current data
        curr_data = await self._fetch_data(tag_name, current_start, current_end)

        if len(ref_data) == 0 or len(curr_data) == 0:
            logger.warning(f"Insufficient data for drift detection: {tag_name}")
            return {
                'tag_name': tag_name,
                'model_id': model_id,
                'drift_type': drift_type,
                'error': 'Insufficient data',
            }

        # Calculate drift metrics
        psi_value, psi_severity = await self.calculate_psi(ref_data, curr_data)

        ks_stat, ks_pvalue, ks_severity = await self.kolmogorov_smirnov_test(
            ref_data, curr_data
        )

        js_div, js_severity = await self.jensen_shannon_divergence(
            ref_data, curr_data
        )

        # Determine overall severity (worst of all metrics)
        overall_severity = max(
            [psi_severity, ks_severity, js_severity],
            key=lambda s: list(DriftSeverity).index(s)
        )

        # Create result
        result = {
            'tag_name': tag_name,
            'model_id': model_id,
            'drift_type': drift_type,
            'reference_period': {
                'start': reference_start.isoformat(),
                'end': reference_end.isoformat(),
                'sample_size': len(ref_data),
            },
            'current_period': {
                'start': current_start.isoformat(),
                'end': current_end.isoformat(),
                'sample_size': len(curr_data),
            },
            'metrics': {
                'psi': {
                    'value': psi_value,
                    'severity': psi_severity,
                },
                'ks_test': {
                    'statistic': ks_stat,
                    'p_value': ks_pvalue,
                    'severity': ks_severity,
                },
                'js_divergence': {
                    'value': js_div,
                    'severity': js_severity,
                },
            },
            'overall_severity': overall_severity,
            'detected_at': datetime.now().isoformat(),
        }

        # Save to database
        await self._save_drift_record(result)

        return result

    async def monitor_drift_continuous(
        self,
        tag_name: str,
        model_id: int,
        reference_days: int = 30,
        check_interval_hours: int = 6,
        alert_threshold: DriftSeverity = DriftSeverity.MEDIUM,
    ):
        """
        Continuously monitor drift in the background.

        Args:
            tag_name: Sensor tag name
            model_id: Model ID
            reference_days: Number of days for reference period
            check_interval_hours: How often to check for drift
            alert_threshold: Severity level to trigger alerts
        """
        logger.info(
            f"Starting continuous drift monitoring for {tag_name} "
            f"(model {model_id})"
        )

        while True:
            try:
                # Calculate time windows
                current_end = datetime.now()
                current_start = current_end - timedelta(hours=check_interval_hours)

                reference_end = current_start
                reference_start = reference_end - timedelta(days=reference_days)

                # Detect drift
                result = await self.detect_drift(
                    tag_name=tag_name,
                    model_id=model_id,
                    reference_start=reference_start,
                    reference_end=reference_end,
                    current_start=current_start,
                    current_end=current_end,
                )

                # Check if alert is needed
                if result.get('overall_severity'):
                    severity_index = list(DriftSeverity).index(
                        result['overall_severity']
                    )
                    threshold_index = list(DriftSeverity).index(alert_threshold)

                    if severity_index >= threshold_index:
                        await self._trigger_drift_alert(result)

            except Exception as e:
                logger.error(f"Error in drift monitoring: {e}", exc_info=True)

            # Wait for next check
            await asyncio.sleep(check_interval_hours * 3600)

    async def _fetch_data(
        self,
        tag_name: str,
        start_time: datetime,
        end_time: datetime,
    ) -> np.ndarray:
        """Fetch sensor data for drift analysis."""
        query = text("""
            SELECT value
            FROM influx_hist
            WHERE tag_name = :tag_name
                AND ts >= :start_time
                AND ts <= :end_time
                AND quality = 192
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

        rows = result.fetchall()
        data = np.array([float(row[0]) for row in rows])

        return data

    async def _save_drift_record(self, result: Dict[str, Any]):
        """Save drift detection result to database."""
        try:
            record = DriftMonitoring(
                tag_name=result['tag_name'],
                model_id=result['model_id'],
                drift_type=result['drift_type'],
                psi_value=result['metrics']['psi']['value'],
                ks_statistic=result['metrics']['ks_test']['statistic'],
                ks_pvalue=result['metrics']['ks_test']['p_value'],
                js_divergence=result['metrics']['js_divergence']['value'],
                severity=result['overall_severity'],
                reference_start=datetime.fromisoformat(
                    result['reference_period']['start']
                ),
                reference_end=datetime.fromisoformat(
                    result['reference_period']['end']
                ),
                current_start=datetime.fromisoformat(
                    result['current_period']['start']
                ),
                current_end=datetime.fromisoformat(
                    result['current_period']['end']
                ),
            )

            self.session.add(record)
            await self.session.commit()

            logger.info(f"Drift record saved for {result['tag_name']}")

        except Exception as e:
            logger.error(f"Failed to save drift record: {e}", exc_info=True)
            await self.session.rollback()

    async def _trigger_drift_alert(self, result: Dict[str, Any]):
        """
        Trigger alert for detected drift.

        In production, this would:
        - Send notifications (email, Slack, etc.)
        - Create alarm records
        - Trigger model retraining workflows
        """
        logger.warning(
            f"🚨 DRIFT ALERT: {result['tag_name']} "
            f"(severity: {result['overall_severity']})"
        )
        logger.warning(f"PSI: {result['metrics']['psi']['value']:.4f}")
        logger.warning(
            f"KS p-value: {result['metrics']['ks_test']['p_value']:.4f}"
        )
        logger.warning(
            f"JS Divergence: {result['metrics']['js_divergence']['value']:.4f}"
        )

        # TODO: Implement actual alerting mechanism
        # - Insert into alarm_history table
        # - Send email/Slack notification
        # - Trigger Dagster pipeline for model retraining

    def _classify_severity(
        self,
        value: float,
        thresholds: Dict[DriftSeverity, float],
    ) -> DriftSeverity:
        """
        Classify drift severity based on value and thresholds.

        Args:
            value: Metric value
            thresholds: Threshold dictionary (higher value = more drift)

        Returns:
            Severity level
        """
        if value < thresholds[DriftSeverity.LOW]:
            return DriftSeverity.NONE
        elif value < thresholds[DriftSeverity.MEDIUM]:
            return DriftSeverity.LOW
        elif value < thresholds[DriftSeverity.HIGH]:
            return DriftSeverity.MEDIUM
        elif value < thresholds[DriftSeverity.CRITICAL]:
            return DriftSeverity.HIGH
        else:
            return DriftSeverity.CRITICAL

    def _classify_severity_inverse(
        self,
        value: float,
        thresholds: Dict[DriftSeverity, float],
    ) -> DriftSeverity:
        """
        Classify drift severity (inverse scale - lower value = more drift).

        Used for p-values where lower values indicate more significant drift.

        Args:
            value: Metric value
            thresholds: Threshold dictionary (lower value = more drift)

        Returns:
            Severity level
        """
        if value > thresholds[DriftSeverity.LOW]:
            return DriftSeverity.NONE
        elif value > thresholds[DriftSeverity.MEDIUM]:
            return DriftSeverity.LOW
        elif value > thresholds[DriftSeverity.HIGH]:
            return DriftSeverity.MEDIUM
        elif value > thresholds[DriftSeverity.CRITICAL]:
            return DriftSeverity.HIGH
        else:
            return DriftSeverity.CRITICAL

    async def get_drift_history(
        self,
        tag_name: Optional[str] = None,
        model_id: Optional[int] = None,
        days: int = 30,
        min_severity: DriftSeverity = DriftSeverity.NONE,
    ) -> List[Dict[str, Any]]:
        """
        Get drift detection history.

        Args:
            tag_name: Optional tag name filter
            model_id: Optional model ID filter
            days: Number of days to look back
            min_severity: Minimum severity to include

        Returns:
            List of drift records
        """
        query = select(DriftMonitoring).where(
            DriftMonitoring.detected_at >= datetime.now() - timedelta(days=days)
        )

        if tag_name:
            query = query.where(DriftMonitoring.tag_name == tag_name)

        if model_id:
            query = query.where(DriftMonitoring.model_id == model_id)

        # Filter by severity
        severity_index = list(DriftSeverity).index(min_severity)
        severity_values = [s.value for s in list(DriftSeverity)[severity_index:]]

        query = query.where(DriftMonitoring.severity.in_(severity_values))

        query = query.order_by(DriftMonitoring.detected_at.desc())

        result = await self.session.execute(query)
        records = result.scalars().all()

        return [
            {
                'id': rec.id,
                'tag_name': rec.tag_name,
                'model_id': rec.model_id,
                'drift_type': rec.drift_type,
                'psi_value': rec.psi_value,
                'ks_statistic': rec.ks_statistic,
                'ks_pvalue': rec.ks_pvalue,
                'js_divergence': rec.js_divergence,
                'severity': rec.severity,
                'detected_at': rec.detected_at.isoformat() if rec.detected_at else None,
            }
            for rec in records
        ]
