# Setup Guide - Static Analysis Platform with Multi-Agent LLM Integration

This guide will help you set up and test the complete platform locally.

## Prerequisites

- Docker and Docker Compose installed
- Git installed
- At least 8GB RAM available
- Ports available: 3000, 5432, 6333, 6379, 7233, 8000, 8233, 9000, 9001

## Quick Start

### 1. Clone and Configure

```bash
# Clone the repository
git clone <repository-url>
cd review-pro

# Create .env file
cp .env.example .env

# Edit .env and add required values:
# - SECRET_KEY (generate with: openssl rand -base64 32)
# - DEBUG=True for development
# - Add LLM API keys if testing AI features:
#   - OPENAI_API_KEY
#   - ANTHROPIC_API_KEY
#   - GOOGLE_API_KEY
```

### 2. Start Infrastructure Services

```bash
# Start all services
docker compose up -d

# Check service health
docker compose ps

# View logs
docker compose logs -f
```

Services will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs/
- **Temporal UI**: http://localhost:8233
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

### 3. Initialize Database

```bash
# Create migrations for all apps
docker compose exec web python manage.py makemigrations

# Apply migrations
docker compose exec web python manage.py migrate

# Create sample data for testing
docker compose exec web python manage.py create_sample_data

# Or reset and create fresh data
docker compose exec web python manage.py create_sample_data --reset
```

### 4. Access the Platform

Open http://localhost:3000 in your browser.

**Demo Accounts:**
- **Admin**: admin@example.com / admin123
- **Demo User**: demo@example.com / demo123

## Testing the Full Stack

### 1. Frontend-Backend Integration

Test that the React frontend can communicate with Django backend:

```bash
# The frontend dashboard should load data
# Navigate to: http://localhost:3000

# Expected behavior:
# - Dashboard shows scan statistics
# - Scans list displays sample scans
# - Clicking a scan shows findings
# - Charts and visualizations render correctly
```

### 2. Temporal Workflows

Test that workflows can be triggered from the API:

```bash
# Check Temporal is running
docker compose logs temporal

# Check worker is running
docker compose logs temporal-worker

# Trigger a scan from the UI:
# 1. Go to http://localhost:3000/scans
# 2. Click "New Scan"
# 3. Fill in repository details
# 4. Submit

# Monitor workflow execution:
# - Open Temporal UI: http://localhost:8233
# - View workflow execution details
# - Check for any errors
```

### 3. LLM Adjudication

Test LLM-based false positive filtering:

```bash
# Ensure API keys are set in .env
# Trigger adjudication from UI:
# 1. Go to a completed scan
# 2. Click "Adjudicate Findings"
# 3. Select LLM provider and model
# 4. Submit

# Monitor in Temporal UI
# Results will appear in the findings list with LLM verdicts
```

### 4. Semantic Clustering

Test vector-based finding clustering:

```bash
# Trigger clustering from UI:
# 1. Go to a completed scan
# 2. Click "Cluster Findings"
# 3. Select algorithm (DBSCAN/Agglomerative)
# 4. Submit

# View clusters:
# - Navigate to Clusters tab
# - Each cluster shows related findings
# - Distance to centroid indicates similarity
```

### 5. Pattern Comparison

Test multi-agent pattern comparison:

```bash
# Trigger comparison from UI:
# 1. Go to a completed scan
# 2. Click "Compare Patterns"
# 3. Wait for workflow completion

# View results in Pattern Comparison tab
# Shows effectiveness of different agent patterns
```

## API Testing

### Using cURL

```bash
# Get JWT token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' \
  | jq -r '.access')

# Get dashboard stats
curl http://localhost:8000/api/dashboard/stats/ \
  -H "Authorization: Bearer $TOKEN" | jq

# List scans
curl http://localhost:8000/api/scans/ \
  -H "Authorization: Bearer $TOKEN" | jq

# Get scan details
curl http://localhost:8000/api/scans/{scan_id}/ \
  -H "Authorization: Bearer $TOKEN" | jq

# Trigger adjudication
curl -X POST http://localhost:8000/api/scans/{scan_id}/adjudicate/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o",
    "pattern": "post_processing",
    "batch_size": 10,
    "max_findings": 100
  }' | jq

# Trigger clustering
curl -X POST http://localhost:8000/api/scans/{scan_id}/cluster/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm": "dbscan",
    "threshold": 0.85
  }' | jq
```

