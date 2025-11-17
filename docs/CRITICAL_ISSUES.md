# Critical Issues - LLM Implementation Priorities

**Generated:** 2025-11-14
**Status:** AI-Generated Code Audit Results

---

## Overview

This document summarizes the critical issues discovered during the comprehensive audit of the Review-Pro security analysis platform. All code is AI-generated and has never been executed. Issues are prioritized based on their blocking impact on core functionality.

---

## Priority 1: Blocking Basic Functionality (MUST FIX FIRST)

### 1. Database Migrations Missing ⛔️

**Status:** Not created
**Impact:** Application cannot run
**Location:** `backend/apps/*/migrations/`

**Issue:**
- No migration files exist for any app
- Database schema cannot be created
- Application will fail on startup

**Action Required:**
```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

**Expected LLM Work:**
- Fix any model definition errors that prevent migration generation
- Resolve field type issues
- Fix missing `default` values for non-nullable fields
- Resolve circular dependencies between apps

---

### 2. Multi-Tenancy Filtering Not Implemented ⛔️

**Status:** Critical security issue
**Impact:** Users can see data from all organizations
**Location:** `backend/apps/*/views.py`

**Issue:**
- ViewSets do not filter querysets by organization
- Users can access resources from organizations they don't belong to
- Violates core security requirement (ADR-001)

**Files to Fix:**
- `backend/apps/organizations/views.py`
- `backend/apps/scans/views.py`
- `backend/apps/findings/views.py`

**Required Implementation:**
```python
# Example fix needed in each ViewSet
class RepositoryViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        # Filter by user's organization memberships
        user_orgs = self.request.user.organization_memberships.values_list(
            'organization_id', flat=True
        )
        return Repository.objects.filter(organization_id__in=user_orgs)
```

**Test Plan:** See Test Plan Phase 5.2

---

### 3. RBAC Permission Classes Not Applied ⛔️

**Status:** Partially implemented, not enforced
**Impact:** Authorization bypass
**Location:** `backend/apps/*/permissions.py`, `backend/apps/*/views.py`

**Issue:**
- Permission classes defined but not applied to ViewSets
- No role-based action restrictions
- Viewers can create/delete resources

**Files to Fix:**
- `backend/apps/organizations/permissions.py` - Verify implementation
- `backend/apps/scans/views.py` - Apply `IsOrganizationMember`
- `backend/apps/findings/views.py` - Apply `IsOrganizationMember`

**Required Implementation:**
```python
# Apply to all ViewSets
class ScanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get_permissions(self):
        # Admin-only actions
        if self.action in ['destroy']:
            return [IsAuthenticated(), IsOrganizationAdmin()]
        return super().get_permissions()
```

**Test Plan:** See Test Plan Phase 5.3

---

## Priority 2: Blocking Core Features (FIX NEXT)

### 4. Scan Worker Not Implemented ⛔️

**Status:** Placeholder code with TODO
**Impact:** Cannot execute security scans (core feature)
**Location:** `backend/apps/scans/tasks.py:52-89`

**Issue:**
- `run_security_scan()` task only logs "Scan started"
- No Docker container execution
- No GitHub repository cloning
- No SARIF collection

**Current Code:**
```python
@shared_task
def run_security_scan(scan_id):
    """Execute a security scan in a Docker container (ADR-004)."""
    # TODO: Implement actual scan execution
    # 1. Create ephemeral GitHub App token
    # 2. Start Docker container with security tools
    # 3. Run scan and collect SARIF output
    # 4. Upload SARIF to S3
    # 5. Parse SARIF and create findings
    # 6. Update scan status
```

**Required Implementation:**
1. GitHub App token generation (see issue #11)
2. Docker SDK integration (see issue #10)
3. Container orchestration with resource limits
4. SARIF output collection
5. Integration with SARIF parser (see issue #5)
6. Error handling and timeout management

**Dependencies:**
- Docker SDK package (already in requirements)
- GitHub App credentials configured
- SARIF parser implemented
- S3 storage integration

**Estimated Complexity:** High (4-6 hours of LLM work)
**Test Plan:** See Test Plan Phase 7.1

---

### 5. SARIF Parser Not Implemented ⛔️

**Status:** Does not exist
**Impact:** Cannot process scan results
**Location:** Need to create `backend/apps/scans/sarif_parser.py`

**Issue:**
- No SARIF file parsing logic
- No finding extraction from SARIF
- No fingerprint generation (ADR-002)

**Required Implementation:**

Create new file `backend/apps/scans/sarif_parser.py`:

```python
class SARIFParser:
    """Parse SARIF files and extract findings (ADR-005)."""

    def parse_file(self, sarif_path):
        """Parse SARIF file and return structured data."""
        pass

    def extract_findings(self, sarif_data, scan, organization, repository):
        """Extract findings and create Finding objects."""
        pass

    def generate_fingerprint(self, rule_id, file_path, line, message):
        """Generate deterministic fingerprint (ADR-002)."""
        # Implement SHA-256 hash of: rule_id + file_path + line + message_hash
        pass

    def deduplicate_finding(self, fingerprint, organization):
        """Handle finding deduplication."""
        pass
```

**Key Requirements:**
- SARIF v2.1.0 schema support
- Extract: rule_id, severity, file_path, line numbers, message
- Generate fingerprints per ADR-002
- Handle malformed SARIF gracefully
- Support multiple SARIF tools

**Dependencies:**
- Finding model (already exists)
- Fingerprint deduplication logic

**Estimated Complexity:** Medium (3-4 hours of LLM work)
**Test Plan:** See Test Plan Phase 7.2

---

### 6. S3/MinIO Storage Integration Incomplete ⛔️

**Status:** Settings configured, no implementation
**Impact:** Cannot store/retrieve SARIF files
**Location:** Need to create `backend/apps/scans/storage.py`

**Issue:**
- No SARIF upload to S3/MinIO
- No presigned URL generation for downloads
- No file size tracking for quotas

**Required Implementation:**

Create new file `backend/apps/scans/storage.py`:

```python
import boto3
from django.conf import settings

class SARIFStorage:
    """Handle SARIF file storage in S3/MinIO (ADR-005)."""

    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.bucket = settings.SARIF_BUCKET_NAME

    def upload_sarif(self, scan_id, sarif_content):
        """Upload SARIF file to S3."""
        pass

    def get_presigned_url(self, file_path, expiry=3600):
        """Generate presigned URL for SARIF download."""
        pass

    def delete_sarif(self, file_path):
        """Delete SARIF file from S3."""
        pass

    def get_file_size(self, file_path):
        """Get SARIF file size for quota tracking."""
        pass
```

**API Integration:**

Fix `backend/apps/scans/views.py`:

```python
@action(detail=True, methods=['get'])
def sarif(self, request, pk=None):
    """Download SARIF file via presigned URL."""
    scan = self.get_object()
    if not scan.sarif_file_path:
        return Response({'error': 'No SARIF file available'}, status=404)

    storage = SARIFStorage()
    url = storage.get_presigned_url(scan.sarif_file_path)
    return Response({'download_url': url})
```

**Dependencies:**
- boto3 package (already in requirements)
- MinIO/S3 running and accessible
- Environment variables configured

**Estimated Complexity:** Low-Medium (2-3 hours of LLM work)
**Test Plan:** See Test Plan Phase 7.2

---

### 7. Quota Enforcement Not Implemented ⛔️

**Status:** QuotaUsage model exists, not enforced
**Impact:** Users can exceed quotas
**Location:** `backend/apps/scans/views.py`

**Issue:**
- No validation before scan creation
- No quota check in API endpoint
- No quota exceeded error handling

**Required Implementation:**

Fix `backend/apps/scans/views.py`:

```python
class ScanViewSet(viewsets.ModelViewSet):
    def perform_create(self, serializer):
        organization = serializer.validated_data['repository'].organization

        # Check scan quota
        from apps.scans.models import QuotaUsage
        from django.utils import timezone

        now = timezone.now()
        quota, _ = QuotaUsage.objects.get_or_create(
            organization=organization,
            year=now.year,
            month=now.month,
            defaults={'scans_used': 0, 'storage_used_bytes': 0}
        )

        if quota.scans_used >= organization.scan_quota_monthly:
            raise ValidationError({
                'error': 'Scan quota exceeded',
                'quota': organization.scan_quota_monthly,
                'used': quota.scans_used
            })

        # Create scan
        scan = serializer.save(triggered_by=self.request.user)

        # Trigger async scan task
        from apps.scans.tasks import run_security_scan
        run_security_scan.delay(str(scan.id))
```

**Additional Quota Checks:**
- Storage quota before SARIF upload
- Organization active check
- Plan limits enforcement

**Estimated Complexity:** Low (1-2 hours of LLM work)
**Test Plan:** See Test Plan Phase 6.3

---

### 8. Finding Fingerprint Generation Missing ⛔️

**Status:** Manual fingerprint only
**Impact:** No automatic deduplication
**Location:** `backend/apps/findings/utils.py` (need to create)

**Issue:**
- Fingerprint must be manually provided
- No automatic generation per ADR-002
- Deduplication logic not implemented

**ADR-002 Requirements:**

Fingerprint = SHA-256(rule_id + file_path + start_line + column + message_hash)

**Required Implementation:**

Create `backend/apps/findings/utils.py`:

```python
import hashlib

def generate_finding_fingerprint(rule_id, file_path, start_line, column, message):
    """Generate deterministic fingerprint for finding (ADR-002)."""
    # Normalize inputs
    normalized_path = file_path.strip().lower()
    message_hash = hashlib.sha256(message.encode('utf-8')).hexdigest()[:16]

    # Create fingerprint components
    components = [
        rule_id,
        normalized_path,
        str(start_line),
        str(column or 0),
        message_hash
    ]

    # Generate SHA-256 hash
    fingerprint_data = '|'.join(components)
    fingerprint = hashlib.sha256(fingerprint_data.encode('utf-8')).hexdigest()

    return fingerprint

def deduplicate_finding(fingerprint, organization):
    """Check for existing finding with same fingerprint."""
    from apps.findings.models import Finding

    existing = Finding.objects.filter(
        organization=organization,
        fingerprint=fingerprint,
        status__in=['open', 'in_review']  # Don't dedupe resolved findings
    ).first()

    return existing
```

**Model Integration:**

Update `backend/apps/findings/models.py`:

```python
class Finding(models.Model):
    # ... existing fields ...

    def save(self, *args, **kwargs):
        # Auto-generate fingerprint if not provided
        if not self.fingerprint:
            from apps.findings.utils import generate_finding_fingerprint
            self.fingerprint = generate_finding_fingerprint(
                self.rule_id,
                self.file_path,
                self.start_line,
                self.column,
                self.message
            )
        super().save(*args, **kwargs)
```

**Estimated Complexity:** Low (1-2 hours of LLM work)
**Test Plan:** See Test Plan Phase 6.5

---

## Priority 3: Advanced Features (FIX AFTER CORE WORKS)

### 9. Row-Level Security Policies Not Created ⚠️

**Status:** Not implemented
**Impact:** Database-level multi-tenancy not enforced
**Location:** Need SQL migration file

**Issue:**
- ADR-001 specifies RLS for defense-in-depth
- No PostgreSQL RLS policies created
- Relying only on application-level filtering

**Required Implementation:**

Create migration `backend/apps/organizations/migrations/0002_row_level_security.py`:

```python
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('organizations', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- Enable RLS on organizations table
                ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;

                -- Policy: Users can only see orgs they're members of
                CREATE POLICY org_member_policy ON organizations
                FOR ALL
                USING (
                    id IN (
                        SELECT organization_id
                        FROM organization_memberships
                        WHERE user_id = current_setting('app.current_user_id')::uuid
                    )
                );

                -- Similar policies for other tables...
            """,
            reverse_sql="""
                DROP POLICY IF EXISTS org_member_policy ON organizations;
                ALTER TABLE organizations DISABLE ROW LEVEL SECURITY;
            """
        ),
    ]
```

**Challenges:**
- Setting `current_user_id` in PostgreSQL session
- Handling superuser bypass
- Testing RLS enforcement

**Note:** This is optional for MVP but recommended for production.

**Estimated Complexity:** Medium (3-4 hours of LLM work)
**Test Plan:** See Test Plan Phase 2.3.3

---

### 10. Server-Sent Events (SSE) Not Implemented ⚠️

**Status:** Not implemented
**Impact:** No real-time scan updates
**Location:** Need to create SSE views

**Issue:**
- ADR-003 specifies SSE for real-time updates
- No SSE endpoints exist
- No Redis pub/sub integration

**Required Implementation:**

Create `backend/apps/scans/sse.py`:

```python
from django.http import StreamingHttpResponse
import json
import redis

def scan_event_stream(request, scan_id):
    """SSE endpoint for scan status updates."""
    redis_client = redis.from_url(settings.REDIS_URL)
    pubsub = redis_client.pubsub()
    channel = f'scan:{scan_id}:events'
    pubsub.subscribe(channel)

    def event_generator():
        for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                yield f"data: {json.dumps(data)}\n\n"

    response = StreamingHttpResponse(
        event_generator(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
```

**Publish Events from Worker:**

```python
# In run_security_scan task
def publish_event(scan_id, event_type, data):
    redis_client = redis.from_url(settings.REDIS_URL)
    channel = f'scan:{scan_id}:events'
    event = {'type': event_type, 'data': data}
    redis_client.publish(channel, json.dumps(event))

# Usage
publish_event(scan_id, 'status_update', {'status': 'running'})
publish_event(scan_id, 'finding_discovered', {'finding_id': str(finding.id)})
```

**Estimated Complexity:** Medium (2-3 hours of LLM work)
**Test Plan:** See Test Plan Phase 7.4

---

### 11. GitHub App Integration Not Implemented ⚠️

**Status:** Settings exist, no implementation
**Impact:** Cannot generate ephemeral tokens for workers
**Location:** Need to create `backend/apps/scans/github_app.py`

**Issue:**
- Worker needs GitHub App tokens (ADR-004)
- No token generation logic
- No GitHub App authentication

**Required Implementation:**

Create `backend/apps/scans/github_app.py`:

```python
import jwt
import time
import requests
from django.conf import settings

class GitHubAppAuth:
    """Generate ephemeral GitHub App tokens (ADR-004)."""

    def generate_app_token(self):
        """Generate JWT for GitHub App authentication."""
        payload = {
            'iat': int(time.time()),
            'exp': int(time.time()) + 600,  # 10 min expiry
            'iss': settings.GITHUB_APP_ID
        }

        token = jwt.encode(
            payload,
            settings.GITHUB_APP_PRIVATE_KEY,
            algorithm='RS256'
        )
        return token

    def generate_installation_token(self, installation_id):
        """Generate installation access token (15 min expiry)."""
        app_token = self.generate_app_token()

        url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
        headers = {
            'Authorization': f'Bearer {app_token}',
            'Accept': 'application/vnd.github+json'
        }

        response = requests.post(url, headers=headers)
        response.raise_for_status()

        return response.json()['token']  # Valid for 15 minutes
```

**Integration with Worker:**

```python
# In run_security_scan task
github_auth = GitHubAppAuth()
ephemeral_token = github_auth.generate_installation_token(
    settings.GITHUB_APP_INSTALLATION_ID
)

# Pass to Docker container
container = docker_client.containers.run(
    environment={'GITHUB_TOKEN': ephemeral_token},
    # ...
)
```

**Dependencies:**
- PyJWT package (already in requirements)
- GitHub App created and configured
- Private key in environment

**Estimated Complexity:** Low-Medium (2-3 hours of LLM work)
**Test Plan:** See Test Plan Phase 7.3

---

### 12. Docker Container Execution Not Implemented ⚠️

**Status:** Placeholder
**Impact:** Cannot run security scans
**Location:** `backend/apps/scans/tasks.py`

**Issue:**
- No Docker SDK usage
- No container orchestration
- No resource limits enforced

**Required Implementation:**

Update `backend/apps/scans/tasks.py`:

```python
import docker
from django.conf import settings

@shared_task
def run_security_scan(scan_id):
    """Execute security scan in Docker container (ADR-004)."""
    from apps.scans.models import Scan, ScanLog
    from apps.scans.github_app import GitHubAppAuth
    from apps.scans.storage import SARIFStorage
    from apps.scans.sarif_parser import SARIFParser

    try:
        scan = Scan.objects.select_related('repository', 'branch').get(id=scan_id)
        scan.status = 'running'
        scan.save()

        # 1. Generate GitHub token
        github_auth = GitHubAppAuth()
        github_token = github_auth.generate_installation_token(
            settings.GITHUB_APP_INSTALLATION_ID
        )

        # 2. Start Docker container
        docker_client = docker.from_env()
        container = docker_client.containers.run(
            image=settings.WORKER_DOCKER_IMAGE,
            environment={
                'GITHUB_TOKEN': github_token,
                'REPO_URL': f'https://github.com/{scan.repository.full_name}',
                'BRANCH': scan.branch.name,
                'COMMIT_SHA': scan.branch.sha
            },
            mem_limit=settings.WORKER_MEMORY_LIMIT,
            cpu_count=settings.WORKER_CPU_LIMIT,
            network_mode='none',  # No network access during scan
            detach=True,
            remove=False  # Keep for log collection
        )

        # 3. Wait for completion (with timeout)
        result = container.wait(timeout=settings.WORKER_TIMEOUT)

        if result['StatusCode'] != 0:
            raise Exception(f"Container exited with code {result['StatusCode']}")

        # 4. Collect SARIF output
        sarif_content = container.logs().decode('utf-8')

        # 5. Upload to S3
        storage = SARIFStorage()
        sarif_path = storage.upload_sarif(scan_id, sarif_content)

        # 6. Parse SARIF and create findings
        parser = SARIFParser()
        findings_created = parser.extract_findings(
            sarif_content,
            scan,
            scan.organization,
            scan.repository
        )

        # 7. Update scan status
        scan.status = 'completed'
        scan.sarif_file_path = sarif_path
        scan.sarif_file_size = len(sarif_content.encode('utf-8'))
        scan.findings_count = findings_created
        scan.save()

        # 8. Cleanup
        container.remove()

        # 9. Update quota
        update_quota_usage.delay(str(scan.organization_id), str(scan.id))

    except Exception as e:
        logger.error(f"Scan {scan_id} failed: {e}")
        scan.status = 'failed'
        scan.error_message = str(e)
        scan.save()
        raise
```

**Security Requirements (ADR-004):**
- Resource limits (CPU, memory)
- Network isolation during scan
- Short-lived GitHub tokens (15 min)
- No persistent storage access

**Estimated Complexity:** High (4-6 hours of LLM work)
**Test Plan:** See Test Plan Phase 7.3

---

## Summary Statistics

| Priority | Issues | Est. Time | Blocking |
|----------|--------|-----------|----------|
| **Priority 1** | 3 | 6-10 hours | Complete blocker |
| **Priority 2** | 5 | 16-24 hours | Feature blocker |
| **Priority 3** | 4 | 13-19 hours | Enhancement |
| **TOTAL** | **12** | **35-53 hours** | - |

---

## Recommended Implementation Order

### Phase 1: Get Basic App Running (Priority 1)
1. Generate and apply database migrations ✅
2. Fix multi-tenancy filtering in all ViewSets ✅
3. Apply and test RBAC permission classes ✅

**Checkpoint:** Basic API works with proper security

---

### Phase 2: Implement Core Scanning (Priority 2)
4. Implement finding fingerprint generation ✅
5. Create SARIF parser service ✅
6. Add S3/MinIO storage integration ✅
7. Implement quota enforcement in API ✅
8. Implement scan worker with Docker execution ✅

**Checkpoint:** Can execute scans and store results

---

### Phase 3: Polish & Advanced Features (Priority 3)
9. Add GitHub App token generation ✅
10. Implement Server-Sent Events for real-time updates ✅
11. Create Row-Level Security policies ✅
12. Rate limiting verification ✅

**Checkpoint:** Production-ready platform

---

## Testing Strategy

For each issue fix:

1. **Unit Test:** Test the component in isolation
2. **Integration Test:** Test with related components
3. **API Test:** Test via HTTP endpoints
4. **Manual Test:** Verify in browser/curl

Refer to **TEST_PLAN.md** for detailed testing procedures.

---

## Notes for LLM Implementation Sessions

### Session 1: Database & Security (Priority 1)
**Goal:** Get basic app running with proper security

**Prompt for LLM:**
```
Fix the following issues in the Django security analysis platform:

1. Generate database migrations for all apps
2. Implement multi-tenancy filtering in ViewSets (filter by user's organization memberships)
3. Apply RBAC permission classes (IsOrganizationMember, IsOrganizationAdmin) to all ViewSets

Test each fix to ensure it works. Refer to ADR-001 for multi-tenancy requirements and ADR-007 for RBAC requirements.
```

**Validation:**
- All migrations apply successfully
- Users can only see their own organization's data
- Role-based permissions are enforced

---

### Session 2: SARIF & Storage (Priority 2, Part 1)
**Goal:** Implement SARIF processing pipeline

**Prompt for LLM:**
```
Implement SARIF processing for the security analysis platform:

1. Create SARIFParser class to parse SARIF v2.1.0 files and extract findings
2. Implement finding fingerprint generation per ADR-002 (SHA-256 of rule_id + file_path + line + message_hash)
3. Create SARIFStorage class for S3/MinIO upload/download with presigned URLs
4. Add automatic fingerprint generation to Finding model save method

Test with a sample SARIF file. Ensure deduplication works correctly.
```

**Validation:**
- SARIF files parse correctly
- Findings extracted with correct fingerprints
- Files upload to MinIO successfully
- Presigned URLs work for downloads

---

### Session 3: Scan Worker (Priority 2, Part 2)
**Goal:** Implement actual scan execution

**Prompt for LLM:**
```
Implement the security scan worker:

1. Create GitHubAppAuth class to generate ephemeral installation tokens (15 min expiry)
2. Implement Docker container execution in run_security_scan task with:
   - Resource limits (CPU, memory)
   - Network isolation
   - SARIF output collection
3. Integrate with SARIFParser and SARIFStorage
4. Add quota enforcement before scan creation
5. Update scan status and findings count after completion

Test with a mock scan. Ensure error handling works for container failures.
```

**Validation:**
- Docker containers execute with proper limits
- SARIF collected and processed
- Quota checked before scan
- Errors handled gracefully

---

### Session 4: Real-Time & Polish (Priority 3)
**Goal:** Add advanced features

**Prompt for LLM:**
```
Implement advanced features:

1. Create SSE endpoint for real-time scan status updates using Redis pub/sub
2. Publish events from scan worker (status changes, findings discovered)
3. Create Row-Level Security policies for PostgreSQL (optional)
4. Test rate limiting configuration

Verify SSE works by connecting with curl and triggering a scan.
```

**Validation:**
- SSE streams work correctly
- Events publish from worker
- RLS policies enforce isolation (if implemented)
- Rate limits trigger correctly

---

## Risk Assessment

| Issue | Risk Level | Impact if Not Fixed |
|-------|-----------|---------------------|
| Database migrations | 🔴 Critical | App won't start |
| Multi-tenancy filtering | 🔴 Critical | Data leakage, security breach |
| RBAC permissions | 🔴 Critical | Authorization bypass |
| Scan worker | 🔴 Critical | Core feature doesn't work |
| SARIF parser | 🟠 High | Can't process scan results |
| S3 storage | 🟠 High | Can't store SARIF files |
| Quota enforcement | 🟠 High | Resource abuse |
| Fingerprinting | 🟡 Medium | No deduplication |
| GitHub App auth | 🟡 Medium | Can't access repos |
| SSE | 🟢 Low | No real-time updates (UX issue) |
| RLS policies | 🟢 Low | Missing defense-in-depth |
| Rate limiting | 🟢 Low | Missing abuse protection |

---

## Success Criteria

**MVP Definition:** Minimum viable product that can:
- ✅ Accept user registrations and logins
- ✅ Create organizations and manage members
- ✅ Add GitHub repositories
- ✅ Trigger security scans
- ✅ Execute scans in Docker containers
- ✅ Process SARIF results
- ✅ Display findings with proper multi-tenancy
- ✅ Enforce quotas
- ✅ Manage finding status and comments

**MVP Excludes:**
- ❌ Real-time SSE updates (can use polling)
- ❌ Row-Level Security (app-level filtering sufficient)
- ❌ Advanced rate limiting (basic protection OK)

---

## Appendix: Quick Reference

### Key Files to Fix

**Priority 1:**
- `backend/apps/*/migrations/` - Generate migrations
- `backend/apps/*/views.py` - Add `get_queryset()` filtering
- `backend/apps/*/views.py` - Add permission classes

**Priority 2:**
- `backend/apps/findings/utils.py` - NEW: Fingerprint generation
- `backend/apps/scans/sarif_parser.py` - NEW: SARIF parser
- `backend/apps/scans/storage.py` - NEW: S3 storage
- `backend/apps/scans/tasks.py` - Complete scan worker
- `backend/apps/scans/views.py` - Add quota enforcement

**Priority 3:**
- `backend/apps/scans/github_app.py` - NEW: GitHub App auth
- `backend/apps/scans/sse.py` - NEW: SSE views
- `backend/apps/organizations/migrations/0002_rls.py` - NEW: RLS policies

### Environment Setup Required

```bash
# Required for testing
GITHUB_APP_ID=your-app-id
GITHUB_APP_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----
GITHUB_APP_INSTALLATION_ID=your-installation-id

WORKER_DOCKER_IMAGE=security-worker:latest
WORKER_TIMEOUT=1800
WORKER_MEMORY_LIMIT=2g
WORKER_CPU_LIMIT=2

USE_S3=True
AWS_S3_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
SARIF_BUCKET_NAME=sarif-files
```

---

**Document Version:** 1.0
**Last Updated:** 2025-11-14
