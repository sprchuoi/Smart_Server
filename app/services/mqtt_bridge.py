import asyncio
import json
import logging
from typing import Optional, Callable, Dict
import paho.mqtt.client as mqtt
from datetime import datetime

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.database import Device, SensorData
from sqlalchemy import select

logger = logging.getLogger(__name__)


class MQTTBridge:
    """MQTT Bridge for connecting to broker and processing device messages."""
    
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.message_handlers: Dict[str, Callable] = {}
        self.loop = None
        
    def setup(self, loop: asyncio.AbstractEventLoop):
        """Setup MQTT client with event loop."""
        self.loop = loop
        self.client = mqtt.Client(client_id="smart_server_bridge")
        
        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Set credentials if provided
        if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
            self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker."""
        if rc == 0:
            self.connected = True
            logger.info("Connected to MQTT broker")
            
            # Subscribe to device topics
            topics = [
                f"{settings.MQTT_TOPIC_PREFIX}/devices/+/status",
                f"{settings.MQTT_TOPIC_PREFIX}/devices/+/sensor/#",
                f"{settings.MQTT_TOPIC_PREFIX}/devices/+/response",
            ]
            for topic in topics:
                client.subscribe(topic)
                logger.info(f"Subscribed to topic: {topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker."""
        self.connected = False
        logger.warning(f"Disconnected from MQTT broker. Return code: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Callback when message received from MQTT broker."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            logger.debug(f"Received message on topic {topic}: {payload}")
            
            # Schedule async processing
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._process_message(topic, payload),
                    self.loop
                )
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    async def _process_message(self, topic: str, payload: str):
        """Process incoming MQTT message."""
        try:
            # Parse topic
            parts = topic.split('/')
            if len(parts) < 4:
                return
            
            device_id = parts[2]
            message_type = parts[3]
            
            # Parse payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                data = {"value": payload}
            
            async with AsyncSessionLocal() as session:
                # Handle different message types
                if message_type == "status":
                    await self._handle_device_status(session, device_id, data)
                elif message_type == "sensor":
                    await self._handle_sensor_data(session, device_id, parts[4:], data)
                elif message_type == "response":
                    await self._handle_device_response(session, device_id, data)
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error processing message from topic {topic}: {e}")
    
    async def _handle_device_status(self, session, device_id: str, data: dict):
        """Handle device status update."""
        result = await session.execute(
            select(Device).where(Device.device_id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if device:
            device.status = data.get("status", "online")
            device.last_seen = datetime.utcnow()
            if "firmware_version" in data:
                device.firmware_version = data["firmware_version"]
            # Update ESP32-specific fields
            if "ip" in data:
                device.device_metadata = device.device_metadata or {}
                device.device_metadata["ip"] = data["ip"]
            if "rssi" in data:
                device.device_metadata = device.device_metadata or {}
                device.device_metadata["rssi"] = data["rssi"]
            logger.info(f"Updated device {device_id} status: {device.status}")
        else:
            # Create new device - support both 'type' and 'device_type' fields
            device_type = data.get("device_type") or data.get("type", "unknown")
            device_name = data.get("name", device_id)
            
            metadata = {}
            if "ip" in data:
                metadata["ip"] = data["ip"]
            if "rssi" in data:
                metadata["rssi"] = data["rssi"]
            
            device = Device(
                device_id=device_id,
                name=device_name,
                device_type=device_type,
                status=data.get("status", "online"),
                firmware_version=data.get("firmware_version"),
                device_metadata=metadata if metadata else None,
                last_seen=datetime.utcnow()
            )
            session.add(device)
            logger.info(f"Registered new device: {device_id} (type: {device_type})")
    
    async def _handle_sensor_data(self, session, device_id: str, sensor_path: list, data: dict):
        """Handle sensor data update - supports multiple sensor values in one message."""
        sensor_type = "/".join(sensor_path) if sensor_path else "data"
        
        # Handle single value format
        if "value" in data:
            try:
                value = float(data.get("value", 0))
                sensor_data = SensorData(
                    device_id=device_id,
                    sensor_type=sensor_type,
                    value=value,
                    unit=data.get("unit", ""),
                    timestamp=datetime.utcnow()
                )
                session.add(sensor_data)
                logger.debug(f"Stored sensor data: {device_id}/{sensor_type} = {value}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid sensor value for {device_id}/{sensor_type}: {data.get('value')}")
        
        # Handle multiple values format (e.g., temperature and humidity in one message)
        else:
            # Extract numeric fields from data (ESP32 format)
            sensor_fields = {}
            for key, val in data.items():
                if key in ["device_id", "timestamp"]:
                    continue
                try:
                    sensor_fields[key] = float(val)
                except (ValueError, TypeError):
                    continue
            
            # Store each sensor value
            for sensor_name, value in sensor_fields.items():
                sensor_data = SensorData(
                    device_id=device_id,
                    sensor_type=f"{sensor_type}/{sensor_name}" if sensor_type != "data" else sensor_name,
                    value=value,
                    unit="",
                    timestamp=datetime.utcnow()
                )
                session.add(sensor_data)
                logger.debug(f"Stored sensor data: {device_id}/{sensor_name} = {value}")
    
    async def _handle_device_response(self, session, device_id: str, data: dict):
        """Handle device command response."""
        logger.info(f"Received response from device {device_id}: {data}")
    
    async def connect(self):
        """Connect to MQTT broker."""
        try:
            logger.info(f"Connecting to MQTT broker at {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
            self.client.connect(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, 60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("Disconnected from MQTT broker")
    
    def publish(self, topic: str, payload: dict):
        """Publish message to MQTT topic."""
        if self.client and self.connected:
            full_topic = f"{settings.MQTT_TOPIC_PREFIX}/{topic}"
            self.client.publish(full_topic, json.dumps(payload))
            logger.debug(f"Published to {full_topic}: {payload}")
        else:
            logger.warning("Cannot publish: MQTT client not connected")


# Global MQTT bridge instance
mqtt_bridge = MQTTBridge()
