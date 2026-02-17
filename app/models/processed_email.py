"""
ProcessedEmail Model - Tracks processed emails to prevent duplicates
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean

from app.core.database import Base


class ProcessedEmail(Base):
    """Tracks which emails have been processed to prevent duplicates"""
    __tablename__ = "processed_emails"

    id = Column(String(36), primary_key=True, index=True)
    message_id = Column(String(255), nullable=False, unique=True, index=True)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=True)
    
    processed_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="success")  # success, failed, skipped
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<ProcessedEmail(message_id={self.message_id}, status={self.status})>"


class Device(Base):
    """Stores registered iOS devices for push notifications"""
    __tablename__ = "devices"

    id = Column(String(36), primary_key=True, index=True)
    device_token = Column(String(255), nullable=False, unique=True, index=True)
    environment = Column(String(20), default="sandbox")  # sandbox or production
    device_name = Column(String(100), nullable=True)
    os_version = Column(String(20), nullable=True)
    
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Device(token={self.device_token[:20]}...)>"
