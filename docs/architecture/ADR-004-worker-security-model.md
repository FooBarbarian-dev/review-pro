# ADR-004: Worker Security Model

**Status:** Accepted
**Date:** 2025-11-13
**Deciders:** Engineering Team, Security Team
**Technical Story:** Secure execution of security scans on untrusted code

## Context and Problem Statement

Our platform analyzes customer codebases by cloning repositories and running security scanners. This involves:

1. **Executing untrusted code:** Static analyzers may trigger code (e.g., build scripts, linters with plugins)
2. **Accessing private repositories:** Need credentials to clone customer repos
3. **Resource consumption:** Malicious repos could DoS our workers
4. **Data isolation:** Must prevent cross-contamination between customer scans

Key decisions:
- Should workers run in isolated containers or bare metal?
- How do workers authenticate to private repositories?
- How do we limit resource consumption?
- How do we handle credential rotation and expiration?

## Decision Drivers

- **Security:** Prevent arbitrary code execution from compromising infrastructure
- **Isolation:** Ensure customer data never leaks between scans
- **Least privilege:** Workers should have minimal permissions
- **Auditability:** Track all repository access for compliance
- **Scalability:** Support thousands of concurrent scans
- **Cost:** Balance security with infrastructure costs

## Considered Options

### Option 1: Bare Metal Workers with Process Isolation

Run scan workers as regular processes on shared VMs, isolated via OS-level process limits.

**Pros:**
- Simpler deployment (no container orchestration)
- Lower overhead (no container runtime)
- Faster startup time

**Cons:**
- ❌ **CRITICAL SECURITY RISK:** Shared filesystem, network, and kernel
- ❌ Escape from process limits is trivial for malicious code
- ❌ No guarantee of clean state between scans
- ❌ Resource limits (ulimit) easily bypassed
- ❌ Shared temp directories risk data leakage

**Verdict:** Unacceptable for untrusted code execution.

### Option 2: Docker Containers per Scan

Spawn ephemeral Docker container for each scan, destroyed after completion.

```python
import docker

client = docker.from_env()
container = client.containers.run(
    image='security-scanner:latest',
    environment={
        'REPO_URL': repo_url,
        'GITHUB_TOKEN': token,  # Ephemeral token
    },
    mem_limit='2g',
    cpu_quota=50000,  # 50% of 1 CPU
    network_mode='none',  # No network access
    read_only=True,
    remove=True,  # Auto-remove after exit
    detach=True
)
```

**Pros:**
- ✅ Filesystem isolation (ephemeral container filesystem)
- ✅ Resource limits enforced by cgroups
- ✅ Clean state per scan
- ✅ Mature tooling (Docker, containerd)
- ✅ Can disable network after repo clone

**Cons:**
- Container escape vulnerabilities exist (though rare)
- Kernel is still shared (privileged containers could escape)
- Requires Docker daemon (adds attack surface)

### Option 3: Firecracker MicroVMs

Use AWS Firecracker to run each scan in a lightweight VM with KVM isolation.

**Pros:**
- ✅ True hardware virtualization (KVM)
- ✅ Kernel-level isolation (guest kernel is isolated)
- ✅ Fast startup (~150ms)
- ✅ Very lightweight (5MB memory overhead)
- ✅ Used by AWS Lambda (battle-tested)

**Cons:**
- More complex setup than Docker
- Requires KVM support (bare metal or nested virtualization)
- Smaller ecosystem than Docker
- Higher operational complexity

### Option 4: gVisor (User-Space Kernel)

Use gVisor to run containers with a user-space kernel, providing defense-in-depth.

**Pros:**
- ✅ Syscall filtering prevents kernel exploits
- ✅ Works with Docker/containerd (drop-in runtime)
- ✅ Better isolation than standard containers
- ✅ No nested virtualization required

**Cons:**
- Performance overhead (syscall interception)
- Compatibility issues with some applications
- Less mature than Docker/Firecracker

