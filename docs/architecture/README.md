# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for the security analysis platform. Each ADR documents a significant architectural decision, including the context, options considered, chosen solution, and consequences.

## What is an ADR?

An Architecture Decision Record captures an important architectural decision made along with its context and consequences. ADRs help teams:

- **Document the "why"** behind architectural choices
- **Onboard new team members** by providing historical context
- **Avoid revisiting settled decisions** without understanding past reasoning
- **Learn from past decisions** and their outcomes

## ADR Format

Each ADR follows a consistent structure:

1. **Status:** Proposed | Accepted | Deprecated | Superseded
2. **Date:** When the decision was made
3. **Context and Problem Statement:** What problem are we solving?
4. **Decision Drivers:** What factors influenced the decision?
5. **Considered Options:** What alternatives did we evaluate?
6. **Decision Outcome:** What did we choose and why?
7. **Consequences:** What are the positive and negative impacts?
8. **References:** Links to relevant documentation

## Index of ADRs

### Core Infrastructure

- **[ADR-001: Multi-Tenancy Model](./ADR-001-multi-tenancy-model.md)**
  - **Decision:** Shared schema with `org_id` filtering + PostgreSQL Row-Level Security
  - **Key Benefit:** Operational simplicity with database-enforced isolation
  - **Status:** Accepted

- **[ADR-003: Real-Time Communication](./ADR-003-real-time-communication.md)**
  - **Decision:** Server-Sent Events (SSE) with polling fallback
  - **Key Benefit:** Simple infrastructure, works through firewalls, auto-reconnect
  - **Status:** Accepted

- **[ADR-004: Worker Security Model](./ADR-004-worker-security-model.md)**
  - **Decision:** Isolated Docker containers per scan with ephemeral GitHub App tokens
  - **Key Benefit:** Strong isolation, short-lived credentials, resource limits
  - **Status:** Accepted

### Data Management

- **[ADR-002: Finding Deduplication](./ADR-002-finding-deduplication.md)**
  - **Decision:** Hybrid approach - PostgreSQL generated fingerprints + Django collision detection
  - **Key Benefit:** Consistent fingerprinting with graceful collision handling
  - **Status:** Accepted

- **[ADR-005: SARIF Storage Strategy](./ADR-005-sarif-storage-strategy.md)**
  - **Decision:** Hybrid - normalized findings in database, full SARIF in object storage (S3)
  - **Key Benefit:** Fast queries, small database, cheap storage, compliance-friendly
  - **Status:** Accepted

- **[ADR-006: Data Model Normalization](./ADR-006-data-model-normalization.md)**
  - **Decision:** Normalized `branches` table with foreign key constraints
  - **Key Benefit:** Data integrity, efficient queries, per-branch metrics
  - **Status:** Accepted

### Security & Access Control

- **[ADR-007: Authentication & Authorization](./ADR-007-authentication-authorization.md)**
  - **Decision:** JWT tokens with refresh tokens, GitHub OAuth SSO, API keys for programmatic access
  - **Key Benefit:** Stateless, scalable, unified auth for web and API
  - **Status:** Accepted

- **[ADR-008: Rate Limiting & Quotas](./ADR-008-rate-limiting-quotas.md)**
  - **Decision:** Hybrid - Redis for rate limits, PostgreSQL for quotas
  - **Key Benefit:** Abuse prevention, fair resource allocation, cost control
  - **Status:** Accepted

## Decision Summary Matrix

| Decision Area | Chosen Approach | Key Trade-off |
|---------------|-----------------|---------------|
| Multi-tenancy | org_id + RLS | Simplicity vs Hard Isolation |
| Deduplication | DB Fingerprint + App Logic | Consistency vs Flexibility |
| Real-time | SSE + Polling Fallback | Simplicity vs Bidirectional |
| Worker Security | Docker Containers | Isolation vs Performance |
| SARIF Storage | Hybrid (DB + S3) | Query Speed vs Storage Cost |
| Branch Tracking | Normalized Table | Integrity vs Simplicity |
| Authentication | JWT + Refresh Tokens | Scalability vs Revocation |
| Rate Limiting | Redis + PostgreSQL | Speed vs Durability |

## Cross-Cutting Concerns

### Technologies Used

- **Backend:** Django (Python), Django REST Framework
- **Database:** PostgreSQL 15+ with JSONB, Row-Level Security
- **Caching/Pub-Sub:** Redis
- **Object Storage:** AWS S3 / MinIO
- **Container Runtime:** Docker
- **Authentication:** JWT (HS256), GitHub OAuth
- **Real-time:** Server-Sent Events (SSE)

### Security Principles

1. **Defense in Depth:** Multiple security layers (RLS, containers, tokens, rate limits)
2. **Least Privilege:** Minimal permissions at all levels (DB, API, containers)
3. **Short-Lived Credentials:** Tokens expire quickly (15 min access, 15 min GitHub tokens)
4. **Audit Logging:** All security-relevant actions logged
5. **Isolation:** Strong boundaries between organizations and scan environments

### Scalability Considerations

1. **Stateless Architecture:** JWT + SSE enables horizontal scaling
2. **Database Partitioning:** Ready to partition by `org_id` if needed
3. **Object Storage:** Offload large files (SARIF) from database
4. **Redis Sharding:** Can shard rate limits and pub/sub by org_id
5. **Worker Pools:** Dedicated scan workers, isolated from API workers

### Compliance (SOC 2, ISO 27001)

1. **Data Isolation:** RLS enforces tenant boundaries at database level
2. **Audit Trail:** All data access logged with org_id context
3. **Encryption:** TLS in transit, AES-256 at rest (S3, database)
4. **Access Control:** RBAC with role-based permissions
5. **Data Retention:** 7-year SARIF archive in Glacier for compliance

## Future Decisions

Areas that may require future ADRs:

1. **Observability:** Logging, metrics, tracing (Datadog, Prometheus, OpenTelemetry?)
2. **CI/CD Pipeline:** Deployment strategy (blue-green, canary, rolling?)
3. **Database Backups:** Backup strategy, point-in-time recovery
4. **Multi-Region:** Cross-region replication for HA
5. **Caching Strategy:** Application-level caching (Redis, memcached?)
6. **Email Notifications:** Transactional email service (SendGrid, SES?)
7. **Webhook Integrations:** Notify external systems of scan results
8. **Data Export:** GDPR compliance, customer data export
9. **Firecracker Migration:** Upgrade from Docker to Firecracker for ultimate isolation
10. **GraphQL API:** Add GraphQL alongside REST for complex queries

## Changing Decisions

When revisiting a decision:

1. **Create a new ADR** (e.g., ADR-009-updated-approach.md)
2. **Reference the old ADR** and explain why it's being superseded
3. **Update the old ADR status** to "Superseded by ADR-XXX"
4. **Document migration path** from old to new approach

## Contributing

When adding a new ADR:

1. Use the next sequential number (ADR-009, ADR-010, etc.)
2. Follow the template structure from existing ADRs
3. Get review from at least two team members
4. Update this README with a link to the new ADR
5. Mark status as "Proposed" until decision is finalized

## References

- [Architecture Decision Records (ADR) Pattern](https://adr.github.io/)
- [Documenting Architecture Decisions by Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [ADR Tools](https://github.com/npryce/adr-tools)
- [When to Write an ADR](https://github.com/joelparkerhenderson/architecture-decision-record#when-to-write-an-adr)
