# Security Analysis Platform - Comprehensive Test Plan

**Version:** 1.0
**Date:** 2025-11-14
**Status:** AI-Generated Code - Not Yet Executed
**Purpose:** Systematic audit of platform features to identify implementation gaps and guide LLM-assisted development

---

## Executive Summary

This test plan provides a systematic approach to auditing the Review-Pro security analysis platform. Since all code is AI-generated and has never been executed, this plan focuses on:

1. **Progressive Complexity**: Starting with foundational features and building to complex integrations
2. **Early Issue Detection**: Identifying critical blockers in lower-level components before testing higher-level features
3. **LLM Feedback Loop**: Clear identification of what needs to be revisited/implemented with LLM assistance
4. **Practical Validation**: Ensuring each layer works before moving to the next

---

## Test Environment Setup

### Prerequisites Checklist

- [ ] Docker and Docker Compose installed
- [ ] Python 3.11+ installed
- [ ] Git configured
- [ ] Network access to GitHub (for OAuth testing)
- [ ] Minimum 4GB RAM available for Docker containers
- [ ] 10GB free disk space

### Initial Setup Steps

**Before any testing:**

```bash
# 1. Verify environment file exists
cp .env.example .env

# 2. Update critical .env values (document current values)
# - SECRET_KEY: Generate a secure key
# - DATABASE_URL: Verify connection string
# - GITHUB_CLIENT_ID/SECRET: (optional for initial tests)
# - REDIS_URL: Verify connection string

# 3. Document baseline state
git status > test_baseline_git_status.txt
git log --oneline -10 > test_baseline_commits.txt
```

---

## Test Phases Overview

This plan is divided into 7 progressive phases:

| Phase | Focus Area | Estimated Time | Blocking Issues Expected |
|-------|-----------|----------------|-------------------------|
| 1 | Infrastructure & Dependencies | 1-2 hours | High |
| 2 | Database Layer | 2-3 hours | High |
| 3 | Model Layer | 2-4 hours | Medium |
| 4 | Authentication & API Basics | 3-4 hours | Medium |
| 5 | Multi-Tenancy & RBAC | 2-3 hours | Medium |
| 6 | Core Business Logic | 4-6 hours | High |
| 7 | Advanced Features & Integration | 4-8 hours | High |

**Total Estimated Time:** 18-30 hours of testing and fixing

---

## Phase 1: Infrastructure & Dependencies

**Goal:** Verify the foundation works before testing application code.

### 1.1 Environment Configuration

**Test:** Environment file validation
```bash
# Check .env file exists and has required variables
cat .env | grep -E "SECRET_KEY|DATABASE_URL|REDIS_URL"
```

**Expected Issues to Fix with LLM:**
- [ ] Missing or invalid environment variables
- [ ] Incorrect Docker service configurations
- [ ] .env.example missing critical variables

**Success Criteria:**
- All required environment variables are defined
- No placeholder values in production-critical settings

---

### 1.2 Docker Services

**Test 1.2.1:** Docker Compose configuration validation
```bash
# Validate docker-compose.yml syntax
docker-compose config
```

**Test 1.2.2:** Start all services
```bash
# Start in detached mode
docker-compose up -d

# Check all services are running
docker-compose ps
```

**Expected Services:**
- [ ] db (PostgreSQL 15)
- [ ] redis (Redis 7)
- [ ] minio (MinIO)
- [ ] web (Django)
- [ ] celery_worker
- [ ] celery_beat

**Test 1.2.3:** Service health checks
```bash
# PostgreSQL
docker-compose exec db pg_isready -U postgres

# Redis
docker-compose exec redis redis-cli ping

# MinIO (check if accessible)
curl -I http://localhost:9000/minio/health/live

# Django (check if web server starts)
docker-compose logs web | tail -20
```

**Expected Issues to Fix with LLM:**
- [ ] Services failing to start due to port conflicts
- [ ] Missing Docker image dependencies
- [ ] Volume mount permission issues
- [ ] Service dependency ordering issues
- [ ] Memory/resource limit problems

**Success Criteria:**
- All 6 services are running and healthy
- No critical errors in logs
- Services can communicate with each other

---

### 1.3 Python Dependencies

**Test 1.3.1:** Requirements installation (local development)
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Test 1.3.2:** Verify critical packages
```python
python -c "import django; print(f'Django {django.VERSION}')"
python -c "import rest_framework; print('DRF OK')"
python -c "import celery; print('Celery OK')"
python -c "import redis; print('Redis OK')"
python -c "import psycopg2; print('psycopg2 OK')"
```

**Expected Issues to Fix with LLM:**
- [ ] Conflicting package versions
- [ ] Missing packages in requirements.txt
- [ ] Platform-specific dependency issues (e.g., psycopg2 on Mac/Windows)

**Success Criteria:**
- All packages install without errors
- No version conflicts
- Critical imports work

---

## Phase 2: Database Layer

**Goal:** Verify database schema can be created and is correct.

### 2.1 Database Connection

**Test 2.1.1:** Connect to PostgreSQL
```bash
# Via Docker
docker-compose exec db psql -U postgres -d secanalysis -c "SELECT version();"

# Via Django
docker-compose exec web python manage.py dbshell
```

**Expected Issues to Fix with LLM:**
- [ ] Database doesn't exist (need to create)
- [ ] Connection string format issues
- [ ] Authentication failures

**Success Criteria:**
- Can connect to database
- Database exists and is accessible

---

### 2.2 Migrations

**CRITICAL:** This is likely the first major blocker since migrations don't exist yet.

