#!/bin/bash

# Validation script for DeepAgents Java Backends
# This script runs all tests and generates a comprehensive report

set -e

echo "=================================="
echo "DeepAgents Backend Validation"
echo "=================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Navigate to Java backends directory
cd "$(dirname "$0")"

echo "1. Cleaning previous build artifacts..."
mvn clean > /dev/null 2>&1
echo -e "${GREEN}✓ Clean complete${NC}"
echo ""

echo "2. Compiling Java sources..."
mvn compile > /dev/null 2>&1
echo -e "${GREEN}✓ Compilation successful${NC}"
echo ""

echo "3. Running comprehensive test suite..."
echo ""

# Run tests with detailed output
TEST_OUTPUT=$(mvn test 2>&1)
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    # Extract test statistics
    TOTAL_TESTS=$(echo "$TEST_OUTPUT" | grep "Tests run:" | tail -1 | sed 's/.*Tests run: \([0-9]*\).*/\1/')
    FAILURES=$(echo "$TEST_OUTPUT" | grep "Tests run:" | tail -1 | sed 's/.*Failures: \([0-9]*\).*/\1/')
    ERRORS=$(echo "$TEST_OUTPUT" | grep "Tests run:" | tail -1 | sed 's/.*Errors: \([0-9]*\).*/\1/')
    
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Test Summary:"
    echo "  Total Tests: ${TOTAL_TESTS}"
    echo "  Failures: ${FAILURES}"
    echo "  Errors: ${ERRORS}"
    echo ""
    
    # Show individual test class results
    echo "Test Results by Backend:"
    echo "$TEST_OUTPUT" | grep "Tests run:" | grep "in com.deepagents.backends" | while read line; do
        CLASS=$(echo "$line" | sed 's/.*in \(.*\)/\1/')
        COUNT=$(echo "$line" | sed 's/.*Tests run: \([0-9]*\).*/\1/')
        echo -e "  ${GREEN}✓${NC} $CLASS: $COUNT tests"
    done
    echo ""
    
    echo -e "${GREEN}Backend implementations verified successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "  - Review COMPREHENSIVE_TEST_REPORT.md for detailed analysis"
    echo "  - Check individual test files for specific test coverage"
    echo "  - Run 'mvn test -Dtest=<TestClass>' for focused testing"
    
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}✗ TESTS FAILED${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Test output:"
    echo "$TEST_OUTPUT"
    exit 1
fi

echo ""
echo "=================================="
echo "Validation Complete"
echo "=================================="
