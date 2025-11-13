#!/bin/bash
# Test script for Docker deployment of DeepAgents FileServer

set -e  # Exit on error

echo "========================================"
echo "DeepAgents FileServer - Docker Test"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    echo ""
    echo "${YELLOW}Cleaning up...${NC}"
    docker compose down -v 2>/dev/null || true
    rm -rf ./test-data 2>/dev/null || true
}

# Trap cleanup on script exit
trap cleanup EXIT

# Create test data directory
echo "${YELLOW}Setting up test environment...${NC}"
mkdir -p ./test-data
echo "test content" > ./test-data/existing.txt

# Start services
echo "${YELLOW}Building Docker image...${NC}"
docker compose build

echo ""
echo "${YELLOW}Starting FastAPI server...${NC}"
docker compose up -d fileserver-fastapi

# Wait for server to be ready
echo "${YELLOW}Waiting for server to be ready...${NC}"
sleep 5

# Get API key from logs
echo "${YELLOW}Extracting API key from logs...${NC}"
API_KEY=$(docker compose logs fileserver-fastapi 2>&1 | grep -oP 'API Key: \K[a-zA-Z0-9-]+' | head -1)

if [ -z "$API_KEY" ]; then
    echo "${RED}Failed to extract API key from logs!${NC}"
    echo "Server logs:"
    docker compose logs fileserver-fastapi
    exit 1
fi

echo "${GREEN}API Key: ${API_KEY}${NC}"
echo ""

# Test 1: Health check (no auth required)
echo "Test 1: Health check"
if curl -f -s http://localhost:8080/health | grep -q "ok"; then
    echo "${GREEN}✓ Health check passed${NC}"
else
    echo "${RED}✗ Health check failed${NC}"
    exit 1
fi

# Test 2: List directory
echo "Test 2: List directory"
if curl -f -s -H "X-API-Key: $API_KEY" "http://localhost:8080/api/ls?path=/" | grep -q "files"; then
    echo "${GREEN}✓ List directory passed${NC}"
else
    echo "${RED}✗ List directory failed${NC}"
    exit 1
fi

# Test 3: Write file
echo "Test 3: Write file"
if curl -f -s -X POST http://localhost:8080/api/write \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{"file_path": "/docker-test.txt", "content": "Hello from Docker!"}' | grep -q "docker-test.txt"; then
    echo "${GREEN}✓ Write file passed${NC}"
else
    echo "${RED}✗ Write file failed${NC}"
    exit 1
fi

# Test 4: Read file
echo "Test 4: Read file"
if curl -f -s -H "X-API-Key: $API_KEY" \
    "http://localhost:8080/api/read?file_path=/docker-test.txt" | grep -q "Hello from Docker"; then
    echo "${GREEN}✓ Read file passed${NC}"
else
    echo "${RED}✗ Read file failed${NC}"
    exit 1
fi

# Test 5: Edit file
echo "Test 5: Edit file"
if curl -f -s -X POST http://localhost:8080/api/edit \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{"file_path": "/docker-test.txt", "old_string": "Docker", "new_string": "Container"}' | grep -q "occurrences"; then
    echo "${GREEN}✓ Edit file passed${NC}"
else
    echo "${RED}✗ Edit file failed${NC}"
    exit 1
fi

# Test 6: Grep
echo "Test 6: Search files (grep)"
if curl -f -s -H "X-API-Key: $API_KEY" \
    "http://localhost:8080/api/grep?pattern=Container&path=/" | grep -q "matches"; then
    echo "${GREEN}✓ Grep passed${NC}"
else
    echo "${RED}✗ Grep failed${NC}"
    exit 1
fi

# Test 7: Glob
echo "Test 7: Find files (glob)"
if curl -f -s -H "X-API-Key: $API_KEY" \
    "http://localhost:8080/api/glob?pattern=*.txt&path=/" | grep -q "docker-test.txt"; then
    echo "${GREEN}✓ Glob passed${NC}"
else
    echo "${RED}✗ Glob failed${NC}"
    exit 1
fi

# Test 8: Authentication required
echo "Test 8: Authentication enforcement"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/ls)
if [ "$HTTP_CODE" == "401" ] || [ "$HTTP_CODE" == "403" ]; then
    echo "${GREEN}✓ Authentication enforcement passed${NC}"
else
    echo "${RED}✗ Authentication enforcement failed (got HTTP $HTTP_CODE)${NC}"
    exit 1
fi

# Test 9: Health check
echo "Test 9: Docker health check"
HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' deepagents-fileserver-fastapi)
if [ "$HEALTH_STATUS" == "healthy" ]; then
    echo "${GREEN}✓ Docker health check passed${NC}"
else
    echo "${YELLOW}⚠ Docker health check status: $HEALTH_STATUS (may need more time)${NC}"
fi

# Test 10: Container logs
echo "Test 10: Container logs check"
if docker compose logs fileserver-fastapi | grep -q "Uvicorn running"; then
    echo "${GREEN}✓ Container logs check passed${NC}"
else
    echo "${RED}✗ Container logs check failed${NC}"
    exit 1
fi

echo ""
echo "========================================"
echo "${GREEN}All tests passed! ✓${NC}"
echo "========================================"
echo ""
echo "Container info:"
docker ps | grep fileserver
echo ""
echo "To access the server:"
echo "  URL: http://localhost:8080"
echo "  API Key: $API_KEY"
echo "  Docs: http://localhost:8080/docs"
echo ""
echo "To view logs: docker compose logs -f fileserver-fastapi"
echo "To stop: docker compose down"
