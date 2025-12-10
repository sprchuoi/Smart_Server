#!/usr/bin/env python3
"""
Example IoT Device Simulator

This script simulates an IoT device that:
- Connects to the MQTT broker
- Publishes status updates
- Publishes sensor data
- Listens for commands
"""

import paho.mqtt.client as mqtt
import json
import time
import random
import argparse
from datetime import datetime


class DeviceSimulator:
    def __init__(self, device_id, device_type, broker_host="localhost", broker_port=1883):
        self.device_id = device_id
        self.device_type = device_type
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = None
        self.topic_prefix = "smart_home"
        self.firmware_version = "1.0.0"
        self.state = {
            "power": "off",
            "brightness": 0,
            "temperature": 20.0
        }
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✓ Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            
            # Subscribe to command topic
            command_topic = f"{self.topic_prefix}/devices/{self.device_id}/command"
            client.subscribe(command_topic)
            print(f"✓ Subscribed to: {command_topic}")
            
            # Publish initial status
            self.publish_status()
        else:
            print(f"✗ Connection failed with code {rc}")
    
    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            command = payload.get("command")
            command_payload = payload.get("payload", {})
            
            print(f"📥 Received command: {command}")
            
            # Process command
            response = self.process_command(command, command_payload)
            
            # Publish response
            response_topic = f"{self.topic_prefix}/devices/{self.device_id}/response"
            self.client.publish(response_topic, json.dumps(response))
            
            # Update status
            self.publish_status()
            
        except Exception as e:
            print(f"✗ Error processing message: {e}")
    
    def process_command(self, command, payload):
        """Process device commands."""
        if command == "turn_on":
            self.state["power"] = "on"
            if "brightness" in payload:
                self.state["brightness"] = payload["brightness"]
            else:
                self.state["brightness"] = 100
            return {"status": "success", "state": self.state}
        
        elif command == "turn_off":
            self.state["power"] = "off"
            self.state["brightness"] = 0
            return {"status": "success", "state": self.state}
        
        elif command == "set_brightness":
            brightness = payload.get("brightness", 50)
            self.state["brightness"] = max(0, min(100, brightness))
            return {"status": "success", "state": self.state}
        
        elif command == "get_status":
            return {"status": "success", "state": self.state}
        
        else:
            return {"status": "error", "message": f"Unknown command: {command}"}
    
    def publish_status(self):
        """Publish device status."""
        status_topic = f"{self.topic_prefix}/devices/{self.device_id}/status"
        status = {
            "status": "online",
            "name": f"{self.device_type.title()} {self.device_id}",
            "type": self.device_type,
            "firmware_version": self.firmware_version,
            "state": self.state,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.client.publish(status_topic, json.dumps(status))
        print(f"📤 Published status: {self.state['power']}")
    
    def publish_sensor_data(self, sensor_type, value, unit):
        """Publish sensor data."""
        sensor_topic = f"{self.topic_prefix}/devices/{self.device_id}/sensor/{sensor_type}"
        data = {
            "value": value,
            "unit": unit,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.client.publish(sensor_topic, json.dumps(data))
        print(f"📊 Published sensor data: {sensor_type} = {value}{unit}")
    
    def run(self):
        """Run the device simulator."""
        print(f"🚀 Starting device simulator: {self.device_id}")
        print(f"   Type: {self.device_type}")
        print(f"   Broker: {self.broker_host}:{self.broker_port}")
        print()
        
        # Set up MQTT client
        self.client = mqtt.Client(client_id=f"sim_{self.device_id}")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # Connect to broker
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # Main loop - publish sensor data periodically
            while True:
                time.sleep(10)
                
                # Simulate temperature sensor
                if self.device_type in ["sensor", "thermostat", "light"]:
                    temp = 20 + random.uniform(-2, 2)
                    self.publish_sensor_data("temperature", round(temp, 1), "°C")
                
                # Simulate humidity sensor
                if self.device_type in ["sensor", "thermostat"]:
                    humidity = 50 + random.uniform(-5, 5)
                    self.publish_sensor_data("humidity", round(humidity, 1), "%")
                
                # Simulate power consumption
                if self.device_type in ["light", "plug"]:
                    if self.state["power"] == "on":
                        power = (self.state["brightness"] / 100) * 60  # Max 60W
                        self.publish_sensor_data("power", round(power, 1), "W")
                
        except KeyboardInterrupt:
            print("\n⏹️  Stopping device simulator...")
            self.client.loop_stop()
            self.client.disconnect()
        except Exception as e:
            print(f"✗ Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="IoT Device Simulator for Smart Server")
    parser.add_argument("--device-id", default="sim_device_1", help="Device ID")
    parser.add_argument("--type", default="light", choices=["light", "sensor", "plug", "thermostat"], help="Device type")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    
    args = parser.parse_args()
    
    simulator = DeviceSimulator(
        device_id=args.device_id,
        device_type=args.type,
        broker_host=args.broker,
        broker_port=args.port
    )
    
    simulator.run()


if __name__ == "__main__":
    main()
