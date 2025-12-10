# Smart Server for Raspberry Pi

A comprehensive smart home server running on Raspberry Pi with MQTT, FastAPI, LLM integration, OTA updates, and reporting capabilities.

## Features

### 🔒 **Tailscale Client**
- Secure remote access from anywhere
- No port forwarding or firewall configuration needed
- Connect to your Pi securely from your phone or computer

### 📡 **Mosquitto MQTT Broker**
- Built-in MQTT broker for device communication
- WebSocket support for browser-based clients
- Persistent message storage

### 🚀 **FastAPI REST API + WebSocket**
- Modern REST API for device management
- Real-time WebSocket endpoint for dashboard updates
- Interactive API documentation at `/docs`
- Serves static UI assets

### 🌉 **MQTT Bridge**
- Subscribe to device topics automatically
- Process and store device messages
- Intent processing and routing
- Real-time device status tracking

### 🤖 **LLM Worker**
- Local LLM support using llama.cpp
- Natural language intent parsing
- Fallback to cloud providers (OpenAI, Anthropic)
- Smart home command understanding

### 📦 **OTA Server**
- Simple firmware update server
- Version management with `version.json`
- Checksum verification
- Update checking endpoint for devices

### 💾 **SQLite Database**
- Lightweight database for device data
- Stores device info, sensor data, commands
- Intent history and reports
- Can be upgraded to PostgreSQL for multi-user

### 📊 **Report Generator**
- Generate device status reports
- Sensor data analysis with charts
- HTML, PDF, and JSON export
- Automated report scheduling

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Raspberry Pi                             │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Tailscale  │  │  Mosquitto   │  │   FastAPI    │      │
│  │    Client    │  │  MQTT Broker │  │  Web Server  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                            │                 │               │
│                            └────────┬────────┘               │
│                                     │                        │
│  ┌──────────────┐  ┌──────────────┐│┌──────────────┐       │
│  │ MQTT Bridge  │──│  LLM Worker  │││  OTA Server  │       │
│  └──────────────┘  └──────────────┘││  (Firmware)  │       │
│         │                           │└──────────────┘       │
│         └───────────┬───────────────┘                       │
│                     │                                        │
│         ┌───────────▼───────────┐  ┌──────────────┐        │
│         │  SQLite Database      │  │   Reports    │        │
│         │  (Devices, Sensors,   │  │  Generator   │        │
│         │   Commands, Intents)  │  └──────────────┘        │
│         └───────────────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites
- Raspberry Pi 3 or newer (4GB RAM recommended for local LLM)
- Raspberry Pi OS (64-bit recommended)
- Internet connection
- microSD card (16GB minimum)

### Quick Install

1. Clone the repository:
```bash
git clone https://github.com/sprchuoi/Smart_Server.git
cd Smart_Server
```

2. Run the installation script:
```bash
chmod +x install.sh
./install.sh
```

3. Configure your settings:
```bash
nano .env
```

4. Start the service:
```bash
sudo systemctl start smart_server
```

### Manual Installation

1. **Update system:**
```bash
sudo apt-get update && sudo apt-get upgrade -y
```

2. **Install dependencies:**
```bash
sudo apt-get install -y python3 python3-pip python3-venv mosquitto mosquitto-clients
```

3. **Install Tailscale:**
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

4. **Set up Python environment:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

5. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your settings
```

6. **Initialize database and start server:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Configuration

### Environment Variables

Edit `.env` file to configure:

```bash
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# MQTT
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=

# Database
DATABASE_URL=sqlite+aiosqlite:///./smart_server.db

# LLM
LLM_PROVIDER=local  # or 'openai', 'anthropic'
LLM_MODEL_PATH=./models/llama-7b.gguf
OPENAI_API_KEY=your_key_here  # if using OpenAI
```

### Mosquitto Configuration

The MQTT broker is configured in `mosquitto/config/mosquitto.conf`:
- Port 1883: Standard MQTT
- Port 9001: WebSocket MQTT

## Usage

### Accessing the Dashboard

1. **Local network:**
   - http://your-pi-ip:8000/static/index.html

2. **Via Tailscale:**
   - http://your-pi-hostname:8000/static/index.html

### API Documentation

Interactive API docs available at:
- Swagger UI: http://your-pi-ip:8000/docs
- ReDoc: http://your-pi-ip:8000/redoc

### Device Integration

Devices should publish to MQTT topics:

```
smart_home/devices/{device_id}/status
smart_home/devices/{device_id}/sensor/{sensor_type}
smart_home/devices/{device_id}/response
```

Example status message:
```json
{
  "status": "online",
  "firmware_version": "1.0.0",
  "name": "Living Room Light",
  "type": "light"
}
```

Example sensor message:
```json
{
  "value": 23.5,
  "unit": "°C"
}
```

### WebSocket API

Connect to `ws://your-pi-ip:8000/ws`

Subscribe to device updates:
```json
{
  "type": "subscribe",
  "topic": "device:device_id"
}
```

