# Security Scanner Worker

Lightweight Docker container for running security scans on GitHub repositories and outputting SARIF (Static Analysis Results Interchange Format).

## Features

- **Multiple Security Scanners:**
  - **Semgrep** - Universal SAST (Static Application Security Testing)
  - **Bandit** - Python-specific security linter
  - **Trivy** - Vulnerability scanner for dependencies and containers
  - **Safety** - Python dependency vulnerability checker
  - **npm audit** - JavaScript/Node.js dependency vulnerabilities

- **Language Support:**
  - Python
  - JavaScript/TypeScript
  - Go
  - Java
  - And more (via Semgrep rules)

- **Security:**
  - Runs as non-root user
  - No persistent storage
  - Ephemeral GitHub tokens (15 min expiry)
  - Network isolation options

- **Output:**
  - SARIF 2.1.0 format
  - Merged results from all scanners
  - JSON structured output

## Building the Image

```bash
# Build the image
docker build -t security-worker:latest -f worker/Dockerfile worker/

# Build with version tag
docker build -t security-worker:1.0.0 -f worker/Dockerfile worker/

# Push to registry (optional)
docker tag security-worker:latest your-registry/security-worker:latest
docker push your-registry/security-worker:latest
```

## Running the Worker

### Basic Usage

```bash
docker run \
  -e GITHUB_TOKEN="ghp_xxxxxxxxxxxx" \
  -e REPO_URL="https://github.com/owner/repo" \
  -e BRANCH="main" \
  security-worker:latest
```

### With All Options

```bash
docker run \
  -e GITHUB_TOKEN="ghp_xxxxxxxxxxxx" \
  -e REPO_URL="https://github.com/owner/repo" \
  -e REPO_NAME="owner/repo" \
  -e BRANCH="develop" \
  -e COMMIT_SHA="abc123" \
  -e SCAN_ID="scan-uuid-here" \
  --memory="2g" \
  --cpus="2" \
  --network="none" \
  security-worker:latest > results.sarif 2> scan.log
```

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `GITHUB_TOKEN` | Yes | GitHub token for authentication | `ghp_xxxxx` or App installation token |
| `REPO_URL` | Yes | Full GitHub repository URL | `https://github.com/owner/repo` |
| `BRANCH` | No | Branch to scan (default: `main`) | `develop` |
| `COMMIT_SHA` | No | Specific commit to scan | `abc123def456` |
| `SCAN_ID` | No | Unique scan identifier for logging | `550e8400-e29b-41d4-a716-446655440000` |

### Resource Limits

Recommended resource limits (configured in Django settings):

```bash
--memory="2g"        # 2GB RAM limit
--cpus="2"           # 2 CPU cores
--network="none"     # No network after clone (optional)
```

## Output

The worker outputs SARIF to **stdout** and logs to **stderr**.

### SARIF Output (stdout)

```json
{
  "version": "2.1.0",
  "$schema": "https://...",
  "runs": [
    {
      "tool": {
        "driver": {
          "name": "Semgrep",
          "version": "1.55.0"
        }
      },
      "results": [
        {
          "ruleId": "python.lang.security.sql-injection",
          "level": "error",
          "message": {
            "text": "Possible SQL injection"
          },
          "locations": [...]
        }
      ]
    }
  ]
}
```

### Log Output (stderr)

```
[INFO] 2024-01-15T10:30:00Z Starting security scan
[INFO] 2024-01-15T10:30:00Z Scan ID: 550e8400-e29b-41d4-a716-446655440000
[INFO] 2024-01-15T10:30:00Z Repository: https://github.com/owner/repo
[INFO] 2024-01-15T10:30:00Z Branch: main
[INFO] 2024-01-15T10:30:01Z Cloning repository...
[SUCCESS] 2024-01-15T10:30:05Z Repository cloned successfully
[INFO] 2024-01-15T10:30:05Z Detecting project type...
[INFO] 2024-01-15T10:30:05Z Project types detected: Python=true, JS=false
[INFO] 2024-01-15T10:30:05Z Running Semgrep...
[SUCCESS] 2024-01-15T10:30:45Z Semgrep completed
[INFO] 2024-01-15T10:30:45Z Running Bandit...
[SUCCESS] 2024-01-15T10:30:50Z Bandit completed
[INFO] 2024-01-15T10:30:50Z Merging SARIF results...
[SUCCESS] 2024-01-15T10:30:51Z Security scan completed successfully
```

## Security Scanners Included

### Semgrep (Universal SAST)

- **What it scans:** Code patterns, security vulnerabilities, bugs
- **Languages:** Python, JavaScript, TypeScript, Go, Java, Ruby, PHP, C, C++, and more
- **Rules:** Automatic rule selection based on detected languages
- **Output:** SARIF format

### Bandit (Python Security)

- **What it scans:** Python-specific security issues
- **Languages:** Python only
- **Checks:** SQL injection, XSS, hardcoded passwords, weak crypto, etc.
- **Output:** SARIF format

### Trivy (Dependency & Container Scanner)

