from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.database import Device, SensorData, Command
from pydantic import BaseModel

router = APIRouter(prefix="/devices", tags=["devices"])


# Pydantic models for request/response
class DeviceCreate(BaseModel):
    device_id: str
    name: str
    device_type: str


class DeviceResponse(BaseModel):
    id: int
    device_id: str
    name: str
    device_type: str
    status: str
    firmware_version: Optional[str]
    last_seen: Optional[datetime]
    
    class Config:
        from_attributes = True


class SensorDataResponse(BaseModel):
    id: int
    device_id: str
    sensor_type: str
    value: float
    unit: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True


class CommandCreate(BaseModel):
    device_id: str
    command: str
    payload: Optional[str] = None


class CommandResponse(BaseModel):
    id: int
    device_id: str
    command: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[DeviceResponse])
async def list_devices(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all registered devices."""
    result = await db.execute(
        select(Device).offset(skip).limit(limit)
    )
    devices = result.scalars().all()
    return devices


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get device details."""
    result = await db.execute(
        select(Device).where(Device.device_id == device_id)
    )
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return device


@router.post("/", response_model=DeviceResponse)
async def create_device(
    device: DeviceCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new device."""
    # Check if device already exists
    result = await db.execute(
        select(Device).where(Device.device_id == device.device_id)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Device already exists")
    
    new_device = Device(
        device_id=device.device_id,
        name=device.name,
        device_type=device.device_type,
        status="offline"
    )
    db.add(new_device)
    await db.commit()
    await db.refresh(new_device)
    
    return new_device


@router.get("/{device_id}/sensor-data", response_model=List[SensorDataResponse])
async def get_sensor_data(
    device_id: str,
    sensor_type: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Get sensor data for a device."""
    query = select(SensorData).where(
        SensorData.device_id == device_id
    )
    
    if sensor_type:
        query = query.where(SensorData.sensor_type == sensor_type)
    
    query = query.order_by(SensorData.timestamp.desc()).limit(limit)
    
    result = await db.execute(query)
    sensor_data = result.scalars().all()
    
    return sensor_data


@router.post("/{device_id}/command", response_model=CommandResponse)
async def send_command(
    device_id: str,
    command: CommandCreate,
    db: AsyncSession = Depends(get_db)
):
    """Send a command to a device."""
    from app.services.mqtt_bridge import mqtt_bridge
    
    # Check if device exists
    result = await db.execute(
        select(Device).where(Device.device_id == device_id)
    )
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Store command in database
    new_command = Command(
        device_id=device_id,
        command=command.command,
        payload=command.payload,
        status="pending"
    )
    db.add(new_command)
    await db.commit()
    await db.refresh(new_command)
    
    # Send command via MQTT
    mqtt_bridge.publish(
        f"devices/{device_id}/command",
        {
            "command": command.command,
            "payload": command.payload,
            "command_id": new_command.id
        }
    )
    
    return new_command
