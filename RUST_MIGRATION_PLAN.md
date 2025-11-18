# Rust Migration Plan for Review-Pro

## Executive Summary

This document outlines a phased approach to migrate performance-critical components of Review-Pro from Python to Rust. Based on comprehensive performance analysis, targeted Rust rewrites can achieve **10-50x speedups** on the most resource-intensive operations while maintaining the existing Django architecture.

**Key Metrics:**
- Current scan processing time: 30-120 seconds per repository
- Expected improvement: 15-30 second reduction (25-50% faster)
- Primary bottlenecks: SARIF parsing (5s), clustering (5s), batch inserts (30s)
- Migration scope: 4-5 microservices, ~3,000-5,000 LOC Rust

**Migration Philosophy:**
- Surgical rewrites, not full rewrite
- Microservices architecture for Rust components
- Maintain Django as primary application framework
- Incremental rollout with A/B testing capability

---

## Current Architecture Analysis

### Technology Stack
```
Frontend: React + TypeScript (328KB, ~2,000 LOC)
Backend: Django 5.0 + DRF (625KB, ~6,100 LOC Python)
Workflows: Temporal (workflow orchestration)
Storage: PostgreSQL 18, Redis 7, MinIO (S3)
Vector DB: Qdrant (semantic search)
LLM: Anthropic Claude, OpenAI GPT-4o
Containers: Docker Compose
```

### Performance Bottlenecks

| Component | Current Tech | Duration | Rust Speedup | Priority |
|-----------|-------------|----------|--------------|----------|
| SARIF Parsing (100MB) | Python JSON | 5.0s | 10-50x | ★★★★★ |
| Clustering (10K vectors) | NumPy + scikit-learn | 5.0s | 5-20x | ★★★★☆ |
| Batch Inserts (10K records) | Django ORM | 30s | 2-5x | ★★★☆☆ |
| Fingerprints (10K hashes) | Python hashlib | 2.0s | 3-5x | ★★☆☆☆ |
| Embeddings (100 items) | OpenAI API (sequential) | 1.0s | 2-3x | ★★☆☆☆ |

---

## Rust Migration Candidates

### Phase 1: Critical Path Optimizations (Weeks 1-4)

#### 1. SARIF Parser Service ⭐ **HIGHEST PRIORITY**

**Current Implementation:** `backend/scanner/sarif_parser.py` (321 LOC)

**Problem:**
- Parses 1-100MB SARIF 2.1.0 JSON files
- Python JSON parsing + manual field extraction
- Sequential processing
- 0.1-5.0 seconds per file (large files are bottleneck)

**Rust Solution:**
```rust
// Technology Stack
- serde_json: Zero-copy JSON parsing
- rayon: Parallel processing of multiple SARIF files
- actix-web or axum: REST API
- tokio: Async runtime

// Architecture
SARIF Parser Service (Rust)
├── HTTP API (POST /parse-sarif)
├── Parallel file processing
├── Schema validation (SARIF 2.1.0)
├── Normalized output (Finding records)
└── Error handling + logging
```

**Performance Target:** 10-50x faster (500ms for 100MB file)

**API Contract:**
```json
POST /parse-sarif
Request:
{
  "sarif_content": "...",  // or "sarif_url": "s3://..."
  "scan_id": "uuid"
}

Response:
{
  "findings": [
    {
      "rule_id": "python.lang.security.audit.dangerous-code-exec",
      "severity": "high",
      "file_path": "src/utils.py",
      "line": 42,
      "column": 10,
      "message": "Dangerous use of exec()",
      "code_snippet": "exec(user_input)",
      "cwe": ["CWE-95"],
      "fingerprint": "sha256:abc123..."
    }
  ],
  "metadata": {
    "tool_name": "semgrep",
    "tool_version": "1.45.0",
    "parse_duration_ms": 487
  }
}
```

**Implementation Steps:**
1. Define SARIF 2.1.0 schema structs with serde
2. Implement parallel file processing
3. Create REST API with actix-web
4. Add fingerprint generation (SHA256)
5. Write integration tests with real SARIF samples
6. Deploy as standalone service in docker-compose