- **What it scans:** Dependencies, OS packages, container images
- **Languages:** All (via dependency files)
- **Checks:** Known CVEs in dependencies
- **Output:** SARIF format

### Safety (Python Dependencies)

- **What it scans:** Python package vulnerabilities
- **Languages:** Python only
- **Checks:** Known vulnerabilities in PyPI packages
- **Output:** JSON format (needs conversion to SARIF)

### npm audit (JavaScript/Node.js)

- **What it scans:** npm package vulnerabilities
- **Languages:** JavaScript/TypeScript/Node.js
- **Checks:** Known vulnerabilities in npm packages
- **Output:** JSON format (needs conversion to SARIF)

## Integration with Review-Pro

The worker is designed to be called from the Review-Pro backend via the `run_security_scan` Celery task.

### Workflow

1. User triggers scan via API
2. Django creates Scan record
3. Celery task `run_security_scan` is queued
4. Worker:
   - Generates ephemeral GitHub App token (15 min)
   - Starts Docker container with environment variables
   - Container clones repo and runs scanners
   - Outputs SARIF to stdout
5. Backend:
   - Collects SARIF output from container
   - Uploads SARIF to S3/MinIO
   - Parses SARIF and creates Finding records
   - Updates scan status

### Example Django Integration

```python
# In apps/scans/tasks.py
container = docker_client.containers.run(
    image='security-worker:latest',
    environment={
        'GITHUB_TOKEN': github_token,
        'REPO_URL': f'https://github.com/{repo.full_name}',
        'BRANCH': branch.name,
        'COMMIT_SHA': branch.sha,
        'SCAN_ID': str(scan.id)
    },
    mem_limit='2g',
    cpu_count=2,
    detach=True,
    remove=False
)

# Wait for completion
result = container.wait(timeout=1800)

# Get SARIF output
sarif_output = container.logs().decode('utf-8')
```

## Customization

### Adding New Scanners

To add a new scanner:

1. Update `Dockerfile` to install the tool
2. Update `scan.sh` to run the tool and collect SARIF output
3. Add SARIF file to `SARIF_FILES` array
4. Test the integration

Example:

```bash
# In scan.sh
log_info "Running MyScanner..."
MYSCANNER_OUTPUT="${OUTPUT_DIR}/myscanner.sarif"

if myscanner --sarif --output "${MYSCANNER_OUTPUT}" "${REPO_PATH}"; then
    log_success "MyScanner completed"
    SARIF_FILES+=("${MYSCANNER_OUTPUT}")
else
    log_error "MyScanner failed (non-fatal)"
fi
```

### Custom Semgrep Rules

You can add custom Semgrep rules by mounting a rules directory:

```bash
docker run \
  -v /path/to/rules:/custom-rules:ro \
  -e GITHUB_TOKEN="xxx" \
  -e REPO_URL="xxx" \
  security-worker:latest
```

Then modify `scan.sh` to use `--config=/custom-rules` instead of `--config=auto`.

## Troubleshooting

### Issue: "Failed to clone repository"

**Causes:**
- Invalid GitHub token
- Token doesn't have access to the repository
- Repository doesn't exist
- Branch doesn't exist

**Solution:**
- Verify GitHub token is valid and has `repo` scope
- Check repository and branch names
- Ensure token has access to private repos if needed

### Issue: "No SARIF files generated"

**Causes:**
- All scanners failed
- No code to scan
- Scanners crashed

**Solution:**
- Check stderr logs for scanner error messages
- Verify repository has code files
- Check scanner versions are compatible

### Issue: "Container timeout"

**Causes:**
- Large repository
- Slow network
- Scanner hanging

**Solution:**
- Increase timeout in Django settings (`WORKER_TIMEOUT`)
- Use `--depth=1` for shallow clones (already default)
- Check scanner logs for hangs

### Issue: "Memory limit exceeded"

**Causes:**
- Repository too large
- Scanner memory leak
- Insufficient memory limit

**Solution:**
- Increase memory limit (`WORKER_MEMORY_LIMIT`)
- Scan specific subdirectories instead of whole repo
- Use more efficient scanners

## Performance

### Benchmarks

Typical scan times for different repository sizes:

| Repo Size | Files | Duration | Memory |
|-----------|-------|----------|--------|
| Small | < 100 | 1-2 min | 500 MB |
| Medium | 100-1000 | 2-5 min | 1 GB |
| Large | 1000-10000 | 5-15 min | 2 GB |
| Very Large | > 10000 | 15-30 min | 4 GB |

### Optimization Tips

1. **Use shallow clones:** Already default (`--depth=1`)
2. **Limit scanners:** Disable scanners not relevant to your stack
3. **Use cached dependencies:** Mount npm/pip cache (if safe)
4. **Parallel scanning:** Some scanners support parallel execution
5. **Scan specific paths:** Focus on `src/` instead of entire repo

## License

Part of the Review-Pro security analysis platform.

## Support

For issues, see the main Review-Pro repository or check logs for error messages.
