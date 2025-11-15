# Security Scanner Worker Dockerfile
# Lightweight container for running security scans and outputting SARIF
#
# Usage:
#   docker build -t security-worker:latest -f worker/Dockerfile worker/
#   docker run -e GITHUB_TOKEN=xxx -e REPO_URL=xxx security-worker:latest

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 scanner && \
    mkdir -p /workspace /output && \
    chown -R scanner:scanner /workspace /output

# Install security scanning tools
WORKDIR /tools

# Install Semgrep (SAST)
RUN pip install semgrep==1.55.0

# Install Bandit (Python security)
RUN pip install bandit[sarif]==1.7.6

# Install Safety (Python dependency vulnerabilities)
RUN pip install safety==3.0.1

# Install Trivy (Container/dependency scanner)
RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin v0.48.3

# Copy scanner scripts
COPY --chown=scanner:scanner scan.sh /tools/scan.sh
COPY --chown=scanner:scanner merge_sarif.py /tools/merge_sarif.py
RUN chmod +x /tools/scan.sh

# Switch to non-root user
USER scanner

# Set working directory
WORKDIR /workspace

# Run scanner script
ENTRYPOINT ["/tools/scan.sh"]