**Files to Replace:**
- `backend/scanner/sarif_parser.py` → Call Rust service

**Testing Strategy:**
- Unit tests: Parse 100+ real SARIF samples from semgrep, bandit, ruff
- Load tests: 100MB files, 10K+ findings per file
- Integration: Django calls Rust service, validates responses

---

#### 2. Clustering Service ⭐ **HIGH PRIORITY**

**Current Implementation:** `backend/services/clustering_service.py` (261 LOC)

**Problem:**
- DBSCAN: O(n²) distance matrix computation
- Agglomerative: O(n²) linkage computation
- NumPy + scikit-learn (Python GIL limits parallelization)
- 1-10 seconds for 10,000 vectors (1536 dimensions)

**Rust Solution:**
```rust
// Technology Stack
- ndarray: N-dimensional arrays (like NumPy)
- ndarray-linalg: Linear algebra operations
- rayon: Parallel matrix operations
- smartcore or linfa: ML algorithms (DBSCAN, Agglomerative)
- actix-web: REST API

// Architecture
Clustering Service (Rust)
├── HTTP API (POST /cluster)
├── Parallel distance matrix computation
├── DBSCAN algorithm
├── Agglomerative clustering
├── Silhouette score calculation
└── Cluster quality metrics
```

**Performance Target:** 5-20x faster (200-500ms for 10K vectors)

**API Contract:**
```json
POST /cluster
Request:
{
  "embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...]], // Nx1536 matrix
  "algorithm": "dbscan",  // or "agglomerative"
  "params": {
    "eps": 0.3,           // DBSCAN epsilon
    "min_samples": 5,     // DBSCAN min samples
    "n_clusters": 10,     // Agglomerative cluster count
    "linkage": "ward"     // Agglomerative linkage method
  }
}

Response:
{
  "cluster_labels": [0, 0, 1, 2, 0, -1, ...],  // -1 = noise
  "n_clusters": 3,
  "silhouette_score": 0.68,
  "cluster_sizes": [1500, 800, 200],
  "noise_count": 50,
  "duration_ms": 421
}
```

**Implementation Steps:**
1. Implement parallel cosine similarity matrix
2. Port DBSCAN algorithm with Rayon parallelization
3. Port Agglomerative clustering with parallel linkage
4. Add silhouette score calculation
5. Create REST API
6. Benchmark against scikit-learn

**Files to Replace:**
- `backend/services/clustering_service.py` → Call Rust service

**Testing Strategy:**
- Unit tests: Known clustering datasets (sklearn toy datasets)
- Performance: 1K, 10K, 100K vector datasets
- Accuracy: Compare results with scikit-learn (should match within 1%)

---

### Phase 2: Database & Deduplication (Weeks 5-6)

#### 3. Batch Insert Service ⭐ **MEDIUM PRIORITY**

**Current Implementation:** Django ORM `bulk_create()` in workflows

**Problem:**
- Django ORM overhead for large batches
- 5-30 seconds for 10,000 finding inserts
- Not using PostgreSQL COPY protocol (fastest bulk insert)

**Rust Solution:**
```rust
// Technology Stack
- tokio-postgres: Async PostgreSQL driver
- rust-postgres: COPY protocol support
- actix-web: REST API

// Architecture
Batch Insert Service (Rust)
├── HTTP API (POST /bulk-insert)
├── PostgreSQL COPY protocol
├── Transaction management
├── Batch size optimization
└── Error handling + rollback
```

**Performance Target:** 2-5x faster (5-10s for 10K records)

**API Contract:**
```json
POST /bulk-insert/findings
Request:
{
  "findings": [
    {
      "scan_id": "uuid",
      "rule_id": "...",
      "severity": "high",
      "file_path": "...",
      "line": 42,
      ...
    }
  ],
  "batch_size": 1000  // Optional, default 1000
}

Response:
{
  "inserted_count": 10000,
  "duration_ms": 8234,
  "errors": []
}
```

**Implementation Steps:**
1. Implement PostgreSQL COPY protocol
2. Add transaction management
3. Handle duplicate fingerprints (ON CONFLICT)
4. Create REST API
5. Benchmark vs Django ORM

