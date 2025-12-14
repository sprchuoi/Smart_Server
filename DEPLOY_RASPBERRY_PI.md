# Deploy Smart Server on Raspberry Pi

Your Docker image is now available on Docker Hub: **sprchuoi/smart-server:latest**

## Supported Architectures
- ✅ AMD64 (x86_64) - PC/Server
- ✅ ARM64 (aarch64) - Raspberry Pi 3/4/5, Raspberry Pi Zero 2 W

## Prerequisites on Raspberry Pi

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (optional, to run without sudo)
sudo usermod -aG docker $USER
# Log out and back in for this to take effect

# Install Docker Compose
sudo apt-get install docker-compose-plugin -y
```

## Deployment Steps

### 1. Create project directory
```bash
mkdir -p ~/smart-server
cd ~/smart-server
```

### 2. Create docker-compose.yml
```bash
cat > docker-compose.yml <<'EOF'
services:
  mosquitto:
    image: eclipse-mosquitto:2.0
    container_name: smart_server_mosquitto
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/log:/mosquitto/log
    restart: unless-stopped
    networks:
      - smart_server_network

  smart_server:
    image: sprchuoi/smart-server:latest
    container_name: smart_server_app
    ports:
      - "8000:8000"
    volumes:
      - ./ota:/app/ota
      - ./reports:/app/reports
      - ./models:/app/models
      - ./logs:/app/logs
    environment:
      - MQTT_BROKER_HOST=mosquitto
      - MQTT_BROKER_PORT=1883
      - DATABASE_URL=sqlite+aiosqlite:///./smart_home.db
      - LOG_LEVEL=INFO
    depends_on:
      - mosquitto
    restart: unless-stopped
    networks:
      - smart_server_network

networks:
  smart_server_network:
    driver: bridge
EOF
```

### 3. Create Mosquitto configuration
```bash
mkdir -p mosquitto/config mosquitto/data mosquitto/log
cat > mosquitto/config/mosquitto.conf <<'EOF'
listener 1883
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest file /mosquitto/log/mosquitto.log
log_dest stdout
EOF
```

### 4. Create required directories
```bash
mkdir -p ota reports models logs
```

### 5. Start the service
```bash
docker compose pull  # Pull the latest images
docker compose up -d  # Start in detached mode
```

### 6. Check status
```bash
# View running containers
docker compose ps

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f smart_server
docker compose logs -f mosquitto
```

## Access the Service

Once running, you can access:
- **Web Interface**: http://<raspberry-pi-ip>:8000
- **API Documentation**: http://<raspberry-pi-ip>:8000/docs
- **MQTT Broker**: <raspberry-pi-ip>:1883
- **MQTT WebSocket**: <raspberry-pi-ip>:9001

## Useful Commands

```bash
# Stop services
docker compose stop

# Start services
docker compose start

# Restart services
docker compose restart

# View logs
docker compose logs -f

# Stop and remove containers
docker compose down

# Update to latest version
docker compose pull
docker compose up -d

# Check resource usage
docker stats
```

## Automatic Start on Boot

Docker containers with `restart: unless-stopped` will automatically start on system boot.

## Troubleshooting

### Check container status
```bash
docker compose ps
docker compose logs smart_server
```

### Enter container for debugging
```bash
docker exec -it smart_server_app bash
```

### Check MQTT connection
```bash
# Install mosquitto client tools
sudo apt-get install mosquitto-clients

# Test MQTT connection
mosquitto_sub -h localhost -t "smart_home/#" -v
```

### Disk Space
```bash
# Check disk usage
df -h

# Clean up old Docker images
docker system prune -a
```

## Performance Tips for Raspberry Pi

1. **Use external storage**: Mount an external SSD/HDD for better performance
2. **Monitor resources**: Use `docker stats` to monitor CPU/memory usage
3. **Disable LLM features**: If not needed, the service works without the LLM model
4. **Update regularly**: Keep Docker and the image updated for best performance

## Environment Variables

You can customize the service by adding more environment variables in docker-compose.yml:

```yaml
environment:
  - MQTT_BROKER_HOST=mosquitto
  - MQTT_BROKER_PORT=1883
  - DATABASE_URL=sqlite+aiosqlite:///./smart_home.db
  - LOG_LEVEL=INFO
  - LLM_PROVIDER=local  # or 'openai', 'anthropic'
  - OPENAI_API_KEY=your_key_here  # if using OpenAI
  - ANTHROPIC_API_KEY=your_key_here  # if using Anthropic
```

## Security Notes

For production deployment:
1. Change Mosquitto to require authentication
2. Use a reverse proxy (nginx) with SSL/TLS
3. Set up a firewall (ufw)
4. Use strong passwords and API keys

## Support

For issues or questions:
- Check logs: `docker compose logs`
- GitHub Issues: https://github.com/sprchuoi/Smart_Server/issues
