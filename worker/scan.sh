#!/bin/bash
# Security Scanner Worker Script
#
# This script clones a repository, runs multiple security scanners,
# and merges their SARIF output into a single report.
#
# Required environment variables:
#   GITHUB_TOKEN - GitHub personal access token or App installation token
#   REPO_URL - Full GitHub repository URL (https://github.com/owner/repo)
#   BRANCH - Branch name to scan (default: main)
#   COMMIT_SHA - Specific commit to scan (optional)
#   SCAN_ID - Unique scan identifier for logging

set -euo pipefail

# Logging functions
log_info() {
    echo "[INFO] $(date -u +"%Y-%m-%dT%H:%M:%SZ") $*" >&2
}

log_error() {
    echo "[ERROR] $(date -u +"%Y-%m-%dT%H:%M:%SZ") $*" >&2
}

log_success() {
    echo "[SUCCESS] $(date -u +"%Y-%m-%dT%H:%M:%SZ") $*" >&2
}

# Validate required environment variables
if [ -z "${GITHUB_TOKEN:-}" ]; then
    log_error "GITHUB_TOKEN environment variable is required"
    exit 1
fi

if [ -z "${REPO_URL:-}" ]; then
    log_error "REPO_URL environment variable is required"
    exit 1
fi

# Set defaults
BRANCH="${BRANCH:-main}"
SCAN_ID="${SCAN_ID:-unknown}"
WORKSPACE="/workspace"
OUTPUT_DIR="/output"
SARIF_FILES=()

log_info "Starting security scan"
log_info "Scan ID: ${SCAN_ID}"
log_info "Repository: ${REPO_URL}"
log_info "Branch: ${BRANCH}"

# Step 1: Clone repository
log_info "Cloning repository..."
cd "${WORKSPACE}"

# Use token for authentication
REPO_WITH_AUTH=$(echo "${REPO_URL}" | sed "s|https://|https://x-access-token:${GITHUB_TOKEN}@|")

if ! git clone --depth=1 --branch="${BRANCH}" "${REPO_WITH_AUTH}" repo 2>&1; then
    log_error "Failed to clone repository"
    exit 1
fi

cd repo

# Checkout specific commit if provided
if [ -n "${COMMIT_SHA:-}" ]; then
    log_info "Checking out commit ${COMMIT_SHA}"
    git fetch --depth=1 origin "${COMMIT_SHA}"
    git checkout "${COMMIT_SHA}"
fi

REPO_PATH=$(pwd)
log_success "Repository cloned successfully"

# Step 2: Detect project type
log_info "Detecting project type..."
HAS_PYTHON=false
HAS_JAVASCRIPT=false
HAS_TYPESCRIPT=false
HAS_GO=false
HAS_JAVA=false

[ -f "requirements.txt" ] || [ -f "setup.py" ] || [ -f "pyproject.toml" ] && HAS_PYTHON=true
[ -f "package.json" ] && HAS_JAVASCRIPT=true
[ -f "tsconfig.json" ] && HAS_TYPESCRIPT=true
[ -f "go.mod" ] && HAS_GO=true
[ -f "pom.xml" ] || [ -f "build.gradle" ] && HAS_JAVA=true

log_info "Project types detected: Python=${HAS_PYTHON}, JS=${HAS_JAVASCRIPT}, TS=${HAS_TYPESCRIPT}, Go=${HAS_GO}, Java=${HAS_JAVA}"

# Step 3: Run Semgrep (Universal SAST)
log_info "Running Semgrep..."
SEMGREP_OUTPUT="${OUTPUT_DIR}/semgrep.sarif"

if semgrep scan --config=auto --sarif --output="${SEMGREP_OUTPUT}" "${REPO_PATH}" 2>&1; then
    log_success "Semgrep completed"
    SARIF_FILES+=("${SEMGREP_OUTPUT}")
else
    log_error "Semgrep failed (non-fatal)"
fi

# Step 4: Run Python-specific scanners
if [ "${HAS_PYTHON}" = true ]; then
    log_info "Running Python security scanners..."

    # Bandit (Python security)
    log_info "Running Bandit..."
    BANDIT_OUTPUT="${OUTPUT_DIR}/bandit.sarif"

    if bandit -r "${REPO_PATH}" -f sarif -o "${BANDIT_OUTPUT}" 2>&1 || true; then
        log_success "Bandit completed"
        SARIF_FILES+=("${BANDIT_OUTPUT}")
    else
        log_error "Bandit failed (non-fatal)"
    fi

    # Safety (Python dependencies)
    if [ -f "requirements.txt" ]; then
        log_info "Running Safety..."
        SAFETY_OUTPUT="${OUTPUT_DIR}/safety.json"

        if safety check --file=requirements.txt --json --output="${SAFETY_OUTPUT}" 2>&1 || true; then
            log_success "Safety completed"
            # Note: Safety outputs JSON, not SARIF (would need conversion)
        else
            log_error "Safety failed (non-fatal)"
        fi
    fi
fi

# Step 5: Run JavaScript/TypeScript scanners
if [ "${HAS_JAVASCRIPT}" = true ] || [ "${HAS_TYPESCRIPT}" = true ]; then
    log_info "Running JavaScript/TypeScript security scanners..."

    # ESLint security plugins (if package.json exists)
    if command -v npm >/dev/null 2>&1; then
        log_info "Running npm audit..."
        NPM_AUDIT_OUTPUT="${OUTPUT_DIR}/npm-audit.json"

        if npm audit --json > "${NPM_AUDIT_OUTPUT}" 2>&1 || true; then
            log_success "npm audit completed"
            # Note: npm audit outputs JSON, not SARIF (would need conversion)
        else
            log_error "npm audit failed (non-fatal)"
        fi
    fi
fi

# Step 6: Run Trivy (vulnerabilities in dependencies and containers)
log_info "Running Trivy filesystem scan..."
TRIVY_OUTPUT="${OUTPUT_DIR}/trivy.sarif"

if trivy fs --format sarif --output "${TRIVY_OUTPUT}" "${REPO_PATH}" 2>&1; then
    log_success "Trivy completed"
    SARIF_FILES+=("${TRIVY_OUTPUT}")
else
    log_error "Trivy failed (non-fatal)"
fi

# Step 7: Merge SARIF files
log_info "Merging SARIF results..."

if [ ${#SARIF_FILES[@]} -eq 0 ]; then
    log_error "No SARIF files generated"
    exit 1
fi

if [ ${#SARIF_FILES[@]} -eq 1 ]; then
    # Only one SARIF file, output directly
    log_info "Only one SARIF file, outputting directly"
    cat "${SARIF_FILES[0]}"
else
    # Merge multiple SARIF files
    log_info "Merging ${#SARIF_FILES[@]} SARIF files"
    python3 /tools/merge_sarif.py "${SARIF_FILES[@]}"
fi

log_success "Security scan completed successfully"
exit 0