**Testing Strategy:**
- Unit tests: 100, 1K, 10K, 100K record batches
- Stress tests: Concurrent batch inserts
- Integrity: Verify all records inserted correctly

---

#### 4. Fingerprint & Deduplication Service ⭐ **LOWER PRIORITY**

**Current Implementation:** `Finding.generate_fingerprint()` in Python

**Problem:**
- SHA256 hash computed 10,000+ times per scan
- Sequential loop in Python
- 2 seconds for 10,000 fingerprints

**Rust Solution:**
```rust
// Technology Stack
- sha2: SHA256 hashing
- rayon: Parallel iteration
- actix-web: REST API

// Architecture
Fingerprint Service (Rust)
├── HTTP API (POST /generate-fingerprints)
├── Parallel hash computation
├── Deduplication logic
└── Batch processing
```

**Performance Target:** 3-5x faster (400-600ms for 10K hashes)

**API Contract:**
```json
POST /generate-fingerprints
Request:
{
  "findings": [
    {
      "rule_id": "...",
      "file_path": "...",
      "line": 42,
      "column": 10,
      "message": "..."
    }
  ]
}

Response:
{
  "fingerprints": [
    {
      "finding_index": 0,
      "fingerprint": "sha256:abc123...",
      "is_duplicate": false
    }
  ],
  "unique_count": 8234,
  "duplicate_count": 1766,
  "duration_ms": 487
}
```

**Implementation Steps:**
1. Implement parallel SHA256 hashing
2. Add deduplication logic (HashSet)
3. Create REST API
4. Benchmark vs Python

---

### Phase 3: Optional Optimizations (Weeks 7-8)

#### 5. Async Embedding Request Pool (OPTIONAL)

**Current Implementation:** `backend/services/embedding_service.py` (sequential OpenAI API calls)

**Problem:**
- Sequential HTTP requests to OpenAI
- 500ms for 100 embeddings (rate-limited)

**Rust Solution:**
```rust
// Technology Stack
- tokio: Async runtime
- reqwest: HTTP client with connection pooling
- tower: Rate limiting
- actix-web: REST API

// Architecture
Embedding Service (Rust)
├── HTTP API (POST /embed)
├── Connection pool (10 concurrent requests)
├── Rate limiting (OpenAI limits)
├── Retry logic with exponential backoff
└── Token usage tracking
```

**Performance Target:** 2-3x throughput (200-300ms for 100 embeddings)

---

## Integration Architecture

### Microservices Design

```
┌─────────────────────────────────────────────────────────────┐
│                     Django Application                       │
│  (Python - 6,100 LOC)                                       │
│  - Models (Scan, Finding, Organization)                     │
│  - REST API (DRF)                                           │
│  - Authentication, Permissions                              │
│  - Temporal Workflows                                       │
└────────────┬────────────────────────────────────────────────┘
             │
             │ HTTP/gRPC calls
             │
    ┌────────┴─────────────────────────────────┐
    │                                           │
    ▼                                           ▼
┌─────────────────────┐              ┌──────────────────────┐
│  SARIF Parser       │              │  Clustering Service  │
│  (Rust Service)     │              │  (Rust Service)      │
│  Port: 8001         │              │  Port: 8002          │
│                     │              │                      │
│  - Parse SARIF JSON │              │  - DBSCAN            │
│  - Extract findings │              │  - Agglomerative     │
│  - Generate FPs     │              │  - Silhouette score  │
│  - REST API         │              │  - REST API          │
└─────────────────────┘              └──────────────────────┘

    ▼                                           ▼
┌─────────────────────┐              ┌──────────────────────┐
│  Batch Insert       │              │  Fingerprint Service │
│  (Rust Service)     │              │  (Rust Service)      │
│  Port: 8003         │              │  Port: 8004          │
│                     │              │                      │
│  - COPY protocol    │              │  - SHA256 parallel   │
│  - Transactions     │              │  - Deduplication     │
│  - Bulk operations  │              │  - REST API          │
└─────────────────────┘              └──────────────────────┘
```

### Service Communication

**Protocol:** REST APIs with JSON (Phase 1), gRPC (Phase 2 optional)

