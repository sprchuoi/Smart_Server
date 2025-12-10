#!/bin/bash

# Quick Start Script for Smart Server
# This script helps you get started quickly with minimal setup

set -e

echo "=================================="
echo "Smart Server Quick Start"
echo "=================================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install basic dependencies (without heavy ones for quick start)
echo "Installing basic dependencies..."
cat > requirements_minimal.txt <<EOF
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
aiofiles==23.2.1
websockets==12.0
paho-mqtt==1.6.1
sqlalchemy==2.0.23
aiosqlite==0.19.0
python-dotenv==1.0.0
pydantic==2.5.1
pydantic-settings==2.1.0
jinja2==3.1.2
python-json-logger==2.0.7
EOF

pip install -r requirements_minimal.txt

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p ota reports logs models

# Check if Mosquitto is running
if command -v mosquitto &> /dev/null; then
    if ! pgrep -x "mosquitto" > /dev/null; then
        echo "Starting Mosquitto MQTT broker..."
        mosquitto -c mosquitto/config/mosquitto.conf -d 2>/dev/null || echo "Warning: Could not start Mosquitto. You may need to install it: sudo apt-get install mosquitto"
    else
        echo "Mosquitto is already running."
    fi
else
    echo "Warning: Mosquitto is not installed. Installing it is recommended:"
    echo "  sudo apt-get install mosquitto mosquitto-clients"
fi

echo ""
echo "=================================="
echo "Starting Smart Server..."
echo "=================================="
echo ""

# Start the server
echo "Server will be available at:"
echo "  - Dashboard: http://localhost:8000/static/index.html"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Health: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
