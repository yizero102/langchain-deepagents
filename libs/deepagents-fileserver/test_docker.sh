#!/bin/bash
# Comprehensive Docker test script for DeepAgents FileServer
# Tests both standard and FastAPI servers with all endpoints

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="deepagents-fileserver"
CONTAINER_NAME_FASTAPI="test-fileserver-fastapi"
CONTAINER_NAME_STANDARD="test-fileserver-standard"
PORT_FASTAPI=8080
PORT_STANDARD=8081
TEST_DATA_DIR="./test_data_docker"
API_KEY="test-secret-key-12345"

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

print_warning() {
    echo -e "${YELLOW}!${NC} $1"
}

cleanup() {
    print_step "Cleaning up..."
    
    # Stop and remove containers
    docker stop $CONTAINER_NAME_FASTAPI 2>/dev/null || true
    docker stop $CONTAINER_NAME_STANDARD 2>/dev/null || true
    docker rm $CONTAINER_NAME_FASTAPI 2>/dev/null || true
    docker rm $CONTAINER_NAME_STANDARD 2>/dev/null || true
    
    # Remove test data directory
    if [ -d "$TEST_DATA_DIR" ]; then
        rm -rf "$TEST_DATA_DIR"
    fi
    
    print_success "Cleanup complete"
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

wait_for_server() {
    local port=$1
    local max_attempts=30
    local attempt=0
    
    print_step "Waiting for server on port $port..."
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f "http://localhost:$port/health" > /dev/null 2>&1; then
            print_success "Server is ready on port $port"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    
    print_error "Server failed to start on port $port within $max_attempts seconds"
    return 1
}

test_health_endpoint() {
    local port=$1
    local server_name=$2
    
    print_step "Testing health endpoint ($server_name)..."
    
    response=$(curl -s "http://localhost:$port/health")
    
    if echo "$response" | grep -q '"status".*"ok"'; then
        print_success "Health check passed"
        return 0
    else
        print_error "Health check failed: $response"
        return 1
    fi
}

test_write_file() {
    local port=$1
    local server_name=$2
    local headers=$3
    
    print_step "Testing write endpoint ($server_name)..."
    
    response=$(curl -s -X POST "http://localhost:$port/api/write" \
        -H "Content-Type: application/json" \
        $headers \
        -d '{"file_path": "test.txt", "content": "Hello Docker World!\nLine 2\nLine 3"}')
    
    if echo "$response" | grep -q '"error":null' && echo "$response" | grep -q '"path"'; then
        print_success "Write file passed"
        return 0
    else
        print_error "Write file failed: $response"
        return 1
    fi
}

test_read_file() {
    local port=$1
    local server_name=$2
    local headers=$3
    
    print_step "Testing read endpoint ($server_name)..."
    
    response=$(curl -s "http://localhost:$port/api/read?file_path=test.txt" $headers)
    
    if echo "$response" | grep -q "Hello Docker World"; then
        print_success "Read file passed"
        return 0
    else
        print_error "Read file failed: $response"
        return 1
    fi
}

test_list_directory() {
    local port=$1
    local server_name=$2
    local headers=$3
    
    print_step "Testing list endpoint ($server_name)..."
    
    response=$(curl -s "http://localhost:$port/api/ls?path=/" $headers)
    
    if echo "$response" | grep -q '"files"' && echo "$response" | grep -q '"path"'; then
        print_success "List directory passed"
        return 0
    else
        print_error "List directory failed: $response"
        return 1
    fi
}

test_edit_file() {
    local port=$1
    local server_name=$2
    local headers=$3
    
    print_step "Testing edit endpoint ($server_name)..."
    
    response=$(curl -s -X POST "http://localhost:$port/api/edit" \
        -H "Content-Type: application/json" \
        $headers \
        -d '{"file_path": "test.txt", "old_string": "World", "new_string": "Container", "replace_all": false}')
    
    if echo "$response" | grep -q '"error":null' && echo "$response" | grep -q '"occurrences":1'; then
        print_success "Edit file passed"
        return 0
    else
        print_error "Edit file failed: $response"
        return 1
    fi
}

test_grep() {
    local port=$1
    local server_name=$2
    local headers=$3
    
    print_step "Testing grep endpoint ($server_name)..."
    
    response=$(curl -s "http://localhost:$port/api/grep?pattern=Docker&path=/" $headers)
    
    if echo "$response" | grep -q '"matches"'; then
        print_success "Grep passed"
        return 0
    else
        print_error "Grep failed: $response"
        return 1
    fi
}

test_glob() {
    local port=$1
    local server_name=$2
    local headers=$3
    
    print_step "Testing glob endpoint ($server_name)..."
    
    response=$(curl -s "http://localhost:$port/api/glob?pattern=*.txt&path=/" $headers)
    
    if echo "$response" | grep -q '"files"'; then
        print_success "Glob passed"
        return 0
    else
        print_error "Glob failed: $response"
        return 1
    fi
}

test_authentication() {
    local port=$1
    
    print_step "Testing authentication (FastAPI only)..."
    
    # Test without API key (should fail)
    response=$(curl -s -w "\n%{http_code}" "http://localhost:$port/api/ls?path=/")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "401" ] || [ "$http_code" = "403" ]; then
        print_success "Authentication check passed (rejected unauthenticated request)"
        return 0
    else
        print_error "Authentication check failed (expected 401/403, got $http_code)"
        return 1
    fi
}