**Test 2.2.1:** Check for existing migrations
```bash
cd backend
find apps -name "migrations" -type d
find apps -path "*/migrations/*.py" ! -name "__init__.py"
```

**Expected Result:** No migration files (besides `__init__.py`)

**Test 2.2.2:** Generate initial migrations
```bash
docker-compose exec web python manage.py makemigrations
```

**Test 2.2.3:** Review generated migrations
```bash
# Check what migrations were created
docker-compose exec web python manage.py showmigrations

# Review migration files for issues
ls -la backend/apps/*/migrations/
```

**Test 2.2.4:** Apply migrations
```bash
docker-compose exec web python manage.py migrate
```

**Expected Issues to Fix with LLM:**
- [ ] **Migration generation fails** due to model errors
- [ ] Circular dependencies between apps
- [ ] Missing `default` values for non-nullable fields
- [ ] Invalid field types or constraints
- [ ] Missing `__init__.py` in migrations directories
- [ ] Foreign key constraint issues

**Success Criteria:**
- Migrations generate without errors
- All migrations apply successfully
- Database schema matches model definitions

---

### 2.3 Database Schema Validation

**Test 2.3.1:** Verify all tables exist
```bash
docker-compose exec db psql -U postgres -d secanalysis -c "\dt"
```

**Expected Tables:**
```
- users
- organizations
- organization_memberships
- repositories
- branches
- scans
- scan_logs
- quota_usage
- findings
- finding_comments
- finding_status_history
```

**Test 2.3.2:** Check table structure
```bash
# Example: Check organizations table
docker-compose exec db psql -U postgres -d secanalysis -c "\d organizations"
```

**Validate:**
- [ ] All columns exist as defined in models
- [ ] Indexes are created properly
- [ ] Foreign keys are set up correctly
- [ ] UUID primary keys are used where specified

**Test 2.3.3:** Row-Level Security (RLS) Policies

**CRITICAL:** RLS policies are not implemented yet.

```bash
# Check if RLS is enabled
docker-compose exec db psql -U postgres -d secanalysis -c "
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public';"
```

**Expected Issues to Fix with LLM:**
- [ ] **RLS policies not implemented** (ADR-001)
- [ ] Need SQL scripts to create RLS policies
- [ ] Policy logic needs to be defined
- [ ] Testing framework for RLS needed

**Action Required:**
- Create SQL migration for RLS policies
- Test RLS enforcement
- Document RLS bypass for superuser queries

**Success Criteria:**
- All tables exist with correct structure
- Indexes are in place
- Foreign keys work properly
- (Optional for MVP) RLS policies are defined and enforced

---

## Phase 3: Model Layer

**Goal:** Verify Django models work correctly with the database.

### 3.1 Model CRUD Operations

**Test 3.1.1:** Create superuser
```bash
docker-compose exec web python manage.py createsuperuser
# Email: admin@example.com
# Password: admin123! (test only)
```

**Test 3.1.2:** Django shell - Basic model tests
```bash
docker-compose exec web python manage.py shell
```

```python
# Test User creation
from apps.users.models import User
user = User.objects.create_user(
    email='test@example.com',
    password='testpass123',
    first_name='Test',
    last_name='User'
)
print(f"Created user: {user.id}, {user.email}")

# Test Organization creation
from apps.organizations.models import Organization
org = Organization.objects.create(
    name='Test Organization',
    slug='test-org',
    plan='free',
    scan_quota_monthly=100,
    storage_quota_gb=10
)
print(f"Created org: {org.id}, {org.name}")

# Test OrganizationMembership
from apps.organizations.models import OrganizationMembership
membership = OrganizationMembership.objects.create(
    organization=org,
    user=user,
    role='owner'
)
print(f"Created membership: {membership.id}, Role: {membership.role}")

# Test Repository
from apps.organizations.models import Repository
repo = Repository.objects.create(
    organization=org,
    github_repo_id='12345',
    name='test-repo',
    full_name='test-org/test-repo',
    default_branch='main'
)
print(f"Created repo: {repo.id}, {repo.full_name}")

# Test Branch
from apps.organizations.models import Branch
branch = Branch.objects.create(
    repository=repo,
    name='main',
    sha='abc123',
    is_default=True
)
print(f"Created branch: {branch.id}, {branch.name}")

# Verify relationships work
print(f"Org repositories: {org.repositories.count()}")
print(f"Repo branches: {repo.branches.count()}")
print(f"User memberships: {user.organization_memberships.count()}")

# Test permission method
print(f"User has 'read' permission: {membership.has_permission('read')}")
print(f"User has 'billing' permission: {membership.has_permission('billing')}")
```

**Expected Issues to Fix with LLM:**
- [ ] Model validation errors
- [ ] Missing `related_name` attributes
- [ ] Incorrect field types
- [ ] UUID generation issues
- [ ] Missing model methods
- [ ] String representation (`__str__`) errors

**Success Criteria:**
- All models can be created
- Relationships work correctly
- Model methods execute without errors
- Cascading deletes work as expected

---

### 3.2 Scan Models

**Test 3.2.1:** Create Scan and related objects
```python
from apps.scans.models import Scan, ScanLog, QuotaUsage
from django.utils import timezone

# Create a scan
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

# Create quota usage
quota = QuotaUsage.objects.create(
    organization=org,
    year=2025,
    month=11,
    scans_used=5,
    storage_used_bytes=1024*1024*500  # 500 MB
)
print(f"Quota: {quota.scans_used} scans, {quota.storage_used_gb:.2f} GB")
```

