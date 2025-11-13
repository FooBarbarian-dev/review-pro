# ADR-002: Finding Deduplication Strategy

**Status:** Accepted
**Date:** 2025-11-13
**Deciders:** Engineering Team
**Technical Story:** Deduplicating security findings across scans

## Context and Problem Statement

When running security scans across multiple commits, branches, and time periods, the same security finding (e.g., "SQL injection on line 45 of users.py") appears repeatedly. We need to:

1. **Identify duplicate findings** efficiently across millions of records
2. **Decide where to compute fingerprints** (application layer vs database)
3. **Handle hash collisions** gracefully (fingerprints are not unique)
4. **Track finding lifecycle** (when did it first appear, is it still present, was it fixed)

The key decision is whether to compute fingerprints in Django (application layer) or PostgreSQL (database layer), and how to handle the inevitable hash collisions.

## Decision Drivers

- **Performance:** Deduplication must not slow down ingestion
- **Consistency:** Fingerprints must be computed the same way every time
- **Collision handling:** Hash collisions will occur, need robust detection
- **Maintainability:** Logic should be version-controlled and testable
- **Flexibility:** Ability to change fingerprint algorithm over time

## Considered Options

### Option 1: Compute Fingerprint in Django

Calculate fingerprint in Python before inserting into database.

```python
def compute_fingerprint(finding):
    content = f"{finding.file_path}:{finding.line_number}:{finding.rule_id}"
    return hashlib.sha256(content.encode()).hexdigest()

# Usage
finding.fingerprint_hash = compute_fingerprint(finding)
finding.save()
```

**Pros:**
- Full control in application code
- Easy to unit test
- Can use complex logic (normalize paths, handle edge cases)
- Can use different algorithms per finding type

**Cons:**
- Manual SQL inserts bypass fingerprint computation
- Logic duplicated if multiple services write findings
- Harder to ensure consistency across application versions
- Database has no knowledge of fingerprint logic

### Option 2: Compute Fingerprint in PostgreSQL (Generated Column)

Use PostgreSQL generated columns to compute fingerprints automatically.

```sql
CREATE TABLE findings (
    id UUID PRIMARY KEY,
    file_path TEXT NOT NULL,
    line_number INT,
    rule_id TEXT NOT NULL,
    fingerprint_hash TEXT GENERATED ALWAYS AS (
        encode(
            sha256(
                (file_path || ':' || COALESCE(line_number::text, '') || ':' || rule_id)::bytea
            ),
            'hex'
        )
    ) STORED
);
```

**Pros:**
- Computed automatically on every insert/update
- Consistency guaranteed (same SQL logic for all writes)
- Defined in migrations (version-controlled)
- Works for manual SQL and bulk imports
- Can create indexes on generated column

**Cons:**
- Limited to SQL expressions (harder to do complex transformations)
- Changing algorithm requires migration
- Less flexible than Python code

### Option 3: Hybrid Approach

Use PostgreSQL for deterministic fingerprints, Django for collision detection and complex deduplication logic.

**Pros:**
- Best of both worlds: DB guarantees consistency, app handles edge cases
- Generated column ensures fingerprints never missed
- Application can perform deep comparison on collision
- Migration-based fingerprint versioning

**Cons:**
- Slightly more complex (two layers)
- Need to document the two-phase approach

## Decision Outcome

**Chosen option:** Option 3 - Hybrid approach (PostgreSQL generated column + Django collision handling).

### Justification

1. **PostgreSQL generates consistent fingerprints** for all inserts (even bulk loads, manual SQL)
2. **Django handles collisions** by comparing full finding content when fingerprints match
3. **Fingerprint algorithm is version-controlled** in migrations, making changes explicit
4. **Best performance:** Database can index and filter by fingerprint, app only compares on hash match

### Implementation Strategy

#### 1. Database Schema

```sql
CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL,
    project_id UUID NOT NULL,
    branch_id UUID NOT NULL,

    -- Finding location
    file_path TEXT NOT NULL,
    line_number INT,
    column_number INT,

    -- Finding details
    rule_id TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    message TEXT,

    -- Deduplication fingerprint (generated column)
    fingerprint_hash TEXT GENERATED ALWAYS AS (
        encode(
            sha256(
                (
                    file_path || ':' ||
                    COALESCE(line_number::text, '0') || ':' ||
                    rule_id
                )::bytea
            ),
            'hex'
        )
    ) STORED,

    -- Metadata
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for efficient deduplication lookups
CREATE INDEX idx_findings_dedup ON findings(org_id, project_id, fingerprint_hash)
WHERE resolved_at IS NULL;

-- Index for tracking finding lifecycle
CREATE INDEX idx_findings_lifecycle ON findings(org_id, first_seen_at, resolved_at);
```

