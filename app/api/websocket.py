from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import logging
import asyncio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections for dashboard."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remove from subscriptions
        for topic in list(self.subscriptions.keys()):
            if websocket in self.subscriptions[topic]:
                self.subscriptions[topic].remove(websocket)
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]
        
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connections."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_to_topic(self, topic: str, message: dict):
        """Broadcast a message to all connections subscribed to a topic."""
        if topic not in self.subscriptions:
            return
        
        disconnected = []
        for connection in self.subscriptions[topic]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to topic {topic}: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            if conn in self.subscriptions[topic]:
                self.subscriptions[topic].remove(conn)
    
    def subscribe(self, websocket: WebSocket, topic: str):
        """Subscribe a connection to a topic."""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
        
        if websocket not in self.subscriptions[topic]:
            self.subscriptions[topic].append(websocket)
            logger.info(f"WebSocket subscribed to topic: {topic}")
    
    def unsubscribe(self, websocket: WebSocket, topic: str):
        """Unsubscribe a connection from a topic."""
        if topic in self.subscriptions and websocket in self.subscriptions[topic]:
            self.subscriptions[topic].remove(websocket)
            logger.info(f"WebSocket unsubscribed from topic: {topic}")


# Global connection manager
manager = ConnectionManager()


async def handle_websocket_message(websocket: WebSocket, data: dict):
    """Handle incoming WebSocket messages."""
    try:
        message_type = data.get("type")
        
        if message_type == "subscribe":
            topic = data.get("topic")
            if topic:
                manager.subscribe(websocket, topic)
                await manager.send_personal_message(
                    {"type": "subscribed", "topic": topic},
                    websocket
                )
        
        elif message_type == "unsubscribe":
            topic = data.get("topic")
            if topic:
                manager.unsubscribe(websocket, topic)
                await manager.send_personal_message(
                    {"type": "unsubscribed", "topic": topic},
                    websocket
                )
        
        elif message_type == "ping":
            await manager.send_personal_message(
                {"type": "pong"},
                websocket
            )
        
        elif message_type == "command":
            # Handle device commands via WebSocket
            await handle_device_command(websocket, data)
        
        else:
            await manager.send_personal_message(
                {"type": "error", "message": f"Unknown message type: {message_type}"},
                websocket
            )
    
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")
        await manager.send_personal_message(
            {"type": "error", "message": str(e)},
            websocket
        )


async def handle_device_command(websocket: WebSocket, data: dict):
    """Handle device command from WebSocket."""
    from app.services.mqtt_bridge import mqtt_bridge
    
    device_id = data.get("device_id")
    command = data.get("command")
    payload = data.get("payload")
    
    if not device_id or not command:
        await manager.send_personal_message(
            {"type": "error", "message": "Missing device_id or command"},
            websocket
        )
        return
    
    # Send command via MQTT
    mqtt_bridge.publish(
        f"devices/{device_id}/command",
        {
            "command": command,
            "payload": payload
        }
    )
    
    await manager.send_personal_message(
        {"type": "command_sent", "device_id": device_id, "command": command},
        websocket
    )


async def send_device_update(device_id: str, status: dict):
    """Send device status update to subscribed clients."""
    await manager.broadcast_to_topic(
        f"device:{device_id}",
        {
            "type": "device_update",
            "device_id": device_id,
            "status": status
        }
    )


async def send_sensor_update(device_id: str, sensor_type: str, data: dict):
    """Send sensor data update to subscribed clients."""
    await manager.broadcast_to_topic(
        f"sensor:{device_id}",
        {
            "type": "sensor_update",
            "device_id": device_id,
            "sensor_type": sensor_type,
            "data": data
        }
    )
