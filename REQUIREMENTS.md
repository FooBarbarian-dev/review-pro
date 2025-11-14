# Static Analysis Platform with Multi-Agent LLM Integration - Requirements

**Project Type:** Proof-of-Concept Research Demonstration
**Timeline:** 9-13 weeks
**Primary Goal:** Demonstrate LLM-enhanced static analysis with empirical agent pattern comparison

---

## Critical Success Criteria

The POC must demonstrate these **4 core capabilities**:

### 1. ✅ Multi-Tool Static Analysis Pipeline
- Scan Python code using **Semgrep, Bandit, and Ruff** (all 3 required)
- Parse SARIF output to normalized schema
- Store findings in PostgreSQL with deduplication fingerprints

### 2. ✅ LLM-Based Finding Adjudication
- Integrate **Claude (Anthropic), GPT (OpenAI), and Gemini (Google)** - minimum 2 of 3
- Use **Langroid framework** for multi-agent orchestration (NOT LangChain, NOT LiteLLM)
- Track token usage and cost per finding

### 3. ✅ Three Agent Patterns with Empirical Comparison
Must implement ALL three patterns with side-by-side metrics:

**Pattern A: Post-Processing Filter**
```
Static Analysis Tools → Findings → LLM Adjudication → Filtered Results
```
- Run all SA tools, then LLM filters findings
- Measure: Precision, Recall, F1, Cost, Latency

**Pattern B: Interactive Retrieval**
```
Minimal Context → LLM Requests More → Targeted Analysis → Verdict
```
- LLM dynamically requests function definitions, type info, etc.
- Measure: Token efficiency, accuracy improvement vs Pattern A

**Pattern C: Multi-Agent Collaboration**
```
Triage Agent (fast/cheap) → Explainer Agent (detailed) → Fixer Agent (suggestions)
```
- TriageAgent: GPT-4o for fast binary classification
- ExplainerAgent: Claude Sonnet 4 for detailed reasoning
- FixerAgent: Claude Sonnet 4 for code fix suggestions
- Measure: Cost savings vs Pattern A, quality parity

### 4. ✅ Workflow Orchestration with Temporal
- Use **Temporal (NOT Celery)** for durable workflow execution
- Visualize DAG of scan → deduplication → adjudication pipeline
- Enable time-travel debugging and workflow versioning

---

## Technology Stack (MANDATORY)

### Backend Framework
- **Django 5.0** - ✅ Correct choice
- **Django Channels** - For WebSocket streaming (real-time LLM responses)
- **Django REST Framework** - API endpoints

### Workflow Orchestration
- **Temporal** - ⚠️ CRITICAL: Must use Temporal, NOT Celery
  - **Why:** Durable execution, workflow versioning, DAG visualization, time-travel debugging
  - **Why NOT Celery:** Task queue ≠ workflow orchestrator, no state management
- **Temporal UI** - Built-in DAG visualization at `localhost:8233`

### LLM Integration
- **Langroid** - Multi-agent framework (explicitly required from research papers)
  - **Why:** Native multi-agent support, tool integration, cleaner than LangChain
  - **Why NOT LangChain:** User rejected generic wrappers
- **Anthropic SDK** - For Claude Sonnet 4.5
- **OpenAI SDK** - For GPT-4o, GPT-4.1
- **Google Generative AI SDK** - For Gemini 2.0 Flash

### Databases
- **PostgreSQL 15+** - Primary database (v18 preferred, v15 acceptable)
- **Qdrant** - Vector database for:
  - Semantic clustering (finding deduplication)
  - RAG (requirement document retrieval)
  - Code embedding storage
  - **Why NOT pgvector:** Performance concerns (user requirement)

### Static Analysis Tools (Dockerized)
- **Semgrep** - Pattern-based scanning, SARIF output
- **Bandit** - Security-focused Python scanner
- **Ruff** - Fast linter for bugs and code quality

### Performance Components (Rust)
- **Code Parser Service** - Actix-web HTTP server with tree-sitter
  - Endpoint: `/parse` - Extract functions, classes, AST
  - Purpose: Provide on-demand context to Interactive agents