**Error Handling:**
- Rust services return standard HTTP status codes
- Django implements circuit breaker pattern
- Fallback to Python implementation if Rust service unavailable
- Comprehensive logging (structured JSON logs)

**Deployment:**
- Each Rust service as separate Docker container
- Health check endpoints (`/health`)
- Metrics endpoints (`/metrics` - Prometheus format)
- Deploy in `docker-compose.yml` alongside existing services

---

## Implementation Roadmap

### Week 1-2: SARIF Parser Service

**Tasks:**
1. Create Rust project structure (`rust-services/sarif-parser/`)
2. Define SARIF 2.1.0 schema structs
3. Implement parser with serde_json
4. Add parallel processing (Rayon)
5. Create REST API (actix-web)
6. Write comprehensive tests
7. Docker container + integration with Django
8. A/B testing: Compare Rust vs Python parsing

**Deliverables:**
- Working SARIF parser service
- 10-50x faster parsing
- Integration tests passing
- Docker deployment

---

### Week 3-4: Clustering Service

**Tasks:**
1. Create Rust project (`rust-services/clustering/`)
2. Implement parallel distance matrix (ndarray + Rayon)
3. Port DBSCAN algorithm
4. Port Agglomerative clustering
5. Add silhouette score calculation
6. Create REST API
7. Benchmark vs scikit-learn
8. Docker deployment

**Deliverables:**
- Working clustering service
- 5-20x faster clustering
- Accuracy matches scikit-learn within 1%
- Docker deployment

---

### Week 5: Batch Insert Service

**Tasks:**
1. Create Rust project (`rust-services/batch-insert/`)
2. Implement PostgreSQL COPY protocol
3. Add transaction management
4. Handle conflict resolution (ON CONFLICT)
5. Create REST API
6. Performance testing
7. Docker deployment

**Deliverables:**
- Working batch insert service
- 2-5x faster inserts
- Docker deployment

---

### Week 6: Fingerprint Service

**Tasks:**
1. Create Rust project (`rust-services/fingerprint/`)
2. Implement parallel SHA256 hashing
3. Add deduplication logic
4. Create REST API
5. Benchmark vs Python
6. Docker deployment

**Deliverables:**
- Working fingerprint service
- 3-5x faster hashing
- Docker deployment

---

### Week 7-8: Integration, Testing, Documentation

**Tasks:**
1. End-to-end integration testing
2. Performance benchmarking (full scan workflow)
3. Load testing (1K, 10K, 100K findings)
4. Error handling & circuit breakers
5. Monitoring & metrics (Prometheus)
6. Documentation (API specs, deployment guide)
7. Migration runbook

**Deliverables:**
- All services integrated
- Comprehensive test suite
- Performance benchmarks
- Production-ready deployment
- Documentation complete

---

## Testing Strategy

### Unit Testing

**Rust Services:**
- Use `cargo test` for unit tests
- Property-based testing with `proptest`
- Mock HTTP clients for API tests
- Coverage target: 80%+

**Integration Testing:**
- Python integration tests call Rust services
- Compare Rust vs Python results (accuracy)
- Test error handling and edge cases

### Performance Benchmarking

**Benchmark Suite:**
```python
# backend/tests/benchmarks/test_rust_performance.py

def benchmark_sarif_parsing():
    # Test files: 1KB, 100KB, 1MB, 10MB, 100MB
    # Compare: Python vs Rust parsing time
    # Assert: Rust is 10x+ faster

def benchmark_clustering():
    # Test datasets: 100, 1K, 10K, 100K vectors
    # Compare: scikit-learn vs Rust
    # Assert: Rust is 5x+ faster

def benchmark_batch_insert():
    # Test batches: 100, 1K, 10K, 100K records
    # Compare: Django ORM vs Rust COPY
    # Assert: Rust is 2x+ faster
```

**Continuous Benchmarking:**
- Run benchmarks in CI/CD
- Track performance over time
- Alert on regressions

### Load Testing

**Scenarios:**
1. 100 concurrent scans (SARIF parsing)
2. 1,000 concurrent clustering requests
3. 10,000 concurrent fingerprint generations

