# ADR-006: Data Model Normalization

**Status:** Accepted
**Date:** 2025-11-13
**Deciders:** Engineering Team
**Technical Story:** Database schema design for security analysis platform

## Context and Problem Statement

Our platform needs to track:
- **Organizations** (tenants)
- **Projects** (repositories)
- **Branches** within projects
- **Scans** performed on branches
- **Findings** discovered by scans

A key decision is **branch tracking**: should branches be normalized into a separate table, or stored as a JSONB array in the `projects` table?

This decision affects query performance, data integrity, and feature development (e.g., per-branch metrics, branch lifecycle management).

## Decision Drivers

- **Query efficiency:** Fast lookups of "findings on branch X"
- **Data integrity:** Foreign key constraints prevent orphaned data
- **Feature requirements:** Track per-branch metadata (last scan time, finding counts)
- **Normalization principles:** Avoid data duplication, maintain consistency
- **Schema evolution:** Easy to add branch-related features in future

## Considered Options

### Option 1: JSONB Array in Projects Table

Store branches as a JSON array column in `projects` table.

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    org_id UUID NOT NULL,
    repo_url TEXT NOT NULL,
    default_branch TEXT DEFAULT 'main',
    branches JSONB,  -- ["main", "develop", "feature/auth"]
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE findings (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id),
    branch_name TEXT NOT NULL,  -- No foreign key constraint
    -- ...
);
```

**Pros:**
- Fewer tables (simpler at first glance)
- Easy to get all branches for a project (single query)

**Cons:**
- ❌ No foreign key constraint (can reference non-existent branch)
- ❌ Can't enforce unique branch names per project
- ❌ Hard to query "all findings on branch X across all projects"
- ❌ Can't track per-branch metadata (last scan time, finding count)
- ❌ Updating a single branch requires rewriting entire array
- ❌ Can't index into array elements efficiently
- ❌ No way to track branch lifecycle (created, deleted, merged)

### Option 2: Normalized Branches Table

Create a separate `branches` table with foreign key from `findings`.

```sql
CREATE TABLE branches (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    last_commit_sha TEXT,
    last_scanned_at TIMESTAMPTZ,
    finding_count INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(project_id, name)
);

CREATE TABLE findings (
    id UUID PRIMARY KEY,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    project_id UUID NOT NULL,
    -- ...
);
```

**Pros:**
- ✅ Foreign key constraint ensures referential integrity
- ✅ Unique constraint on (project_id, name) prevents duplicates
- ✅ Can track per-branch metadata
- ✅ Easy to query "all findings on branch X" (JOIN on branch_id)
- ✅ Can track branch lifecycle (soft delete, archived_at column)
- ✅ Can add branch-related features (default branch, protected branches)
- ✅ Efficient indexes on branch columns

**Cons:**
- One more table to manage (minor)
- JOINs required to get branch name (mitigated by proper indexing)

## Decision Outcome

**Chosen option:** Option 2 - Normalized `branches` table.

### Justification

1. **Branches are first-class entities** with their own lifecycle (created, updated, deleted, merged)
2. **Foreign key constraints prevent data integrity issues** (no orphaned findings)
3. **Per-branch metrics are essential** (last scan time, finding counts, trends)
4. **Query performance:** `SELECT * FROM findings WHERE branch_id = X` is faster than JSON array filtering
5. **Future-proof:** Easy to add branch-related features (protected branches, default branch, branch policies)

### Complete Database Schema

```sql
-- Organizations (tenants)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,  -- URL-friendly name
    github_installation_id BIGINT,  -- GitHub App installation ID
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_organizations_slug ON organizations(slug);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

-- Organization memberships (many-to-many)
CREATE TABLE organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(org_id, user_id)
);

CREATE INDEX idx_org_members_org ON organization_members(org_id);
CREATE INDEX idx_org_members_user ON organization_members(user_id);

-- Row-level security policies
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON organizations
    USING (id = current_setting('app.current_org_id', true)::uuid);