- **Embedding Pipeline** - Batch embedding generation
  - Purpose: Efficiently generate vectors for Qdrant

### Frontend
- **React 18+** with **TypeScript**
- **Key Libraries:**
  - `@monaco-editor/react` - Code viewing with syntax highlighting
  - `reactflow` - DAG visualization for Temporal workflows
  - `@tanstack/react-query` - Data fetching with caching
  - `shadcn/ui` - Component library
  - `recharts` - Metrics visualization

### Infrastructure
- **Docker Compose** - Local development orchestration
- **Redis** - For Temporal visibility, caching
- **MinIO** - S3-compatible storage for full SARIF files

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  ┌────────────┐  ┌──────────────┐  ┌────────────┐              │
│  │  Findings  │  │ DAG Viewer   │  │ Chat UI    │              │
│  │  Dashboard │  │ (ReactFlow)  │  │ (Monaco)   │              │
│  └────────────┘  └──────────────┘  └────────────┘              │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST + WebSocket
┌───────────────────────────▼─────────────────────────────────────┐
│                    Django Backend (API)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ REST API     │  │ WebSocket    │  │ Django Admin │         │
│  │ (DRF)        │  │ (Channels)   │  │ (LLM Config) │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                  Temporal (Workflow Orchestration)               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Scan Workflow                                            │  │
│  │  ├─ Run Semgrep (parallel)                               │  │
│  │  ├─ Run Bandit (parallel)                                │  │
│  │  ├─ Run Ruff (parallel)                                  │  │
│  │  └─ Deduplicate Findings ──┬─> Exact Match               │  │
│  │                             ├─> Semantic Cluster (Qdrant) │  │
│  │                             └─> LLM Confirmation          │  │
│  │                                                            │  │
│  │  Adjudication Workflow (per pattern)                      │  │
│  │  ├─ Pattern A: Post-Processing                           │  │
│  │  ├─ Pattern B: Interactive Retrieval                     │  │
│  │  └─ Pattern C: Multi-Agent Pipeline                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                   Langroid Multi-Agent System                    │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐   │
│  │ TriageAgent    │  │ ExplainerAgent │  │ FixerAgent     │   │
│  │ (GPT-4o)       │─>│ (Claude S4.5)  │─>│ (Claude S4.5)  │   │
│  │ Fast binary    │  │ Detailed trace │  │ Code fixes     │   │
│  └────────────────┘  └────────────────┘  └────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ├─> Anthropic API (Claude)
                            ├─> OpenAI API (GPT)
                            └─> Google API (Gemini)
```

---

## Core Workflows (Temporal)

### Workflow 1: Code Scan Execution

```python
@workflow.defn(name="CodeScanWorkflow")
class CodeScanWorkflow:
    async def run(self, scan_id: str, code_path: str, patterns: List[str]):
        # Step 1: Run SA tools in parallel
        semgrep, bandit, ruff = await asyncio.gather(
            execute_activity(run_semgrep, code_path),
            execute_activity(run_bandit, code_path),
            execute_activity(run_ruff, code_path)
        )

        # Step 2: Parse SARIF outputs
        findings = await execute_activity(parse_sarif, [semgrep, bandit, ruff])

        # Step 3: Deduplicate (child workflow)
        deduplicated = await execute_child_workflow(
            DeduplicateFindings,
            findings
        )

        # Step 4: Run each agent pattern for comparison
        results = {}
        for pattern in patterns:
            results[pattern] = await execute_child_workflow(
                f"{pattern}Adjudication",
                deduplicated
            )

        # Step 5: Store metrics
        await execute_activity(store_metrics, results)
        return results
