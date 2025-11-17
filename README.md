# Static Analysis Platform with Multi-Agent LLM Integration

A proof-of-concept research platform demonstrating LLM-enhanced static analysis with empirical comparison of three agent patterns. Built with Django, Temporal workflows, Langroid multi-agent system, and React + TypeScript frontend.

## Project Status

**Current Implementation:** ~75% Complete (Backend core + Frontend complete)

### ✅ Completed
- **Phase 1-2**: Infrastructure & Static Analysis (Temporal, Semgrep/Bandit/Ruff, SARIF parsing)
- **Phase 3**: LLM Adjudication (Post-processing filter pattern)
- **Phase 4**: Interactive & Multi-Agent Patterns (3 agent patterns implemented)
- **Phase 5**: Semantic Clustering (Qdrant + vector embeddings)
- **Frontend**: Complete React + TypeScript UI with all pages

### 🚧 In Progress
- Django REST API endpoints for frontend
- Database migrations for new models
- Integration testing

### 📋 Remaining
- Rust parser service
- WebSocket real-time updates
- Authentication/authorization
- Production deployment
- Performance optimization

**See**: [MISSING_REQUIREMENTS.md](./MISSING_REQUIREMENTS.md) for detailed gap analysis

## Core Features

- ✅ **Static Analysis Pipeline**: Scan Python code with Semgrep, Bandit, and Ruff
- ✅ **LLM Adjudication**: Use Claude, GPT to filter false positives
- ✅ **Three Agent Patterns**: Post-processing, interactive retrieval, and multi-agent collaboration
- ✅ **Temporal Workflows**: Durable execution with DAG visualization
- ✅ **Semantic Deduplication**: 40-60% finding reduction using Qdrant vector search
- ✅ **React Frontend**: Dashboard, scans, findings, clusters, pattern comparison
- ⏳ **Interactive Chat**: Query codebase with context-aware LLM agents (backend ready, frontend TBD)
- ⏳ **Performance Metrics**: Empirical comparison framework ready (needs API endpoints)

## Architecture

This is a **research POC**, not a production security platform. See [REQUIREMENTS.md](./REQUIREMENTS.md) for complete specification.

### Technology Stack

**Backend:**
- Django 5.0 + Django REST Framework
- Temporal workflow orchestration (v1.5.0)
- Langroid multi-agent framework (v0.1.297)
- PostgreSQL 18+ (with Row-Level Security)
- Python 3.12+
- Qdrant vector database (v1.7.0)

**Frontend:**
- React 18 + TypeScript
- Vite (dev server + build tool)
- TailwindCSS for styling
- TanStack Query for data fetching
- Recharts for visualizations
- React Router for routing

**Static Analysis Tools:**
- Semgrep (multi-language SAST)
- Bandit (Python security)
- Ruff (fast Python linter)
- All run in isolated Docker containers

**LLM Providers:**
- Anthropic Claude (Sonnet 4)
- OpenAI GPT-4o
- OpenAI text-embedding-3-small (for vector embeddings)

**Infrastructure:**
- Docker Compose for local development
- Pixi for Python environment management

## Quick Start

### Prerequisites

**Supported Platforms:**
- **Arch Linux** (Manjaro, EndeavourOS, etc.)
- **Ubuntu 22.04+** (Debian-based distros)

