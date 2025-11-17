# Comprehensive Testing Guide

This guide provides step-by-step instructions for testing the Review-Pro platform after implementing Priority 1 (migrations, multi-tenancy, RBAC).

## Quick Start

### Automated Testing

```bash
# Run all tests
./scripts/test_platform.sh

# Run specific phase
./scripts/test_platform.sh --phase 1

# Run without Docker
./scripts/test_platform.sh --skip-docker

# Verbose output
./scripts/test_platform.sh --verbose
```

### Manual Testing

Follow this guide for comprehensive manual testing.

---

## Prerequisites

Before starting:

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Update critical values in .env
# - SECRET_KEY (generate new)
# - GITHUB_CLIENT_ID/SECRET (optional for initial tests)
# - Database credentials

# 3. Start services
docker-compose up -d

# 4. Wait for services to be ready
sleep 10

# 5. Run migrations
docker-compose exec web python manage.py migrate

# 6. Create superuser
docker-compose exec web python manage.py createsuperuser
# Email: admin@example.com
# Password: (choose secure password)
```

---

## Phase 1: Infrastructure & Dependencies

### 1.1 Environment Configuration

```bash
# Check all required variables exist
grep -E "SECRET_KEY|DATABASE_URL|REDIS_URL" .env

# Verify they're not placeholder values
```

**Expected:** All variables defined with actual values.

### 1.2 Docker Services

```bash
# Check all services are running
docker-compose ps

# Expected services:
# - db (PostgreSQL 15)
# - redis (Redis 7)
# - minio (MinIO)
# - web (Django)
# - celery_worker
# - celery_beat
```

**Test each service:**

```bash
# PostgreSQL
docker-compose exec db pg_isready -U postgres
# Expected: "accepting connections"

# Redis
docker-compose exec redis redis-cli ping
# Expected: "PONG"

# MinIO
curl -I http://localhost:9000/minio/health/live
# Expected: HTTP 200

# Django
docker-compose logs web | tail -20
# Expected: No critical errors

# Celery Worker
docker-compose logs celery_worker | tail -10
# Expected: "[INFO/MainProcess] ready."
```

### 1.3 Python Dependencies

```bash
# List installed packages
docker-compose exec web pip list

# Verify critical packages
docker-compose exec web python -c "import django; print(django.VERSION)"
docker-compose exec web python -c "import rest_framework"
docker-compose exec web python -c "import celery"
```

**Expected:** All imports succeed without errors.

---

## Phase 2: Database Layer

### 2.1 Verify Migrations

```bash
# Check migration files exist
ls -la backend/apps/users/migrations/
ls -la backend/apps/organizations/migrations/
ls -la backend/apps/scans/migrations/
ls -la backend/apps/findings/migrations/

# Check migration status
docker-compose exec web python manage.py showmigrations

# Expected: All migrations show [X] (applied)
```

### 2.2 Verify Database Schema

```bash
# Connect to database
docker-compose exec db psql -U postgres -d secanalysis

# List all tables
\dt

# Expected tables:
# - users
# - organizations
# - organization_memberships
# - repositories
# - branches
# - scans
# - scan_logs
# - quota_usage
# - findings
# - finding_comments
# - finding_status_history
# - auth_* (Django auth tables)
```

**Check specific table structure:**

```sql
-- Check organizations table
\d organizations

-- Verify UUID primary key
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'organizations'
AND column_name = 'id';

-- Expected: id | uuid
```

### 2.3 Test Database Constraints

```sql
-- Test unique constraint on organization slug
INSERT INTO organizations (id, name, slug, plan)
VALUES (gen_random_uuid(), 'Test Org', 'test-org', 'free');

-- Try duplicate (should fail)
INSERT INTO organizations (id, name, slug, plan)
VALUES (gen_random_uuid(), 'Another Org', 'test-org', 'free');

-- Expected: ERROR: duplicate key value violates unique constraint

-- Cleanup
DELETE FROM organizations WHERE slug = 'test-org';
```

---

## Phase 3: Model Layer

### 3.1 Django Shell Tests

```bash
# Open Django shell
docker-compose exec web python manage.py shell
```

**Test User creation:**

```python
from apps.users.models import User

# Create user
user = User.objects.create_user(
    email='test@example.com',
    password='testpass123',
    first_name='Test',
    last_name='User'
)

print(f"Created user: {user.id}, {user.email}")
# Expected: UUID and email