Send device command:
```json
{
  "type": "command",
  "device_id": "light_1",
  "command": "turn_on",
  "payload": {"brightness": 100}
}
```

### REST API Examples

**List devices:**
```bash
curl http://localhost:8000/api/devices/
```

**Send command to device:**
```bash
curl -X POST http://localhost:8000/api/devices/light_1/command \
  -H "Content-Type: application/json" \
  -d '{"device_id": "light_1", "command": "turn_on"}'
```

**Chat with LLM assistant:**
```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Turn on the living room light"}'
```

**Check for firmware updates:**
```bash
curl -X POST http://localhost:8000/api/ota/check-update \
  -H "Content-Type: application/json" \
  -d '{"current_version": "1.0.0"}'
```

**Generate device status report:**
```bash
curl http://localhost:8000/api/reports/device-status?format=html
```

## OTA Updates

### For Firmware Developers

Upload new firmware:
```bash
curl -X POST http://localhost:8000/api/ota/firmware/upload \
  -F "file=@firmware.bin" \
  -F "version=1.1.0" \
  -F "changelog=Bug fixes and improvements"
```

### For Devices

Devices can check for updates:
```bash
curl -X POST http://localhost:8000/api/ota/check-update \
  -H "Content-Type: application/json" \
  -d '{"current_version": "1.0.0", "device_id": "device_1"}'
```

Download firmware:
```bash
curl -O http://localhost:8000/api/ota/firmware/firmware.bin
```

## LLM Setup

### Using Local LLM (llama.cpp)

1. Download a model (e.g., Llama 7B):
```bash
mkdir -p models
cd models
# Download your preferred GGUF model
wget https://huggingface.co/...model.gguf
```

2. Update `.env`:
```bash
LLM_PROVIDER=local
LLM_MODEL_PATH=./models/your-model.gguf
```

### Using Cloud LLM

For OpenAI:
```bash
LLM_PROVIDER=openai
LLM_FALLBACK_PROVIDER=openai
OPENAI_API_KEY=your_api_key
```

For Anthropic Claude:
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_api_key
```

## Docker Deployment

Alternatively, use Docker Compose:

```bash
docker-compose up -d
```

This will start:
- Mosquitto MQTT broker on ports 1883 and 9001
- Smart Server on port 8000

## Maintenance

### View Logs
```bash
sudo journalctl -u smart_server -f
```

### Restart Service
```bash
sudo systemctl restart smart_server
```

### Update Software
```bash
cd Smart_Server
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart smart_server
```

### Backup Database
```bash
cp smart_server.db smart_server.db.backup
```

## Troubleshooting

### MQTT Connection Issues
```bash
# Check Mosquitto status
sudo systemctl status mosquitto

# Test MQTT connection
mosquitto_sub -h localhost -t "#" -v
```

### Service Won't Start
```bash
# Check service logs
sudo journalctl -u smart_server -n 50

# Check if port is in use
sudo netstat -tulpn | grep 8000
```

### Tailscale Issues
```bash
# Check Tailscale status
sudo tailscale status

# Re-authenticate
sudo tailscale up
```

## Development

### Running in Development Mode

```bash
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Project Structure

```
Smart_Server/
├── app/
│   ├── api/              # API endpoints
│   │   ├── devices.py    # Device management
│   │   ├── chat.py       # LLM chat interface
│   │   ├── ota.py        # OTA updates
│   │   ├── reports.py    # Report generation
│   │   └── websocket.py  # WebSocket handlers
│   ├── core/             # Core functionality
│   │   ├── config.py     # Configuration
│   │   ├── database.py   # Database connection
│   │   └── logging.py    # Logging setup
│   ├── models/           # Database models
│   │   └── database.py   # SQLAlchemy models
│   ├── services/         # Business logic
│   │   ├── mqtt_bridge.py      # MQTT integration
│   │   ├── llm_service.py      # LLM processing
│   │   ├── ota_service.py      # OTA management
│   │   └── report_generator.py # Report creation
│   ├── static/           # Static files
│   │   └── index.html    # Dashboard UI
│   └── main.py           # FastAPI application
├── mosquitto/
│   └── config/
│       └── mosquitto.conf # MQTT configuration
├── ota/                  # Firmware files
├── reports/              # Generated reports
├── logs/                 # Application logs
├── docker-compose.yml    # Docker setup
├── Dockerfile            # Container image
├── requirements.txt      # Python dependencies
├── install.sh           # Installation script
└── .env.example         # Configuration template
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
- Open an issue on GitHub
- Check the documentation at `/docs` endpoint

## Roadmap

- [ ] Add authentication and user management
- [ ] PostgreSQL support for multi-user scenarios
- [ ] Advanced automation rules engine
- [ ] Mobile app integration
- [ ] Voice assistant integration
- [ ] Energy monitoring and analytics
- [ ] Zigbee/Z-Wave device support
- [ ] Home Assistant integration

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Mosquitto](https://mosquitto.org/) - MQTT broker
- [llama.cpp](https://github.com/ggerganov/llama.cpp) - LLM inference
- [Tailscale](https://tailscale.com/) - Secure networking
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM