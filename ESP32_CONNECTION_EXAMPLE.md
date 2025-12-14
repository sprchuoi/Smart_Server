# ESP32 Device Connection Guide

Connect your ESP32 devices to the Smart Server running on Raspberry Pi.

## Server Information

**Raspberry Pi Server:**
- IP Address: `192.168.2.1`
- MQTT Broker Port: `1883`
- HTTP API Port: `8000`
- WebSocket Port: `8000/ws`

## ESP32 Configuration Example

### Arduino/PlatformIO Code

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// MQTT Broker settings
const char* mqtt_server = "192.168.2.1";
const int mqtt_port = 1883;
const char* mqtt_username = "";  // Empty for anonymous (default config)
const char* mqtt_password = "";  // Empty for anonymous (default config)

// Device configuration
struct Config {
    const char* broker_host = "192.168.2.1";
    int broker_port = 1883;
    const char* client_id = "esp32_001";
    const char* username = "";  // Optional, leave empty if not configured
    const char* password = "";  // Optional, leave empty if not configured
    const char* device_id = "esp32_001";
    const char* device_type = "sensor";  // sensor, switch, light, etc.
};

Config default_config;

WiFiClient espClient;
PubSubClient mqtt_client(espClient);

// MQTT Topics
String statusTopic = "smart_home/devices/" + String(default_config.device_id) + "/status";
String sensorTopic = "smart_home/devices/" + String(default_config.device_id) + "/sensor/data";
String commandTopic = "smart_home/devices/" + String(default_config.device_id) + "/command";
String responseTopic = "smart_home/devices/" + String(default_config.device_id) + "/response";

void setup_wifi() {
    delay(10);
    Serial.println();
    Serial.print("Connecting to WiFi: ");
    Serial.println(ssid);
    
    WiFi.begin(ssid, password);
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    
    Serial.println("");
    Serial.println("WiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* payload, unsigned int length) {
    Serial.print("Message arrived [");
    Serial.print(topic);
    Serial.print("] ");
    
    String message;
    for (int i = 0; i < length; i++) {
        message += (char)payload[i];
    }
    Serial.println(message);
    
    // Parse JSON command
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, message);
    
    if (!error) {
        const char* cmd = doc["command"];
        Serial.print("Command: ");
        Serial.println(cmd);
        
        // Handle commands
        if (strcmp(cmd, "get_status") == 0) {
            publishStatus();
        } else if (strcmp(cmd, "turn_on") == 0) {
            // Turn on device
            Serial.println("Turning ON");
            publishResponse(cmd, "success", "Device turned on");
        } else if (strcmp(cmd, "turn_off") == 0) {
            // Turn off device
            Serial.println("Turning OFF");
            publishResponse(cmd, "success", "Device turned off");
        }
    }
}

void reconnect() {
    while (!mqtt_client.connected()) {
        Serial.print("Attempting MQTT connection...");
        
        // Attempt to connect
        boolean connected;
        if (strlen(default_config.username) > 0) {
            // Connect with username/password
            connected = mqtt_client.connect(
                default_config.client_id,
                default_config.username,
                default_config.password
            );
        } else {
            // Connect anonymously
            connected = mqtt_client.connect(default_config.client_id);
        }
        
        if (connected) {
            Serial.println("connected!");
            
            // Subscribe to command topic
            mqtt_client.subscribe(commandTopic.c_str());
            Serial.print("Subscribed to: ");
            Serial.println(commandTopic);
            
            // Publish online status
            publishStatus();
            
        } else {
            Serial.print("failed, rc=");
            Serial.print(mqtt_client.state());
            Serial.println(" retrying in 5 seconds");
            delay(5000);
        }
    }
}

void publishStatus() {
    StaticJsonDocument<256> doc;
    doc["device_id"] = default_config.device_id;
    doc["device_type"] = default_config.device_type;
    doc["status"] = "online";
    doc["timestamp"] = millis();
    doc["ip"] = WiFi.localIP().toString();
    doc["rssi"] = WiFi.RSSI();
    
    char buffer[256];
    serializeJson(doc, buffer);
    
    mqtt_client.publish(statusTopic.c_str(), buffer, true);
    Serial.print("Published status: ");
    Serial.println(buffer);
}

void publishSensorData(float temperature, float humidity) {
    StaticJsonDocument<256> doc;
    doc["device_id"] = default_config.device_id;
    doc["timestamp"] = millis();
    doc["temperature"] = temperature;
    doc["humidity"] = humidity;
    
    char buffer[256];
    serializeJson(doc, buffer);
    
    mqtt_client.publish(sensorTopic.c_str(), buffer);
    Serial.print("Published sensor data: ");
    Serial.println(buffer);
}

void publishResponse(const char* command, const char* status, const char* message) {
    StaticJsonDocument<256> doc;
    doc["device_id"] = default_config.device_id;
    doc["command"] = command;
    doc["status"] = status;
    doc["message"] = message;
    doc["timestamp"] = millis();
    
    char buffer[256];
    serializeJson(doc, buffer);
    
    mqtt_client.publish(responseTopic.c_str(), buffer);
    Serial.print("Published response: ");
    Serial.println(buffer);
}