```

### Workflow 2: Deduplication Pipeline

```python
@workflow.defn(name="DeduplicateFindings")
class DeduplicateFindings:
    async def run(self, findings: List[Finding]):
        # Step 1: Exact matching (hash-based)
        exact_clusters = await execute_activity(exact_dedup, findings)

        # Step 2: Semantic clustering (Qdrant)
        unique = [c[0] for c in exact_clusters.values()]
        semantic_clusters = await execute_activity(
            semantic_cluster,
            unique,
            threshold=0.85
        )

        # Step 3: LLM confirmation for near-duplicates
        confirmed = []
        for cluster in semantic_clusters:
            result = await execute_activity(
                llm_confirm_dedup,
                cluster
            )
            confirmed.append(result)

        return build_final_set(confirmed)
```

### Workflow 3: Multi-Agent Adjudication

```python
@workflow.defn(name="MultiAgentAdjudication")
class MultiAgentAdjudication:
    async def run(self, findings: List[Finding]):
        results = []
        for finding in findings:
            # Step 1: Triage (fast/cheap)
            triage = await execute_activity(
                triage_agent_classify,
                finding
            )

            if triage['classification'] == 'LIKELY_SAFE':
                results.append({
                    'verdict': 'FALSE_POSITIVE',
                    'agents_used': ['triage'],
                    'cost': triage['cost']
                })
                continue

            # Step 2: Detailed explanation (only if likely vuln)
            explanation = await execute_activity(
                explainer_agent_analyze,
                finding
            )

            # Step 3: Fix suggestion (only if true positive)
            fix = None
            if explanation['verdict'] == 'TRUE_POSITIVE':
                fix = await execute_activity(
                    fixer_agent_suggest,
                    finding,
                    explanation
                )

            results.append({
                'verdict': explanation['verdict'],
                'agents_used': ['triage', 'explainer', 'fixer'] if fix else ['triage', 'explainer'],
                'cost': triage['cost'] + explanation['cost'] + (fix['cost'] if fix else 0),
                'fix': fix
            })

        return results
```

---

## Agent Implementation (Langroid)

### Triage Agent (Pattern C)

```python
from langroid.agent.chat_agent import ChatAgent, ChatAgentConfig
from langroid.language_models.openai_gpt import OpenAIGPTConfig

class TriageAgent:
    def __init__(self, system_prompt: str):
        self.config = ChatAgentConfig(
            name="TriageAgent",
            llm=OpenAIGPTConfig(
                chat_model="gpt-4o",  # Fast and cheap
                temperature=0.1,
                max_output_tokens=500
            ),
            system_message=system_prompt
        )
        self.agent = ChatAgent(self.config)

    async def classify(self, finding: Dict) -> Dict:
        prompt = f"""Classify this static analysis finding as LIKELY_VULN or LIKELY_SAFE.

Tool: {finding['tool']}
Rule: {finding['rule_id']}
Code:
```python
{finding['code_snippet']}
```

Respond with JSON ONLY:
{{
    "classification": "LIKELY_VULN" | "LIKELY_SAFE",
    "confidence": 0.0-1.0,
    "reasoning": "one sentence"
}}
"""
        response = await self.agent.llm_response_async(prompt)
        return json.loads(response.content)
```

### Explainer Agent (Pattern C)

```python
from anthropic import Anthropic

class ExplainerAgent:
    def __init__(self, system_prompt: str):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.system_prompt = system_prompt

    async def explain(self, finding: Dict) -> Dict:
        prompt = f"""Provide detailed vulnerability analysis.

Code:
```python
{finding['code_snippet']}
```

Analyze step-by-step:
1. Identify input sources
2. Trace data flow
3. Check sanitization
4. Assess exploitability

Respond with JSON:
{{
    "verdict": "TRUE_POSITIVE|FALSE_POSITIVE|UNCERTAIN",
    "confidence": 0.0-1.0,
    "trace": ["step 1", "step 2", ...],
    "cwe_id": "CWE-XXX",
    "reasoning": "detailed explanation"
}}
"""

        message = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )

        return json.loads(message.content[0].text)
