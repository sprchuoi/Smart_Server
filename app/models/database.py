from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Device(Base):
    """Model for IoT devices."""
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    device_type = Column(String(50), nullable=False)
    status = Column(String(20), default="offline")
    firmware_version = Column(String(20))
    last_seen = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SensorData(Base):
    """Model for sensor data readings."""
    __tablename__ = "sensor_data"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(100), nullable=False, index=True)
    sensor_type = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20))
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class Command(Base):
    """Model for device commands."""
    __tablename__ = "commands"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(100), nullable=False, index=True)
    command = Column(String(100), nullable=False)
    payload = Column(Text)
    status = Column(String(20), default="pending")
    response = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    executed_at = Column(DateTime(timezone=True))


class Intent(Base):
    """Model for LLM-parsed intents."""
    __tablename__ = "intents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_message = Column(Text, nullable=False)
    intent_type = Column(String(50), nullable=False)
    entities = Column(Text)  # JSON string
    confidence = Column(Float)
    actions = Column(Text)  # JSON string of actions to take
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))


class Report(Base):
    """Model for generated reports."""
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    file_path = Column(String(500))
    status = Column(String(20), default="pending")
    parameters = Column(Text)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
