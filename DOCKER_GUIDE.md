# Docker Development Guide

This guide covers how to run `review-pro` using Docker and Docker Compose for a fully containerized development environment.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Git

## Installation

### Manjaro Linux

```bash
# Install Docker
sudo pacman -S docker docker-compose

# Start and enable Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to docker group
sudo usermod -aG docker $USER

# Log out and log back in for group changes to take effect
# Or run: newgrp docker
```

### Other Linux Distributions

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose

# Fedora
sudo dnf install docker docker-compose

# Enable and start
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### Verify Installation

```bash
docker --version
docker-compose --version
docker ps  # Should not show permission error
```

## Quick Start with Docker

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd review-pro

# Copy environment configuration
cp .env.example .env

# Edit .env with your configuration
vim .env
```

### 2. Environment Configuration

Key environment variables for Docker setup:

```bash
# Django
SECRET_KEY=your-secret-key-here-generate-new-one
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,web

# Database (Docker internal networking)
DATABASE_URL=postgresql://postgres:postgres@db:5432/secanalysis

# Redis (Docker internal networking)
REDIS_URL=redis://redis:6379/0

# MinIO (Docker internal networking)
USE_S3=True
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_STORAGE_BUCKET_NAME=review-pro
AWS_S3_ENDPOINT_URL=http://minio:9000

# Optional: GitHub OAuth
# GITHUB_CLIENT_ID=your-github-oauth-client-id
# GITHUB_CLIENT_SECRET=your-github-oauth-client-secret
```

**Generate SECRET_KEY:**

```bash
docker-compose run --rm web python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. Start Services

```bash
# Start all services in detached mode
docker-compose up -d

# Check services are running
docker-compose ps

# Expected services:
# - db (PostgreSQL)
# - redis (Redis)
# - minio (MinIO)
# - web (Django)
# - celery_worker (Celery worker)
# - celery_beat (Celery beat scheduler)
```

### 4. Run Initial Setup

```bash
# Wait for services to be ready (about 10 seconds)
sleep 10

# Run database migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser
# Enter email and password when prompted

# Create MinIO bucket (if using S3)
docker-compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker-compose exec minio mc mb local/review-pro
```

### 5. Access the Application

- **API**: http://localhost:8000
- **Admin Interface**: http://localhost:8000/admin
- **API Documentation**: http://localhost:8000/api/docs/
- **MinIO Console**: http://localhost:9001 (credentials: minioadmin/minioadmin)

## Docker Compose Services

### Service Architecture

```yaml
┌─────────────────────────────────────────────┐
│              Frontend/Client                │
│         (http://localhost:8000)             │
└───────────────────┬─────────────────────────┘
                    │
        ┌───────────▼──────────┐
        │     web (Django)     │
        │  Port: 8000          │
        └───┬────────┬────────┬┘
            │        │        │
  ┌─────────▼──┐ ┌──▼────┐ ┌─▼────────┐
  │     db     │ │ redis │ │  minio   │
  │ PostgreSQL │ │       │ │  (S3)    │
  │ Port: 5432 │ │ 6379  │ │ 9000/9001│
  └────────────┘ └───┬───┘ └──────────┘
                     │
          ┌──────────▼─────────────┐
          │   celery_worker        │
          │   celery_beat          │
          └────────────────────────┘
```

### Service Details

**web** - Django application server
- Image: Built from `./backend/Dockerfile` (or Python 3.11)
- Ports: 8000:8000
- Depends on: db, redis, minio

**db** - PostgreSQL database
- Image: postgres:15
- Port: 5432:5432
- Volume: postgres_data (persistent)

**redis** - Redis cache and message broker
- Image: redis:7-alpine
- Port: 6379:6379
- Volume: redis_data (persistent)

**minio** - S3-compatible object storage
- Image: minio/minio:latest
- Ports: 9000:9000 (API), 9001:9001 (Console)
- Volume: minio_data (persistent)

**celery_worker** - Asynchronous task worker
- Image: Same as web
- No exposed ports
- Depends on: db, redis, minio

**celery_beat** - Task scheduler
- Image: Same as web
- No exposed ports
- Depends on: db, redis

## Common Docker Operations

### Starting and Stopping

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d web

# Stop all services
docker-compose stop

# Stop specific service
docker-compose stop web

# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes (WARNING: Deletes data!)
docker-compose down -v
```

### Viewing Logs

```bash
# View all logs
docker-compose logs

# Follow logs (real-time)
docker-compose logs -f

# View specific service logs
docker-compose logs web
docker-compose logs celery_worker
docker-compose logs db

# Follow specific service with tail
docker-compose logs -f --tail=100 web
```

### Executing Commands

```bash
# Django management commands
docker-compose exec web python manage.py <command>

# Examples:
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py shell

# Access PostgreSQL
docker-compose exec db psql -U postgres -d secanalysis

# Access Redis CLI
docker-compose exec redis redis-cli

# Access container shell
docker-compose exec web bash
docker-compose exec db bash
```

### Development Workflow

```bash
# Make code changes (files are mounted as volumes)
vim backend/apps/organizations/models.py

# Restart service to apply changes
docker-compose restart web

# Watch logs for errors
docker-compose logs -f web

# Run tests
docker-compose exec web pytest

# Run migrations after model changes
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
```

## Testing with Docker

### Run Tests

```bash
# All tests
docker-compose exec web pytest