**Expected Issues to Fix with LLM:**
- [ ] Missing imports in models
- [ ] Incorrect property implementations (e.g., `storage_used_gb`)
- [ ] Timezone handling issues

---

### 3.3 Finding Models

**Test 3.3.1:** Create Finding and related objects
```python
from apps.findings.models import Finding, FindingComment, FindingStatusHistory

# Create a finding
finding = Finding.objects.create(
    organization=org,
    repository=repo,
    scan=scan,
    rule_id='SECURITY-001',
    severity='high',
    status='open',
    file_path='src/main.py',
    start_line=42,
    end_line=45,
    message='Potential SQL injection vulnerability',
    fingerprint='abc123def456'  # In production, this would be auto-generated
)
print(f"Created finding: {finding.id}, Severity: {finding.severity}")

# Create finding comment
comment = FindingComment.objects.create(
    finding=finding,
    user=user,
    comment='This needs immediate attention'
)
print(f"Created comment: {comment.id}")

# Create status history
history = FindingStatusHistory.objects.create(
    finding=finding,
    changed_by=user,
    old_status='open',
    new_status='in_review',
    comment='Starting review'
)
print(f"Created history: {history.id}")
```

**Expected Issues to Fix with LLM:**
- [ ] Fingerprint generation logic not implemented
- [ ] Status transition validation missing
- [ ] Related name conflicts

**Success Criteria:**
- All finding models create successfully
- Relationships are maintained
- Queries work efficiently

---

### 3.4 Model Validation & Constraints

**Test 3.4.1:** Test unique constraints
```python
# Should fail - duplicate slug
try:
    duplicate_org = Organization.objects.create(
        name='Another Org',
        slug='test-org'  # Same as existing
    )
except Exception as e:
    print(f"✓ Unique constraint working: {type(e).__name__}")

# Should fail - duplicate membership
try:
    duplicate_membership = OrganizationMembership.objects.create(
        organization=org,
        user=user,  # Already a member
        role='admin'
    )
except Exception as e:
    print(f"✓ Unique together working: {type(e).__name__}")
```

**Test 3.4.2:** Test cascading deletes
```python
# Create test data
test_user = User.objects.create_user(email='delete@test.com', password='test')
test_org = Organization.objects.create(name='Delete Test', slug='delete-test')
test_membership = OrganizationMembership.objects.create(
    organization=test_org,
    user=test_user,
    role='member'
)
test_repo = Repository.objects.create(
    organization=test_org,
    github_repo_id='delete-123',
    name='delete-repo',
    full_name='delete-test/delete-repo'
)

# Delete organization - should cascade
initial_count = Repository.objects.count()
test_org.delete()
after_count = Repository.objects.count()
print(f"✓ Cascade delete working: {initial_count - after_count} repos deleted")
```

**Success Criteria:**
- Unique constraints prevent duplicates
- Cascade deletes work correctly
- No orphaned records

---

## Phase 4: Authentication & API Basics

**Goal:** Verify authentication works and basic API endpoints respond.

### 4.1 Django Admin

**Test 4.1.1:** Access Django admin
```bash
# Navigate to http://localhost:8000/admin
# Login with superuser credentials
```

**Verify:**
- [ ] Admin interface loads
- [ ] Can view all model admin pages
- [ ] Can create/edit/delete records via admin
- [ ] No 500 errors on any admin page

**Expected Issues to Fix with LLM:**
- [ ] Admin classes not registered
- [ ] `list_display` errors
- [ ] Missing `search_fields` or `list_filter`
- [ ] Inline admin errors

---

### 4.2 API Documentation

**Test 4.2.1:** OpenAPI schema generation
```bash
# Generate schema
curl http://localhost:8000/api/schema/ -o openapi-schema.json

# Check if valid JSON
cat openapi-schema.json | python -m json.tool > /dev/null && echo "✓ Valid JSON"
```

**Test 4.2.2:** Access API documentation
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/

**Expected Issues to Fix with LLM:**
- [ ] Schema generation fails
- [ ] Missing endpoint documentation
- [ ] Serializer schema errors
- [ ] Invalid OpenAPI specification

---

### 4.3 JWT Authentication

**Test 4.3.1:** User login (obtain JWT tokens)
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

**Expected Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Test 4.3.2:** Use access token
```bash
# Save token from previous response
TOKEN="your-access-token-here"

# Test authenticated endpoint
curl http://localhost:8000/api/v1/auth/me/ \
  -H "Authorization: Bearer $TOKEN"
```

**Test 4.3.3:** Refresh token
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "your-refresh-token-here"
  }'
```

**Expected Issues to Fix with LLM:**
- [ ] Login endpoint returns 500 error
- [ ] JWT settings misconfigured
- [ ] Token validation failures
- [ ] Missing authentication classes on views
- [ ] Serializer validation errors

**Success Criteria:**
- Can obtain JWT tokens via login
- Access token works for authenticated requests
- Refresh token generates new access token
- Invalid tokens are rejected

---

### 4.4 API Key Authentication

**Test 4.4.1:** Create API key via shell
```python
from apps.users.models import User

user = User.objects.get(email='test@example.com')
api_key = user.generate_api_key()
print(f"API Key: {api_key}")
```

**Test 4.4.2:** Use API key
```bash
curl http://localhost:8000/api/v1/auth/me/ \
  -H "Authorization: Api-Key your-api-key-here"
```

**Expected Issues to Fix with LLM:**
- [ ] API key generation method not implemented
- [ ] API key authentication class missing or broken
- [ ] API key validation errors

---

## Phase 5: Multi-Tenancy & RBAC

**Goal:** Verify organization-based isolation and role-based access control.

### 5.1 Organization API

**Test 5.1.1:** List organizations (as authenticated user)
```bash
curl http://localhost:8000/api/v1/organizations/ \
  -H "Authorization: Bearer $TOKEN"