void setup() {
    Serial.begin(115200);
    
    setup_wifi();
    
    mqtt_client.setServer(default_config.broker_host, default_config.broker_port);
    mqtt_client.setCallback(callback);
}

void loop() {
    if (!mqtt_client.connected()) {
        reconnect();
    }
    mqtt_client.loop();
    
    // Example: Publish sensor data every 10 seconds
    static unsigned long lastMsg = 0;
    unsigned long now = millis();
    if (now - lastMsg > 10000) {
        lastMsg = now;
        
        // Simulate sensor readings
        float temperature = random(200, 300) / 10.0;  // 20.0 - 30.0°C
        float humidity = random(400, 700) / 10.0;     // 40.0 - 70.0%
        
        publishSensorData(temperature, humidity);
    }
}
```

## MQTT Topics Structure

Your ESP32 device should use these topics:

```
smart_home/devices/{device_id}/status        - Device status (online/offline)
smart_home/devices/{device_id}/sensor/data   - Sensor data
smart_home/devices/{device_id}/command       - Incoming commands from server
smart_home/devices/{device_id}/response      - Command responses
```

### Example: For device_id = "esp32_001"

- Status: `smart_home/devices/esp32_001/status`
- Sensor: `smart_home/devices/esp32_001/sensor/data`
- Command: `smart_home/devices/esp32_001/command`
- Response: `smart_home/devices/esp32_001/response`

## Message Formats

### Status Message (ESP32 → Server)
```json
{
    "device_id": "esp32_001",
    "device_type": "sensor",
    "status": "online",
    "timestamp": 12345678,
    "ip": "192.168.2.50",
    "rssi": -65
}
```

### Sensor Data (ESP32 → Server)
```json
{
    "device_id": "esp32_001",
    "timestamp": 12345678,
    "temperature": 25.5,
    "humidity": 60.2
}
```

### Command Message (Server → ESP32)
```json
{
    "command": "turn_on",
    "params": {}
}
```

### Response Message (ESP32 → Server)
```json
{
    "device_id": "esp32_001",
    "command": "turn_on",
    "status": "success",
    "message": "Device turned on",
    "timestamp": 12345678
}
```

## Testing Connection

### 1. Test MQTT Connection from Computer

```bash
# Install mosquitto clients
sudo apt-get install mosquitto-clients

# Subscribe to all device messages
mosquitto_sub -h 192.168.2.1 -t "smart_home/devices/#" -v

# Publish a test message
mosquitto_pub -h 192.168.2.1 -t "smart_home/devices/esp32_001/command" -m '{"command":"get_status"}'
```

### 2. Monitor in Web Dashboard

Open: `http://192.168.2.1:8000/static/index.html`

You should see your ESP32 device appear in the device list once it connects.

## Troubleshooting

### ESP32 can't connect to MQTT broker

1. **Check network connectivity:**
   ```cpp
   Serial.println(WiFi.localIP());  // Should be 192.168.2.x
   ```

2. **Ping the server:**
   ```bash
   ping 192.168.2.1
   ```

3. **Check firewall on Raspberry Pi:**
   ```bash
   sudo ufw allow 1883
   ```

4. **Verify MQTT broker is running:**
   ```bash
   sudo docker compose logs mosquitto
   ```

### Device connects but server doesn't receive messages

1. **Check topic format** - Must follow: `smart_home/devices/{device_id}/{subtopic}`
2. **Verify JSON format** - Use ArduinoJson library
3. **Check serial output** for error messages

## Multiple Devices

To connect multiple ESP32 devices:

```cpp
// Device 1
Config device1 = {
    .broker_host = "192.168.2.1",
    .broker_port = 1883,
    .client_id = "esp32_001",
    .device_id = "esp32_001",
    .device_type = "sensor"
};

// Device 2
Config device2 = {
    .broker_host = "192.168.2.1",
    .broker_port = 1883,
    .client_id = "esp32_002",
    .device_id = "esp32_002",
    .device_type = "switch"
};

// Device 3 (with authentication if configured)
Config device3 = {
    .broker_host = "192.168.2.1",
    .broker_port = 1883,
    .client_id = "esp32_003",
    .username = "esp32_user",
    .password = "secure_password",
    .device_id = "esp32_003",
    .device_type = "light"
};
```

**Important:** Each device must have a unique `client_id` and `device_id`.

## Required Libraries

Install these in PlatformIO or Arduino IDE:

```ini
# platformio.ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
lib_deps = 
    knolleary/PubSubClient@^2.8
    bblanchon/ArduinoJson@^6.21.3
```

Or in Arduino IDE:
- PubSubClient by Nick O'Leary
- ArduinoJson by Benoit Blanchon

## Security Notes

Current setup uses anonymous MQTT (no authentication). For production:

1. **Enable MQTT authentication** in mosquitto.conf
2. **Use TLS/SSL** for encrypted communication
3. **Set strong passwords** for MQTT users
4. **Use firewall rules** to restrict access

## Next Steps

1. Flash the example code to your ESP32
2. Open Serial Monitor (115200 baud)
3. Watch for "WiFi connected" and "MQTT connected" messages
4. Check the web dashboard at `http://192.168.2.1:8000/static/index.html`
5. Your device should appear in the device list!
