"""
Device Schemas - For push notification registration
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DeviceRegister(BaseModel):
    """Schema for device registration"""
    device_token: str
    environment: str = "sandbox"  # sandbox or production
    device_name: Optional[str] = None
    os_version: Optional[str] = None


class DeviceResponse(BaseModel):
    """Schema for device response"""
    id: str
    device_token: str
    environment: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