# Verify user exists
assert User.objects.filter(email='test@example.com').exists()
print("✓ User created successfully")
```

**Test Organization creation:**

```python
from apps.organizations.models import Organization, OrganizationMembership

# Create organization
org = Organization.objects.create(
    name='Test Organization',
    slug='test-org',
    plan='free',
    scan_quota_monthly=100,
    storage_quota_gb=10
)

print(f"Created org: {org.id}, {org.name}")

# Create membership
membership = OrganizationMembership.objects.create(
    organization=org,
    user=user,
    role='owner'
)

print(f"Created membership: {membership.id}, Role: {membership.role}")

# Test permission method
assert membership.has_permission('billing') == True
assert membership.has_permission('read') == True
print("✓ Membership permissions working")
```

**Test Repository creation:**

```python
from apps.organizations.models import Repository, Branch

# Create repository
repo = Repository.objects.create(
    organization=org,
    github_repo_id='12345',
    name='test-repo',
    full_name='test-org/test-repo',
    default_branch='main'
)

print(f"Created repo: {repo.id}, {repo.full_name}")

# Create branch
branch = Branch.objects.create(
    repository=repo,
    name='main',
    sha='abc123def456',
    is_default=True
)

print(f"Created branch: {branch.id}, {branch.name}")

# Verify relationships
assert org.repositories.count() == 1
assert repo.branches.count() == 1
print("✓ Relationships working correctly")
```

**Test Scan creation:**

```python
from apps.scans.models import Scan, ScanLog, QuotaUsage
from django.utils import timezone

# Create scan
scan = Scan.objects.create(
    organization=org,
    repository=repo,
    branch=branch,
    status='pending',
    triggered_by=user
)

print(f"Created scan: {scan.id}, Status: {scan.status}")

# Create scan log
log = ScanLog.objects.create(
    scan=scan,
    level='info',
    message='Test log message'
)

print(f"Created log: {log.id}")

# Create quota
quota = QuotaUsage.objects.create(
    organization=org,
    year=2025,
    month=11,
    scans_used=5,
    storage_used_bytes=1024*1024*500  # 500 MB
)

print(f"Quota: {quota.scans_used} scans, {quota.storage_used_gb:.2f} GB")
print("✓ Scan models working correctly")
```

**Test Finding creation:**

```python
from apps.findings.models import Finding, FindingComment

# Create finding
finding = Finding.objects.create(
    organization=org,
    repository=repo,
    first_seen_scan=scan,
    last_seen_scan=scan,
    rule_id='SEC-001',
    severity='high',
    status='open',
    file_path='src/main.py',
    start_line=42,
    start_column=1,
    message='Potential SQL injection vulnerability',
    tool_name='Semgrep'
)

print(f"Created finding: {finding.id}, Fingerprint: {finding.fingerprint}")

# Verify auto-generated fingerprint
assert finding.fingerprint is not None
assert len(finding.fingerprint) == 64  # SHA-256 hex
print("✓ Fingerprint auto-generated correctly")

# Create comment
comment = FindingComment.objects.create(
    finding=finding,
    author=user,
    content='This needs immediate attention'
)

print(f"Created comment: {comment.id}")
print("✓ Finding models working correctly")

# Exit shell
exit()
```

---

## Phase 4: Authentication & API Basics

### 4.1 Admin Interface

```bash
# Navigate to http://localhost:8000/admin
# Login with superuser credentials

# Verify:
# - Can see all models
# - Can create/edit/delete records
# - No 500 errors
```

### 4.2 API Documentation

```bash
# OpenAPI schema
curl http://localhost:8000/api/schema/ | jq . | head -20

# Swagger UI
open http://localhost:8000/api/docs/

# ReDoc
open http://localhost:8000/api/redoc/
```

**Expected:** Valid JSON schema, interactive docs load.

### 4.3 JWT Authentication

```bash
# Login
TOKEN_RESPONSE=$(curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "your-password"
  }')

echo "$TOKEN_RESPONSE" | jq .

# Extract access token
ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access')
REFRESH_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.refresh')

# Test authenticated endpoint
curl http://localhost:8000/api/v1/auth/me/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

# Expected: User details

# Test refresh token
curl -X POST http://localhost:8000/api/v1/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d "{\"refresh\": \"$REFRESH_TOKEN\"}" | jq .

# Expected: New access token
```

---

## Phase 5: Multi-Tenancy & RBAC

### 5.1 Create Test Scenario

```bash
# Django shell
docker-compose exec web python manage.py shell
```

```python
from apps.users.models import User
from apps.organizations.models import Organization, OrganizationMembership, Repository

