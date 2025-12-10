#!/bin/bash

# Smart Server Installation Script for Raspberry Pi

set -e

echo "=================================="
echo "Smart Server Installation"
echo "=================================="
echo ""

# Check if running on Raspberry Pi
if [[ ! -f /proc/device-tree/model ]] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "Warning: This script is designed for Raspberry Pi, but will continue anyway."
fi

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    mosquitto \
    mosquitto-clients \
    build-essential \
    cmake \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info

# Install Tailscale
echo "Installing Tailscale..."
if ! command -v tailscale &> /dev/null; then
    curl -fsSL https://tailscale.com/install.sh | sh
    echo "Tailscale installed. Please run 'sudo tailscale up' to authenticate."
else
    echo "Tailscale already installed."
fi

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Copy environment file
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your configuration."
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p ota reports logs models mosquitto/data mosquitto/log

# Configure Mosquitto
echo "Configuring Mosquitto..."
if [ ! -f /etc/mosquitto/conf.d/smart_server.conf ]; then
    sudo cp mosquitto/config/mosquitto.conf /etc/mosquitto/conf.d/smart_server.conf
    sudo systemctl restart mosquitto
    sudo systemctl enable mosquitto
fi

# Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/smart_server.service > /dev/null <<EOF
[Unit]
Description=Smart Server
After=network.target mosquitto.service
Wants=mosquitto.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin"
ExecStart=$(pwd)/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload
sudo systemctl enable smart_server

echo ""
echo "=================================="
echo "Installation Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration: nano .env"
echo "2. If using Tailscale, authenticate: sudo tailscale up"
echo "3. Start the service: sudo systemctl start smart_server"
echo "4. Check status: sudo systemctl status smart_server"
echo "5. View logs: sudo journalctl -u smart_server -f"
echo "6. Access dashboard: http://$(hostname -I | awk '{print $1}'):8000/static/index.html"
echo ""
echo "For Tailscale access, use: http://$(hostname):8000/static/index.html"
echo ""
