# ADR-001: Multi-Tenancy Model

**Status:** Accepted
**Date:** 2025-11-13
**Deciders:** Engineering Team
**Technical Story:** Multi-tenant architecture for security analysis platform

## Context and Problem Statement

Our security analysis platform needs to support multiple organizations (tenants) with strict data isolation requirements. We need to decide between two primary PostgreSQL multi-tenancy approaches:

1. **Schema-per-tenant:** Each organization gets its own PostgreSQL schema
2. **Shared schema with org_id:** Single schema with organization ID filtering

Each approach has significant implications for data isolation, operational complexity, query performance, and regulatory compliance.

## Decision Drivers

- **Data isolation:** Prevent accidental cross-tenant data leaks
- **Operational simplicity:** Database migrations, backups, monitoring
- **Query performance:** Efficient queries within and across tenants
- **Scalability:** Support for thousands of organizations
- **Compliance:** Meet SOC 2, ISO 27001 requirements for data isolation
- **Cost:** Infrastructure and operational overhead

## Considered Options

### Option 1: Schema-per-Tenant

Each organization gets a dedicated PostgreSQL schema (e.g., `org_12345`, `org_67890`).

**Pros:**
- Strong logical isolation at the database level
- Simpler to understand data boundaries
- Easier to export/backup individual tenant data
- Can set per-schema resource limits
- Meets strict regulatory requirements (HIPAA, FedRAMP)
- Schema-level permissions provide defense-in-depth

**Cons:**
- Migration complexity scales with tenant count (N migrations for N tenants)
- Cross-tenant analytics and admin queries become complex
- PostgreSQL can handle thousands of schemas, but management overhead grows
- Connection pooling complexity (must route to correct schema)
- Increased backup/restore time as tenant count grows
- Harder to implement shared reference data (e.g., rule definitions)

### Option 2: Shared Schema with org_id Filtering (with Row-Level Security)

Single schema with `org_id` column on all multi-tenant tables, enforced by PostgreSQL Row-Level Security (RLS).

**Pros:**
- Single migration path for all tenants
- Simpler backup/restore operations
- Easy cross-tenant analytics for platform insights
- Connection pooling straightforward
- Efficient use of database resources
- Simple to implement shared reference data
- Good performance with proper indexing (`org_id` prefix in indexes)

**Cons:**
- Application bugs could leak data across tenants (mitigated by RLS)
- All tenants share same resource pool (need connection limits)
- Requires discipline to add `org_id` to all queries
- More complex compliance auditing

## Decision Outcome

**Chosen option:** Option 2 - Shared schema with `org_id` filtering and PostgreSQL Row-Level Security (RLS).

### Justification

For a B2B SaaS security analysis platform, the operational benefits of a shared schema outweigh the isolation benefits of schema-per-tenant. Key reasons:

1. **Operational simplicity:** Running migrations across thousands of organizations would be prohibitively slow and risky
2. **PostgreSQL RLS provides database-level enforcement:** Even if application code has bugs, RLS prevents cross-tenant data access
3. **Better fits our security scanning use case:** Not handling PII/PHI that requires schema-level isolation
4. **Scales to thousands of organizations** without operational overhead growing linearly
5. **Enables platform-wide analytics** for security trend analysis, benchmarking

### Implementation Strategy

#### 1. Database Layer

Enable RLS on all multi-tenant tables:

```sql
-- Example for findings table
CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL,
    project_id UUID NOT NULL,
    -- ... other columns
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable Row-Level Security
ALTER TABLE findings ENABLE ROW LEVEL SECURITY;

-- Create policy for tenant isolation
CREATE POLICY tenant_isolation ON findings
    USING (org_id = current_setting('app.current_org_id')::uuid);

-- Create policy for platform admins (can see all orgs)
CREATE POLICY admin_access ON findings
    USING (
        current_setting('app.user_role', true) = 'platform_admin'
    );

-- Composite index for efficient queries
CREATE INDEX idx_findings_org_created ON findings(org_id, created_at DESC);
```

#### 2. Application Layer (Django)

Use middleware to set the organization context for each request:

```python
# middleware.py
class TenantContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            org_id = request.user.organization_id

            # Set PostgreSQL session variable for RLS
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('app.current_org_id', %s, true)",
                    [str(org_id)]
                )

        response = self.get_response(request)
        return response
```

```python
# models.py - Base class for all tenant-scoped models
class TenantModel(models.Model):
    org_id = models.UUIDField(db_index=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Ensure org_id is set
        if not self.org_id:
            raise ValueError("org_id must be set")
        super().save(*args, **kwargs)
```

#### 3. Testing Strategy

- Unit tests must set `app.current_org_id` in test database
- Integration tests verify cross-tenant data isolation
- Security tests attempt SQL injection to bypass `org_id` filters
- Load tests verify query performance with org_id filtering

#### 4. Migration Path

All new tables must:
1. Include `org_id UUID NOT NULL` column
2. Have RLS enabled from day one
3. Include composite indexes with `org_id` as first column
4. Be documented in schema docs

### Compliance Considerations

For SOC 2 Type II and ISO 27001 compliance:

- **Audit logging:** All queries log `org_id` context
- **RLS enforcement:** Database-level controls auditable by third parties
- **Separation of duties:** Platform admins require separate policy
- **Data export:** Can generate per-tenant data dumps for GDPR requests
- **Breach notification:** Can identify affected tenants via `org_id`

## Consequences

### Positive

- Faster database migrations (single schema)
- Simpler backup/restore operations
- Easier to implement cross-tenant features (benchmarking, aggregated insights)
- Lower operational complexity
- Better resource utilization

### Negative

- Requires discipline to always filter by `org_id`
- All tenants share database resource pool (mitigate with connection limits)
- Application-level bugs could expose data (mitigate with RLS)
- More complex compliance documentation (need to explain RLS)

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Application forgets to filter by org_id | RLS enforces at DB level; code review checklist |
| SQL injection bypasses org_id filter | Parameterized queries; security testing; RLS as backstop |
| Performance degrades with large org_id cardinality | Composite indexes with org_id prefix; partition by org_id if needed |
| Tenant "noisy neighbor" impacts others | Connection pooling limits; query timeouts; separate worker pools |

## Related Decisions

- **ADR-006:** Data model normalization (all foreign keys include org_id)
- **ADR-007:** Authentication & authorization (org_id derived from JWT claims)
- **ADR-008:** Rate limiting (per-org quotas enforced at API layer)

## References

- [PostgreSQL Row-Level Security Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Django Multi-Tenant Patterns](https://books.agiliq.com/projects/django-multi-tenant/en/latest/)
- [OWASP Multi-Tenancy Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multitenant_Architecture_Cheat_Sheet.html)
- [AWS SaaS Multi-Tenant Isolation Strategies](https://docs.aws.amazon.com/whitepapers/latest/saas-architecture-fundamentals/tenant-isolation.html)