**Tools:**
- `wrk` or `hey` for HTTP load testing
- Grafana for monitoring
- Prometheus for metrics

---

## Deployment Strategy

### Docker Compose Integration

```yaml
# docker-compose.yml additions

services:
  # Existing services (postgres, redis, django, etc.)

  sarif-parser:
    build: ./rust-services/sarif-parser
    ports:
      - "8001:8001"
    environment:
      - RUST_LOG=info
      - SERVICE_PORT=8001
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  clustering:
    build: ./rust-services/clustering
    ports:
      - "8002:8002"
    environment:
      - RUST_LOG=info
      - SERVICE_PORT=8002
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  batch-insert:
    build: ./rust-services/batch-insert
    ports:
      - "8003:8003"
    environment:
      - RUST_LOG=info
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/reviewpro
    depends_on:
      - postgres
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  fingerprint:
    build: ./rust-services/fingerprint
    ports:
      - "8004:8004"
    environment:
      - RUST_LOG=info
      - SERVICE_PORT=8004
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8004/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped
```

### Django Configuration

```python
# backend/config/settings.py

RUST_SERVICES = {
    'SARIF_PARSER': {
        'URL': os.getenv('SARIF_PARSER_URL', 'http://sarif-parser:8001'),
        'TIMEOUT': 30,  # seconds
        'ENABLED': os.getenv('USE_RUST_SARIF_PARSER', 'true').lower() == 'true',
    },
    'CLUSTERING': {
        'URL': os.getenv('CLUSTERING_URL', 'http://clustering:8002'),
        'TIMEOUT': 60,
        'ENABLED': os.getenv('USE_RUST_CLUSTERING', 'true').lower() == 'true',
    },
    'BATCH_INSERT': {
        'URL': os.getenv('BATCH_INSERT_URL', 'http://batch-insert:8003'),
        'TIMEOUT': 120,
        'ENABLED': os.getenv('USE_RUST_BATCH_INSERT', 'true').lower() == 'true',
    },
    'FINGERPRINT': {
        'URL': os.getenv('FINGERPRINT_URL', 'http://fingerprint:8004'),
        'TIMEOUT': 30,
        'ENABLED': os.getenv('USE_RUST_FINGERPRINT', 'true').lower() == 'true',
    },
}

# Circuit breaker settings
RUST_CIRCUIT_BREAKER = {
    'FAILURE_THRESHOLD': 5,  # Open circuit after 5 failures
    'SUCCESS_THRESHOLD': 2,  # Close circuit after 2 successes
    'TIMEOUT': 60,  # Try again after 60 seconds
}
```

### Rollout Strategy

**Phase 1: Canary Deployment**
1. Deploy Rust services alongside Python
2. Route 10% of traffic to Rust
3. Monitor metrics (latency, errors, resource usage)
4. Gradually increase to 50%, 100%

**Phase 2: A/B Testing**
```python
# Use feature flags to test Rust vs Python
if settings.RUST_SERVICES['SARIF_PARSER']['ENABLED']:
    result = rust_sarif_parser.parse(sarif_content)
else:
    result = python_sarif_parser.parse(sarif_content)
```

**Phase 3: Full Migration**
1. All traffic routed to Rust services
2. Remove Python implementations (deprecated)
3. Monitor for 2 weeks
4. Declare migration complete

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Rust learning curve** | Medium | Start with SARIF parser (simple), team training |
| **Integration complexity** | Medium | REST APIs, comprehensive integration tests |
| **Performance not as expected** | Low | Benchmarking before full deployment |
| **Service downtime** | Medium | Circuit breakers, fallback to Python |
| **Data corruption** | High | Comprehensive testing, transaction rollback |

### Operational Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Deployment failures** | Medium | Docker health checks, automated rollback |
| **Monitoring gaps** | Low | Prometheus metrics, structured logging |
| **Team knowledge** | Medium | Documentation, runbooks, on-call training |

---

## Success Metrics

### Performance Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Scan Duration (avg)** | 60s | 40s | 33% reduction |
| **SARIF Parse (100MB)** | 5.0s | 0.1-0.5s | 10-50x faster |
| **Clustering (10K)** | 5.0s | 0.25-1.0s | 5-20x faster |
| **Batch Insert (10K)** | 30s | 6-15s | 2-5x faster |
| **Fingerprint (10K)** | 2.0s | 0.4-0.7s | 3-5x faster |

### Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Test Coverage** | 80%+ | Cargo tarpaulin |
| **API Uptime** | 99.9% | Prometheus alerts |
| **Error Rate** | <0.1% | Structured logs |
| **Accuracy** | 100% match with Python | Integration tests |

### Cost Metrics

| Metric | Current | Target | Savings |
|--------|---------|--------|---------|
| **Compute Time (per scan)** | 60s | 40s | 33% reduction |
| **Infrastructure Costs** | $X/month | $0.7X/month | 30% reduction |

---

## Project Structure

```
review-pro/
├── backend/                        # Existing Django app
│   ├── scanner/
│   │   └── sarif_parser.py        # Will call Rust service
│   ├── services/
│   │   └── clustering_service.py  # Will call Rust service
│   └── config/
│       └── settings.py            # Rust service config
│
├── rust-services/                  # NEW: Rust microservices
│   ├── Cargo.toml                 # Workspace config
│   │
│   ├── sarif-parser/
│   │   ├── Cargo.toml
│   │   ├── Dockerfile
│   │   ├── src/
│   │   │   ├── main.rs            # REST API
│   │   │   ├── parser.rs          # SARIF parsing logic
│   │   │   ├── schema.rs          # SARIF structs
│   │   │   └── fingerprint.rs     # Hash generation
│   │   └── tests/
│   │       └── integration_test.rs
│   │
│   ├── clustering/
│   │   ├── Cargo.toml
│   │   ├── Dockerfile
│   │   ├── src/
│   │   │   ├── main.rs            # REST API
│   │   │   ├── dbscan.rs          # DBSCAN algorithm
│   │   │   ├── agglomerative.rs   # Agglomerative clustering
│   │   │   └── metrics.rs         # Silhouette score
│   │   └── tests/
│   │
│   ├── batch-insert/
│   │   ├── Cargo.toml
│   │   ├── Dockerfile
│   │   ├── src/
│   │   │   ├── main.rs            # REST API
│   │   │   ├── postgres.rs        # COPY protocol
│   │   │   └── transaction.rs     # Transaction mgmt
│   │   └── tests/
│   │
│   └── fingerprint/
│       ├── Cargo.toml
│       ├── Dockerfile
│       ├── src/
│       │   ├── main.rs            # REST API
│       │   ├── hasher.rs          # Parallel SHA256
│       │   └── dedup.rs           # Deduplication
│       └── tests/
│
├── docker-compose.yml              # Updated with Rust services
├── RUST_MIGRATION_PLAN.md          # This document
└── docs/
    ├── rust-services/
    │   ├── sarif-parser-api.md    # API documentation
    │   ├── clustering-api.md
    │   ├── batch-insert-api.md
    │   └── fingerprint-api.md
    └── deployment/
        └── rust-deployment-guide.md
```

---

## Dependencies & Technology Choices

### Core Rust Dependencies

```toml
# Shared dependencies across all services

[dependencies]
# Web Framework
actix-web = "4.4"           # High-performance web framework
actix-rt = "2.9"            # Async runtime

# Serialization
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"          # JSON parsing/serialization

# Async Runtime
tokio = { version = "1.35", features = ["full"] }

# Error Handling
anyhow = "1.0"              # Error handling
thiserror = "1.0"           # Custom error types

# Logging
tracing = "0.1"             # Structured logging
tracing-subscriber = "0.3"  # Log formatting

# HTTP Client
reqwest = { version = "0.11", features = ["json"] }

# Parallelization
rayon = "1.8"               # Data parallelism

# Testing
proptest = "1.4"            # Property-based testing
```

### Service-Specific Dependencies

#### SARIF Parser
```toml
[dependencies]
sha2 = "0.10"               # SHA256 hashing
regex = "1.10"              # Pattern matching
```

#### Clustering
```toml
[dependencies]
ndarray = "0.15"            # N-dimensional arrays
ndarray-linalg = "0.16"     # Linear algebra
linfa = "0.7"               # ML algorithms
linfa-clustering = "0.7"    # Clustering algorithms
```