```

### Interactive Agent (Pattern B)

```python
class InteractiveAgent:
    """Agent that requests context dynamically"""

    def __init__(self, rust_parser_url: str):
        self.parser_url = rust_parser_url
        self.agent = ChatAgent(...)

    async def analyze(self, finding: Dict) -> Dict:
        context_history = []

        # Start with minimal context
        prompt = f"Analyze this finding: {finding['message']}\nCode: {finding['code_snippet']}"

        while True:
            response = await self.agent.llm_response_async(prompt)

            # Check if LLM requests more context
            if "NEED_FUNCTION:" in response.content:
                func_name = extract_function_name(response.content)

                # Fetch from Rust parser service
                func_def = await self.fetch_function(func_name)
                context_history.append(func_name)

                prompt = f"Here's the definition of {func_name}:\n{func_def}\nContinue analysis."

            elif "FINAL_VERDICT:" in response.content:
                return {
                    'verdict': extract_verdict(response.content),
                    'context_requests': context_history,
                    'reasoning': response.content
                }

    async def fetch_function(self, func_name: str) -> str:
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                f"{self.parser_url}/parse",
                json={"code": self.full_code, "query_type": "functions"}
            )
            data = await response.json()
            return next(f['content'] for f in data['result'] if f['name'] == func_name)
```

---

## Database Schema (Required Tables)

### Existing (Keep)
- ✅ `projects` - Project metadata
- ✅ `code_scans` - Scan execution records
- ✅ `static_analysis_findings` - Raw SA findings
- ✅ `finding_clusters` - Deduplication clusters
- ✅ `llm_configs` - LLM provider configuration
- ✅ `system_prompts` - Agent prompt templates

### Missing (Must Add)

```sql
-- Temporal workflow tracking
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY,
    scan_id UUID REFERENCES code_scans(id),
    temporal_workflow_id VARCHAR(255) UNIQUE,
    temporal_run_id VARCHAR(255),
    workflow_name VARCHAR(255),
    status VARCHAR(50),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    parameters JSONB,
    result JSONB
);

-- Agent interaction logs (for transparency)
CREATE TABLE agent_interactions (
    id UUID PRIMARY KEY,
    workflow_execution_id UUID REFERENCES workflow_executions(id),
    agent_name VARCHAR(100),
    agent_type VARCHAR(50), -- 'triage', 'explainer', 'fixer'
    finding_id UUID REFERENCES static_analysis_findings(id),
    prompt TEXT,
    response TEXT,
    tokens_used INTEGER,
    cost_usd DECIMAL(10, 6),
    latency_ms INTEGER,
    created_at TIMESTAMP
);

-- Pattern performance metrics (for comparison)
CREATE TABLE pattern_metrics (
    id UUID PRIMARY KEY,
    scan_id UUID REFERENCES code_scans(id),
    pattern VARCHAR(50), -- 'post_processing', 'interactive', 'multi_agent'
    total_findings INTEGER,
    true_positives INTEGER,
    false_positives INTEGER,
    uncertain_count INTEGER,
    avg_confidence FLOAT,
    total_tokens_used INTEGER,
    total_cost_usd DECIMAL(10, 4),
    avg_latency_ms INTEGER,
    execution_time_seconds INTEGER
);

-- RAG documents
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    doc_type VARCHAR(50), -- 'requirement', 'assumption', 'architecture'
    format VARCHAR(20), -- 'structured', 'unstructured'
    title VARCHAR(255),
    content TEXT,
    structured_data JSONB,
    qdrant_collection VARCHAR(255),
    embedding_id VARCHAR(255),
    created_at TIMESTAMP
);
```

---

## Docker Compose Services (Required)

### Existing (Keep)
- ✅ `postgres` - PostgreSQL 15
- ✅ `redis` - Redis 7
- ✅ `minio` - S3-compatible storage
- ✅ `django` - Django backend

### Missing (Must Add)

```yaml
services:
  # Temporal Server (all-in-one)
  temporal:
    image: temporalio/auto-setup:latest
    environment:
      - DB=postgresql
      - POSTGRES_SEEDS=postgres
      - DYNAMIC_CONFIG_FILE_PATH=config/dynamicconfig/development-sql.yaml
    ports:
      - "7233:7233"  # gRPC
      - "8233:8233"  # UI
    depends_on:
      - postgres

  # Temporal Worker (runs workflows)
  temporal-worker:
    build: ./backend
    command: python workers/temporal_worker.py
    environment:
      TEMPORAL_HOST: temporal:7233
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - temporal
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # For running SA tools

  # Qdrant Vector Database
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"  # HTTP
      - "6334:6334"  # gRPC
    volumes:
      - qdrant_data:/qdrant/storage

  # Rust Parser Service
  rust-parser:
    build: ./rust-parser
    ports:
      - "8001:8001"
    environment:
      RUST_LOG: info

  # Static Analysis Tools (on-demand)
  semgrep:
    image: returntocorp/semgrep:latest
    profiles: [tools]

  bandit:
    build: ./docker/bandit
    profiles: [tools]

  ruff:
    build: ./docker/ruff
    profiles: [tools]

  # React Frontend
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      REACT_APP_API_URL: http://localhost:8000
      REACT_APP_WS_URL: ws://localhost:8000
    depends_on:
      - django