#### 2. Django Model

```python
# models.py
from django.db import models
from django.utils import timezone

class Finding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    org_id = models.UUIDField(db_index=True)
    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE)

    # Location
    file_path = models.TextField()
    line_number = models.IntegerField(null=True)
    column_number = models.IntegerField(null=True)

    # Details
    rule_id = models.CharField(max_length=255)
    severity = models.CharField(max_length=20, choices=[
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('info', 'Info'),
    ])
    message = models.TextField()

    # Fingerprint (generated by DB, read-only in Django)
    fingerprint_hash = models.CharField(max_length=64, editable=False)

    # Lifecycle
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'findings'
        indexes = [
            models.Index(fields=['org_id', 'project', 'fingerprint_hash']),
        ]

    def is_duplicate_of(self, other):
        """
        Deep comparison for hash collision detection.
        Only called when fingerprints match.
        """
        return (
            self.file_path == other.file_path and
            self.line_number == other.line_number and
            self.rule_id == other.rule_id and
            self.message == other.message
        )
```

#### 3. Deduplication Service

```python
# services/finding_deduplicator.py
from django.db import transaction
from django.utils import timezone
from .models import Finding

class FindingDeduplicator:
    """
    Handles deduplication logic when ingesting new findings.
    Uses two-phase approach:
    1. Fast fingerprint lookup (DB-generated hash)
    2. Deep comparison on hash collision (application logic)
    """

    @transaction.atomic
    def ingest_finding(self, org_id, project_id, branch_id, finding_data):
        """
        Ingest a finding, deduplicating against existing findings.

        Returns:
            (Finding, created: bool) - The finding and whether it was newly created
        """
        # Create temporary finding to get fingerprint
        # (Django will read the generated column after insert)
        temp_finding = Finding(
            org_id=org_id,
            project_id=project_id,
            branch_id=branch_id,
            file_path=finding_data['file_path'],
            line_number=finding_data.get('line_number'),
            column_number=finding_data.get('column_number'),
            rule_id=finding_data['rule_id'],
            severity=finding_data['severity'],
            message=finding_data['message'],
        )

        # Phase 1: Fast fingerprint lookup
        existing_findings = Finding.objects.filter(
            org_id=org_id,
            project_id=project_id,
            fingerprint_hash=models.F('fingerprint_hash'),  # Will use DB-generated value
            resolved_at__isnull=True
        ).select_for_update()

        # Phase 2: Deep comparison on hash collision
        for existing in existing_findings:
            if temp_finding.is_duplicate_of(existing):
                # Update last_seen timestamp
                existing.last_seen_at = timezone.now()
                existing.save(update_fields=['last_seen_at', 'updated_at'])
                return existing, False

        # Not a duplicate, insert new finding
        temp_finding.save()
        return temp_finding, True

    def mark_resolved(self, org_id, project_id, branch_id, current_scan_findings):
        """
        Mark findings as resolved if they don't appear in current scan.

        Args:
            current_scan_findings: Set of fingerprint_hash values from current scan
        """
        findings_to_resolve = Finding.objects.filter(
            org_id=org_id,
            project_id=project_id,
            branch_id=branch_id,
            resolved_at__isnull=True
        ).exclude(
            fingerprint_hash__in=current_scan_findings
        )

        findings_to_resolve.update(
            resolved_at=timezone.now(),
            updated_at=timezone.now()
        )

        return findings_to_resolve.count()
```

#### 4. Scan Ingestion Workflow

