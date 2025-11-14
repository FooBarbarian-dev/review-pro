#!/bin/bash
# Comprehensive test runner script for backend and frontend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Running Comprehensive Test Suite"
echo "=========================================="
echo ""

# Function to print section headers
print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
    echo ""
}

# Function to check exit code
check_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2 passed${NC}"
        return 0
    else
        echo -e "${RED}✗ $2 failed${NC}"
        return 1
    fi
}

# Change to backend directory
cd "$(dirname "$0")/../backend"

# Backend Tests
print_header "Backend Tests (Django + pytest)"

echo "Running backend unit tests..."
if docker compose exec -T web pytest -v -m unit --cov-report= 2>/dev/null; then
    check_result 0 "Backend unit tests"
else
    # Try running directly if not in Docker
    pytest -v -m unit --cov-report= || check_result $? "Backend unit tests"
fi

echo ""
echo "Running backend API tests..."
if docker compose exec -T web pytest -v -m api --cov-append --cov-report= 2>/dev/null; then
    check_result 0 "Backend API tests"
else
    pytest -v -m api --cov-append --cov-report= || check_result $? "Backend API tests"
fi

echo ""
echo "Running full backend test suite with coverage..."
if docker compose exec -T web pytest --cov=apps --cov=services --cov=api --cov-report=term-missing --cov-report=html --cov-report=json --cov-branch 2>/dev/null; then
    check_result 0 "Backend full test suite"
    BACKEND_RESULT=0
else
    pytest --cov=apps --cov=services --cov=api --cov-report=term-missing --cov-report=html --cov-report=json --cov-branch || BACKEND_RESULT=$?
    check_result $BACKEND_RESULT "Backend full test suite"
fi

# Frontend Tests
cd ../frontend

print_header "Frontend Tests (React + Vitest)"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}⚠ Installing frontend dependencies...${NC}"
    npm install
fi

echo "Running frontend tests with coverage..."
if npm run test:coverage -- --run; then
    check_result 0 "Frontend tests"
    FRONTEND_RESULT=0
else
    FRONTEND_RESULT=$?
    check_result $FRONTEND_RESULT "Frontend tests"
fi

# Summary
cd ..
print_header "Test Summary"

echo "Backend Coverage Report: backend/htmlcov/index.html"
echo "Backend Coverage JSON: backend/coverage.json"
echo "Frontend Coverage Report: frontend/coverage/index.html"
echo ""

if [ ${BACKEND_RESULT:-1} -eq 0 ] && [ ${FRONTEND_RESULT:-1} -eq 0 ]; then
    echo -e "${GREEN}=========================================="
    echo -e "✓ All tests passed!"
    echo -e "==========================================${NC}"
    exit 0
else
    echo -e "${RED}=========================================="
    echo -e "✗ Some tests failed"
    echo -e "==========================================${NC}"
    exit 1
fi
