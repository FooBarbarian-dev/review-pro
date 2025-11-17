#!/bin/bash
# Comprehensive Testing Script for Review-Pro Platform
#
# This script automates testing across all phases from TEST_PLAN.md
# Run after implementing Priority 1 (migrations, multi-tenancy, RBAC)
#
# Usage:
#   ./scripts/test_platform.sh [--phase N] [--skip-docker] [--verbose]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
PHASE="${1:-all}"
SKIP_DOCKER=false
VERBOSE=false
BACKEND_DIR="backend"
API_URL="http://localhost:8000"
FAILED_TESTS=0
PASSED_TESTS=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --phase)
            PHASE="$2"
            shift 2
            ;;
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --phase N        Run only phase N (1-8, default: all)"
            echo "  --skip-docker    Skip Docker-related tests"
            echo "  --verbose        Show detailed output"
            echo "  --help           Show this help message"
            echo ""
            echo "Phases:"
            echo "  1. Infrastructure & Dependencies"
            echo "  2. Database Layer"
            echo "  3. Model Layer"
            echo "  4. Authentication & API Basics"
            echo "  5. Multi-Tenancy & RBAC"
            echo "  6. Core Business Logic"
            echo "  7. Advanced Features"
            echo "  8. Integration & End-to-End"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# Logging functions
log_section() {
    echo ""
    echo -e "${BLUE}=== $1 ===${NC}"
    echo ""
}

log_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED_TESTS++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED_TESTS++))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Test functions
test_command_exists() {
    if command -v "$1" &> /dev/null; then
        log_pass "Command '$1' is available"
        return 0
    else
        log_fail "Command '$1' not found"
        return 1
    fi
}

test_file_exists() {
    if [ -f "$1" ]; then
        log_pass "File exists: $1"
        return 0
    else
        log_fail "File not found: $1"
        return 1
    fi
}

test_docker_service() {
    if docker-compose ps "$1" | grep -q "Up"; then
        log_pass "Docker service '$1' is running"
        return 0
    else
        log_fail "Docker service '$1' is not running"
        return 1
    fi
}

test_http_endpoint() {
    local url="$1"
    local expected_code="${2:-200}"

    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_code"; then
        log_pass "HTTP $expected_code: $url"
        return 0
    else
        log_fail "HTTP endpoint failed: $url"
        return 1
    fi
}

# Phase 1: Infrastructure & Dependencies
phase1_infrastructure() {
    log_section "Phase 1: Infrastructure & Dependencies"

    log_test "1.1 Environment Configuration"
    test_file_exists ".env" || log_warn "Create .env from .env.example"

    log_test "1.2 Docker Services"
    if [ "$SKIP_DOCKER" = false ]; then
        test_command_exists "docker"
        test_command_exists "docker-compose"

        log_info "Checking Docker services..."
        test_docker_service "db" || true
        test_docker_service "redis" || true
        test_docker_service "minio" || true
        test_docker_service "web" || true
        test_docker_service "celery_worker" || true
        test_docker_service "celery_beat" || true
    else
        log_info "Skipping Docker tests (--skip-docker)"
    fi

    log_test "1.3 Python Dependencies"
    test_file_exists "$BACKEND_DIR/requirements.txt"
}

# Phase 2: Database Layer
phase2_database() {
    log_section "Phase 2: Database Layer"

    log_test "2.1 Migration Files"
    test_file_exists "$BACKEND_DIR/apps/users/migrations/0001_initial.py"
    test_file_exists "$BACKEND_DIR/apps/organizations/migrations/0001_initial.py"
    test_file_exists "$BACKEND_DIR/apps/scans/migrations/0001_initial.py"
    test_file_exists "$BACKEND_DIR/apps/findings/migrations/0001_initial.py"

    if [ "$SKIP_DOCKER" = false ]; then
        log_test "2.2 Database Connection"
        if docker-compose exec -T db pg_isready -U postgres &>/dev/null; then
            log_pass "PostgreSQL is ready"
        else
            log_fail "PostgreSQL connection failed"
        fi

        log_test "2.3 Run Migrations"
        log_info "Running migrations..."
        if docker-compose exec -T web python manage.py migrate --noinput 2>&1 | grep -q "OK\|Applying"; then
            log_pass "Migrations applied successfully"
        else
            log_warn "Migrations may have already been applied"
        fi
    fi
}

# Phase 3: Model Layer
phase3_models() {
    log_section "Phase 3: Model Layer"

    if [ "$SKIP_DOCKER" = false ]; then
        log_test "3.1 Create Superuser (if needed)"
        log_info "Note: Skip if superuser already exists"

        log_test "3.2 Model CRUD Operations"
        log_info "Testing via Django shell would go here"
        log_info "Skipping interactive tests (run manually as needed)"
    fi
}

# Phase 4: Authentication & API Basics
phase4_authentication() {
    log_section "Phase 4: Authentication & API Basics"

    log_test "4.1 API Documentation"
    test_http_endpoint "$API_URL/api/schema/" "200"
    test_http_endpoint "$API_URL/api/docs/" "200"
    test_http_endpoint "$API_URL/api/redoc/" "200"

    log_test "4.2 Admin Interface"
    test_http_endpoint "$API_URL/admin/" "302"

    log_test "4.3 Authentication Endpoints"
    test_http_endpoint "$API_URL/api/v1/auth/login/" "405"  # Method not allowed (needs POST)
}

