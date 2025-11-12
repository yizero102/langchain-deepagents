#!/bin/bash

# Verification script for FileServer FastAPI Security & Java Client Implementation
# This script verifies all components of the implementation

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "FileServer Implementation Verification"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counter for tests
TOTAL_TESTS=0
PASSED_TESTS=0

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        ((PASSED_TESTS++))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
    fi
    ((TOTAL_TESTS++))
}

echo "1. Verifying FastAPI server code..."
if [ -f "libs/deepagents-fileserver/fileserver/fastapi_server.py" ]; then
    print_status 0 "FastAPI server file exists"
else
    print_status 1 "FastAPI server file missing"
fi

echo ""
echo "2. Verifying Java client code..."
if [ -f "libs/deepagents-fileserver-java-client/src/main/java/com/deepagents/fileserver/client/FileServerClient.java" ]; then
    print_status 0 "Java client file exists"
else
    print_status 1 "Java client file missing"
fi

echo ""
echo "3. Checking Python dependencies..."
if [ -f "libs/deepagents-fileserver/pyproject.toml" ]; then
    if grep -q "fastapi" libs/deepagents-fileserver/pyproject.toml; then
        print_status 0 "FastAPI dependency declared"
    else
        print_status 1 "FastAPI dependency missing"
    fi
    if grep -q "uvicorn" libs/deepagents-fileserver/pyproject.toml; then
        print_status 0 "Uvicorn dependency declared"
    else
        print_status 1 "Uvicorn dependency missing"
    fi
else
    print_status 1 "pyproject.toml missing"
fi

echo ""
echo "4. Checking Java build configuration..."
if [ -f "libs/deepagents-fileserver-java-client/pom.xml" ]; then
    print_status 0 "Java pom.xml exists"
    if grep -q "gson" libs/deepagents-fileserver-java-client/pom.xml; then
        print_status 0 "Gson dependency declared"
    else
        print_status 1 "Gson dependency missing"
    fi
else
    print_status 1 "Java pom.xml missing"
fi

echo ""
echo "5. Verifying test files..."
if [ -f "libs/deepagents-fileserver/tests/test_fastapi_server.py" ]; then
    print_status 0 "FastAPI tests exist"
else
    print_status 1 "FastAPI tests missing"
fi

if [ -f "libs/deepagents-fileserver/tests/test_integration_backends.py" ]; then
    print_status 0 "Integration tests exist"
else
    print_status 1 "Integration tests missing"
fi

if [ -f "libs/deepagents-fileserver-java-client/src/test/java/com/deepagents/fileserver/client/FileServerClientTest.java" ]; then
    print_status 0 "Java client tests exist"
else
    print_status 1 "Java client tests missing"
fi

echo ""
echo "6. Building Java client..."
cd libs/deepagents-fileserver-java-client
if mvn clean compile > /tmp/mvn_compile.log 2>&1; then
    print_status 0 "Java client compiles"
else
    print_status 1 "Java client compilation failed"
    cat /tmp/mvn_compile.log
fi
cd "$SCRIPT_DIR"

echo ""
echo "7. Running Python tests (without server)..."
cd libs/deepagents-fileserver
if pytest tests/test_fastapi_server.py -v --tb=short > /tmp/pytest_fastapi.log 2>&1; then
    FASTAPI_TESTS=$(grep -o "[0-9]* passed" /tmp/pytest_fastapi.log | head -1 | awk '{print $1}')
    print_status 0 "FastAPI tests pass ($FASTAPI_TESTS tests)"
else
    print_status 1 "FastAPI tests failed"
    tail -20 /tmp/pytest_fastapi.log
fi
cd "$SCRIPT_DIR"

echo ""
echo "8. Starting test server..."
mkdir -p /tmp/fileserver-verify-test
rm -rf /tmp/fileserver-verify-test/*
python -c "from fileserver.fastapi_server import SecureFileServer; server = SecureFileServer('/tmp/fileserver-verify-test', '0.0.0.0', 8081, enable_auth=False); server.start()" > /tmp/fileserver_test.log 2>&1 &
SERVER_PID=$!
sleep 3

echo "9. Verifying server is running..."
if curl -s http://localhost:8081/health | grep -q "ok"; then
    print_status 0 "Server health check responds"
else
    print_status 1 "Server health check failed"
fi

echo ""
echo "10. Running integration tests..."
cd libs/deepagents-fileserver
if pytest tests/test_integration_backends.py -v --tb=short > /tmp/pytest_integration.log 2>&1; then
    INTEGRATION_TESTS=$(grep -o "[0-9]* passed" /tmp/pytest_integration.log | head -1 | awk '{print $1}')
    print_status 0 "Integration tests pass ($INTEGRATION_TESTS tests)"
else
    print_status 1 "Integration tests failed"
    tail -20 /tmp/pytest_integration.log
fi
cd "$SCRIPT_DIR"

echo ""
echo "11. Running Java client tests..."
cd libs/deepagents-fileserver-java-client
# Update test to use port 8081
sed -i 's/8080/8081/g' src/test/java/com/deepagents/fileserver/client/FileServerClientTest.java
if mvn test > /tmp/mvn_test.log 2>&1; then
    JAVA_TESTS=$(grep -o "Tests run: [0-9]*" /tmp/mvn_test.log | head -1 | awk '{print $3}')
    print_status 0 "Java client tests pass ($JAVA_TESTS tests)"
else
    print_status 1 "Java client tests failed"
    tail -30 /tmp/mvn_test.log
fi
# Restore original port
sed -i 's/8081/8080/g' src/test/java/com/deepagents/fileserver/client/FileServerClientTest.java
cd "$SCRIPT_DIR"

echo ""
echo "12. Stopping test server..."
kill $SERVER_PID 2>/dev/null || true
sleep 1
print_status 0 "Test server stopped"

echo ""
echo "13. Verifying documentation..."
if [ -f "libs/deepagents-fileserver/README.md" ]; then
    print_status 0 "FileServer README exists"
else
    print_status 1 "FileServer README missing"
fi

if [ -f "libs/deepagents-fileserver-java-client/README.md" ]; then
    print_status 0 "Java client README exists"
else
    print_status 1 "Java client README missing"
fi

if [ -f "FILESERVER_FASTAPI_SECURITY_JAVA_CLIENT_IMPLEMENTATION.md" ]; then
    print_status 0 "Implementation summary exists"
else
    print_status 1 "Implementation summary missing"
fi

echo ""
echo "=========================================="
echo "Verification Summary"
echo "=========================================="
echo -e "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$((TOTAL_TESTS - PASSED_TESTS))${NC}"
echo ""

if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo -e "${GREEN}✓ All verifications passed!${NC}"
    echo ""
    echo "Summary of test counts:"
    echo "  - FastAPI Tests: ${FASTAPI_TESTS:-N/A}"
    echo "  - Integration Tests: ${INTEGRATION_TESTS:-N/A}"
    echo "  - Java Client Tests: ${JAVA_TESTS:-N/A}"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some verifications failed${NC}"
    exit 1
fi