```python
# services/scan_ingester.py
from .finding_deduplicator import FindingDeduplicator

def ingest_sarif_results(org_id, project_id, branch_id, sarif_results):
    """
    Ingest SARIF scan results with deduplication.
    """
    deduplicator = FindingDeduplicator()

    current_scan_fingerprints = set()
    new_count = 0
    updated_count = 0

    for result in sarif_results:
        finding_data = {
            'file_path': result['locations'][0]['physicalLocation']['artifactLocation']['uri'],
            'line_number': result['locations'][0]['physicalLocation']['region'].get('startLine'),
            'rule_id': result['ruleId'],
            'severity': map_severity(result['level']),
            'message': result['message']['text'],
        }

        finding, created = deduplicator.ingest_finding(
            org_id, project_id, branch_id, finding_data
        )

        # Track fingerprint for resolution logic
        current_scan_fingerprints.add(finding.fingerprint_hash)

        if created:
            new_count += 1
        else:
            updated_count += 1

    # Mark findings not in current scan as resolved
    resolved_count = deduplicator.mark_resolved(
        org_id, project_id, branch_id, current_scan_fingerprints
    )

    return {
        'new_findings': new_count,
        'existing_findings': updated_count,
        'resolved_findings': resolved_count,
    }
```

### Handling Fingerprint Algorithm Changes

When we need to change the fingerprint algorithm (e.g., to include column_number):

```sql
-- Migration: Update fingerprint algorithm
-- This will recompute all fingerprints

-- Step 1: Add version column to track algorithm
ALTER TABLE findings ADD COLUMN fingerprint_version INT DEFAULT 1;

-- Step 2: Create new fingerprint column with v2 algorithm
ALTER TABLE findings ADD COLUMN fingerprint_hash_v2 TEXT GENERATED ALWAYS AS (
    encode(
        sha256(
            (
                file_path || ':' ||
                COALESCE(line_number::text, '0') || ':' ||
                COALESCE(column_number::text, '0') || ':' ||
                rule_id
            )::bytea
        ),
        'hex'
    )
) STORED;

-- Step 3: Backfill version for existing rows
UPDATE findings SET fingerprint_version = 1;

-- Step 4: Create new index
CREATE INDEX idx_findings_dedup_v2 ON findings(org_id, project_id, fingerprint_hash_v2)
WHERE resolved_at IS NULL;

-- Step 5: Drop old column and rename (in separate migration after deploy)
ALTER TABLE findings DROP COLUMN fingerprint_hash;
ALTER TABLE findings RENAME COLUMN fingerprint_hash_v2 TO fingerprint_hash;
```

### Hash Collision Probability

With SHA-256 fingerprints (64 hex chars = 256 bits):

- **1 million findings:** ~0% collision probability
- **1 billion findings:** ~0.0000000001% collision probability
- **Birthday paradox applies:** Collisions likely after ~2^128 findings (astronomically improbable)

For our use case (< 100M findings per org), collisions are theoretical. However, the deep comparison in `is_duplicate_of()` handles them gracefully.

## Consequences

### Positive

- **Automatic fingerprinting:** Never forget to compute fingerprint
- **Consistent across all inserts:** Bulk loads, manual SQL, Django ORM all use same logic
- **Version-controlled algorithm:** Changes require migrations (good for auditability)
- **Fast deduplication:** Index on `(org_id, project_id, fingerprint_hash)` is very efficient
- **Graceful collision handling:** Deep comparison catches hash collisions
- **Finding lifecycle tracking:** Can see when finding first appeared and was resolved

### Negative

- **Less flexible fingerprint logic:** Limited to SQL expressions (can't easily call external libraries)
- **Migration required to change algorithm:** Can't A/B test fingerprint strategies easily
- **Two-phase deduplication adds complexity:** Need to understand both DB and app layer

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Fingerprint collisions cause false duplicates | Deep comparison in `is_duplicate_of()` catches collisions |
| Fingerprint algorithm produces different results across DB versions | Pin PostgreSQL version; integration tests verify fingerprint stability |
| Performance degrades with millions of findings | Composite index on `(org_id, project_id, fingerprint_hash)`; partition table by org_id if needed |
| Changing algorithm breaks historical deduplication | Version fingerprints; keep old algorithm for historical data |

## Related Decisions

- **ADR-001:** Multi-tenancy model (org_id is first column in deduplication index)
- **ADR-005:** SARIF storage (SARIF results are source of finding data)
- **ADR-006:** Data model normalization (branch_id foreign key for per-branch deduplication)

## References

- [PostgreSQL Generated Columns](https://www.postgresql.org/docs/current/ddl-generated-columns.html)
- [Birthday Paradox and Hash Collisions](https://en.wikipedia.org/wiki/Birthday_problem)
- [SARIF Specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
- [GitHub Advisory Database Fingerprinting](https://github.blog/2022-06-06-how-we-calculate-security-advisory-impact/)