## Decision Outcome

**Chosen option:** Option 2 - Docker containers per scan with defense-in-depth security layers.

### Justification

1. **Sufficient isolation for our threat model:** Container escapes are rare and require sophisticated exploits
2. **Mature ecosystem:** Docker is well-understood, widely deployed, and has extensive tooling
3. **Easier to operate than Firecracker:** Lower barrier to entry for team
4. **Defense-in-depth mitigations:** We layer additional controls (see Implementation Strategy)
5. **Cost-effective:** Runs on standard VMs without KVM requirement

**Future consideration:** Migrate to Firecracker for ultimate isolation if we onboard high-security customers (government, defense contractors).

### Implementation Strategy

#### 1. Container Image Design

```dockerfile
# Dockerfile for scan worker
FROM python:3.11-slim

# Run as non-root user
RUN useradd -m -u 1000 scanner
USER scanner

# Install security tools
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Install static analysis tools
RUN pip install bandit semgrep safety

# Set read-only filesystem (worker writes to /tmp only)
VOLUME /tmp

# Entrypoint script
COPY scan_entrypoint.sh /usr/local/bin/
ENTRYPOINT ["/usr/local/bin/scan_entrypoint.sh"]
```

#### 2. Worker Orchestration (Celery + Docker)

```python
# workers/scan_worker.py
from celery import shared_task
import docker
from datetime import timedelta
from django.utils import timezone
import secrets

@shared_task
def run_security_scan(scan_id):
    scan = Scan.objects.get(id=scan_id)
    project = scan.project

    # Generate ephemeral GitHub App installation token (15 min TTL)
    github_token = generate_github_app_token(
        project.github_installation_id,
        ttl=timedelta(minutes=15)
    )

    # Create Docker client
    client = docker.from_env()

    # Generate unique container name
    container_name = f"scan_{scan_id}_{secrets.token_hex(8)}"

    try:
        # Run scan in isolated container
        container = client.containers.run(
            image=settings.SCANNER_IMAGE,
            name=container_name,
            environment={
                'REPO_URL': project.repo_url,
                'BRANCH': scan.branch.name,
                'COMMIT_SHA': scan.commit_sha,
                'GITHUB_TOKEN': github_token,  # Ephemeral token
                'SCAN_ID': str(scan_id),
                'REDIS_URL': settings.REDIS_URL,  # For publishing progress
            },

            # Resource limits
            mem_limit='4g',            # 4GB RAM limit
            memswap_limit='4g',        # No swap
            cpu_quota=200000,          # 2 CPU cores (200% of 1 core)
            pids_limit=1024,           # Max 1024 processes
            storage_opt={'size': '10G'},  # Max 10GB disk

            # Security settings
            security_opt=['no-new-privileges'],  # Prevent privilege escalation
            cap_drop=['ALL'],          # Drop all capabilities
            cap_add=['CHOWN', 'DAC_OVERRIDE'],  # Only needed caps
            read_only=True,            # Read-only filesystem
            tmpfs={'/tmp': 'size=2G'},  # Writable /tmp (2GB limit)

            # Network isolation (disabled after clone)
            network_mode='bridge',     # Will disable after clone

            # Detach and auto-remove
            detach=True,
            remove=True,               # Auto-remove when stopped
            auto_remove=True,
        )

        # Wait for container to complete (with timeout)
        exit_code = container.wait(timeout=3600)  # 1 hour max

        # Get logs for debugging
        logs = container.logs().decode('utf-8')

        if exit_code['StatusCode'] != 0:
            raise Exception(f"Scan failed with exit code {exit_code['StatusCode']}")

        # Mark scan as completed
        scan.status = 'completed'
        scan.completed_at = timezone.now()
        scan.save()

    except docker.errors.ContainerError as e:
        # Container exited with non-zero status
        scan.status = 'failed'
        scan.error_message = str(e)
        scan.save()
        raise

    except docker.errors.APIError as e:
        # Docker API error
        scan.status = 'failed'
        scan.error_message = f"Docker error: {str(e)}"
        scan.save()
        raise

    finally:
        # Revoke GitHub token (best effort)
        try:
            revoke_github_app_token(github_token)
        except Exception:
            pass  # Token expires anyway
```

