#!/bin/bash

# Demo/Test Script for Smart Server API
# This script demonstrates various API endpoints

BASE_URL="${1:-http://localhost:8000}"

echo "=================================="
echo "Smart Server API Demo"
echo "Base URL: $BASE_URL"
echo "=================================="
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4
    
    echo -e "${BLUE}Testing: $name${NC}"
    echo "Endpoint: $method $endpoint"
    
    if [ -z "$data" ]; then
        response=$(curl -s -X $method "$BASE_URL$endpoint")
    else
        response=$(curl -s -X $method "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    echo "Response:"
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    echo ""
    echo "-----------------------------------"
    echo ""
}

# Test health check
test_endpoint "Health Check" "GET" "/health"

# Test root endpoint
test_endpoint "Root Endpoint" "GET" "/"

# Test list devices
test_endpoint "List Devices" "GET" "/api/devices/"

# Test create device
test_endpoint "Create Device" "POST" "/api/devices/" '{
  "device_id": "demo_light_1",
  "name": "Demo Living Room Light",
  "device_type": "light"
}'

# Test get device
test_endpoint "Get Device" "GET" "/api/devices/demo_light_1"

# Test send command
test_endpoint "Send Device Command" "POST" "/api/devices/demo_light_1/command" '{
  "device_id": "demo_light_1",
  "command": "turn_on",
  "payload": "{\"brightness\": 100}"
}'

# Test chat/intent parsing
test_endpoint "Chat - Turn on light" "POST" "/api/chat/" '{
  "message": "Turn on the living room light"
}'

test_endpoint "Chat - Check status" "POST" "/api/chat/" '{
  "message": "What is the status of my devices?"
}'

# Test OTA version
test_endpoint "Get OTA Version" "GET" "/api/ota/version"

# Test check update
test_endpoint "Check for Update" "POST" "/api/ota/check-update" '{
  "current_version": "1.0.0",
  "device_id": "demo_light_1"
}'

# Test list reports
test_endpoint "List Reports" "GET" "/api/reports/"

# Test generate device status report
test_endpoint "Generate Device Status Report" "GET" "/api/reports/device-status?format=json"

echo -e "${GREEN}Demo completed!${NC}"
echo ""
echo "Additional endpoints to try:"
echo "  - Dashboard: $BASE_URL/static/index.html"
echo "  - API Docs: $BASE_URL/docs"
echo "  - WebSocket: ws://localhost:8000/ws"
echo ""
