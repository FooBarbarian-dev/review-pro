# Testing Guide

This guide provides comprehensive testing instructions for the review-pro platform. Tests should be run in order to ensure the base environment is working before moving to integration tests.

## Quick Start

### Native Environment (Recommended)

```bash
# Run all unit tests
pixi run test-unit

# Run all tests
pixi run test

# Run with coverage
pixi run test-cov
```

### Docker Environment

```bash
# Run all unit tests
docker-compose exec web pytest -m unit

# Run all tests
docker-compose exec web pytest

# Run with coverage
docker-compose exec web pytest --cov=apps --cov-report=html
```

---

## Phase 1: Base Environment Setup

Before running any tests, ensure your base environment is configured correctly.

### 1.1 Native Environment Setup

Follow the [Quick Start Guide](./QUICKSTART.md) to set up your native environment.

**Verify environment:**

```bash
# Check pixi is installed
pixi --version

# Check Python environment
pixi run python --version  # Should be 3.11.x

# Check dependencies are installed
pixi list
```

**Verify services:**

```bash
# PostgreSQL
pg_isready
psql -d review_pro -c "SELECT version();"

# Redis
redis-cli ping  # Should return PONG

# Check environment variables
cat .env | grep -E "SECRET_KEY|DATABASE_URL|REDIS_URL"
```

### 1.2 Docker Environment Setup

Follow the [Docker Guide](./DOCKER_GUIDE.md) to set up Docker environment.

**Verify services:**

```bash
# Check all services are running
docker-compose ps

# Expected services: db, redis, minio, web, celery_worker, celery_beat

# Check service health
docker-compose exec db pg_isready
docker-compose exec redis redis-cli ping
docker-compose exec web python -c "import django; print(django.VERSION)"
```

### 1.3 Database Migrations

Ensure migrations are applied:

```bash
# Native
pixi run migrate

# Docker
docker-compose exec web python manage.py migrate

# Verify migration status
pixi run shell  # or: docker-compose exec web python manage.py shell
```

In Django shell:
```python
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT COUNT(*) FROM django_migrations;")
print(f"Applied migrations: {cursor.fetchone()[0]}")
exit()
```

---

## Phase 2: Unit Tests

Unit tests validate individual components in isolation. **Start here** to ensure the foundation is solid.

### 2.1 Run All Unit Tests

```bash
# Native
pixi run test-unit

# Docker
docker-compose exec web pytest -m unit

# Expected output:
# ====== test session starts ======
# collected X items
#
# apps/users/tests/test_models.py ......
# apps/organizations/tests/test_models.py ......
#
# ====== X passed in X.XXs ======
```

### 2.2 Test Individual Components

**User Model Tests:**

```bash
# Native
pixi shell
cd backend
pytest apps/users/tests/test_models.py -v

# Docker
docker-compose exec web pytest apps/users/tests/test_models.py -v

# Expected tests:
# - test_create_user
# - test_create_superuser
# - test_user_str_method
# - test_generate_api_key
# - test_revoke_api_key
```

**Organization Model Tests:**

```bash
# Native
pytest apps/organizations/tests/test_models.py -v

# Docker
docker-compose exec web pytest apps/organizations/tests/test_models.py -v

# Expected tests:
# - test_create_organization
# - test_organization_membership
# - test_membership_permissions
# - test_create_repository
# - test_create_branch
```

### 2.3 Verify Test Coverage

```bash
# Native
pixi run test-cov

# Docker
docker-compose exec web pytest --cov=apps --cov-report=html --cov-report=term

# View HTML coverage report
xdg-open htmlcov/index.html  # Native
# or browse to backend/htmlcov/index.html
```

### 2.4 Fix Failing Unit Tests

If unit tests fail, investigate and fix before proceeding:

```bash
# Run with verbose output
pytest apps/users/tests/test_models.py -vv

# Run single test
pytest apps/users/tests/test_models.py::TestUserModel::test_create_user -vv

# Run with print statements (disable capture)
pytest apps/users/tests/test_models.py -s

# Drop into debugger on failure
pytest apps/users/tests/test_models.py --pdb
```

**Common issues:**

1. **Database connection errors:**
   - Check DATABASE_URL in .env
   - Ensure PostgreSQL is running
   - Verify database exists

2. **Import errors:**
   - Check PYTHONPATH
   - Ensure all dependencies are installed
   - Verify DJANGO_SETTINGS_MODULE

3. **Migration errors:**
   - Run migrations: `python manage.py migrate`
   - Check for unapplied migrations

---

## Phase 3: Model Layer Tests

After unit tests pass, verify models work correctly in the database.

### 3.1 Django Shell Tests

Open Django shell:

```bash
# Native
pixi run shell

# Docker
docker-compose exec web python manage.py shell
```

**Test User model:**

```python
from apps.users.models import User

# Create user
user = User.objects.create_user(
    email='test@example.com',
    password='testpass123',
    first_name='Test',
    last_name='User'
)

print(f"✓ User created: {user.id}, {user.email}")

# Test API key generation
api_key = user.generate_api_key()
print(f"✓ API key generated: {api_key[:20]}...")

# Cleanup
user.delete()
print("✓ User deleted")
```

