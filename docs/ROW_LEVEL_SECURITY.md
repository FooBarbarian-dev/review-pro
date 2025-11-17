# Row-Level Security (RLS) Setup Guide

**Status:** Optional - Defense-in-depth feature
**Priority:** Priority 3 (Advanced Feature)
**ADR:** ADR-001 Multi-Tenancy Model

---

## Overview

Row-Level Security (RLS) provides database-level enforcement of multi-tenancy isolation. This is a **defense-in-depth** measure that protects against data leakage even if application-level filtering fails.

### Benefits

✅ **Database-level isolation** - PostgreSQL enforces access control
✅ **Defense-in-depth** - Protection even if app code has bugs
✅ **Audit trail** - Clear security policies in database
✅ **Performance** - PostgreSQL optimizes filtered queries

### Trade-offs

⚠️ **Complexity** - Requires session variable management
⚠️ **Testing overhead** - More complex to test
⚠️ **Debugging** - Can be harder to troubleshoot
⚠️ **Not required for MVP** - Application-level filtering sufficient

---

## Prerequisites

Before enabling RLS:

1. ✅ Database migrations completed (Priority 1)
2. ✅ Application-level multi-tenancy filtering working (Priority 1)
3. ✅ All tests passing with app-level filtering
4. ✅ PostgreSQL 12+ (RLS support)

**⚠️ WARNING:** Do NOT enable RLS until application-level filtering is tested and working. RLS is defense-in-depth, not a replacement for proper application security.

---

## Installation

### Step 1: Apply RLS SQL Script

Run the SQL script to create RLS policies:

```bash
# Using psql directly
psql -U postgres -d secanalysis -f backend/apps/organizations/sql/row_level_security.sql

# OR using Django dbshell
docker-compose exec web python manage.py dbshell < backend/apps/organizations/sql/row_level_security.sql
```

### Step 2: Enable RLS Middleware

Add the middleware to `backend/config/settings.py`:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # Add RLS middleware AFTER authentication
    'apps.organizations.middleware.RowLevelSecurityMiddleware',
]
```

**⚠️ IMPORTANT:** The middleware must come AFTER `AuthenticationMiddleware` so that `request.user` is available.

### Step 3: Verify Installation

Check that RLS is enabled:

```sql
-- Connect to database
psql -U postgres -d secanalysis

-- Check RLS is enabled on tables
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
AND rowsecurity = true
ORDER BY tablename;

-- Expected output: All main tables with rowsecurity = true
```

Check policies exist:

```sql
-- List all RLS policies
SELECT tablename, policyname
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- Expected: Multiple policies for each table
```

---

## Testing RLS

### Manual Testing

Test RLS enforcement via psql:

```sql
-- 1. Create test users and organizations
INSERT INTO users (id, email, password, is_active)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'user1@test.com', 'hashed', true),
    ('22222222-2222-2222-2222-222222222222', 'user2@test.com', 'hashed', true);

INSERT INTO organizations (id, name, slug)
VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Org A', 'org-a'),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Org B', 'org-b');

