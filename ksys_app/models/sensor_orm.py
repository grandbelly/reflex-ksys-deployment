"""Sensor ORM - SQLAlchemy style models for clarity"""
from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from typing import List, Optional
from datetime import datetime

Base = declarative_base()


class SensorTag(Base):
    """센서 태그 정의 - ORM Model"""
    __tablename__ = 'influx_tag'

    key = Column(String, primary_key=True)
    tag_id = Column(String)
    tag_name = Column(String, unique=True)
    tag_type = Column(String)
    meta = Column(String)  # JSONB in DB but treated as string for simplicity
    updated_at = Column(DateTime(timezone=True))

    # Relationships - with lazy="raise" to prevent implicit I/O
    latest_value = relationship("SensorLatest", back_populates="tag",
                              foreign_keys="SensorLatest.tag_name",
                              primaryjoin="SensorTag.tag_name==SensorLatest.tag_name",
                              lazy="raise")  # Prevent lazy loading
    qc_rule = relationship("SensorQCRule", back_populates="tag", uselist=False,
                          foreign_keys="SensorQCRule.tag_name",
                          primaryjoin="SensorTag.tag_name==SensorQCRule.tag_name",
                          lazy="raise")  # Prevent lazy loading

    def to_dict(self):
        """Convert to dictionary for State"""
        return {
            "tag_name": self.tag_name,
            "tag_type": self.tag_type,
            "description": self.tag_id or self.tag_name,
            "unit": "",  # Not in table
            "min_scale": 0.0,  # Default
            "max_scale": 100.0  # Default
        }


class SensorLatest(Base):
    """최신 센서 값 - ORM Model"""
    __tablename__ = 'influx_latest'

    tag_name = Column(String(50), primary_key=True)
    value = Column(Float, nullable=False)
    ts = Column(DateTime(timezone=True), nullable=False)
    quality = Column(Integer, default=0)

    # Relationships - using string reference for join
    tag = relationship("SensorTag", back_populates="latest_value",
                      foreign_keys=[tag_name],
                      primaryjoin="SensorTag.tag_name==SensorLatest.tag_name",
                      lazy="raise")  # Prevent lazy loading

    # Status calculation removed to prevent lazy loading
    # Calculate in service layer instead

    def to_dict(self):
        """Convert to dictionary for State - no lazy loading"""
        return {
            "tag_name": self.tag_name,
            "value": self.value,
            "timestamp": self.ts.isoformat() if self.ts else None,
            "quality": self.quality
            # status and unit should be calculated/added in service layer
        }


class SensorQCRule(Base):
    """센서 QC 규칙 - ORM Model"""
    __tablename__ = 'influx_qc_rule'

    tag_name = Column(String(50), primary_key=True)
    min_val = Column(Float, nullable=False)
    max_val = Column(Float, nullable=False)
    warning_low = Column(Float)
    warning_high = Column(Float)

    # Relationships
    tag = relationship("SensorTag", back_populates="qc_rule",
                      foreign_keys=[tag_name],
                      primaryjoin="SensorTag.tag_name==SensorQCRule.tag_name")

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "tag_name": self.tag_name,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "warning_low": self.warning_low,
            "warning_high": self.warning_high
        }


class SensorHistory(Base):
    """센서 이력 데이터 - ORM Model"""
    __tablename__ = 'influx_hist'
    __table_args__ = (
        Index('idx_tag_ts', 'tag_name', 'ts'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tag_name = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    ts = Column(DateTime(timezone=True), nullable=False)
    quality = Column(Integer, default=0)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "time": self.ts.strftime("%H:%M") if self.ts else "",
            "value": self.value
        }


class SensorAggregation(Base):
    """센서 집계 데이터 - ORM View Model"""
    __tablename__ = 'influx_agg_1h'
    __table_args__ = {'info': {'is_view': True}}  # This is a view

    bucket = Column(DateTime(timezone=True), primary_key=True)
    tag_name = Column(String(50), primary_key=True)
    avg = Column(Float)
    min = Column(Float)
    max = Column(Float)
    count = Column(Integer)

    def to_chart_point(self):
        """Convert to chart point"""
        return {
            "time": self.bucket.strftime("%H:%M") if self.bucket else "",
            "value": self.avg or 0
        }