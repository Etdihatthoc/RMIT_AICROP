"""
SQLAlchemy ORM Models for AI Crop Doctor
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Diagnosis(Base):
    """Diagnosis records table"""
    __tablename__ = "diagnoses"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Farmer info
    farmer_id = Column(String, nullable=True, index=True)

    # Input files (at least one of image, audio, or question required)
    image_path = Column(String, nullable=True)
    audio_path = Column(String, nullable=True)
    question = Column(Text, nullable=True)

    # Location data
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    province = Column(String, nullable=True)
    district = Column(String, nullable=True)

    # Context data
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    weather_conditions = Column(Text, nullable=True)  # JSON array as string

    # AI Response
    disease_detected = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    severity = Column(String, nullable=True)  # "low", "medium", "high"
    full_response = Column(Text, nullable=True)

    # Status
    status = Column(String, default="pending")  # "pending", "confirmed", "rejected", "expert_review"
    expert_reviewed = Column(Boolean, default=False)
    expert_comment = Column(Text, nullable=True)
    expert_id = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_location', 'latitude', 'longitude'),
        Index('idx_disease', 'disease_detected'),
        Index('idx_created_at', 'created_at'),
        Index('idx_status', 'status'),
    )


class Expert(Base):
    """Expert users table"""
    __tablename__ = "experts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    # Profile
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    specialization = Column(String, nullable=True)  # e.g., "rice_diseases"

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())


class EpidemicAlert(Base):
    """Epidemic alerts table"""
    __tablename__ = "epidemic_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Disease info
    disease_name = Column(String, nullable=False)
    province = Column(String, nullable=False)
    district = Column(String, nullable=True)

    # Alert metrics
    case_count = Column(Integer, default=0)
    radius_km = Column(Float, nullable=True)
    center_lat = Column(Float, nullable=True)
    center_lon = Column(Float, nullable=True)
    severity = Column(String, nullable=True)  # "low", "medium", "high"

    # Alert status
    alert_status = Column(String, default="active")  # "active", "resolved"
    alert_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_alert_location', 'province', 'district'),
        Index('idx_alert_disease', 'disease_name'),
    )


class ChatHistory(Base):
    """Chat history table for conversational AI"""
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # User info
    farmer_id = Column(String, nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)  # Group related messages

    # Message content
    role = Column(String, nullable=False)  # "user" or "assistant"
    message = Column(Text, nullable=False)

    # Input files (for multimodal chat)
    image_path = Column(String, nullable=True)
    audio_path = Column(String, nullable=True)

    # Location context
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    province = Column(String, nullable=True)

    # Weather context
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)

    # If this message triggered a diagnosis
    diagnosis_id = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_chat_session', 'session_id', 'created_at'),
        Index('idx_chat_farmer', 'farmer_id', 'created_at'),
    )