run_all_tests() {
    local port=$1
    local server_name=$2
    local headers=$3
    
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Testing $server_name${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    test_health_endpoint $port "$server_name" || true
    test_write_file $port "$server_name" "$headers" || true
    test_read_file $port "$server_name" "$headers" || true
    test_list_directory $port "$server_name" "$headers" || true
    test_edit_file $port "$server_name" "$headers" || true
    test_grep $port "$server_name" "$headers" || true
    test_glob $port "$server_name" "$headers" || true
}

# Main execution
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}DeepAgents FileServer Docker Test Suite${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    # Create test data directory
    print_step "Creating test data directory..."
    mkdir -p "$TEST_DATA_DIR"
    print_success "Test data directory created"
    
    # Build Docker image
    print_step "Building Docker image..."
    if docker build -t $IMAGE_NAME .; then
        print_success "Docker image built successfully"
    else
        print_error "Docker image build failed"
        exit 1
    fi
    
    # Test 1: FastAPI Server
    print_step "Starting FastAPI server container..."
    docker run -d \
        --name $CONTAINER_NAME_FASTAPI \
        -p $PORT_FASTAPI:8080 \
        -v "$(pwd)/$TEST_DATA_DIR:/data" \
        -e "FILESERVER_API_KEY=$API_KEY" \
        $IMAGE_NAME fileserver.server_fastapi /data 8080
    
    if wait_for_server $PORT_FASTAPI; then
        # Test authentication first
        test_authentication $PORT_FASTAPI || true
        
        # Run all tests with API key
        run_all_tests $PORT_FASTAPI "FastAPI Server" "-H \"X-API-Key: $API_KEY\""
        
        # Check container logs for errors
        print_step "Checking FastAPI container logs..."
        if docker logs $CONTAINER_NAME_FASTAPI 2>&1 | grep -i "error" > /dev/null; then
            print_warning "Found errors in FastAPI container logs"
        else
            print_success "No errors in FastAPI container logs"
        fi
    fi
    
    # Stop FastAPI container
    print_step "Stopping FastAPI container..."
    docker stop $CONTAINER_NAME_FASTAPI
    docker rm $CONTAINER_NAME_FASTAPI
    
    # Clean test data for next test
    rm -rf "$TEST_DATA_DIR"
    mkdir -p "$TEST_DATA_DIR"
    
    # Test 2: Standard Server
    print_step "Starting Standard server container..."
    docker run -d \
        --name $CONTAINER_NAME_STANDARD \
        -p $PORT_STANDARD:8080 \
        -v "$(pwd)/$TEST_DATA_DIR:/data" \
        $IMAGE_NAME fileserver.server /data 8080
    
    if wait_for_server $PORT_STANDARD; then
        # Run all tests without API key
        run_all_tests $PORT_STANDARD "Standard Server" ""
        
        # Check container logs for errors
        print_step "Checking Standard container logs..."
        if docker logs $CONTAINER_NAME_STANDARD 2>&1 | grep -i "error" > /dev/null; then
            print_warning "Found errors in Standard container logs"
        else
            print_success "No errors in Standard container logs"
        fi
    fi
    
    # Print summary
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Test Summary${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}Passed:${NC} $TESTS_PASSED"
    echo -e "${RED}Failed:${NC} $TESTS_FAILED"
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}✗ Some tests failed!${NC}"
        return 1
    fi
}

# Run main function
main
