# ADR-005: SARIF Storage Strategy

**Status:** Accepted
**Date:** 2025-11-13
**Deciders:** Engineering Team
**Technical Story:** How to store SARIF (Static Analysis Results Interchange Format) reports

## Context and Problem Statement

Security scanning tools output results in SARIF format (JSON-based standard). A single SARIF file can contain:
- Tool metadata (name, version, rules)
- Scan configuration
- Hundreds to thousands of findings (results)
- Code snippets and fix suggestions
- Graph data for data flow analysis

SARIF files can range from **a few KB to 100+ MB** for large codebases. We need to decide:

1. Store full SARIF in PostgreSQL JSONB column?
2. Store full SARIF in object storage (S3/MinIO)?
3. Hybrid: Store parsed findings in DB, full SARIF in object storage?

The decision impacts query performance, database size, storage costs, and developer experience.

## Decision Drivers

- **Query performance:** Fast queries for finding lists, filters, aggregations
- **Database size:** PostgreSQL performance degrades with large TOAST values
- **Storage cost:** Object storage is cheaper than database storage
- **Data integrity:** Need to preserve original SARIF for compliance/auditing
- **Developer experience:** Easy to query findings, download full SARIF when needed
- **Compliance:** Ability to export/archive full scan results

## Considered Options

### Option 1: Store Full SARIF in PostgreSQL JSONB

Store entire SARIF JSON document in a `sarif` JSONB column on `scans` or `findings` table.

```sql
CREATE TABLE scans (
    id UUID PRIMARY KEY,
    org_id UUID NOT NULL,
    project_id UUID NOT NULL,
    sarif JSONB NOT NULL,  -- Full SARIF document
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Query findings from SARIF
SELECT
    id,
    sarif->'runs'->0->'results' AS findings
FROM scans
WHERE org_id = '...';
```

**Pros:**
- All data in one place (database)
- Can query SARIF fields with `->>` and `->` operators
- ACID guarantees for SARIF data
- Simple backup/restore (PostgreSQL dump includes SARIF)

**Cons:**
- ❌ **SARIF files can be 10s-100s of MB** (degrades performance)
- ❌ PostgreSQL TOAST limit is 1GB per row, but perf degrades well before
- ❌ Can't efficiently stream large SARIF to client (must load entire row)
- ❌ Wastes database storage (SARIF rarely queried in full)
- ❌ Indexing large JSONB is expensive
- ❌ Database backups grow huge with SARIF data

### Option 2: Store Full SARIF in Object Storage Only

Store SARIF files in S3/MinIO, reference by URL. Parse findings into database table for querying.

```sql
CREATE TABLE scans (
    id UUID PRIMARY KEY,
    org_id UUID NOT NULL,
    project_id UUID NOT NULL,
    sarif_url TEXT NOT NULL,  -- s3://bucket/org_id/scan_id.sarif
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE findings (
    id UUID PRIMARY KEY,
    scan_id UUID NOT NULL REFERENCES scans(id),
    org_id UUID NOT NULL,
    file_path TEXT NOT NULL,
    line_number INT,
    rule_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT,
    -- Queryable fields extracted from SARIF
);
```

**Pros:**
- ✅ Database stays small (only extracted fields)
- ✅ Fast queries (indexed columns, not JSONB traversal)
- ✅ Object storage is cheaper ($0.023/GB vs $0.10+/GB for DB)
- ✅ Can stream SARIF from S3 to client (presigned URLs)
- ✅ Easy to archive old SARIFs to Glacier

**Cons:**
- Need to parse SARIF and extract findings (extra processing)
- SARIF and findings can get out of sync (two sources of truth)
- Requires object storage infrastructure (S3, MinIO, GCS)

### Option 3: Hybrid Approach

Store **extracted findings** in database (normalized), **summary metadata** in JSONB, **full SARIF** in object storage.