#### 3. Private Repository Access: GitHub App Installation Tokens

**Chosen approach:** GitHub App with installation access tokens (not personal access tokens).

**Why GitHub Apps:**
- ✅ Fine-grained permissions (read-only repository access)
- ✅ Scoped to specific repositories/organizations
- ✅ Short-lived tokens (default 1 hour, we use 15 minutes)
- ✅ Audit trail (all clones logged in GitHub audit log)
- ✅ Revocable at any time
- ✅ No user impersonation (separate "bot" identity)

**Token lifecycle:**
1. User installs GitHub App on their org/repos
2. We store `installation_id` in `projects` table
3. At scan time, generate installation token:
   ```python
   POST https://api.github.com/app/installations/{installation_id}/access_tokens
   {
     "repositories": ["repo-name"],
     "permissions": {"contents": "read"},
     "expires_at": "2024-11-13T12:30:00Z"  # 15 min from now
   }
   ```
4. Pass token to container as `GITHUB_TOKEN` env var
5. Container clones: `git clone https://x-access-token:${GITHUB_TOKEN}@github.com/org/repo.git`
6. After scan, revoke token (or let it expire)

**Security benefits:**
- Token is valid for 15 minutes only
- Token can't be reused after scan completes
- Token is scoped to single repository
- Token never persisted to disk/database
- If container is compromised, token expires quickly

#### 4. Network Isolation Strategy

```python
# In scan_entrypoint.sh (inside container)
#!/bin/bash
set -e

# Clone repository (network required)
git clone https://x-access-token:${GITHUB_TOKEN}@github.com/${REPO} /workspace
cd /workspace
git checkout ${COMMIT_SHA}

# Disable network access after clone
# (requires container to be run with NET_ADMIN capability for iptables)
# Alternative: Let orchestrator disable network via Docker API

# Run scans (no network needed for static analysis)
bandit -r . -f json -o /tmp/bandit.json
semgrep --config auto --json -o /tmp/semgrep.json
safety check --json > /tmp/safety.json

# Upload results to S3 or publish to Redis
# (requires network re-enabled by orchestrator)
python /usr/local/bin/upload_results.py
```

**Better approach:** Orchestrator disables network after detecting clone completion:

```python
# Wait for clone to complete (detect by log message)
for log in container.logs(stream=True):
    if b"Clone completed" in log:
        # Disable network
        client.networks.disconnect('bridge', container)
        break
```

#### 5. Secrets Management

**Never store credentials in database** (except encrypted GitHub App private key).

```python
# Store GitHub App private key in AWS Secrets Manager / HashiCorp Vault
from aws_secretsmanager import get_secret

GITHUB_APP_PRIVATE_KEY = get_secret('prod/github-app/private-key')

def generate_github_app_token(installation_id, ttl):
    # Generate JWT from App ID + private key
    jwt_token = create_jwt(
        app_id=settings.GITHUB_APP_ID,
        private_key=GITHUB_APP_PRIVATE_KEY,
        expiration=timedelta(minutes=10)
    )

    # Exchange JWT for installation token
    response = requests.post(
        f'https://api.github.com/app/installations/{installation_id}/access_tokens',
        headers={'Authorization': f'Bearer {jwt_token}'},
        json={
            'permissions': {'contents': 'read'},
            'expires_at': (timezone.now() + ttl).isoformat()
        }
    )

    return response.json()['token']  # Short-lived installation token
```

#### 6. Resource Limits & Anti-DoS