```

---

## Success Metrics

The POC is successful if it demonstrates:

### Quantitative Metrics
1. **F1 Score ≥ 0.75** on vulnerability detection (target: match GPT-4.1 at 0.797)
2. **Finding Reduction:** 40-60% through deduplication
3. **Cost Savings:** Multi-agent pattern 30-50% cheaper than post-processing with Claude
4. **Token Efficiency:** Interactive pattern uses <50% tokens vs post-processing

### Qualitative Metrics
5. **Visual DAG:** Temporal UI shows complete workflow execution
6. **Agent Comparison:** Side-by-side metrics dashboard for 3 patterns
7. **Chat Demo:** Interactive LLM queries with context retrieval
8. **Deduplication:** Semantic clustering visibly better than exact matching

---

## Non-Requirements (Out of Scope)

### Explicitly Not Needed for POC
- ❌ Production deployment (local Docker only)
- ❌ User authentication beyond basic Django auth
- ❌ Multi-tenant security hardening (single-user POC)
- ❌ CI/CD integration
- ❌ Rate limiting beyond basic protection
- ❌ Advanced caching strategies
- ❌ Mobile responsiveness
- ❌ Internationalization (i18n)
- ❌ Email notifications
- ❌ Webhooks
- ❌ Data export APIs
- ❌ Advanced monitoring (Prometheus/Grafana)

### Keep Simple
- Single project support (no multi-project dashboard)
- Basic error handling (no advanced retry strategies beyond Temporal)
- Simple UI (functional over beautiful)
- Mock data acceptable for demonstrations

---

## Development Phases

### Phase 1: Foundation (Week 1-2)
**Goal:** Infrastructure + LLM integration proof-of-concept

- [ ] Remove Celery completely from project
- [ ] Add Temporal server + worker to Docker Compose
- [ ] Create basic Temporal workflow (hello world)
- [ ] Integrate Anthropic SDK with single Claude call
- [ ] Integrate OpenAI SDK with single GPT call
- [ ] Deploy Qdrant to Docker Compose
- [ ] Create basic Langroid agent (single LLM call)
- [ ] **Milestone:** Can trigger Temporal workflow that calls LLM and stores result

### Phase 2: Static Analysis Pipeline (Week 3)
**Goal:** Generate findings to feed LLM agents

- [ ] Create Semgrep Docker image
- [ ] Create Bandit Docker image
- [ ] Create Ruff Docker image
- [ ] Implement Temporal workflow to run all 3 tools
- [ ] Parse SARIF outputs to normalized schema
- [ ] Store findings in PostgreSQL
- [ ] **Milestone:** Can scan Python code and generate findings database

### Phase 3: Agent Pattern A - Post-Processing (Week 4)
**Goal:** First complete agent pattern working

- [ ] Implement TriageAgent with Langroid + GPT-4o
- [ ] Implement ExplainerAgent with Langroid + Claude Sonnet 4
- [ ] Create Temporal workflow for post-processing pattern
- [ ] Track tokens, cost, latency for each LLM call
- [ ] Store adjudications in database
- [ ] **Milestone:** Can adjudicate findings and see metrics

### Phase 4: Deduplication System (Week 5)
**Goal:** Reduce finding count by 40-60%

- [ ] Implement exact matching (hash-based)
- [ ] Build Rust embedding service
- [ ] Generate embeddings for code snippets
- [ ] Store embeddings in Qdrant
- [ ] Implement semantic clustering (similarity search)
- [ ] Create LLM-based confirmation for near-duplicates
- [ ] **Milestone:** Can deduplicate findings with visible reduction

### Phase 5: Agent Patterns B & C (Week 6-7)
**Goal:** Complete all 3 patterns for comparison

- [ ] Implement Interactive pattern with context requests
- [ ] Build Rust parser service with tree-sitter
- [ ] Implement Multi-Agent pattern (Triage → Explainer → Fixer)
- [ ] Create FixerAgent with code fix suggestions
- [ ] Run all 3 patterns on same dataset
- [ ] Store comparative metrics
- [ ] **Milestone:** Can compare 3 patterns side-by-side

### Phase 6: Rust Parser Service (Week 8)
**Goal:** Enable context-aware analysis

- [ ] Set up Rust project with Actix-web + tree-sitter
- [ ] Implement `/parse` endpoint (functions, classes, AST)
- [ ] Implement `/embeddings` endpoint (batch processing)
- [ ] Integrate with Interactive agent
- [ ] **Milestone:** Interactive agent can request and receive context

### Phase 7: Frontend (Week 9-11)
**Goal:** Visual demonstration of POC

- [ ] Set up React + TypeScript project
- [ ] Implement findings dashboard with filtering
- [ ] Integrate ReactFlow for DAG visualization
- [ ] Create Monaco editor with finding highlights
- [ ] Build pattern comparison metrics view
- [ ] Implement chat interface with streaming
- [ ] **Milestone:** Can demonstrate POC visually

### Phase 8: RAG System (Week 12)
**Goal:** Context-aware analysis with custom requirements

- [ ] Implement document upload/parsing
- [ ] Generate embeddings for requirement docs
- [ ] Store in Qdrant with metadata
- [ ] Build retrieval system for context injection
- [ ] Test with structured and unstructured docs
- [ ] **Milestone:** Can query custom requirements during analysis

### Phase 9: Testing & Polish (Week 13)
**Goal:** Production-ready demo

- [ ] End-to-end integration tests
- [ ] Benchmark on medium-sized codebases (5-10K LOC)
- [ ] Optimize Temporal workflows
- [ ] Tune vector search parameters
- [ ] Document findings and create demo script
- [ ] **Milestone:** POC ready for presentation

---

## Quick Start (Target: Arch/Ubuntu)

### Prerequisites

**System Requirements:**
- Arch Linux (Manjaro) OR Ubuntu 22.04+
- Docker 24.0+ with Docker Compose V2
- Pixi package manager
- 16GB RAM minimum (for LLM calls + Temporal + Qdrant)
- 20GB free disk space

**API Keys Required:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."  # Required
export OPENAI_API_KEY="sk-..."         # Required
export GOOGLE_API_KEY="..."            # Optional
```