CREATE POLICY member_access ON organization_members
    USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Projects (repositories)
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    repo_url TEXT NOT NULL,  -- https://github.com/org/repo
    default_branch TEXT DEFAULT 'main',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(org_id, repo_url)
);

CREATE INDEX idx_projects_org ON projects(org_id, created_at DESC);

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON projects
    USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Branches (normalized)
CREATE TABLE branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    last_commit_sha TEXT,
    last_scanned_at TIMESTAMPTZ,

    -- Aggregated metrics
    finding_count INT DEFAULT 0,
    critical_finding_count INT DEFAULT 0,
    high_finding_count INT DEFAULT 0,

    -- Lifecycle
    is_default BOOLEAN DEFAULT false,
    is_protected BOOLEAN DEFAULT false,
    archived_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(project_id, name)
);

CREATE INDEX idx_branches_project ON branches(project_id, name);
CREATE INDEX idx_branches_last_scanned ON branches(project_id, last_scanned_at DESC NULLS LAST);

-- Scans
CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL,  -- Denormalized for RLS
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,

    commit_sha TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),

    -- SARIF data (see ADR-005)
    sarif_summary JSONB,
    sarif_url TEXT,

    -- Progress tracking
    progress_percentage INT DEFAULT 0,
    current_step TEXT,

    -- Timestamps
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_scans_org_project ON scans(org_id, project_id, created_at DESC);
CREATE INDEX idx_scans_branch ON scans(branch_id, created_at DESC);
CREATE INDEX idx_scans_status ON scans(status) WHERE status IN ('pending', 'running');

ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON scans
    USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Findings
CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    org_id UUID NOT NULL,  -- Denormalized for RLS
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,

    -- Location
    file_path TEXT NOT NULL,
    line_number INT,
    line_end_number INT,
    column_number INT,
    column_end_number INT,

    -- Details
    rule_id TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    message TEXT NOT NULL,

    -- Metadata (small JSONB)
    metadata JSONB,

    -- SARIF reference
    sarif_url TEXT,
    sarif_result_index INT,

    -- Deduplication (see ADR-002)
    fingerprint_hash TEXT GENERATED ALWAYS AS (
        encode(
            sha256(
                (file_path || ':' || COALESCE(line_number::text, '0') || ':' || rule_id)::bytea
            ),
            'hex'
        )
    ) STORED,

    -- Lifecycle
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_findings_org_project ON findings(org_id, project_id, severity, resolved_at);
CREATE INDEX idx_findings_branch ON findings(branch_id, severity, resolved_at);
CREATE INDEX idx_findings_dedup ON findings(org_id, project_id, fingerprint_hash) WHERE resolved_at IS NULL;
CREATE INDEX idx_findings_file ON findings(org_id, file_path, resolved_at);
CREATE INDEX idx_findings_severity ON findings(org_id, severity, created_at DESC) WHERE resolved_at IS NULL;

ALTER TABLE findings ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON findings
    USING (org_id = current_setting('app.current_org_id', true)::uuid);
```

### Django Models

```python
# models.py
from django.db import models
from django.utils import timezone
import uuid

class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    github_installation_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organizations'
        ordering = ['name']

class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    password_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'