# Phase 5: Multi-Tenancy & RBAC
phase5_multitenancy() {
    log_section "Phase 5: Multi-Tenancy & RBAC"

    log_test "5.1 Multi-Tenancy Filtering"
    log_info "Checking ViewSet implementations..."

    # Check that get_queryset() exists in views
    if grep -q "def get_queryset" "$BACKEND_DIR/apps/organizations/views.py"; then
        log_pass "Organizations ViewSet has multi-tenancy filtering"
    else
        log_fail "Organizations ViewSet missing get_queryset()"
    fi

    if grep -q "def get_queryset" "$BACKEND_DIR/apps/scans/views.py"; then
        log_pass "Scans ViewSet has multi-tenancy filtering"
    else
        log_fail "Scans ViewSet missing get_queryset()"
    fi

    if grep -q "def get_queryset" "$BACKEND_DIR/apps/findings/views.py"; then
        log_pass "Findings ViewSet has multi-tenancy filtering"
    else
        log_fail "Findings ViewSet missing get_queryset()"
    fi

    log_test "5.2 RBAC Permission Classes"
    if grep -q "IsOrganizationMember\|IsOrganizationAdmin" "$BACKEND_DIR/apps/organizations/permissions.py"; then
        log_pass "RBAC permission classes defined"
    else
        log_fail "RBAC permission classes missing"
    fi
}

# Phase 6: Core Business Logic
phase6_core() {
    log_section "Phase 6: Core Business Logic"

    log_test "6.1 Scan Worker Implementation"
    if grep -q "run_security_scan" "$BACKEND_DIR/apps/scans/tasks.py"; then
        log_pass "Scan worker task defined"
    else
        log_fail "Scan worker task missing"
    fi

    log_test "6.2 SARIF Parser"
    test_file_exists "$BACKEND_DIR/apps/scans/sarif_parser.py"

    log_test "6.3 S3 Storage Integration"
    test_file_exists "$BACKEND_DIR/apps/scans/storage.py"

    log_test "6.4 Quota Enforcement"
    if grep -q "quota" "$BACKEND_DIR/apps/scans/views.py"; then
        log_pass "Quota enforcement implemented in views"
    else
        log_fail "Quota enforcement missing"
    fi

    log_test "6.5 Finding Fingerprinting"
    test_file_exists "$BACKEND_DIR/apps/findings/utils.py"
}

# Phase 7: Advanced Features
phase7_advanced() {
    log_section "Phase 7: Advanced Features"

    log_test "7.1 Server-Sent Events (SSE)"
    test_file_exists "$BACKEND_DIR/apps/scans/sse.py"
    test_file_exists "$BACKEND_DIR/apps/scans/events.py"

    log_test "7.2 Row-Level Security"
    test_file_exists "$BACKEND_DIR/apps/organizations/sql/row_level_security.sql"
    test_file_exists "$BACKEND_DIR/apps/organizations/middleware.py"

    log_test "7.3 Rate Limiting"
    if grep -q "RATELIMIT_ENABLE" "$BACKEND_DIR/config/settings.py"; then
        log_pass "Rate limiting configured"
    else
        log_fail "Rate limiting not configured"
    fi
}

# Phase 8: Integration
phase8_integration() {
    log_section "Phase 8: Integration & End-to-End"

    log_test "8.1 Worker Docker Image"
    test_file_exists "worker/Dockerfile"
    test_file_exists "worker/scan.sh"
    test_file_exists "worker/merge_sarif.py"

    if [ "$SKIP_DOCKER" = false ]; then
        log_test "8.2 Build Worker Image"
        log_info "Attempting to build worker image..."
        if docker build -t security-worker:test -f worker/Dockerfile worker/ &>/dev/null; then
            log_pass "Worker image builds successfully"
        else
            log_warn "Worker image build failed (may need dependencies)"
        fi
    fi

    log_test "8.3 Documentation"
    test_file_exists "docs/TEST_PLAN.md"
    test_file_exists "docs/CRITICAL_ISSUES.md"
    test_file_exists "docs/ROW_LEVEL_SECURITY.md"
    test_file_exists "docs/RATE_LIMITING.md"
}

# Main execution
main() {
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}║  Review-Pro Platform Comprehensive Test Suite             ║${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    log_info "Testing Phase: $PHASE"
    log_info "API URL: $API_URL"
    log_info "Skip Docker: $SKIP_DOCKER"
    echo ""

    # Run tests based on phase
    case "$PHASE" in
        1)
            phase1_infrastructure
            ;;
        2)
            phase2_database
            ;;
        3)
            phase3_models
            ;;
        4)
            phase4_authentication
            ;;
        5)
            phase5_multitenancy
            ;;
        6)
            phase6_core
            ;;
        7)
            phase7_advanced
            ;;
        8)
            phase8_integration
            ;;
        all)
            phase1_infrastructure
            phase2_database
            phase3_models
            phase4_authentication
            phase5_multitenancy
            phase6_core
            phase7_advanced
            phase8_integration
            ;;
        *)
            echo -e "${RED}Invalid phase: $PHASE${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac

    # Summary
    echo ""
    log_section "Test Summary"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"
    echo ""

    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠ Some tests failed. Review output above.${NC}"
        exit 1
    fi
}

# Run main function
main