```sql
CREATE TABLE scans (
    id UUID PRIMARY KEY,
    org_id UUID NOT NULL,
    project_id UUID NOT NULL,
    branch_id UUID NOT NULL,

    -- Summary metadata (small, frequently accessed)
    sarif_summary JSONB,  -- Tool info, rule counts, scan config
    -- Example:
    -- {
    --   "tool": {"name": "semgrep", "version": "1.45.0"},
    --   "rules_count": 250,
    --   "results_count": 42,
    --   "scan_duration_ms": 12500
    -- }

    -- Full SARIF reference
    sarif_url TEXT NOT NULL,  -- s3://bucket/org_id/scan_id.sarif

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE findings (
    id UUID PRIMARY KEY,
    scan_id UUID NOT NULL REFERENCES scans(id),
    org_id UUID NOT NULL,
    project_id UUID NOT NULL,
    branch_id UUID NOT NULL,

    -- Normalized finding data (queryable)
    file_path TEXT NOT NULL,
    line_number INT,
    rule_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT,

    -- Small metadata JSONB (fix suggestions, tags, etc.)
    metadata JSONB,  -- Max ~10KB per finding

    -- Reference to full SARIF result
    sarif_url TEXT NOT NULL,  -- Same as scan.sarif_url
    sarif_result_index INT,  -- Index in SARIF runs[0].results array

    fingerprint_hash TEXT GENERATED ALWAYS AS (...) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Pros:**
- ✅ Best query performance (indexed, normalized columns)
- ✅ Database stays small (<10KB per finding vs 1-10MB per SARIF)
- ✅ Can query across scans efficiently (aggregations, filters)
- ✅ Full SARIF available when needed (presigned URL download)
- ✅ Small metadata JSONB for flexible fields
- ✅ Cheaper storage (object storage for large files)

**Cons:**
- More complex ingestion (parse SARIF, extract findings, upload to S3)
- Two sources of truth (mitigated by storing `sarif_result_index` for reconciliation)
- Requires object storage infrastructure

## Decision Outcome

**Chosen option:** Option 3 - Hybrid approach (normalized findings in DB, full SARIF in object storage).

### Justification

1. **Query performance is critical:** Users need fast filtering/searching across findings
2. **Database size matters:** Storing full SARIF would bloat PostgreSQL
3. **Storage cost:** Object storage is 4-5x cheaper than database storage
4. **Compliance:** Can always retrieve full SARIF from S3 for audits
5. **Streaming:** Can generate presigned URLs for direct browser downloads

### Implementation Strategy

#### 1. Database Schema

```sql
-- Scans table
CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,

    -- Scan metadata
    commit_sha TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),

    -- SARIF summary (small JSONB, frequently accessed)
    sarif_summary JSONB,
    -- Example structure:
    -- {
    --   "tool": {"name": "semgrep", "version": "1.45.0", "uri": "https://semgrep.dev"},
    --   "invocations": [{"executionSuccessful": true, "startTimeUtc": "..."}],
    --   "rules": [{"id": "javascript.lang.security.audit.sql-injection", "level": "error"}],
    --   "results_count": 42,
    --   "scan_duration_seconds": 12.5
    -- }

    -- Full SARIF reference
    sarif_url TEXT NOT NULL,  -- s3://prod-sarif/org_id/scan_id.sarif

    -- Timestamps
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_scans_org_project ON scans(org_id, project_id, created_at DESC);
CREATE INDEX idx_scans_status ON scans(status) WHERE status IN ('pending', 'running');

-- Findings table (normalized, queryable)
CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    org_id UUID NOT NULL,
    project_id UUID NOT NULL,
    branch_id UUID NOT NULL,

    -- Finding location
    file_path TEXT NOT NULL,
    line_number INT,
    line_end_number INT,
    column_number INT,
    column_end_number INT,

    -- Finding details
    rule_id TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    message TEXT NOT NULL,

    -- Small metadata (fix suggestions, tags, related locations)
    metadata JSONB,
    -- Example:
    -- {
    --   "kind": "pass",
    --   "fixes": [{"description": "Use parameterized query", "edits": [...]}],
    --   "code_flows": [...],
    --   "tags": ["cwe-89", "sql-injection"]
    -- }

    -- Reference back to SARIF
    sarif_url TEXT NOT NULL,
    sarif_result_index INT,  -- Index in runs[0].results array

    -- Deduplication
    fingerprint_hash TEXT GENERATED ALWAYS AS (...) STORED,

    -- Lifecycle tracking
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_findings_org_project ON findings(org_id, project_id, severity, resolved_at);
CREATE INDEX idx_findings_dedup ON findings(org_id, project_id, fingerprint_hash);
CREATE INDEX idx_findings_file ON findings(org_id, file_path, resolved_at);
```

#### 2. SARIF Upload to S3

```python
# services/sarif_storage.py
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
import json