```

**Expected:** Only organizations where user is a member

**Test 5.1.2:** Create organization
```bash
curl -X POST http://localhost:8000/api/v1/organizations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Org",
    "slug": "new-org",
    "plan": "free"
  }'
```

**Test 5.1.3:** Verify creator becomes owner
- Check that membership with role='owner' is created automatically

**Expected Issues to Fix with LLM:**
- [ ] Queryset not filtered by organization membership
- [ ] Missing `get_queryset()` override
- [ ] Auto-creation of owner membership not implemented
- [ ] Serializer validation issues

---

### 5.2 Multi-Tenancy Filtering

**Test 5.2.1:** Create test scenario
```python
# Create two organizations with different users
from apps.users.models import User
from apps.organizations.models import Organization, OrganizationMembership

# User 1 in Org A
user1 = User.objects.create_user(email='user1@test.com', password='test')
org_a = Organization.objects.create(name='Org A', slug='org-a')
OrganizationMembership.objects.create(organization=org_a, user=user1, role='owner')

# User 2 in Org B
user2 = User.objects.create_user(email='user2@test.com', password='test')
org_b = Organization.objects.create(name='Org B', slug='org-b')
OrganizationMembership.objects.create(organization=org_b, user=user2, role='owner')

# Create repository in each org
from apps.organizations.models import Repository
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
```

**Test 5.2.2:** Verify isolation
```bash
# Login as user1
TOKEN_USER1=$(curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user1@test.com", "password": "test"}' \
  | jq -r '.access')

# List repositories - should only see repo-a
curl http://localhost:8000/api/v1/repositories/ \
  -H "Authorization: Bearer $TOKEN_USER1"

# Try to access repo-b directly (should fail)
REPO_B_ID=$(echo "get from previous creation")
curl http://localhost:8000/api/v1/repositories/$REPO_B_ID/ \
  -H "Authorization: Bearer $TOKEN_USER1"
```

**Expected:**
- User 1 can only see repositories in Org A
- Attempting to access Org B's resources returns 404 (not 403, to avoid info leakage)

**Expected Issues to Fix with LLM:**
- [ ] **CRITICAL:** No multi-tenancy filtering implemented
- [ ] Users can see all organizations
- [ ] ViewSets missing `get_queryset()` filtering
- [ ] Missing permission checks

---

### 5.3 RBAC Testing

**Test 5.3.1:** Role permission enforcement
```python
# Create users with different roles in same org
owner = User.objects.create_user(email='owner@test.com', password='test')
admin = User.objects.create_user(email='admin@test.com', password='test')
member = User.objects.create_user(email='member@test.com', password='test')
viewer = User.objects.create_user(email='viewer@test.com', password='test')

org = Organization.objects.get(slug='test-org')

OrganizationMembership.objects.create(organization=org, user=owner, role='owner')
OrganizationMembership.objects.create(organization=org, user=admin, role='admin')
OrganizationMembership.objects.create(organization=org, user=member, role='member')
OrganizationMembership.objects.create(organization=org, user=viewer, role='viewer')
```

**Test 5.3.2:** API permission tests
```bash
# Test as viewer (should not be able to create scan)
TOKEN_VIEWER=$(curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "viewer@test.com", "password": "test"}' \
  | jq -r '.access')

curl -X POST http://localhost:8000/api/v1/scans/ \
  -H "Authorization: Bearer $TOKEN_VIEWER" \
  -H "Content-Type: application/json" \
  -d '{...}'
# Expected: 403 Forbidden

# Test as member (should be able to create scan)
TOKEN_MEMBER=$(curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "member@test.com", "password": "test"}' \
  | jq -r '.access')

curl -X POST http://localhost:8000/api/v1/scans/ \
  -H "Authorization: Bearer $TOKEN_MEMBER" \
  -H "Content-Type: application/json" \
  -d '{...}'
# Expected: 201 Created
```

**Permission Matrix to Test:**

| Role | Read | Write | Delete | Admin | Billing |
|------|------|-------|--------|-------|---------|
| Owner | ✓ | ✓ | ✓ | ✓ | ✓ |
| Admin | ✓ | ✓ | ✓ | ✓ | ✗ |
| Member | ✓ | ✓ | ✗ | ✗ | ✗ |
| Viewer | ✓ | ✗ | ✗ | ✗ | ✗ |

**Expected Issues to Fix with LLM:**
- [ ] Permission classes not applied to viewsets
- [ ] `IsOrganizationMember` permission not implemented correctly
- [ ] `IsOrganizationAdmin` permission not implemented correctly
- [ ] No role-based action restrictions

---

## Phase 6: Core Business Logic

**Goal:** Test main features - scanning, findings, quotas.

### 6.1 Repository & Branch Management

**Test 6.1.1:** Create repository via API
```bash
curl -X POST http://localhost:8000/api/v1/repositories/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organization": "org-uuid-here",
    "github_repo_id": "123456789",
    "name": "my-app",
    "full_name": "myorg/my-app",
    "default_branch": "main",
    "is_private": true
  }'
```

**Test 6.1.2:** List branches for repository
```bash
curl http://localhost:8000/api/v1/repositories/{repo_id}/branches/ \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Issues to Fix with LLM:**
- [ ] Nested routes not configured correctly
- [ ] Serializer nesting issues
- [ ] Organization UUID validation

---

### 6.2 Scan Creation