# Unit tests only
docker-compose exec web pytest -m unit

# With coverage
docker-compose exec web pytest --cov=apps --cov-report=html

# Specific test file
docker-compose exec web pytest apps/users/tests/test_models.py

# Specific test function
docker-compose exec web pytest apps/users/tests/test_models.py::TestUserModel::test_create_user

# Verbose output
docker-compose exec web pytest -vv
```

### Debugging

```bash
# Access Django shell
docker-compose exec web python manage.py shell

# Access database directly
docker-compose exec db psql -U postgres -d secanalysis

# Check service health
docker-compose ps
docker-compose exec web python -c "import django; print(django.VERSION)"
docker-compose exec db pg_isready
docker-compose exec redis redis-cli ping
```

## Building Custom Images

### Build Web Service

If you have a custom Dockerfile:

```bash
# Build image
docker-compose build web

# Build without cache
docker-compose build --no-cache web

# Build and start
docker-compose up -d --build web
```

### Build Worker Image

```bash
# Build security worker
cd worker
docker build -t review-pro-worker:latest .

# Test worker
docker run --rm \
  -e GITHUB_TOKEN="your-token" \
  -e REPO_URL="https://github.com/owner/repo" \
  -e BRANCH="main" \
  review-pro-worker:latest
```

## Data Persistence

### Volumes

Docker Compose creates named volumes for data persistence:

```bash
# List volumes
docker volume ls | grep review-pro

# Inspect volume
docker volume inspect review-pro_postgres_data

# Backup database volume
docker run --rm \
  -v review-pro_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_backup.tar.gz /data

# Restore database volume
docker run --rm \
  -v review-pro_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/postgres_backup.tar.gz -C /
```

### Database Backup and Restore

```bash
# Backup database
docker-compose exec -T db pg_dump -U postgres secanalysis > backup.sql

# Restore database
docker-compose exec -T db psql -U postgres secanalysis < backup.sql

# Backup with compression
docker-compose exec -T db pg_dump -U postgres -Fc secanalysis > backup.dump

# Restore compressed backup
docker-compose exec -T db pg_restore -U postgres -d secanalysis < backup.dump
```

## Production Considerations

### Security Hardening

```bash
# Use secrets management (not .env)
# Use Docker secrets or environment-specific configs

# Don't expose database ports
# Comment out db ports in docker-compose.yml:
# db:
#   ports:
#     - "5432:5432"  # Remove in production

# Use non-root users in containers
# Add to Dockerfile:
# USER django
```

### Performance Optimization

```bash
# Use production WSGI server (already in docker-compose)
# Gunicorn or uWSGI instead of runserver

# Adjust worker count
# In docker-compose.yml:
# command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4

# Enable PostgreSQL connection pooling
# Use pgbouncer service

# Use Redis for session storage
# Already configured in settings
```

### Monitoring

```bash
# Add monitoring services to docker-compose.yml
# - Prometheus
# - Grafana
# - Elasticsearch + Kibana for logs

# Check resource usage
docker stats

# Check service health
docker-compose ps
curl http://localhost:8000/api/health/  # If health endpoint exists
```

## Troubleshooting

### Services Not Starting

```bash
# Check logs
docker-compose logs

# Check specific service
docker-compose logs web

# Restart services
docker-compose restart

# Rebuild and restart
docker-compose up -d --build
```

### Database Connection Errors

```bash
# Verify database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Test connection
docker-compose exec web python manage.py dbshell

# Reset database (CAUTION: Deletes data!)
docker-compose down -v
docker-compose up -d
docker-compose exec web python manage.py migrate
```

### Port Conflicts

```bash
# Check if ports are in use
sudo netstat -tulpn | grep LISTEN | grep -E '8000|5432|6379|9000|9001'

# Stop conflicting services or change ports in docker-compose.yml
# Example:
# ports:
#   - "8080:8000"  # Use port 8080 instead of 8000
```

### Volume Permission Issues

```bash
# Fix volume permissions
docker-compose exec web chown -R django:django /app

# Or run as root
docker-compose exec -u root web chown -R django:django /app
```

### Clean Slate

```bash
# Stop everything
docker-compose down

# Remove volumes (WARNING: Deletes all data!)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Remove everything including orphaned containers
docker-compose down -v --rmi all --remove-orphans

# Start fresh
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

## Docker Compose Configuration

### Example docker-compose.yml Structure

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: secanalysis
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"

  web:
    build: ./backend
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
      - minio
    env_file:
      - .env

  celery_worker:
    build: ./backend
    command: celery -A config worker -l info
    volumes:
      - ./backend:/app
    depends_on:
      - db
      - redis
      - minio
    env_file:
      - .env

  celery_beat:
    build: ./backend
    command: celery -A config beat -l info
    volumes:
      - ./backend:/app
    depends_on:
      - db
      - redis
    env_file:
      - .env

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

## Next Steps

- Read the [Quick Start Guide](./QUICKSTART.md) for native development setup
- Read the [Testing Guide](./TESTING_GUIDE.md) to run comprehensive tests
- Check [Architecture Documentation](./docs/architecture/README.md)
- Review production deployment guides in the docs

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres)
- [Redis Docker Hub](https://hub.docker.com/_/redis)
- [MinIO Documentation](https://min.io/docs/minio/container/index.html)