**Required:**
- [Pixi](https://prefix.dev/docs/pixi/overview) package manager
- Docker 24.0+ with Docker Compose V2
- Node.js 18+ and npm (for frontend)
- Git 2.30+
- 16GB RAM (for LLM calls + Temporal + Qdrant)
- **API Keys** for Anthropic (Claude) and OpenAI (GPT)

> 💡 **New to Pixi?** It's a modern, fast Python package manager. Install with `curl -fsSL https://pixi.sh/install.sh | bash`

### Installation

**Arch/Manjaro:**
```bash
# Install system dependencies
sudo pacman -S docker docker-compose git base-devel nodejs npm

# Install Pixi
yay -S pixi
# OR: curl -fsSL https://pixi.sh/install.sh | bash

# Start Docker
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker
```

**Ubuntu 22.04+:**
```bash
# Install system dependencies
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git build-essential libpq-dev nodejs npm

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

# 2. Install backend dependencies with Pixi
pixi install

# 3. Install frontend dependencies
cd frontend
npm install
cd ..

# 4. Configure environment (CRITICAL: Add your API keys!)
cp .env.example .env
nano .env  # Add ANTHROPIC_API_KEY and OPENAI_API_KEY

# 5. Start infrastructure (Postgres, Temporal, Qdrant)
docker compose up -d postgres temporal qdrant

# 6. Wait for Temporal to initialize (30 seconds)
docker compose logs -f temporal  # Look for "Started Temporal server"

# 7. Run database migrations
pixi run migrate

# 8. Start Temporal worker (separate terminal)
pixi run temporal-worker

# 9. Start Django backend (separate terminal)
pixi run runserver

# 10. Start frontend dev server (separate terminal)
cd frontend
npm run dev

# 11. Access the application
# Frontend:  http://localhost:3000
# API:       http://localhost:8000
# Temporal:  http://localhost:8233
# Qdrant:    http://localhost:6333/dashboard
```

### Run Test Scan

```bash
# Test the complete pipeline (SA tools → LLM adjudication)
pixi run django python manage.py test_scan \
    --file examples/vulnerable_code.py \
    --pattern post_processing

# Watch workflow execution in Temporal UI
open http://localhost:8233
```

**Available Pixi Commands:**
- `pixi run runserver` - Start Django dev server (port 8000)
- `pixi run temporal-worker` - Start Temporal worker
- `pixi run migrate` - Run database migrations
- `pixi run makemigrations` - Create new migrations
- `pixi run test` - Run backend tests
- `pixi run format` - Format code (Black + isort)
- `pixi run lint` - Lint code (flake8 + mypy)
- `pixi task list` - See all available tasks

**Frontend Commands:**
```bash
cd frontend
npm run dev          # Start dev server (port 3000)
npm run build        # Build for production
npm run type-check   # TypeScript type checking
npm run lint         # ESLint checking
```

## Project Structure

```
review-pro/
├── backend/                    # Django backend
│   ├── apps/                   # Django applications
│   │   ├── authentication/     # JWT & GitHub OAuth
│   │   ├── organizations/      # Multi-tenancy & repos
│   │   ├── scans/              # Security scans
│   │   ├── findings/           # Security findings (+ LLMVerdict, FindingCluster)
│   │   └── users/              # User management
│   ├── agents/                 # Langroid LLM agents
│   │   ├── adjudicator.py      # Post-processing filter agent
│   │   ├── interactive_agent.py # Interactive retrieval agent
│   │   ├── multi_agent.py      # Multi-agent collaboration
│   │   └── pattern_comparison.py # Pattern comparison framework
│   ├── scanner/                # Static analysis tools
│   │   ├── base.py             # Base scanner with Docker execution
│   │   ├── semgrep.py          # Semgrep scanner
│   │   ├── bandit.py           # Bandit scanner
│   │   ├── ruff.py             # Ruff scanner
│   │   └── sarif_parser.py     # SARIF 2.1.0 parser
│   ├── services/               # Business logic services
│   │   ├── embedding_service.py # OpenAI embeddings
│   │   ├── qdrant_manager.py   # Vector database operations
│   │   └── clustering_service.py # DBSCAN + Agglomerative clustering
│   ├── workflows/              # Temporal workflows
│   │   ├── scan_workflow.py    # Main scan orchestration
│   │   ├── adjudication_workflow.py # LLM adjudication
│   │   ├── comparison_workflow.py # Pattern comparison
│   │   └── clustering_workflow.py # Semantic clustering
│   ├── workers/
│   │   └── temporal_worker.py  # Temporal worker process
│   ├── config/                 # Django settings
│   │   └── settings.py         # Main settings (Temporal config)
│   ├── manage.py               # Django management
│   └── requirements.txt        # Python dependencies
├── frontend/                   # React + TypeScript frontend
│   ├── src/
│   │   ├── components/         # React components
│   │   │   ├── ui/             # Reusable UI (Card, Badge, Button, etc.)
│   │   │   └── Layout.tsx      # App layout with navigation
│   │   ├── pages/              # Page components
│   │   │   ├── Dashboard.tsx   # Overview with charts
│   │   │   ├── Scans.tsx       # Scan list
│   │   │   ├── ScanDetail.tsx  # Scan detail + actions
│   │   │   ├── Findings.tsx    # Finding list + filters
│   │   │   ├── FindingDetail.tsx # Finding detail + LLM verdicts
│   │   │   ├── Clusters.tsx    # Cluster list
│   │   │   ├── ClusterDetail.tsx # Cluster visualization
│   │   │   └── Patterns.tsx    # Pattern comparison charts
│   │   ├── services/
│   │   │   └── api.ts          # API client (Axios)
│   │   ├── hooks/
│   │   │   └── useApi.ts       # TanStack Query hooks
│   │   ├── types/
│   │   │   └── index.ts        # TypeScript type definitions
│   │   ├── App.tsx             # Root component with routing
│   │   ├── main.tsx            # Entry point
│   │   └── index.css           # Global styles (Tailwind)
│   ├── package.json            # Node dependencies
│   ├── vite.config.ts          # Vite configuration
│   └── tsconfig.json           # TypeScript configuration
├── docker-compose.yml          # Docker services (Postgres, Temporal, Qdrant)
├── pixi.toml                   # Pixi project configuration
├── .env.example                # Environment template
├── GAP_ANALYSIS.md             # What was wrong in original implementation
├── REQUIREMENTS.md             # Complete specification
├── IMPLEMENTATION_ROADMAP.md   # 13-week implementation plan
├── MISSING_REQUIREMENTS.md     # Current gaps and next steps
└── README.md                   # This file
```

## Three Agent Patterns (Implemented)

### 1. Post-Processing Filter (Fast & Cheap)
- **Flow**: SA Tool → LLM Filter
- **Cost**: ~$0.005/finding
- **Latency**: ~800ms/finding
- **Use Case**: High-volume triage, quick filtering

### 2. Interactive Retrieval (Balanced)
- **Flow**: LLM → Request Context → LLM
- **Cost**: ~$0.007/finding
- **Latency**: ~1400ms/finding
- **Use Case**: Adaptive analysis with context gathering

### 3. Multi-Agent Collaboration (Thorough)
- **Flow**: Triage (GPT-4o) → Explainer (Claude) → Fixer (Claude)
- **Cost**: ~$0.015/finding
- **Latency**: ~2200ms/finding
- **Use Case**: Critical findings requiring detailed analysis

## API Documentation

### Backend API (Django REST Framework)

**Base URL**: `http://localhost:8000/api`

**Key Endpoints (Implemented in Code, API Endpoints TBD):**
- `GET /dashboard/stats/` - Dashboard statistics
- `GET /scans/` - List scans
- `GET /scans/:id/` - Scan details
- `POST /scans/:id/adjudicate/` - Trigger LLM adjudication
- `POST /scans/:id/cluster/` - Trigger clustering
- `POST /scans/:id/compare-patterns/` - Run pattern comparison
- `GET /findings/` - List findings (with filters)
- `GET /findings/:id/` - Finding details
- `PATCH /findings/:id/` - Update finding status
- `GET /clusters/` - List clusters
- `GET /clusters/:id/` - Cluster details
- `GET /clusters/:id/findings/` - Cluster member findings

**Note**: API endpoints are currently being implemented. The backend logic exists in workflows and services.

## Configuration

### Environment Variables

See `.env.example` for all available configuration options. Key variables:

**Django:**
- `DEBUG`: Enable debug mode (default: False)
- `SECRET_KEY`: Django secret key (change in production!)
- `DATABASE_URL`: PostgreSQL connection string
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts

**Temporal:**
- `TEMPORAL_HOST`: Temporal server address (default: localhost:7233)
- `TEMPORAL_NAMESPACE`: Temporal namespace (default: default)
- `TEMPORAL_TASK_QUEUE`: Task queue name (default: code-analysis)

**LLM Providers:**
- `ANTHROPIC_API_KEY`: **REQUIRED** - Anthropic API key for Claude
- `OPENAI_API_KEY`: **REQUIRED** - OpenAI API key for GPT and embeddings
- `GOOGLE_API_KEY`: Optional - Google API key for Gemini

**Qdrant:**
- `QDRANT_URL`: Qdrant server URL (default: http://localhost:6333)
- `QDRANT_COLLECTION`: Collection name (default: findings)

**GitHub:**
- `GITHUB_CLIENT_ID`: GitHub OAuth client ID
- `GITHUB_CLIENT_SECRET`: GitHub OAuth client secret

## Testing

**Backend Tests:**
```bash
# Run all tests
pixi run test

# With coverage report
pixi run test-cov

# Specific test file
pytest backend/apps/findings/tests/test_models.py

# Verbose output
pytest -v
```

**Frontend Tests:**
```bash
cd frontend

# Type checking
npm run type-check

# Linting
npm run lint

# Build (validates all imports/types)
npm run build
```

## Development

### Code Quality

**Backend (with Pixi):**
```bash
# Format code (Black + isort)
pixi run format

# Lint code (flake8 + mypy)
pixi run lint

# Run all checks
pixi run format && pixi run lint && pixi run test
```

**Frontend:**
```bash
cd frontend

# Format + lint
npm run lint

# Type checking
npm run type-check

# Build check
npm run build
```

### Database Migrations

```bash
# Create migrations
pixi run makemigrations

# Apply migrations
pixi run migrate

# Show migration status
pixi run showmigrations

# Rollback last migration
pixi run django python manage.py migrate <app_name> <previous_migration>
```

### Temporal Workflows

**Start Worker:**
```bash
pixi run temporal-worker
```

**View Workflow Executions:**
- Open http://localhost:8233
- Navigate to Workflows → All
- Click on any workflow to see execution history, DAG visualization, and event timeline

**Trigger Workflows Programmatically:**
```python
from temporalio.client import Client
from workflows.scan_workflow import ScanRepositoryWorkflow

async def trigger_scan():
    client = await Client.connect("localhost:7233")
    result = await client.execute_workflow(
        ScanRepositoryWorkflow.run,
        args=["scan-id-123", "/path/to/code"],
        id=f"scan-workflow-{scan_id}",
        task_queue="code-analysis",
    )
```

## Monitoring & Debugging

### Service Dashboards

- **Frontend**: http://localhost:3000
- **Django API**: http://localhost:8000
- **Temporal UI**: http://localhost:8233 (workflow visualization, execution history)
- **Qdrant Dashboard**: http://localhost:6333/dashboard (vector database, collections)

### Logs

**Backend Logs:**
```bash
# Django dev server
pixi run runserver  # Logs to console

# Temporal worker
pixi run temporal-worker  # Logs to console
```

**Frontend Logs:**
```bash
cd frontend
npm run dev  # Logs to console + browser DevTools
```

**Docker Services:**
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f postgres
docker compose logs -f temporal
docker compose logs -f qdrant
```

### Debugging Workflows

1. Open Temporal UI: http://localhost:8233
2. Navigate to failing workflow execution
3. Check "Event History" tab for detailed execution timeline
4. Check "Stack Trace" tab for errors
5. Use "Reset" to retry from a specific point

## Deployment

**⚠️ This is a POC/Research Project - NOT production-ready**

For production deployment, you would need:
- Authentication/authorization (JWT, OAuth)
- HTTPS/SSL certificates
- Environment-specific settings
- Database backups
- Monitoring (Prometheus, Grafana)
- Error tracking (Sentry)
- Rate limiting
- Secrets management
- CI/CD pipeline

See [MISSING_REQUIREMENTS.md](./MISSING_REQUIREMENTS.md) for production readiness gaps.

## Contributing

1. Review architecture and implementation status
2. Check [MISSING_REQUIREMENTS.md](./MISSING_REQUIREMENTS.md) for available work
3. Follow code style (Black, isort, flake8 for Python; ESLint for TypeScript)
4. Write tests for new features
5. Update documentation
6. Create a pull request

## Documentation

- [GAP_ANALYSIS.md](./GAP_ANALYSIS.md) - Analysis of original implementation issues
- [REQUIREMENTS.md](./REQUIREMENTS.md) - Complete project specification
- [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) - 13-week implementation plan
- [MISSING_REQUIREMENTS.md](./MISSING_REQUIREMENTS.md) - Current gaps and next steps
- [frontend/README.md](./frontend/README.md) - Frontend-specific documentation

## License

[Add your license here]

## Support

For issues and questions, please open an issue on GitHub.