#### Batch Insert
```toml
[dependencies]
tokio-postgres = "0.7"      # Async PostgreSQL
postgres-types = "0.2"      # PostgreSQL types
```

---

## Monitoring & Observability

### Metrics to Collect

```rust
// Example metrics for each service
use prometheus::{Histogram, Counter, Gauge};

lazy_static! {
    // Request metrics
    static ref REQUEST_DURATION: Histogram = register_histogram!(
        "rust_service_request_duration_seconds",
        "Request duration in seconds"
    ).unwrap();

    static ref REQUEST_COUNT: Counter = register_counter!(
        "rust_service_request_total",
        "Total number of requests"
    ).unwrap();

    static ref ERROR_COUNT: Counter = register_counter!(
        "rust_service_errors_total",
        "Total number of errors"
    ).unwrap();

    // Service-specific metrics
    static ref SARIF_PARSE_SIZE: Histogram = register_histogram!(
        "sarif_parse_size_bytes",
        "Size of SARIF files parsed"
    ).unwrap();

    static ref CLUSTERING_VECTOR_COUNT: Histogram = register_histogram!(
        "clustering_vector_count",
        "Number of vectors clustered"
    ).unwrap();
}
```

### Logging Strategy

```rust
// Structured logging with tracing
use tracing::{info, error, warn};

#[tracing::instrument]
async fn parse_sarif(content: &str) -> Result<ParsedSarif> {
    info!("Starting SARIF parsing", size = content.len());

    let start = Instant::now();
    let result = do_parse(content)?;

    info!(
        "SARIF parsing complete",
        duration_ms = start.elapsed().as_millis(),
        findings_count = result.findings.len()
    );

    Ok(result)
}
```

### Health Checks

```rust
// Health check endpoint for each service
async fn health_check() -> impl Responder {
    HttpResponse::Ok().json(json!({
        "status": "healthy",
        "service": "sarif-parser",
        "version": env!("CARGO_PKG_VERSION"),
        "uptime_seconds": UPTIME.elapsed().as_secs(),
    }))
}
```

---

## Documentation Plan

### API Documentation

Each service will have:
- OpenAPI/Swagger spec
- Request/response examples
- Error codes and handling
- Performance characteristics

### Developer Documentation

- Setup guide for Rust development
- Architecture diagrams
- Code contribution guidelines
- Testing procedures

### Operations Documentation

- Deployment runbook
- Monitoring guide
- Troubleshooting playbook
- Rollback procedures

---

## Future Enhancements

### Post-Migration Optimizations

1. **gRPC Migration:** Replace REST with gRPC for better performance
2. **WebAssembly:** Compile Rust to WASM for browser-side processing
3. **Native Libraries:** Expose Rust as Python extensions (PyO3) instead of services
4. **GPU Acceleration:** Use Rust GPU libraries for clustering on large datasets
5. **Real-time Processing:** Stream processing with Rust for live scan results

### Additional Components for Rust

- **Scanner Execution:** Replace Docker subprocess calls with direct Docker API
- **S3 Upload/Download:** Faster SARIF file handling
- **Report Generation:** PDF/HTML report generation (faster than Python)

---

## Conclusion

This migration plan provides a structured, low-risk approach to integrating Rust into Review-Pro for performance-critical components. By following this phased approach:

✅ **25-50% reduction** in scan processing time
✅ **Minimal disruption** to existing Django architecture
✅ **Incremental rollout** with A/B testing
✅ **Clear success metrics** and monitoring
✅ **8-week timeline** to production

The migration prioritizes high-impact optimizations (SARIF parsing, clustering) while maintaining the flexibility to fall back to Python implementations if needed. This surgical rewrite approach maximizes ROI while minimizing risk.

---

**Next Steps:**
1. Review and approve this migration plan
2. Set up Rust development environment
3. Create `rust-services/` workspace
4. Begin Phase 1: SARIF Parser Service (Week 1-2)
5. Establish benchmarking framework
6. Deploy to staging environment for testing

**Questions? Contact:** [Project lead/architect contact info]