class SarifStorage:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket = settings.SARIF_BUCKET

    def upload_sarif(self, org_id, scan_id, sarif_data):
        """
        Upload SARIF to S3.

        Args:
            org_id: Organization UUID
            scan_id: Scan UUID
            sarif_data: SARIF dict or JSON string

        Returns:
            S3 URL (s3://bucket/path/to/file.sarif)
        """
        # Ensure sarif_data is dict
        if isinstance(sarif_data, str):
            sarif_data = json.loads(sarif_data)

        # Construct S3 key
        key = f"{org_id}/{scan_id}.sarif"

        # Upload to S3
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(sarif_data, indent=2),
            ContentType='application/json',
            Metadata={
                'org_id': str(org_id),
                'scan_id': str(scan_id),
            }
        )

        return f"s3://{self.bucket}/{key}"

    def get_presigned_url(self, sarif_url, expiration=3600):
        """
        Generate presigned URL for downloading SARIF.

        Args:
            sarif_url: S3 URL (s3://bucket/key)
            expiration: URL validity in seconds (default 1 hour)

        Returns:
            HTTPS presigned URL
        """
        # Parse S3 URL
        parts = sarif_url.replace('s3://', '').split('/', 1)
        bucket = parts[0]
        key = parts[1]

        url = self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiration
        )

        return url

    def download_sarif(self, sarif_url):
        """
        Download SARIF from S3.

        Args:
            sarif_url: S3 URL (s3://bucket/key)

        Returns:
            SARIF dict
        """
        parts = sarif_url.replace('s3://', '').split('/', 1)
        bucket = parts[0]
        key = parts[1]

        response = self.s3_client.get_object(Bucket=bucket, Key=key)
        sarif_json = response['Body'].read().decode('utf-8')
        return json.loads(sarif_json)
```

#### 3. SARIF Parsing and Ingestion

```python
# services/sarif_parser.py
from typing import List, Dict
import hashlib

class SarifParser:
    """
    Parse SARIF 2.1.0 format and extract findings.
    """

    def parse_sarif(self, sarif_data: dict) -> dict:
        """
        Parse SARIF and extract summary + findings.

        Returns:
            {
                'summary': {...},  # For scans.sarif_summary
                'findings': [...]  # For findings table
            }
        """
        run = sarif_data['runs'][0]  # Most tools output single run

        # Extract summary metadata
        summary = {
            'tool': {
                'name': run['tool']['driver']['name'],
                'version': run['tool']['driver'].get('version'),
                'uri': run['tool']['driver'].get('informationUri'),
            },
            'invocations': run.get('invocations', []),
            'rules': [
                {
                    'id': rule['id'],
                    'name': rule.get('shortDescription', {}).get('text'),
                    'level': rule.get('defaultConfiguration', {}).get('level', 'warning'),
                }
                for rule in run['tool']['driver'].get('rules', [])
            ],
            'results_count': len(run.get('results', [])),
        }

        # Extract findings
        findings = []
        for idx, result in enumerate(run.get('results', [])):
            finding = self._parse_result(result, idx)
            findings.append(finding)

        return {
            'summary': summary,
            'findings': findings,
        }

    def _parse_result(self, result: dict, index: int) -> dict:
        """
        Parse a single SARIF result into finding dict.
        """
        # Extract location
        location = result['locations'][0]['physicalLocation']
        region = location.get('region', {})

        # Extract severity
        level = result.get('level', 'warning')
        severity_map = {
            'error': 'high',
            'warning': 'medium',
            'note': 'low',
            'none': 'info',
        }

        # Extract metadata (fixes, code flows, etc.)
        metadata = {
            'kind': result.get('kind', 'fail'),
            'fixes': result.get('fixes', []),
            'code_flows': result.get('codeFlows', []),
            'related_locations': result.get('relatedLocations', []),
        }

        return {
            'file_path': location['artifactLocation']['uri'],
            'line_number': region.get('startLine'),
            'line_end_number': region.get('endLine'),
            'column_number': region.get('startColumn'),
            'column_end_number': region.get('endColumn'),
            'rule_id': result['ruleId'],
            'severity': severity_map.get(level, 'medium'),
            'message': result['message']['text'],
            'metadata': metadata,
            'sarif_result_index': index,
        }
```

#### 4. Scan Ingestion Workflow

```python
# workers/scan_worker.py
from services.sarif_storage import SarifStorage
from services.sarif_parser import SarifParser
from services.finding_deduplicator import FindingDeduplicator

