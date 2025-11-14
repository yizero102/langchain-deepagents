#!/bin/bash
# Verification script for Docker setup
# Validates all Docker-related files without running containers

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

print_check() {
    echo -e "${BLUE}Checking:${NC} $1"
}

print_pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    PASSED=$((PASSED + 1))
}

print_fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    FAILED=$((FAILED + 1))
}

print_warn() {
    echo -e "${YELLOW}⚠ WARN:${NC} $1"
}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Docker Setup Verification${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check 1: Required files exist
print_check "Required Docker files exist"
if [ -f "Dockerfile" ]; then
    print_pass "Dockerfile exists"
else
    print_fail "Dockerfile is missing"
fi

if [ -f "docker-compose.yml" ]; then
    print_pass "docker-compose.yml exists"
else
    print_fail "docker-compose.yml is missing"
fi

if [ -f ".dockerignore" ]; then
    print_pass ".dockerignore exists"
else
    print_fail ".dockerignore is missing"
fi

if [ -f "test_docker.sh" ]; then
    print_pass "test_docker.sh exists"
else
    print_fail "test_docker.sh is missing"
fi

if [ -f "DOCKER.md" ]; then
    print_pass "DOCKER.md documentation exists"
else
    print_fail "DOCKER.md is missing"
fi

if [ -f ".env.example" ]; then
    print_pass ".env.example exists"
else
    print_fail ".env.example is missing"
fi

echo ""

# Check 2: Dockerfile validation
print_check "Dockerfile content validation"

if grep -q "FROM python:3.11" Dockerfile; then
    print_pass "Uses Python 3.11 base image"
else
    print_fail "Does not use Python 3.11 base image"
fi

if grep -q "fastapi>=0.104.0" Dockerfile; then
    print_pass "Includes FastAPI dependency"
else
    print_fail "Missing FastAPI dependency"
fi

if grep -q "uvicorn\[standard\]>=0.24.0" Dockerfile; then
    print_pass "Includes Uvicorn dependency"
else
    print_fail "Missing Uvicorn dependency"
fi

if grep -q "EXPOSE 8080" Dockerfile; then
    print_pass "Exposes port 8080"
else
    print_fail "Does not expose port 8080"
fi

if grep -q "HEALTHCHECK" Dockerfile; then
    print_pass "Includes health check"
else
    print_fail "Missing health check"
fi

if grep -q "fileserver.server_fastapi" Dockerfile; then
    print_pass "Default CMD uses FastAPI server"
else
    print_fail "Default CMD does not use FastAPI server"
fi

echo ""

# Check 3: docker-compose.yml validation
print_check "docker-compose.yml content validation"

if grep -q "version: '3.8'" docker-compose.yml; then
    print_pass "Uses docker-compose version 3.8"
else
    print_warn "Not using docker-compose version 3.8"
fi

if grep -q "fileserver-fastapi:" docker-compose.yml; then
    print_pass "Defines FastAPI service"
else
    print_fail "Missing FastAPI service definition"
fi

if grep -q "fileserver-standard:" docker-compose.yml; then
    print_pass "Defines Standard service"
else
    print_fail "Missing Standard service definition"
fi

if grep -q "8080:8080" docker-compose.yml; then
    print_pass "Maps port 8080"
else
    print_fail "Does not map port 8080"
fi

if grep -q "./data:/data" docker-compose.yml; then
    print_pass "Mounts data volume"
else
    print_fail "Missing data volume mount"
fi

if grep -q "healthcheck:" docker-compose.yml; then
    print_pass "Includes healthcheck configuration"
else
    print_fail "Missing healthcheck configuration"
fi

echo ""

# Check 4: .dockerignore validation
print_check ".dockerignore content validation"

if grep -q "__pycache__" .dockerignore; then
    print_pass "Ignores Python cache files"
else
    print_warn "Does not ignore __pycache__"
fi

if grep -q "\.git" .dockerignore; then
    print_pass "Ignores .git directory"
else
    print_warn "Does not ignore .git directory"
fi

if grep -q "tests" .dockerignore; then
    print_pass "Ignores test files"
else
    print_warn "Does not ignore test files"
fi

echo ""

# Check 5: Test script validation
print_check "test_docker.sh validation"

if [ -x "test_docker.sh" ]; then
    print_pass "test_docker.sh is executable"
else
    print_fail "test_docker.sh is not executable"
fi

if bash -n test_docker.sh 2>/dev/null; then
    print_pass "test_docker.sh has valid bash syntax"
else
    print_fail "test_docker.sh has syntax errors"
fi

if grep -q "test_health_endpoint" test_docker.sh; then
    print_pass "Includes health endpoint test"
else
    print_fail "Missing health endpoint test"
fi

if grep -q "test_write_file" test_docker.sh; then
    print_pass "Includes write file test"
else
    print_fail "Missing write file test"
fi

if grep -q "test_read_file" test_docker.sh; then
    print_pass "Includes read file test"
else
    print_fail "Missing read file test"
fi

if grep -q "test_authentication" test_docker.sh; then
    print_pass "Includes authentication test"
else
    print_fail "Missing authentication test"
fi

echo ""

# Check 6: Server files exist
print_check "Server implementation files"

if [ -f "fileserver/server.py" ]; then
    print_pass "fileserver/server.py exists"
else
    print_fail "fileserver/server.py is missing"
fi

if [ -f "fileserver/server_fastapi.py" ]; then
    print_pass "fileserver/server_fastapi.py exists"
else
    print_fail "fileserver/server_fastapi.py is missing"
fi

if [ -f "fileserver/__init__.py" ]; then
    print_pass "fileserver/__init__.py exists"
else
    print_fail "fileserver/__init__.py is missing"
fi

echo ""

# Check 7: Documentation
print_check "Documentation validation"

if grep -q "Docker" README.md; then
    print_pass "README.md mentions Docker"
else
    print_fail "README.md does not mention Docker"
fi

if [ -f "DOCKER.md" ]; then
    if grep -q "Quick Start" DOCKER.md; then
        print_pass "DOCKER.md includes Quick Start section"
    else
        print_warn "DOCKER.md missing Quick Start section"
    fi
    
    if grep -q "docker-compose" DOCKER.md; then
        print_pass "DOCKER.md includes docker-compose examples"
    else
        print_warn "DOCKER.md missing docker-compose examples"
    fi
    
    if grep -q "Testing" DOCKER.md; then
        print_pass "DOCKER.md includes Testing section"
    else
        print_warn "DOCKER.md missing Testing section"
    fi
fi

echo ""

# Check 8: Python module can be imported
print_check "Python module structure"

if python -c "import sys; sys.path.insert(0, '.'); from fileserver import FileServer" 2>/dev/null; then
    print_pass "FileServer can be imported"
else
    print_warn "Cannot import FileServer (dependencies may not be installed locally)"
    print_warn "This is OK - dependencies will be installed in Docker container"
fi

if python -c "import sys; sys.path.insert(0, '.'); from fileserver import FastAPIFileServer" 2>/dev/null; then
    print_pass "FastAPIFileServer can be imported"
else
    print_warn "Cannot import FastAPIFileServer (dependencies may not be installed locally)"
    print_warn "This is OK - dependencies will be installed in Docker container"
fi

echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Verification Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${RED}Failed:${NC} $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo -e "${GREEN}Docker setup is ready for deployment.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Build the image: docker build -t deepagents-fileserver ."
    echo "  2. Run with docker-compose: docker-compose up -d"
    echo "  3. Run tests: ./test_docker.sh"
    exit 0
else
    echo -e "${RED}✗ Some checks failed!${NC}"
    echo -e "${RED}Please fix the issues before deploying.${NC}"
    exit 1
fi