**Test Organization models:**

```python
from apps.organizations.models import Organization, OrganizationMembership, Repository, Branch

# Create organization
org = Organization.objects.create(
    name='Test Org',
    slug='test-org',
    plan='free'
)
print(f"✓ Organization created: {org.id}")

# Create user
user = User.objects.create_user(email='test@example.com', password='test')

# Create membership
membership = OrganizationMembership.objects.create(
    organization=org,
    user=user,
    role='member'
)
print(f"✓ Membership created: {membership.id}, Role: {membership.role}")

# Test permissions
assert membership.has_permission('read') == True
assert membership.has_permission('write') == True
assert membership.has_permission('admin') == False
print("✓ Permissions working correctly")

# Create repository
repo = Repository.objects.create(
    organization=org,
    github_repo_id='12345',
    name='test-repo',
    full_name='test-org/test-repo'
)
print(f"✓ Repository created: {repo.id}")

# Create branch
branch = Branch.objects.create(
    repository=repo,
    name='main',
    sha='abc123',
    is_default=True
)
print(f"✓ Branch created: {branch.id}")

# Cleanup
org.delete()  # Cascades to repo, branch, membership
user.delete()
print("✓ Cleanup complete")

exit()
```

### 3.2 Test Database Constraints

```bash
# Native
pixi shell
cd backend
python manage.py dbshell

# Docker
docker-compose exec web python manage.py dbshell
```

**Test unique constraints:**

```sql
-- Test organization slug uniqueness
BEGIN;

INSERT INTO organizations_organization (id, name, slug, plan, is_active, created_at, updated_at)
VALUES (gen_random_uuid(), 'Test Org', 'test-unique', 'free', true, now(), now());

-- Try duplicate (should fail)
INSERT INTO organizations_organization (id, name, slug, plan, is_active, created_at, updated_at)
VALUES (gen_random_uuid(), 'Another Org', 'test-unique', 'free', true, now(), now());
-- Expected: ERROR: duplicate key value

ROLLBACK;
\q
```

---

## Phase 4: API Tests

Test the REST API endpoints.

### 4.1 Authentication Tests

```bash
# Create superuser if not exists
pixi run createsuperuser  # or docker-compose exec web python manage.py createsuperuser
```

**Test JWT login:**

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "your-password"}' | jq .

# Expected response:
# {
#   "access": "eyJ...",
#   "refresh": "eyJ..."
# }

# Save token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "your-password"}' | jq -r '.access')

# Test authenticated endpoint
curl http://localhost:8000/api/v1/auth/me/ \
  -H "Authorization: Bearer $TOKEN" | jq .

# Expected: User details
```

### 4.2 API Endpoint Tests

```bash
# List organizations
curl http://localhost:8000/api/v1/organizations/ \
  -H "Authorization: Bearer $TOKEN" | jq .

# List repositories
curl http://localhost:8000/api/v1/repositories/ \
  -H "Authorization: Bearer $TOKEN" | jq .

# API schema
curl http://localhost:8000/api/schema/ | jq . | head -20
```

### 4.3 Admin Interface Test

```bash
# Open in browser
xdg-open http://localhost:8000/admin

# Or test with curl
curl -I http://localhost:8000/admin/
# Expected: HTTP 200
```

---

## Phase 5: Integration Tests

Test complete workflows and interactions between components.

### 5.1 Multi-Tenancy Tests

Create test scenario:

```bash
pixi run shell  # or docker-compose exec web python manage.py shell
```

```python
from apps.users.models import User
from apps.organizations.models import Organization, OrganizationMembership, Repository

# Create two separate organizations
user1 = User.objects.create_user(email='user1@test.com', password='test')
org_a = Organization.objects.create(name='Org A', slug='org-a')
OrganizationMembership.objects.create(organization=org_a, user=user1, role='owner')

user2 = User.objects.create_user(email='user2@test.com', password='test')
org_b = Organization.objects.create(name='Org B', slug='org-b')
OrganizationMembership.objects.create(organization=org_b, user=user2, role='owner')

# Create repos
repo_a = Repository.objects.create(organization=org_a, github_repo_id='a', name='repo-a', full_name='org-a/repo-a')
repo_b = Repository.objects.create(organization=org_b, github_repo_id='b', name='repo-b', full_name='org-b/repo-b')

print("✓ Test scenario created")
exit()
```

**Test isolation:**

```bash
# Login as user1
TOKEN1=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user1@test.com", "password": "test"}' | jq -r '.access')

# List repositories - should only see repo-a
curl -s http://localhost:8000/api/v1/repositories/ \
  -H "Authorization: Bearer $TOKEN1" | jq '.results[].name'
# Expected: "repo-a" only

# Login as user2
TOKEN2=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user2@test.com", "password": "test"}' | jq -r '.access')

# List repositories - should only see repo-b
curl -s http://localhost:8000/api/v1/repositories/ \
  -H "Authorization: Bearer $TOKEN2" | jq '.results[].name'