```python
# Per-organization concurrent scan limit
MAX_CONCURRENT_SCANS_PER_ORG = 5

@shared_task
def run_security_scan(scan_id):
    scan = Scan.objects.select_related('project').get(id=scan_id)
    org_id = scan.project.org_id

    # Check concurrent scan limit
    running_scans = Scan.objects.filter(
        project__org_id=org_id,
        status='running'
    ).count()

    if running_scans >= MAX_CONCURRENT_SCANS_PER_ORG:
        scan.status = 'queued'
        scan.save()
        raise self.retry(countdown=30)  # Retry in 30 seconds

    # Proceed with scan...
```

**Container-level limits** (already shown above):
- CPU: 2 cores max
- Memory: 4GB max
- Disk: 10GB max
- Processes: 1024 max
- Execution time: 1 hour max

**Worker pool limits:**
- Dedicated worker pool for scans (isolated from API workers)
- Max N concurrent scan workers (based on infrastructure capacity)
- Queue-based backpressure (Celery queue length limits)

#### 7. Audit Logging

```python
# Log all scan executions
import structlog

logger = structlog.get_logger()

@shared_task
def run_security_scan(scan_id):
    scan = Scan.objects.select_related('project').get(id=scan_id)

    logger.info(
        "scan_started",
        scan_id=str(scan_id),
        org_id=str(scan.project.org_id),
        repo_url=scan.project.repo_url,
        branch=scan.branch.name,
        commit_sha=scan.commit_sha,
        container_image=settings.SCANNER_IMAGE,
    )

    try:
        # ... run scan ...

        logger.info(
            "scan_completed",
            scan_id=str(scan_id),
            findings_count=findings_count,
            duration_seconds=duration,
        )
    except Exception as e:
        logger.error(
            "scan_failed",
            scan_id=str(scan_id),
            error=str(e),
        )
        raise
```

**Audit log requirements for compliance:**
- Which organization triggered scan
- Which repository was accessed
- What GitHub token was used (token ID, not value)
- When token was created and revoked
- Container exit code and logs
- Resource usage (CPU, memory, duration)

## Consequences

### Positive

- **Strong isolation:** Container escapes are rare and difficult
- **Resource limits enforced:** cgroups prevent DoS attacks
- **Clean state per scan:** No cross-contamination between customer data
- **Ephemeral credentials:** GitHub tokens expire in 15 minutes
- **Audit trail:** All repository access logged
- **Defense-in-depth:** Multiple security layers (non-root, read-only FS, capability dropping, network isolation)

### Negative

- **Container overhead:** ~100MB memory per container, slight CPU overhead
- **Operational complexity:** Requires Docker orchestration (Kubernetes or simple Docker API)
- **Container escape risk:** Rare but possible; mitigated by multiple security layers
- **Shared kernel:** All containers share host kernel (Firecracker would eliminate this)

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Container escape vulnerability | Keep Docker/kernel updated; use read-only FS; drop capabilities; run as non-root |
| Malicious repo DoS (fork bomb, zip bomb) | Resource limits (pids, memory, CPU, disk, time); rate limiting per org |
| Credential leak from container logs | Never log tokens; sanitize logs; encrypt logs at rest |
| Compromised worker node | Principle of least privilege (worker nodes can't access DB directly); network segmentation |
| GitHub token abuse | Short TTL (15 min); revoke after use; scope to single repo; audit all access |

## Related Decisions

- **ADR-003:** Real-time communication (workers publish progress via Redis)
- **ADR-005:** SARIF storage (workers upload results to S3)
- **ADR-007:** Authentication (GitHub App installation flow)
- **ADR-008:** Rate limiting (per-org concurrent scan limits)

## References

- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [GitHub Apps Documentation](https://docs.github.com/en/apps)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [AWS Firecracker](https://firecracker-microvm.github.io/)
- [gVisor Documentation](https://gvisor.dev/docs/)
- [Linux Capabilities](https://man7.org/linux/man-pages/man7/capabilities.7.html)