**Test 6.2.1:** Create scan via API
```bash
curl -X POST http://localhost:8000/api/v1/scans/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "repo-uuid-here",
    "branch": "branch-uuid-here"
  }'
```

**Expected:**
- Scan created with status='pending'
- Celery task triggered
- QuotaUsage updated

**Test 6.2.2:** Check scan logs
```bash
curl http://localhost:8000/api/v1/scans/{scan_id}/logs/ \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Issues to Fix with LLM:**
- [ ] **CRITICAL:** `run_security_scan` task not implemented (only placeholder)
- [ ] Celery task not triggered on scan creation
- [ ] Organization context not passed to scan
- [ ] Quota check not enforced before scan creation

---

### 6.3 Quota Management

**Test 6.3.1:** Check quota usage
```python
from apps.scans.models import QuotaUsage
from apps.organizations.models import Organization

org = Organization.objects.get(slug='test-org')
quota = QuotaUsage.objects.filter(organization=org, year=2025, month=11).first()

print(f"Scans used: {quota.scans_used}/{org.scan_quota_monthly}")
print(f"Storage used: {quota.storage_used_gb:.2f}/{org.storage_quota_gb} GB")
```

**Test 6.3.2:** Test quota enforcement
```python
# Set quota to limit
org.scan_quota_monthly = 1
org.save()

# Create scan - should succeed
scan1 = Scan.objects.create(organization=org, repository=repo, branch=branch, triggered_by=user)

# Update quota
quota.scans_used = 1
quota.save()

# Try to create another scan - should fail
try:
    scan2 = Scan.objects.create(organization=org, repository=repo, branch=branch, triggered_by=user)
except Exception as e:
    print(f"✓ Quota enforcement working: {e}")
```

**Expected Issues to Fix with LLM:**
- [ ] **Quota enforcement not implemented** in API
- [ ] No validation before scan creation
- [ ] QuotaUsage not auto-created
- [ ] Storage calculation incorrect

---

### 6.4 Finding Management

**Test 6.4.1:** Create finding via API (normally done by worker)
```bash
curl -X POST http://localhost:8000/api/v1/findings/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scan": "scan-uuid-here",
    "rule_id": "SEC-001",
    "severity": "high",
    "file_path": "src/main.py",
    "start_line": 42,
    "message": "SQL injection vulnerability"
  }'
```

**Test 6.4.2:** Update finding status
```bash
curl -X POST http://localhost:8000/api/v1/findings/{finding_id}/update_status/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in_review",
    "comment": "Investigating this issue"
  }'
```

**Test 6.4.3:** Add comment to finding
```bash
curl -X POST http://localhost:8000/api/v1/findings/{finding_id}/comments/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "comment": "This looks like a false positive"
  }'
```

**Test 6.4.4:** Get finding statistics
```bash
curl http://localhost:8000/api/v1/findings/stats/ \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "total": 10,
  "by_severity": {
    "critical": 2,
    "high": 3,
    "medium": 4,
    "low": 1
  },
  "by_status": {
    "open": 5,
    "in_review": 3,
    "resolved": 2
  }
}
```

**Expected Issues to Fix with LLM:**
- [ ] Stats endpoint not implemented
- [ ] Status history not created on update
- [ ] Fingerprint auto-generation missing
- [ ] Deduplication logic not implemented

---

### 6.5 Finding Deduplication (ADR-002)

**Test 6.5.1:** Create duplicate findings
```python
from apps.findings.models import Finding

# Create first finding
finding1 = Finding.objects.create(
    organization=org,
    repository=repo,
    scan=scan,
    rule_id='SEC-001',
    file_path='src/main.py',
    start_line=42,
    message='SQL injection',
    severity='high',
    fingerprint='generated-fingerprint-123'
)

# Create duplicate (same fingerprint)
finding2 = Finding.objects.create(
    organization=org,
    repository=repo,
    scan=scan,
    rule_id='SEC-001',
    file_path='src/main.py',
    start_line=42,
    message='SQL injection',
    severity='high',
    fingerprint='generated-fingerprint-123'  # Same fingerprint
)
```

**Expected:**
- Fingerprint collision should be handled gracefully
- Second finding should reference the first (deduplication)

**Expected Issues to Fix with LLM:**
- [ ] **Fingerprint generation not implemented**
- [ ] **Deduplication logic not implemented**
- [ ] Collision handling missing
- [ ] No `first_seen_at`/`last_seen_at` tracking

---

## Phase 7: Advanced Features & Integration

**Goal:** Test complex features requiring multiple components.

### 7.1 Celery Task Execution

**Test 7.1.1:** Verify Celery worker is running
```bash
docker-compose logs celery_worker | tail -20
```

**Test 7.1.2:** Test quota update task
```python
from apps.scans.tasks import update_quota_usage

# Trigger task
result = update_quota_usage.delay(str(org.id), str(scan.id))

# Check task status
print(f"Task ID: {result.id}")
print(f"Task Status: {result.status}")
```

**Test 7.1.3:** Test scan execution task (will fail - not implemented)
```python
from apps.scans.tasks import run_security_scan