@shared_task
def ingest_scan_results(scan_id, sarif_data):
    """
    Ingest SARIF results: upload to S3, parse, save findings.
    """
    scan = Scan.objects.select_related('project', 'branch').get(id=scan_id)

    # Step 1: Upload full SARIF to S3
    storage = SarifStorage()
    sarif_url = storage.upload_sarif(
        org_id=scan.project.org_id,
        scan_id=scan_id,
        sarif_data=sarif_data
    )

    # Step 2: Parse SARIF
    parser = SarifParser()
    parsed = parser.parse_sarif(sarif_data)

    # Step 3: Save summary to scan
    scan.sarif_summary = parsed['summary']
    scan.sarif_url = sarif_url
    scan.save(update_fields=['sarif_summary', 'sarif_url', 'updated_at'])

    # Step 4: Save findings (with deduplication)
    deduplicator = FindingDeduplicator()
    new_count = 0
    existing_count = 0

    for finding_data in parsed['findings']:
        finding_data.update({
            'scan_id': scan_id,
            'org_id': scan.project.org_id,
            'project_id': scan.project_id,
            'branch_id': scan.branch_id,
            'sarif_url': sarif_url,
        })

        finding, created = deduplicator.ingest_finding(**finding_data)
        if created:
            new_count += 1
        else:
            existing_count += 1

    return {
        'new_findings': new_count,
        'existing_findings': existing_count,
    }
```

#### 5. API Endpoints

```python
# views/scans.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from services.sarif_storage import SarifStorage

@api_view(['GET'])
def scan_findings(request, scan_id):
    """
    Get findings for a scan (from database, not SARIF).
    """
    scan = Scan.objects.get(id=scan_id, project__org_id=request.user.org_id)

    findings = Finding.objects.filter(
        scan_id=scan_id,
        org_id=request.user.org_id
    ).order_by('-severity', 'file_path')

    return Response({
        'scan_id': scan_id,
        'summary': scan.sarif_summary,
        'findings': FindingSerializer(findings, many=True).data,
    })

@api_view(['GET'])
def download_sarif(request, scan_id):
    """
    Get presigned URL to download full SARIF from S3.
    """
    scan = Scan.objects.get(id=scan_id, project__org_id=request.user.org_id)

    storage = SarifStorage()
    presigned_url = storage.get_presigned_url(scan.sarif_url, expiration=300)  # 5 min

    return Response({
        'download_url': presigned_url,
        'expires_in_seconds': 300,
    })
```

#### 6. S3 Bucket Configuration

```terraform
# S3 bucket for SARIF storage
resource "aws_s3_bucket" "sarif" {
  bucket = "prod-sarif-reports"

  # Versioning for compliance
  versioning {
    enabled = true
  }

  # Lifecycle policy: Move old SARIFs to Glacier
  lifecycle_rule {
    enabled = true

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 2555  # 7 years for compliance
    }
  }

  # Server-side encryption
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  # Block public access
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

## Consequences

### Positive

- **Fast queries:** Normalized `findings` table with proper indexes
- **Small database:** <10KB per finding vs 1-10MB per SARIF
- **Cheap storage:** Object storage is $0.023/GB vs $0.10+/GB for DB
- **Compliance:** Full SARIF archived for 7 years in Glacier
- **Flexible schema:** Small metadata JSONB for tool-specific fields
- **Streaming:** Presigned URLs allow direct S3 downloads

### Negative

- **Two sources of truth:** Findings in DB, full SARIF in S3 (mitigated by `sarif_result_index`)
- **More complex ingestion:** Parse SARIF, upload S3, save findings
- **Object storage dependency:** Requires S3/MinIO infrastructure

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Findings out of sync with SARIF | Store `sarif_result_index` for reconciliation; checksums |
| S3 unavailable | Cache SARIF summary in DB; retry logic; multi-region replication |
| SARIF format changes (future versions) | Version SARIF schema; parser handles multiple versions |
| Large metadata JSONB degrades performance | Limit metadata to <10KB; extract common fields to columns |

## Related Decisions

- **ADR-002:** Finding deduplication (fingerprints computed from extracted fields)
- **ADR-004:** Worker security (workers upload SARIF to S3 after scan)
- **ADR-006:** Data model normalization (findings table schema)

## References

- [SARIF 2.1.0 Specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
- [SARIF Tutorials](https://github.com/microsoft/sarif-tutorials)
- [AWS S3 Pricing](https://aws.amazon.com/s3/pricing/)
- [PostgreSQL TOAST](https://www.postgresql.org/docs/current/storage-toast.html)
- [PostgreSQL JSONB Performance](https://www.postgresql.org/docs/current/datatype-json.html)
