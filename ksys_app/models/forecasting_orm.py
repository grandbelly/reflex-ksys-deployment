"""
SQLAlchemy ORM Models for Time-Series Forecasting

This module defines SQLAlchemy ORM models for the forecasting system.
All models use lazy="raise" to prevent implicit database queries.

Created: 2025-10-08
Task: 31 - Database Schema Design
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean,
    Integer,
    String,
    Text,
    BigInteger,
    LargeBinary,
    Numeric,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ksys_app.models.sensor_orm import Base


# ============================================================================
# Model Registry
# ============================================================================


class ModelRegistry(Base):
    """
    ML Model Registry for storing model metadata and versioning.

    Stores information about trained models including hyperparameters,
    performance metrics, and model artifacts location.
    """

    __tablename__ = "model_registry"

    # Primary key
    model_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Model identification
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)  # arima, prophet, xgboost, ensemble
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    tag_name: Mapped[str] = mapped_column(
        String(50), nullable=False  # References influx_tag.tag_name (no FK due to missing unique constraint)
    )

    # Model configuration (stored as JSON)
    hyperparameters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    feature_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    pipeline_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Model artifacts
    model_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Legacy: file path
    model_pickle: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)  # NEW: BYTEA pickle storage
    model_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Training metadata
    training_data_start: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    training_data_end: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    training_samples: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    training_duration_seconds: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)

    # Performance metrics
    train_mape: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    train_rmse: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    train_mae: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    validation_mape: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    validation_rmse: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    validation_mae: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    created_by: Mapped[str] = mapped_column(String(100), nullable=True, default="system")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Deployment tracking
    is_deployed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deployed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    deployed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships (with lazy="raise" to prevent implicit queries)
    predictions: Mapped[list["Prediction"]] = relationship(
        "Prediction", back_populates="model", lazy="raise"
    )
    performances: Mapped[list["PredictionPerformance"]] = relationship(
        "PredictionPerformance", back_populates="model", lazy="raise"
    )
    drift_records: Mapped[list["DriftMonitoring"]] = relationship(
        "DriftMonitoring", back_populates="model", lazy="raise"
    )

    # Table constraints
    __table_args__ = (
        UniqueConstraint("tag_name", "model_type", "version", name="unique_model_version"),
        Index("idx_model_registry_tag_name", "tag_name"),
        Index("idx_model_registry_model_type", "model_type"),
        Index("idx_model_registry_created_at", "created_at"),
        # Partial index for active models only
        Index("idx_model_registry_active", "is_active", postgresql_where=is_active == True),
    )

    def __repr__(self) -> str:
        return f"<ModelRegistry(id={self.model_id}, name={self.model_name}, type={self.model_type}, version={self.version})>"


# ============================================================================
# Predictions
# ============================================================================


class Prediction(Base):
    """
    Prediction results from forecasting models.

    Stores forecast values with confidence intervals. This is a TimescaleDB
    hypertable partitioned by target_time.
    """

    __tablename__ = "predictions"

    # Composite primary key
    target_time: Mapped[datetime] = mapped_column(TIMESTAMP, primary_key=True, nullable=False)
    tag_name: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("influx_tag.tag_name", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("model_registry.model_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    horizon_minutes: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)

    # Additional columns (auto-generated by database sequence)
    prediction_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("nextval('predictions_prediction_id_seq'::regclass)")
    )

    # Time information
    forecast_time: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)  # When prediction was made

    # Prediction values
    predicted_value: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    ci_lower: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)  # 95% CI lower bound
    ci_upper: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)  # 95% CI upper bound

    # Actual value (filled in after target_time)
    actual_value: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    prediction_error: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    absolute_percentage_error: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)

    # Relationships
    model: Mapped["ModelRegistry"] = relationship("ModelRegistry", back_populates="predictions", lazy="raise")

    # Table constraints
    __table_args__ = (
        Index("idx_predictions_forecast_time", "forecast_time"),
        Index("idx_predictions_tag_name", "tag_name", "target_time"),
        Index("idx_predictions_model_id", "model_id", "target_time"),
        Index("idx_predictions_horizon", "horizon_minutes", "target_time"),
        Index("idx_predictions_tag_horizon", "tag_name", "horizon_minutes", "target_time"),
    )

    def __repr__(self) -> str:
        return f"<Prediction(tag={self.tag_name}, target={self.target_time}, value={self.predicted_value})>"


# ============================================================================
# Prediction Performance
# ============================================================================


class PredictionPerformance(Base):
    """
    Model performance metrics tracked over time.

    Stores evaluation metrics (MAPE, RMSE, MAE) for models across different
    time periods. This is a TimescaleDB hypertable partitioned by evaluation_time.
    """

    __tablename__ = "prediction_performance"

    # Composite primary key
    evaluation_time: Mapped[datetime] = mapped_column(TIMESTAMP, primary_key=True, nullable=False)
    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("model_registry.model_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    horizon_minutes: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)

    # Additional columns
    performance_id: Mapped[int] = mapped_column(BigInteger, autoincrement=True, nullable=False)

    # Identification
    tag_name: Mapped[str] = mapped_column(
        String(50), nullable=False  # References influx_tag.tag_name (no FK due to missing unique constraint)
    )

    # Evaluation period
    eval_start_time: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    eval_end_time: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    num_predictions: Mapped[int] = mapped_column(Integer, nullable=False)

    # Performance metrics
    mape: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    rmse: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    mae: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    r2_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)

    # Distribution metrics
    mean_error: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    median_error: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    std_error: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)

    # Confidence interval metrics
    ci_coverage_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    ci_width_avg: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    model: Mapped["ModelRegistry"] = relationship(
        "ModelRegistry", back_populates="performances", lazy="raise"
    )

    # Table constraints
    __table_args__ = (
        Index("idx_perf_model_id", "model_id", "evaluation_time"),
        Index("idx_perf_tag_name", "tag_name", "evaluation_time"),
        Index("idx_perf_horizon", "horizon_minutes", "evaluation_time"),
        # Partial index for non-null MAPE
        Index("idx_perf_mape", "mape", postgresql_where=mape.isnot(None)),
    )

    def __repr__(self) -> str:
        return f"<PredictionPerformance(model_id={self.model_id}, mape={self.mape}, time={self.evaluation_time})>"


# ============================================================================
# Feature Store
# ============================================================================


class FeatureStore(Base):
    """
    Engineered features for model training and inference.

    Stores lag features, rolling statistics, time-based features, and
    seasonal decomposition results. This is a TimescaleDB hypertable
    partitioned by feature_time.
    """

    __tablename__ = "feature_store"

    # Composite primary key
    feature_time: Mapped[datetime] = mapped_column(TIMESTAMP, primary_key=True, nullable=False)
    tag_name: Mapped[str] = mapped_column(
        String(50), ForeignKey("influx_tag.tag_name", ondelete="CASCADE"), primary_key=True, nullable=False
    )

    # Additional columns
    feature_id: Mapped[int] = mapped_column(BigInteger, autoincrement=True, nullable=False)

    # Lag features
    lag_1h: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    lag_3h: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    lag_6h: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    lag_12h: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    lag_24h: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)

    # Rolling window statistics (6 hours)
    rolling_mean_6h: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    rolling_std_6h: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    rolling_min_6h: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    rolling_max_6h: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    rolling_median_6h: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)

    # Rolling window statistics (24 hours)
    rolling_mean_24h: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    rolling_std_24h: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    rolling_min_24h: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    rolling_max_24h: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)

    # Rolling window statistics (1 week)
    rolling_mean_1w: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    rolling_std_1w: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)

    # Time-based features
    hour_of_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    day_of_week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    day_of_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quarter: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_weekend: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_business_hour: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Seasonal decomposition (from STL)
    trend_component: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    seasonal_component: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    residual_component: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)

    # Advanced features
    rate_of_change: Mapped[Optional[float]] = mapped_column(Numeric(15, 6), nullable=True)
    acceleration: Mapped[Optional[float]] = mapped_column(Numeric(15, 6), nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    feature_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")

    # Table constraints
    __table_args__ = (
        Index("idx_feature_tag_name", "tag_name", "feature_time"),
        Index("idx_feature_version", "feature_version"),
    )

    def __repr__(self) -> str:
        return f"<FeatureStore(tag={self.tag_name}, time={self.feature_time})>"


# ============================================================================
# Drift Monitoring
# ============================================================================


class DriftMonitoring(Base):
    """
    Data and model drift monitoring records.

    Tracks distribution changes and concept drift over time using various
    statistical tests (PSI, KS-test, JS-divergence). This is a TimescaleDB
    hypertable partitioned by monitoring_time.
    """

    __tablename__ = "drift_monitoring"

    # Composite primary key
    monitoring_time: Mapped[datetime] = mapped_column(TIMESTAMP, primary_key=True, nullable=False)
    tag_name: Mapped[str] = mapped_column(
        String(50), ForeignKey("influx_tag.tag_name", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    drift_type: Mapped[str] = mapped_column(String(50), primary_key=True, nullable=False)

    # Additional columns
    drift_id: Mapped[int] = mapped_column(BigInteger, autoincrement=True, nullable=False)

    # Model reference (optional)
    model_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("model_registry.model_id", ondelete="CASCADE"), nullable=True
    )

    # Drift detection metrics
    psi_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    ks_statistic: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    ks_pvalue: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    js_divergence: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)

    # Distribution statistics (current window)
    current_mean: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    current_std: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    current_min: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    current_max: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)

    # Distribution statistics (reference window)
    reference_mean: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    reference_std: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    reference_min: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    reference_max: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)

    # Drift detection results
    is_drift_detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    drift_severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # low, medium, high, critical
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

    # Evaluation windows
    current_window_start: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    current_window_end: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    reference_window_start: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    reference_window_end: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)

    # Actions and metadata
    action_taken: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    alert_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    model: Mapped[Optional["ModelRegistry"]] = relationship(
        "ModelRegistry", back_populates="drift_records", lazy="raise"
    )

    # Table constraints
    __table_args__ = (
        Index("idx_drift_tag_name", "tag_name", "monitoring_time"),
        Index("idx_drift_model_id", "model_id", "monitoring_time", postgresql_where=model_id.isnot(None)),
        Index("idx_drift_detected", "is_drift_detected", "monitoring_time", postgresql_where=is_drift_detected == True),
        Index("idx_drift_severity", "drift_severity", "monitoring_time"),
    )

    def __repr__(self) -> str:
        return f"<DriftMonitoring(tag={self.tag_name}, type={self.drift_type}, detected={self.is_drift_detected})>"