# Expected: "repo-b" only
```

### 5.2 RBAC Tests

Test role-based access control:

```python
# In Django shell
from apps.users.models import User
from apps.organizations.models import Organization, OrganizationMembership

org = Organization.objects.get(slug='test-org')

viewer = User.objects.create_user(email='viewer@test.com', password='test')
member = User.objects.create_user(email='member@test.com', password='test')
admin = User.objects.create_user(email='admin@test.com', password='test')

OrganizationMembership.objects.create(organization=org, user=viewer, role='viewer')
OrganizationMembership.objects.create(organization=org, user=member, role='member')
OrganizationMembership.objects.create(organization=org, user=admin, role='admin')

print("✓ Users with different roles created")
exit()
```

Test permissions via API (tests will depend on implemented views).

---

## Phase 6: Celery & Async Tests

Test asynchronous task processing.

### 6.1 Verify Celery is Running

```bash
# Native
ps aux | grep celery

# Docker
docker-compose ps celery_worker
docker-compose logs celery_worker | tail
```

### 6.2 Test Celery Task

```python
# In Django shell
from config.celery import app

# Test basic task
result = app.send_task('tasks.test_task')  # If you have a test task
print(f"Task ID: {result.id}")

# Check result
print(result.get(timeout=10))
```

---

## Phase 7: Worker & End-to-End Tests

### 7.1 Build Worker Image

```bash
cd worker
chmod +x build.sh
./build.sh

# Verify image
docker images | grep security-worker
```

### 7.2 Test Worker Locally

```bash
# Requires GitHub token
docker run --rm \
  -e GITHUB_TOKEN="your-token" \
  -e REPO_URL="https://github.com/owner/public-repo" \
  -e BRANCH="main" \
  review-pro-worker:latest > test-output.sarif 2> test-logs.txt

# Check output
cat test-output.sarif | jq . | head -20
# Expected: Valid SARIF JSON
```

---

## Automated Test Script

Use the automated testing script:

```bash
# Native
./scripts/test_platform.sh

# Run specific phase
./scripts/test_platform.sh --phase 2  # Unit tests only

# Skip Docker tests
./scripts/test_platform.sh --skip-docker

# Verbose output
./scripts/test_platform.sh --verbose
```

---

## Test Summary Checklist

Use this checklist to track testing progress:

### Base Environment
- [ ] Pixi/Python environment configured
- [ ] PostgreSQL running and accessible
- [ ] Redis running and accessible
- [ ] Environment variables set
- [ ] Database migrations applied

### Unit Tests
- [ ] All unit tests passing
- [ ] User model tests pass
- [ ] Organization model tests pass
- [ ] Test coverage > 80%

### Model Layer
- [ ] Models create successfully
- [ ] Relationships work correctly
- [ ] Database constraints enforced
- [ ] Model methods work

### API Tests
- [ ] JWT authentication works
- [ ] API endpoints accessible
- [ ] Admin interface loads
- [ ] API documentation available

### Integration Tests
- [ ] Multi-tenancy isolation works
- [ ] RBAC permissions enforced
- [ ] Users can't access other orgs

### Advanced Features
- [ ] Celery worker running
- [ ] Async tasks execute
- [ ] Worker image builds

---

## Troubleshooting

### Unit Tests Failing

```bash
# Run with verbose output
pytest -vv

# Run with print statements
pytest -s

# Run specific failing test
pytest apps/users/tests/test_models.py::TestUserModel::test_create_user -vv

# Check for missing fixtures
pytest --fixtures apps/users/tests/
```

### Database Issues

```bash
# Reset test database
pixi run shell
python manage.py flush
python manage.py migrate

# Or drop and recreate
dropdb review_pro
createdb review_pro
pixi run migrate
```

### Import Errors

```bash
# Check Python path
pixi run python -c "import sys; print('\n'.join(sys.path))"

# Verify installed packages
pixi list | grep django

# Reinstall environment
rm -rf .pixi
pixi install
```

### Pytest Configuration Issues

```bash
# Check pytest finds tests
pytest --collect-only

# Verify pytest.ini
cat backend/pytest.ini

# Run from correct directory
cd backend
pytest
```

---

## Next Steps

After all tests pass:

1. **Review Documentation:**
   - [Architecture ADRs](./docs/architecture/README.md)
   - [API Documentation](http://localhost:8000/api/docs/)

2. **Enable Advanced Features:**
   - Row-Level Security (see docs/ROW_LEVEL_SECURITY.md)
   - Rate Limiting (see docs/RATE_LIMITING.md)

3. **Deploy:**
   - Configure production environment
   - Set up CI/CD pipeline
   - Deploy to staging/production

---

## Additional Resources

- [Quick Start Guide](./QUICKSTART.md) - Native development setup
- [Docker Guide](./DOCKER_GUIDE.md) - Docker development setup
- [Pytest Documentation](https://docs.pytest.org/)
- [Django Testing Documentation](https://docs.djangoproject.com/en/5.0/topics/testing/)