class OrganizationMember(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organization_members'
        unique_together = ['organization', 'user']

class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    org_id = models.UUIDField()  # Denormalized for RLS
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    repo_url = models.URLField()
    default_branch = models.CharField(max_length=255, default='main')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projects'
        unique_together = ['organization', 'repo_url']
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.org_id:
            self.org_id = self.organization_id
        super().save(*args, **kwargs)

class Branch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    last_commit_sha = models.CharField(max_length=40, null=True, blank=True)
    last_scanned_at = models.DateTimeField(null=True, blank=True)

    # Aggregated metrics
    finding_count = models.IntegerField(default=0)
    critical_finding_count = models.IntegerField(default=0)
    high_finding_count = models.IntegerField(default=0)

    # Lifecycle
    is_default = models.BooleanField(default=False)
    is_protected = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'branches'
        unique_together = ['project', 'name']
        ordering = ['-last_scanned_at']

    @property
    def is_archived(self):
        return self.archived_at is not None

class Scan(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    org_id = models.UUIDField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='scans')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='scans')

    commit_sha = models.CharField(max_length=40)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    sarif_summary = models.JSONField(null=True, blank=True)
    sarif_url = models.TextField(null=True, blank=True)

    progress_percentage = models.IntegerField(default=0)
    current_step = models.CharField(max_length=255, null=True, blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'scans'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.org_id:
            self.org_id = self.project.org_id
        super().save(*args, **kwargs)

class Finding(models.Model):
    SEVERITY_CHOICES = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('info', 'Info'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    scan = models.ForeignKey(Scan, on_delete=models.CASCADE, related_name='findings')
    org_id = models.UUIDField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)

    # Location
    file_path = models.TextField()
    line_number = models.IntegerField(null=True, blank=True)
    line_end_number = models.IntegerField(null=True, blank=True)
    column_number = models.IntegerField(null=True, blank=True)
    column_end_number = models.IntegerField(null=True, blank=True)

    # Details
    rule_id = models.CharField(max_length=255)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    message = models.TextField()

    # Metadata
    metadata = models.JSONField(null=True, blank=True)

    # SARIF reference
    sarif_url = models.TextField(null=True, blank=True)
    sarif_result_index = models.IntegerField(null=True, blank=True)

    # Fingerprint (generated by DB)
    fingerprint_hash = models.CharField(max_length=64, editable=False)

    # Lifecycle
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'findings'
        ordering = ['-severity', 'file_path']

    def save(self, *args, **kwargs):
        if not self.org_id:
            self.org_id = self.project.org_id
        super().save(*args, **kwargs)

    @property
    def is_resolved(self):
        return self.resolved_at is not None
```

### Example Queries

```python
# Get all findings for a branch
findings = Finding.objects.filter(
    branch_id=branch_id,
    resolved_at__isnull=True
).order_by('-severity', 'file_path')

# Get branch metrics
branch = Branch.objects.annotate(
    total_findings=Count('findings', filter=Q(findings__resolved_at__isnull=True)),
    critical_findings=Count('findings', filter=Q(findings__severity='critical', findings__resolved_at__isnull=True))
).get(id=branch_id)

# Get all branches with recent scans
branches = Branch.objects.filter(
    project_id=project_id,
    last_scanned_at__gte=timezone.now() - timedelta(days=7)
).order_by('-last_scanned_at')

# Get stale branches (not scanned in 90 days)
stale_branches = Branch.objects.filter(
    project_id=project_id,
    last_scanned_at__lt=timezone.now() - timedelta(days=90)
)

# Archive stale branches
stale_branches.update(archived_at=timezone.now())
```

## Consequences

### Positive

- **Data integrity:** Foreign key constraints prevent orphaned findings
- **Query performance:** Indexed branch_id enables fast lookups
- **Per-branch metrics:** Easy to aggregate findings, track trends
- **Branch lifecycle:** Can track creation, archival, deletion
- **Future features:** Easy to add branch policies, default branches, protected branches

### Negative

- **One more table:** Slightly more complex schema (but worth it)
- **JOINs required:** Need to JOIN to get branch name (mitigated by proper indexing and Django ORM)

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Too many branches bloat database | Archive stale branches; soft delete with archived_at |
| Deleting branch deletes findings | Cascade delete is intentional; can add soft delete if needed |
| Branch renaming breaks historical data | Keep branch renames as new records; add previous_name field |

## Related Decisions

- **ADR-001:** Multi-tenancy (org_id denormalized in tables for RLS)
- **ADR-002:** Finding deduplication (fingerprint includes branch context)
- **ADR-005:** SARIF storage (scan references branch_id)

## References

- [Database Normalization](https://en.wikipedia.org/wiki/Database_normalization)
- [PostgreSQL Foreign Keys](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-FK)
- [Django Models Best Practices](https://docs.djangoproject.com/en/stable/topics/db/models/)
- [PostgreSQL Index Types](https://www.postgresql.org/docs/current/indexes-types.html)