# This will fail because task is not implemented
result = run_security_scan.delay(str(scan.id))
```

**Expected Issues to Fix with LLM:**
- [ ] **CRITICAL:** `run_security_scan` task not implemented
- [ ] Missing Docker SDK code
- [ ] No GitHub token generation
- [ ] No SARIF parsing logic

---

### 7.2 SARIF Processing (ADR-005)

**CRITICAL:** This is completely unimplemented.

**What Needs Implementation:**

1. **SARIF Parser Service:**
   - Parse SARIF JSON files
   - Extract findings from SARIF
   - Generate fingerprints
   - Create Finding objects

2. **S3/MinIO Upload:**
   - Upload full SARIF file to object storage
   - Generate presigned URLs for download
   - Track file size for quota

3. **Integration with Scan Worker:**
   - Receive SARIF output from Docker container
   - Process and upload SARIF
   - Create findings from SARIF data

**Test Plan for SARIF (when implemented):**

```bash
# Test SARIF upload
curl -X POST http://localhost:8000/api/v1/scans/{scan_id}/upload_sarif/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "sarif_file=@sample.sarif"

# Test SARIF download (presigned URL)
curl http://localhost:8000/api/v1/scans/{scan_id}/sarif/ \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Issues to Fix with LLM:**
- [ ] **No SARIF parser implemented**
- [ ] **No S3 upload utilities**
- [ ] **No presigned URL generation**
- [ ] SARIF schema validation missing
- [ ] Error handling for malformed SARIF

---

### 7.3 Docker Container Execution (ADR-004)

**CRITICAL:** Worker implementation is a placeholder.

**What Needs Implementation:**

1. **GitHub App Token Generation:**
   - Generate ephemeral tokens (15 min expiry)
   - Use GitHub App credentials
   - Pass token to Docker container

2. **Docker Container Orchestration:**
   - Pull/build security scanner image
   - Mount repository code
   - Pass environment variables
   - Collect SARIF output
   - Handle timeouts and failures

3. **Security Isolation:**
   - Resource limits (CPU, memory)
   - Network isolation
   - Read-only mounts
   - User namespacing

**Test Plan for Docker Worker (when implemented):**

```python
# Mock test of worker logic
def test_worker_execution():
    # 1. Create GitHub token (mock)
    github_token = create_github_app_token(repo_id, installation_id)

    # 2. Start Docker container
    container = docker_client.containers.run(
        image='security-worker:latest',
        environment={
            'GITHUB_TOKEN': github_token,
            'REPO_URL': repo_url,
            'BRANCH': branch_name
        },
        mem_limit='2g',
        cpu_count=2,
        detach=True
    )

    # 3. Wait for completion (with timeout)
    result = container.wait(timeout=1800)

    # 4. Collect SARIF output
    sarif_data = container.logs()

    # 5. Cleanup
    container.remove()

    return sarif_data
```

**Expected Issues to Fix with LLM:**
- [ ] **Docker SDK integration not implemented**
- [ ] **GitHub App authentication not implemented**
- [ ] No error handling for container failures
- [ ] No timeout mechanism
- [ ] Resource limits not enforced

---

### 7.4 Real-Time Updates via SSE (ADR-003)

**CRITICAL:** SSE not implemented.

**What Needs Implementation:**

1. **SSE View/Consumer:**
   - Stream scan status updates
   - Stream finding discovery events
   - Handle client reconnection

2. **Redis Pub/Sub:**
   - Publish events from Celery tasks
   - Subscribe to events in SSE view
   - Channel naming and routing

3. **Fallback to Polling:**
   - Polling endpoint for scan status
   - Detect SSE support

**Test Plan for SSE (when implemented):**

```bash
# Test SSE connection
curl -N http://localhost:8000/api/v1/scans/{scan_id}/events/ \
  -H "Authorization: Bearer $TOKEN"

# Expected output (streaming):
# data: {"type": "status_update", "status": "running"}
# data: {"type": "finding_discovered", "finding_id": "..."}
# data: {"type": "scan_complete", "total_findings": 10}
```

**Expected Issues to Fix with LLM:**
- [ ] **SSE views not implemented**
- [ ] **Redis pub/sub not configured**
- [ ] No event serialization
- [ ] No authentication for SSE streams

---

### 7.5 Rate Limiting (ADR-008)

**Test 7.5.1:** Test API rate limiting
```bash
# Make rapid requests to trigger rate limit
for i in {1..100}; do
  curl http://localhost:8000/api/v1/organizations/ \
    -H "Authorization: Bearer $TOKEN" &
done
wait

# Expected: Some requests return 429 Too Many Requests
```

**Test 7.5.2:** Check rate limit configuration
```python
from django.conf import settings
print(settings.RATELIMIT_ENABLE)
# Check if Redis is used for rate limiting
```

**Expected Issues to Fix with LLM:**
- [ ] Rate limiting not configured
- [ ] Redis backend not set up for rate limiting
- [ ] No per-user/per-IP limits defined

---

### 7.6 GitHub OAuth Integration (ADR-007)

**Test 7.6.1:** Configure GitHub OAuth app
- Create OAuth app in GitHub settings
- Update .env with client ID and secret
- Set callback URL: `http://localhost:8000/auth/complete/github/`

**Test 7.6.2:** Test OAuth flow (manual browser test)
1. Navigate to: `http://localhost:8000/api/v1/auth/github/`
2. Should redirect to GitHub authorization page
3. After authorization, should redirect back with tokens

**Expected Issues to Fix with LLM:**
- [ ] OAuth callback not configured correctly
- [ ] Social auth pipeline errors
- [ ] User creation from OAuth data fails
- [ ] Token storage issues

---

## Phase 8: Integration & End-to-End Testing

**Goal:** Test complete workflows from start to finish.

### 8.1 Full Scan Workflow (When Core Features Implemented)

**End-to-End Test:**

1. User logs in
2. Creates organization
3. Adds repository
4. Triggers scan
5. Worker executes scan
6. SARIF is uploaded to S3
7. Findings are created from SARIF
8. User views findings
9. User updates finding status
10. User adds comments