# Create user1 in org A
user1 = User.objects.create_user(email='user1@test.com', password='test123')
org_a = Organization.objects.create(name='Org A', slug='org-a')
OrganizationMembership.objects.create(organization=org_a, user=user1, role='owner')

# Create user2 in org B
user2 = User.objects.create_user(email='user2@test.com', password='test123')
org_b = Organization.objects.create(name='Org B', slug='org-b')
OrganizationMembership.objects.create(organization=org_b, user=user2, role='owner')

# Create repository in each org
repo_a = Repository.objects.create(
    organization=org_a,
    github_repo_id='repo-a',
    name='repo-a',
    full_name='org-a/repo-a'
)

repo_b = Repository.objects.create(
    organization=org_b,
    github_repo_id='repo-b',
    name='repo-b',
    full_name='org-b/repo-b'
)

print("✓ Test scenario created")
exit()
```

### 5.2 Test Multi-Tenancy Isolation

```bash
# Login as user1
TOKEN1=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user1@test.com", "password": "test123"}' \
  | jq -r '.access')

# List repositories - should only see repo-a
curl -s http://localhost:8000/api/v1/repositories/ \
  -H "Authorization: Bearer $TOKEN1" | jq '.results[].name'

# Expected: Only "repo-a"

# Login as user2
TOKEN2=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user2@test.com", "password": "test123"}' \
  | jq -r '.access')

# List repositories - should only see repo-b
curl -s http://localhost:8000/api/v1/repositories/ \
  -H "Authorization: Bearer $TOKEN2" | jq '.results[].name'

# Expected: Only "repo-b"
```

### 5.3 Test RBAC

```bash
# Create test users with different roles
docker-compose exec web python manage.py shell
```

```python
from apps.users.models import User
from apps.organizations.models import Organization, OrganizationMembership

org = Organization.objects.get(slug='test-org')

owner = User.objects.create_user(email='owner@test.com', password='test')
admin = User.objects.create_user(email='admin@test.com', password='test')
member = User.objects.create_user(email='member@test.com', password='test')
viewer = User.objects.create_user(email='viewer@test.com', password='test')

OrganizationMembership.objects.create(organization=org, user=owner, role='owner')
OrganizationMembership.objects.create(organization=org, user=admin, role='admin')
OrganizationMembership.objects.create(organization=org, user=member, role='member')
OrganizationMembership.objects.create(organization=org, user=viewer, role='viewer')

exit()
```

**Test role-based access:**

```bash
# Get viewer token
VIEWER_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "viewer@test.com", "password": "test"}' \
  | jq -r '.access')

# Try to create scan as viewer (should fail)
curl -X POST http://localhost:8000/api/v1/scans/ \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "repo-uuid-here",
    "branch": "branch-uuid-here"
  }'

# Expected: 403 Forbidden

# Get member token and try again
MEMBER_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "member@test.com", "password": "test"}' \
  | jq -r '.access')

# Try to create scan as member (should succeed)
curl -X POST http://localhost:8000/api/v1/scans/ \
  -H "Authorization: Bearer $MEMBER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "repo-uuid-here",
    "branch": "branch-uuid-here"
  }'

# Expected: 201 Created
```

---

## Phase 6: Core Business Logic

### 6.1 Test Quota Enforcement

```bash
# Set low quota for testing
docker-compose exec web python manage.py shell
```

```python
from apps.organizations.models import Organization
from apps.scans.models import QuotaUsage
from django.utils import timezone

org = Organization.objects.get(slug='test-org')
org.scan_quota_monthly = 1  # Only 1 scan allowed
org.save()

# Create quota record
now = timezone.now()
quota, _ = QuotaUsage.objects.get_or_create(
    organization=org,
    year=now.year,
    month=now.month,
    defaults={'scans_used': 0, 'storage_used_bytes': 0}
)
quota.scans_used = 0
quota.save()

exit()
```

```bash
# Try to create first scan (should succeed)
curl -X POST http://localhost:8000/api/v1/scans/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "repo-uuid",
    "branch": "branch-uuid"
  }' | jq .

# Expected: 201 Created

# Try to create second scan (should fail - quota exceeded)
curl -X POST http://localhost:8000/api/v1/scans/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "repo-uuid",
    "branch": "branch-uuid"
  }' | jq .

# Expected: 400 Bad Request with quota error
```

### 6.2 Test Finding Management

```bash
# Get findings
curl http://localhost:8000/api/v1/findings/ \
  -H "Authorization: Bearer $TOKEN" | jq .