### Installation

**Arch/Manjaro:**
```bash
# Install system dependencies
sudo pacman -S docker docker-compose git base-devel

# Install Pixi
yay -S pixi
# OR
curl -fsSL https://pixi.sh/install.sh | bash

# Start Docker
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker
```

**Ubuntu:**
```bash
# Install system dependencies
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git build-essential libpq-dev

# Install Pixi
curl -fsSL https://pixi.sh/install.sh | bash
export PATH="$HOME/.pixi/bin:$PATH"

# Start Docker
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker
```

### Project Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd review-pro

# 2. Install Python dependencies with Pixi
pixi install

# 3. Set up environment variables
cp .env.example .env
nano .env  # Add your API keys

# 4. Start infrastructure (Postgres, Redis, Temporal, Qdrant)
docker compose up -d postgres redis temporal qdrant

# 5. Wait for services to be ready
docker compose logs -f temporal  # Wait for "Started Temporal server"

# 6. Run database migrations
pixi run migrate

# 7. Load default system prompts
pixi run django python manage.py load_system_prompts

# 8. Start Temporal worker
pixi run temporal-worker  # In separate terminal

# 9. Start Django backend
pixi run runserver  # In separate terminal

# 10. Start frontend (when implemented)
cd frontend && npm install && npm start
```

### Verify Installation

```bash
# Check all services are running
docker compose ps