INSERT INTO organization_memberships (id, organization_id, user_id, role)
VALUES
    (gen_random_uuid(), 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', 'owner'),
    (gen_random_uuid(), 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '22222222-2222-2222-2222-222222222222', 'owner');

-- 2. Set RLS context to user1
SET SESSION app.current_user_id = '11111111-1111-1111-1111-111111111111';

-- 3. Query organizations - should only see Org A
SELECT id, name FROM organizations;
-- Expected: Only 'Org A'

-- 4. Try to access Org B - should return empty
SELECT * FROM organizations WHERE id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';
-- Expected: No rows

-- 5. Switch to user2
SET SESSION app.current_user_id = '22222222-2222-2222-2222-222222222222';

-- 6. Query organizations - should only see Org B
SELECT id, name FROM organizations;
-- Expected: Only 'Org B'

-- 7. Clear context (superuser mode)
RESET app.current_user_id;

-- 8. Query as superuser - should see all
SELECT id, name FROM organizations;
-- Expected: Both orgs
```

### Django Shell Testing

Test via Django shell:

```python
# Start shell
python manage.py shell

# Test RLS context manager
from apps.organizations.middleware import RLSContextManager
from apps.organizations.models import Organization
from apps.users.models import User

# Create test data
user1 = User.objects.create_user(email='test1@example.com', password='test')
user2 = User.objects.create_user(email='test2@example.com', password='test')

org1 = Organization.objects.create(name='Org 1', slug='org-1')
org2 = Organization.objects.create(name='Org 2', slug='org-2')

from apps.organizations.models import OrganizationMembership
OrganizationMembership.objects.create(organization=org1, user=user1, role='owner')
OrganizationMembership.objects.create(organization=org2, user=user2, role='owner')

# Test RLS filtering
with RLSContextManager(user1.id):
    orgs = Organization.objects.all()
    print(f"User1 sees {orgs.count()} organizations: {list(orgs)}")
    # Expected: 1 organization (org1)

with RLSContextManager(user2.id):
    orgs = Organization.objects.all()
    print(f"User2 sees {orgs.count()} organizations: {list(orgs)}")
    # Expected: 1 organization (org2)

# Without context (superuser)
orgs = Organization.objects.all()
print(f"Superuser sees {orgs.count()} organizations: {list(orgs)}")
# Expected: 2 organizations
```

### API Testing

Test via API requests:

```bash
# 1. Login as user1
TOKEN1=$(curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user1@test.com", "password": "testpass"}' \
  | jq -r '.access')

# 2. Get organizations - should only see user1's orgs
curl http://localhost:8000/api/v1/organizations/ \
  -H "Authorization: Bearer $TOKEN1"

# 3. Try to access other organization - should fail
curl http://localhost:8000/api/v1/organizations/org2-uuid/ \
  -H "Authorization: Bearer $TOKEN1"
# Expected: 404 Not Found (RLS filters it out)
```

---

## Monitoring & Debugging

### Check RLS is Active

```sql
-- Verify session variable is set
SHOW app.current_user_id;
-- Expected: User UUID or unset

-- Check if RLS is bypassed
SELECT current_setting('session_authorization');
-- Expected: Your database user
```

### Debug RLS Issues

If RLS is blocking legitimate queries:

```python
# Temporarily disable RLS for debugging
from apps.organizations.middleware import clear_rls_user

clear_rls_user()
# Now queries run without RLS

# Check what user context was set
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SHOW app.current_user_id")
    user_id = cursor.fetchone()
    print(f"Current RLS user: {user_id}")
```

### Performance Impact

RLS has minimal performance impact since PostgreSQL optimizes the policies. To verify:

```sql
-- Explain query without RLS
EXPLAIN ANALYZE SELECT * FROM organizations;

-- Set RLS context
SET SESSION app.current_user_id = 'some-uuid';

-- Explain query with RLS
EXPLAIN ANALYZE SELECT * FROM organizations;

-- Compare execution times
```

---

## Celery Workers & Background Tasks

Background tasks need RLS context too:

```python
from apps.organizations.middleware import RLSContextManager

@shared_task
def my_background_task(user_id, data):
    """Background task with RLS enforcement."""
    with RLSContextManager(user_id):
        # All queries filtered by RLS for this user
        orgs = Organization.objects.all()
        # Process...
```

For worker-initiated tasks (no specific user):

```python
# Option 1: Run as system (no RLS)
from apps.organizations.middleware import clear_rls_user

@shared_task
def system_task():
    clear_rls_user()  # Run as superuser
    # Process all organizations
    for org in Organization.objects.all():
        # ...

# Option 2: Iterate with RLS context per org
@shared_task
def multi_org_task():
    clear_rls_user()  # Get all orgs first
    orgs = Organization.objects.all()

    for org in orgs:
        # Get an owner/admin user for this org
        owner = org.memberships.filter(role='owner').first()
        if owner:
            with RLSContextManager(owner.user_id):
                # Process with RLS context
                pass
```

---

## Troubleshooting

### Issue: "RLS is blocking my queries"

**Solution:** Check that middleware is configured correctly:

```python
# In settings.py
MIDDLEWARE = [
    # ...
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Must be before RLS
    'apps.organizations.middleware.RowLevelSecurityMiddleware',  # After auth
]
```

### Issue: "Tests failing with RLS"

**Solution:** Update test fixtures to set RLS context:

```python
from apps.organizations.middleware import RLSContextManager

class MyTestCase(TestCase):
    def test_with_rls(self):
        user = User.objects.create_user(email='test@example.com')

        with RLSContextManager(user.id):
            # Test code with RLS context
            orgs = Organization.objects.all()
            self.assertEqual(orgs.count(), 1)
```

Or disable RLS for tests:

```python
# In test settings
MIDDLEWARE = [
    m for m in MIDDLEWARE
    if m != 'apps.organizations.middleware.RowLevelSecurityMiddleware'
]
```

### Issue: "Migrations fail with RLS enabled"

**Solution:** Disable RLS during migrations:

```sql
-- Disable RLS temporarily
ALTER TABLE organizations DISABLE ROW LEVEL SECURITY;
-- Run migrations
-- Re-enable RLS
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
```

---

## Rollback / Disable RLS

To remove RLS completely:

```bash
# 1. Remove middleware from settings.py

# 2. Drop RLS policies
psql -U postgres -d secanalysis <<EOF
DROP SCHEMA IF EXISTS rls CASCADE;

ALTER TABLE organizations DISABLE ROW LEVEL SECURITY;
ALTER TABLE organization_memberships DISABLE ROW LEVEL SECURITY;
ALTER TABLE repositories DISABLE ROW LEVEL SECURITY;
ALTER TABLE branches DISABLE ROW LEVEL SECURITY;
ALTER TABLE scans DISABLE ROW LEVEL SECURITY;
ALTER TABLE scan_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE quota_usage DISABLE ROW LEVEL SECURITY;
ALTER TABLE findings DISABLE ROW LEVEL SECURITY;
ALTER TABLE finding_comments DISABLE ROW LEVEL SECURITY;
ALTER TABLE finding_status_history DISABLE ROW LEVEL SECURITY;

-- Drop policies
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN SELECT policyname, tablename FROM pg_policies WHERE schemaname = 'public'
    LOOP
        EXECUTE 'DROP POLICY IF EXISTS ' || r.policyname || ' ON ' || r.tablename;
    END LOOP;
END $$;
EOF
```

---

## Best Practices

1. **✅ Test application-level filtering first** - RLS is defense-in-depth
2. **✅ Use RLS in production** - Extra security layer
3. **✅ Monitor RLS performance** - Should be negligible impact
4. **✅ Document RLS context** - Clear when context is set/cleared
5. **⚠️ Don't rely solely on RLS** - Application filtering is primary
6. **⚠️ Test RLS thoroughly** - Edge cases with permissions
7. **⚠️ Handle background tasks** - Set proper context

---

## References

- **ADR-001:** Multi-Tenancy Model
- **PostgreSQL RLS Docs:** https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- **Django Multi-tenancy:** https://django-tenants.readthedocs.io/
- **Security Best Practices:** OWASP Multi-tenancy Security Cheat Sheet

---

## Summary

- **Status:** Optional feature for defense-in-depth
- **When to enable:** After application-level filtering is tested
- **Performance:** Minimal impact
- **Complexity:** Medium (session management)
- **Benefit:** Protection against app-level filtering bugs
- **Risk:** Increases debugging complexity

**Recommendation:** Enable RLS in production after thorough testing, but application-level filtering is sufficient for MVP.