# Get finding stats
curl http://localhost:8000/api/v1/findings/stats/ \
  -H "Authorization: Bearer $TOKEN" | jq .

# Expected: Stats grouped by severity and status

# Update finding status
curl -X POST http://localhost:8000/api/v1/findings/{finding-id}/update_status/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in_review",
    "reason": "Investigating this issue"
  }' | jq .

# Add comment
curl -X POST http://localhost:8000/api/v1/findings/{finding-id}/add_comment/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "This looks like a false positive"
  }' | jq .
```

---

## Phase 7: Advanced Features

### 7.1 Test Server-Sent Events (SSE)

```bash
# Terminal 1: Connect to SSE stream
curl -N -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/scans/{scan-id}/events/

# Terminal 2: Trigger events (create scan, etc.)
curl -X POST http://localhost:8000/api/v1/scans/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...}'

# Expected in Terminal 1:
# event: connected
# data: {"scan_id": "...", "status": "pending"}
#
# event: status
# data: {"type": "status", "status": "queued"}
```

### 7.2 Test Polling Fallback

```bash
# Poll for scan status
curl http://localhost:8000/api/v1/scans/{scan-id}/status/ \
  -H "Authorization: Bearer $TOKEN" | jq .

# Expected: Current scan state with logs
```

### 7.3 Test Rate Limiting (if applied)

```bash
# Rapid requests to trigger rate limit
for i in {1..20}; do
  curl -X POST http://localhost:8000/api/v1/auth/login/ \
    -H "Content-Type: application/json" \
    -d '{"email": "test@test.com", "password": "wrong"}' \
    -w "\nStatus: %{http_code}\n"
  sleep 0.1
done

# Expected: Some requests return 429 Too Many Requests
```

---

## Phase 8: Integration & End-to-End

### 8.1 Build Worker Image

```bash
# Build worker
cd worker
chmod +x build.sh
./build.sh

# Expected: Image builds successfully
```

### 8.2 Test Worker Locally

```bash
# Test with mock repository (requires GitHub token)
docker run \
  -e GITHUB_TOKEN="your-token" \
  -e REPO_URL="https://github.com/owner/public-repo" \
  -e BRANCH="main" \
  security-worker:latest > test-output.sarif 2> test-logs.txt

# Check output
cat test-output.sarif | jq . | head -20

# Expected: Valid SARIF JSON
```

---

## Summary Checklist

Use this checklist to track testing progress:

### Infrastructure
- [ ] Environment variables configured
- [ ] Docker services running
- [ ] Dependencies installed

### Database
- [ ] Migrations applied
- [ ] Tables created
- [ ] Constraints working

### Models
- [ ] All models create successfully
- [ ] Relationships work
- [ ] Methods execute correctly

### Authentication
- [ ] Admin accessible
- [ ] API docs load
- [ ] JWT login works
- [ ] Tokens validate

### Multi-Tenancy
- [ ] Organization isolation works
- [ ] Users can't access other orgs
- [ ] RBAC permissions enforce correctly

### Core Features
- [ ] Quota enforcement works
- [ ] Finding management works
- [ ] Fingerprinting works

### Advanced Features
- [ ] SSE streams events
- [ ] Polling fallback works
- [ ] Worker image builds

---

## Next Steps

After all tests pass:

1. **Enable RLS (Optional):**
   - See `docs/ROW_LEVEL_SECURITY.md`
   - Apply SQL script
   - Enable middleware
   - Test isolation

2. **Apply Rate Limiting:**
   - See `docs/RATE_LIMITING.md`
   - Add decorators to views
   - Test limits

3. **Production Deployment:**
   - Update environment for production
   - Configure HTTPS
   - Set up monitoring
   - Deploy worker image to registry

4. **Build Frontend:**
   - Connect to API
   - Implement SSE client
   - Add scanning interface
   - Display findings

---

## Troubleshooting

### Tests Failing?

1. **Check logs:**
   ```bash
   docker-compose logs web
   docker-compose logs celery_worker
   ```

2. **Restart services:**
   ```bash
   docker-compose restart
   ```

3. **Reset database:**
   ```bash
   docker-compose down
   docker-compose up -d
   docker-compose exec web python manage.py migrate
   ```

4. **Check critical issues doc:**
   - See `docs/CRITICAL_ISSUES.md`
   - Verify all Priority 1 items complete

---

**Happy Testing! 🎉**