### Using the API Documentation

Navigate to http://localhost:8000/api/docs/ for interactive API documentation.

## Troubleshooting

### Services Not Starting

```bash
# Check logs for specific service
docker compose logs <service-name>

# Common services:
# - web (Django backend)
# - frontend (React app)
# - db (PostgreSQL)
# - temporal (Workflow engine)
# - temporal-worker (Workflow executor)
# - qdrant (Vector database)
```

### Database Issues

```bash
# Reset database
docker compose down -v
docker compose up -d db redis
docker compose exec db psql -U postgres -c "CREATE DATABASE secanalysis;"
docker compose up -d

# Re-run migrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py create_sample_data
```

### Frontend Not Loading

```bash
# Check frontend logs
docker compose logs frontend

# Rebuild frontend
docker compose up -d --build frontend

# Check if backend is accessible
curl http://localhost:8000/api/dashboard/stats/
```

### Temporal Workflows Failing

```bash
# Check Temporal server
docker compose logs temporal

# Check worker logs
docker compose logs temporal-worker

# Verify Temporal connection
docker compose exec temporal-worker python -c "
from temporalio.client import Client
import asyncio

async def test():
    client = await Client.connect('temporal:7233')
    print('Connected successfully!')

asyncio.run(test())
"
```

### Qdrant Vector DB Issues

```bash
# Check Qdrant logs
docker compose logs qdrant

# Verify collections exist
curl http://localhost:6333/collections

# Recreate collections (if needed)
docker compose exec temporal-worker python -c "
from services.vector_service import initialize_qdrant_collections
import asyncio
asyncio.run(initialize_qdrant_collections())
"
```

## Development Workflow

### Hot Reload

Both frontend and backend support hot reload in development:

```bash
# Frontend changes auto-reload
# Edit files in frontend/src/

# Backend changes require restart
docker compose restart web

# Worker changes require restart
docker compose restart temporal-worker
```

### Running Tests

```bash
# Backend tests
docker compose exec web python manage.py test

# Frontend tests
docker compose exec frontend npm test

# Type checking
docker compose exec frontend npm run type-check

# Linting
docker compose exec frontend npm run lint
```

### Database Management

```bash
# Access PostgreSQL shell
docker compose exec db psql -U postgres -d secanalysis

# Create a database backup
docker compose exec db pg_dump -U postgres secanalysis > backup.sql

# Restore from backup
docker compose exec -T db psql -U postgres secanalysis < backup.sql
```

## Architecture Overview

```
┌─────────────────┐
│  React Frontend │  (Port 3000)
│   (Vite + TS)   │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│  Django Backend │  (Port 8000)
│   (REST API)    │
└────────┬────────┘
         │
         ├─────────► PostgreSQL (Port 5432)
         ├─────────► Redis (Port 6379)
         ├─────────► MinIO/S3 (Port 9000)
         │
         │ Trigger Workflows
         ▼
┌─────────────────┐
│ Temporal Server │  (Port 7233, UI: 8233)
└────────┬────────┘
         │ Execute
         ▼
┌─────────────────┐
│ Temporal Worker │
│  - Scan Workflow
│  - Adjudication
│  - Clustering
│  - Comparison
└────────┬────────┘
         │
         ├─────────► Qdrant (Vector DB, Port 6333)
         ├─────────► Docker (Run SA tools)
         └─────────► LLM APIs (OpenAI, Anthropic, Google)
```

## Next Steps

1. **Configure GitHub Integration**
   - Set up GitHub App for repository access
   - Configure webhook for automatic scans

2. **Add More Security Tools**
   - Extend scan workflow with additional tools
   - Configure tool-specific settings

3. **Production Deployment**
   - Configure proper secrets management
   - Set up monitoring and alerting
   - Configure SSL/TLS
   - Set up CDN for frontend

4. **Scaling**
   - Add more Temporal workers
   - Configure horizontal pod autoscaling
   - Set up read replicas for PostgreSQL

## Support

For issues and questions:
- Check the [API Documentation](http://localhost:8000/api/docs/)
- View [Temporal Workflows](http://localhost:8233)
- Check service logs: `docker compose logs -f <service>`
