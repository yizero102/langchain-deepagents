#!/bin/bash
# Manual Docker test script
# This script demonstrates how to build and test the Docker image manually

set -e

echo "======================================"
echo "DeepAgents FileServer Docker Test"
echo "======================================"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="test-fileserver"
IMAGE_NAME="deepagents-fileserver"
PORT=8080
API_KEY="test-api-key-12345"

# Cleanup function
cleanup() {
    echo -e "${YELLOW}Cleaning up...${NC}"
    docker rm -f $CONTAINER_NAME 2>/dev/null || true
}

# Trap cleanup on exit
trap cleanup EXIT

# Step 1: Build the image
echo "Step 1: Building Docker image..."
if docker build -t $IMAGE_NAME .; then
    echo -e "${GREEN}✓ Image built successfully${NC}"
else
    echo -e "${RED}✗ Failed to build image${NC}"
    exit 1
fi
echo

# Step 2: Start the container
echo "Step 2: Starting FastAPI container..."
docker run -d \
    --name $CONTAINER_NAME \
    -p $PORT:8080 \
    -e FILESERVER_MODE=fastapi \
    -e FILESERVER_API_KEY=$API_KEY \
    $IMAGE_NAME

echo -e "${GREEN}✓ Container started${NC}"
echo "Container ID: $(docker ps -q -f name=$CONTAINER_NAME)"
echo

# Step 3: Wait for server to be ready
echo "Step 3: Waiting for server to be ready..."
sleep 5

MAX_RETRIES=30
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Server is ready${NC}"
        break
    fi
    RETRY=$((RETRY + 1))
    echo "Waiting... ($RETRY/$MAX_RETRIES)"
    sleep 1
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ Server failed to start${NC}"
    echo "Container logs:"
    docker logs $CONTAINER_NAME
    exit 1
fi
echo

# Step 4: Run API tests
echo "Step 4: Testing API endpoints..."
echo

# Test 1: Health check (no auth)
echo -n "Test 1 - Health check: "
if curl -s http://localhost:$PORT/health | grep -q "ok"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
fi

# Test 2: List directory
echo -n "Test 2 - List directory: "
if curl -s -H "X-API-Key: $API_KEY" "http://localhost:$PORT/api/ls?path=/" | grep -q "files"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
fi

# Test 3: Write file
echo -n "Test 3 - Write file: "
if curl -s -X POST \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"file_path": "/test.txt", "content": "Hello Docker!"}' \
    http://localhost:$PORT/api/write | grep -q "test.txt"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
fi

# Test 4: Read file
echo -n "Test 4 - Read file: "
if curl -s -H "X-API-Key: $API_KEY" \
    "http://localhost:$PORT/api/read?file_path=/test.txt" | grep -q "Hello Docker"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
fi

# Test 5: Edit file
echo -n "Test 5 - Edit file: "
if curl -s -X POST \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"file_path": "/test.txt", "old_string": "Docker", "new_string": "Container"}' \
    http://localhost:$PORT/api/edit | grep -q "occurrences"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
fi

# Test 6: Grep
echo -n "Test 6 - Grep search: "
if curl -s -H "X-API-Key: $API_KEY" \
    "http://localhost:$PORT/api/grep?pattern=Container&path=/" | grep -q "matches"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
fi

# Test 7: Glob
echo -n "Test 7 - Glob pattern: "
if curl -s -H "X-API-Key: $API_KEY" \
    "http://localhost:$PORT/api/glob?pattern=*.txt&path=/" | grep -q "files"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
fi

# Test 8: API documentation
echo -n "Test 8 - API docs: "
if curl -s http://localhost:$PORT/docs | grep -q "swagger"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
fi

echo
echo "======================================"
echo "All tests completed!"
echo "======================================"
echo
echo "Container is still running. You can:"
echo "  - View logs: docker logs $CONTAINER_NAME"
echo "  - Access API docs: http://localhost:$PORT/docs"
echo "  - Test manually with curl"
echo
echo "Press Enter to stop and remove the container..."
read

echo -e "${YELLOW}Stopping container...${NC}"
docker stop $CONTAINER_NAME
echo -e "${GREEN}✓ Tests complete!${NC}"