**Success Criteria:**
- All steps complete without errors
- Data is persisted correctly
- Multi-tenancy is enforced throughout
- Quota is updated correctly

---

### 8.2 Performance Testing

**Test 8.2.1:** Database query performance
```python
from django.db import connection
from django.test.utils import override_settings

# Enable query logging
with override_settings(DEBUG=True):
    # Execute a complex query
    findings = Finding.objects.filter(
        organization=org
    ).select_related('repository', 'scan').prefetch_related('comments')

    # Check query count
    print(f"Queries executed: {len(connection.queries)}")
    # Should be minimal (N+1 check)
```

**Test 8.2.2:** API response times
```bash
# Measure response time for common endpoints
time curl http://localhost:8000/api/v1/findings/ \
  -H "Authorization: Bearer $TOKEN"
```

**Success Criteria:**
- No N+1 query problems
- API responses under 200ms for simple queries
- Proper use of `select_related` and `prefetch_related`

---

## Critical Blockers Summary

Based on this test plan, here are the **critical issues that need LLM implementation**:

### Priority 1 (Blocking Basic Functionality)

1. **Database Migrations**
   - Location: `backend/apps/*/migrations/`
   - Status: Don't exist
   - Action: Generate with `makemigrations` and fix any errors

2. **Multi-Tenancy Filtering**
   - Location: `backend/apps/*/views.py`
   - Status: Not implemented in viewsets
   - Action: Add `get_queryset()` filtering by organization

3. **RBAC Permission Classes**
   - Location: `backend/apps/*/permissions.py`
   - Status: Partially implemented
   - Action: Apply to all viewsets and test enforcement

### Priority 2 (Blocking Core Features)

4. **Scan Worker Implementation**
   - Location: `backend/apps/scans/tasks.py`
   - Status: Placeholder with TODO
   - Action: Implement Docker execution, GitHub token, SARIF collection

5. **SARIF Parser Service**
   - Location: Need to create `backend/apps/scans/sarif_parser.py`
   - Status: Does not exist
   - Action: Create SARIF parsing and finding extraction logic

6. **S3/MinIO Storage Integration**
   - Location: `backend/apps/scans/storage.py`
   - Status: Does not exist
   - Action: Implement SARIF upload/download, presigned URLs

7. **Quota Enforcement**
   - Location: `backend/apps/scans/views.py`
   - Status: Not enforced in API
   - Action: Add quota check before scan creation

8. **Finding Fingerprint Generation**
   - Location: `backend/apps/findings/models.py` or utils
   - Status: Manual fingerprint only
   - Action: Implement ADR-002 fingerprint algorithm

### Priority 3 (Advanced Features)

9. **Row-Level Security Policies**
   - Location: SQL migration file needed
   - Status: Not created
   - Action: Create PostgreSQL RLS policies for multi-tenancy

10. **Server-Sent Events (SSE)**
    - Location: Need to create SSE views/consumers
    - Status: Not implemented
    - Action: Implement SSE endpoints and Redis pub/sub

11. **GitHub App Integration**
    - Location: `backend/apps/scans/github_app.py`
    - Status: Does not exist
    - Action: Implement ephemeral token generation

12. **Rate Limiting Configuration**
    - Location: `backend/config/settings.py`
    - Status: Configured but not tested
    - Action: Verify and test rate limits

---

## Testing Checklist

Use this checklist to track progress through the test plan:

### Phase 1: Infrastructure
- [ ] Environment variables configured
- [ ] Docker services start successfully
- [ ] Python dependencies install without errors
- [ ] All services are healthy

### Phase 2: Database
- [ ] Database connection works
- [ ] Migrations generate successfully
- [ ] Migrations apply without errors
- [ ] All tables created correctly
- [ ] Indexes are in place

### Phase 3: Models
- [ ] All models can be created
- [ ] Relationships work correctly
- [ ] Unique constraints enforced
- [ ] Cascade deletes work
- [ ] Model methods execute without errors

### Phase 4: Authentication
- [ ] Django admin accessible
- [ ] API documentation loads
- [ ] JWT login works
- [ ] JWT tokens validate correctly
- [ ] API keys work (if implemented)

### Phase 5: Multi-Tenancy
- [ ] Organization CRUD works
- [ ] Users can only see their organizations
- [ ] Cross-organization access blocked
- [ ] RBAC permissions enforced
- [ ] All roles tested

### Phase 6: Core Features
- [ ] Repository management works
- [ ] Scan creation works
- [ ] Quota tracking works
- [ ] Quota enforcement works
- [ ] Finding CRUD works
- [ ] Finding status updates work
- [ ] Comments work

### Phase 7: Advanced Features
- [ ] Celery tasks execute
- [ ] SARIF upload/download (when implemented)
- [ ] Docker worker execution (when implemented)
- [ ] SSE streaming (when implemented)
- [ ] Rate limiting enforced
- [ ] GitHub OAuth works

### Phase 8: Integration
- [ ] Full scan workflow completes
- [ ] No N+1 queries
- [ ] Performance acceptable

---

## Next Steps

1. **Start with Phase 1:** Ensure infrastructure is working
2. **Generate and apply migrations:** This is the first major task
3. **Test models in Django shell:** Verify data layer works
4. **Fix multi-tenancy filtering:** Critical for security
5. **Implement scan worker (with LLM):** Core feature
6. **Test end-to-end workflow:** Validate everything works together

---

## Appendix A: Test Data Script

Create a file `backend/scripts/create_test_data.py`:

```python
"""
Create comprehensive test data for manual testing.
Run with: python manage.py shell < scripts/create_test_data.py
"""

from apps.users.models import User
from apps.organizations.models import Organization, OrganizationMembership, Repository, Branch
from apps.scans.models import Scan, ScanLog, QuotaUsage
from apps.findings.models import Finding, FindingComment
from django.utils import timezone

# Create users
print("Creating users...")
admin_user = User.objects.create_superuser(
    email='admin@example.com',
    password='admin123!',
    first_name='Admin',
    last_name='User'
)

test_user = User.objects.create_user(
    email='test@example.com',
    password='test123!',
    first_name='Test',
    last_name='User'
)

viewer_user = User.objects.create_user(
    email='viewer@example.com',
    password='viewer123!',
    first_name='Viewer',
    last_name='User'
)

# Create organization
print("Creating organization...")
org = Organization.objects.create(
    name='Test Organization',
    slug='test-org',
    plan='professional',
    scan_quota_monthly=100,
    storage_quota_gb=50
)

# Create memberships
print("Creating memberships...")
OrganizationMembership.objects.create(
    organization=org,
    user=admin_user,
    role='owner'
)

OrganizationMembership.objects.create(
    organization=org,
    user=test_user,
    role='member'
)

OrganizationMembership.objects.create(
    organization=org,
    user=viewer_user,
    role='viewer'
)

# Create repository
print("Creating repository...")
repo = Repository.objects.create(
    organization=org,
    github_repo_id='12345678',
    name='test-app',
    full_name='test-org/test-app',
    default_branch='main',
    is_private=True
)

# Create branches
print("Creating branches...")
main_branch = Branch.objects.create(
    repository=repo,
    name='main',
    sha='abc123def456',
    is_default=True,
    is_protected=True
)

dev_branch = Branch.objects.create(
    repository=repo,
    name='develop',
    sha='def456ghi789',
    is_default=False,
    is_protected=False
)

# Create scans
print("Creating scans...")
scan1 = Scan.objects.create(
    organization=org,
    repository=repo,
    branch=main_branch,
    status='completed',
    triggered_by=test_user,
    sarif_file_path='scans/scan1.sarif',
    sarif_file_size=1024*1024*2  # 2 MB
)

scan2 = Scan.objects.create(
    organization=org,
    repository=repo,
    branch=dev_branch,
    status='running',
    triggered_by=test_user
)

# Create scan logs
print("Creating scan logs...")
ScanLog.objects.create(scan=scan1, level='info', message='Scan started')
ScanLog.objects.create(scan=scan1, level='info', message='Cloning repository')
ScanLog.objects.create(scan=scan1, level='info', message='Running security analysis')
ScanLog.objects.create(scan=scan1, level='success', message='Scan completed successfully')

# Create quota usage
print("Creating quota usage...")
QuotaUsage.objects.create(
    organization=org,
    year=timezone.now().year,
    month=timezone.now().month,
    scans_used=2,
    storage_used_bytes=1024*1024*2
)

# Create findings
print("Creating findings...")
finding1 = Finding.objects.create(
    organization=org,
    repository=repo,
    scan=scan1,
    rule_id='SEC-001',
    severity='critical',
    status='open',
    file_path='src/auth/login.py',
    start_line=45,
    end_line=48,
    message='SQL Injection vulnerability detected',
    fingerprint='fp-001'
)

finding2 = Finding.objects.create(
    organization=org,
    repository=repo,
    scan=scan1,
    rule_id='SEC-002',
    severity='high',
    status='in_review',
    file_path='src/api/views.py',
    start_line=120,
    end_line=125,
    message='Potential XSS vulnerability',
    fingerprint='fp-002'
)

finding3 = Finding.objects.create(
    organization=org,
    repository=repo,
    scan=scan1,
    rule_id='SEC-003',
    severity='medium',
    status='resolved',
    file_path='src/utils/crypto.py',
    start_line=32,
    end_line=35,
    message='Weak cryptographic algorithm',
    fingerprint='fp-003'
)

# Create finding comments
print("Creating finding comments...")
FindingComment.objects.create(
    finding=finding1,
    user=test_user,
    comment='This is a critical issue that needs immediate attention'
)

FindingComment.objects.create(
    finding=finding2,
    user=admin_user,
    comment='Reviewing this XSS vulnerability'
)

print("\n✓ Test data created successfully!")
print(f"  - Users: {User.objects.count()}")
print(f"  - Organizations: {Organization.objects.count()}")
print(f"  - Repositories: {Repository.objects.count()}")
print(f"  - Scans: {Scan.objects.count()}")
print(f"  - Findings: {Finding.objects.count()}")
```

---

## Appendix B: Common Commands Reference

```bash
# Docker commands
docker-compose up -d                          # Start services
docker-compose down                           # Stop services
docker-compose logs -f web                    # Follow web logs
docker-compose exec web python manage.py shell  # Django shell
docker-compose restart web                    # Restart Django

# Django commands
python manage.py makemigrations               # Create migrations
python manage.py migrate                      # Apply migrations
python manage.py createsuperuser              # Create admin user
python manage.py shell                        # Interactive shell
python manage.py test                         # Run tests

# Celery commands
celery -A config worker -l info               # Start worker
celery -A config beat -l info                 # Start beat scheduler
celery -A config purge                        # Clear all tasks

# Database commands
docker-compose exec db psql -U postgres -d secanalysis  # Access DB
python manage.py dbshell                      # Django DB shell

# Testing commands
pytest                                        # Run all tests
pytest --cov=apps --cov-report=html          # With coverage
pytest -v -s                                  # Verbose output
```

---

## Document Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-14 | Initial comprehensive test plan created |

