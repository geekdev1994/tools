"""
Device API Endpoints
For push notification registration
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Device
from app.schemas import DeviceRegister, DeviceResponse

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/register", response_model=DeviceResponse, status_code=status.HTTP_200_OK)
@router.post("/", response_model=DeviceResponse, status_code=status.HTTP_200_OK)
def register_device(device_data: DeviceRegister, db: Session = Depends(get_db)):
    """
    Register or update a device for push notifications.
    Compatible with iOS registerDevice(token:environment:) method.
    """
    # Check if device already exists
    existing = db.query(Device).filter(
        Device.device_token == device_data.device_token
    ).first()
    
    if existing:
        # Update existing device
        existing.environment = device_data.environment
        existing.device_name = device_data.device_name
        existing.os_version = device_data.os_version
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create new device
    device = Device(
        id=str(uuid.uuid4()),
        device_token=device_data.device_token,
        environment=device_data.environment,
        device_name=device_data.device_name,
        os_version=device_data.os_version,
        is_active=True
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.delete("/{device_token}", status_code=status.HTTP_200_OK)
def unregister_device(device_token: str, db: Session = Depends(get_db)):
    """Unregister a device (mark as inactive)"""
    device = db.query(Device).filter(Device.device_token == device_token).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device.is_active = False
    db.commit()
    return {"message": "Device unregistered successfully"}