# Should see:
# - postgres (healthy)
# - redis (healthy)
# - temporal (running, ports 7233, 8233)
# - qdrant (running, ports 6333, 6334)

# Access services:
# - Django API: http://localhost:8000
# - Django Admin: http://localhost:8000/admin
# - Temporal UI: http://localhost:8233
# - Qdrant Dashboard: http://localhost:6333/dashboard
# - Frontend: http://localhost:3000 (when implemented)
```

### Run Test Scan

```bash
# Upload test Python file and run scan
pixi run django python manage.py test_scan \
    --file examples/vulnerable_code.py \
    --patterns post_processing interactive multi_agent

# Watch workflow execution in Temporal UI
# Open http://localhost:8233 → Recent Workflows
```

---

## Environment Variables

```bash
# .env.example

# === LLM Provider API Keys (REQUIRED) ===
ANTHROPIC_API_KEY=sk-ant-your-key-here  # Required for Claude
OPENAI_API_KEY=sk-your-key-here          # Required for GPT
GOOGLE_API_KEY=your-key-here             # Optional for Gemini

# === Database ===
DATABASE_URL=postgresql://sa_user:sa_password@localhost:5432/static_analysis

# === Temporal ===
TEMPORAL_HOST=localhost:7233

# === Qdrant Vector Database ===
QDRANT_HOST=localhost
QDRANT_PORT=6333

# === Rust Parser Service ===
RUST_PARSER_URL=http://localhost:8001

# === Django ===
SECRET_KEY=your-django-secret-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# === Redis ===
REDIS_URL=redis://localhost:6379/0

# === S3/MinIO ===
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_STORAGE_BUCKET_NAME=sarif-files
AWS_S3_ENDPOINT_URL=http://localhost:9000

# === CORS (for frontend) ===
CORS_ALLOWED_ORIGINS=http://localhost:3000

# === Rate Limiting (optional) ===
ANTHROPIC_RPM=50  # Requests per minute
OPENAI_RPM=60
GOOGLE_RPM=60
```

---

## Common Issues & Solutions

### "Temporal connection refused"
```bash
# Ensure Temporal is running
docker compose logs temporal

# Restart if needed
docker compose restart temporal

# Wait 30 seconds for initialization
```

### "LLM API key invalid"
```bash
# Verify keys are set
echo $ANTHROPIC_API_KEY
echo $OPENAI_API_KEY

# Re-export if needed
export ANTHROPIC_API_KEY="sk-ant-..."

# Restart Django/worker
pixi run runserver
```

### "Qdrant collection not found"
```bash
# Initialize collections
pixi run django python manage.py init_qdrant

# Or manually via Qdrant API:
curl -X PUT http://localhost:6333/collections/code_findings \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 768, "distance": "Cosine"}}'
```

### "Docker socket permission denied"
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker ps
```

---

## Summary

**What Must Be Built:**
1. ✅ Temporal workflows (NOT Celery)
2. ✅ Langroid multi-agent system
3. ✅ LLM integration (Claude, GPT, Gemini)
4. ✅ Static analysis tools (Semgrep, Bandit, Ruff)
5. ✅ Three agent patterns with metrics
6. ✅ Qdrant for semantic clustering
7. ✅ Rust parser service
8. ✅ React frontend with DAG visualization

**What Already Exists (Keep):**
- ✅ Django models and schema
- ✅ PostgreSQL with good indexing
- ✅ Docker Compose environment
- ✅ Pixi integration
- ✅ ADR documentation

**Timeline:** 13 weeks for complete POC
**Priority:** LLM integration → Temporal workflows → Static analysis tools → Agent patterns → Frontend
