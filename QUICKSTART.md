# Quick Start - Manjaro + Sway Development Environment

This guide will get you up and running with `review-pro` on a native Manjaro Linux development environment using Sway window manager and pixi for Python environment management.

## Prerequisites

- Manjaro Linux with Sway
- Git
- PostgreSQL 15+
- Redis 7+
- Pixi package manager

## 1. Install System Dependencies

### Install Pixi

```bash
# Install pixi using the official installer
curl -fsSL https://pixi.sh/install.sh | bash

# Restart your shell or source your profile
source ~/.bashrc  # or ~/.zshrc
```

### Install PostgreSQL and Redis

```bash
# Install PostgreSQL
sudo pacman -S postgresql

# Initialize PostgreSQL cluster
sudo -iu postgres initdb -D /var/lib/postgres/data

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Install Redis
sudo pacman -S redis

# Start and enable Redis
sudo systemctl start redis
sudo systemctl enable redis
```

### Verify Services

```bash
# Check PostgreSQL
sudo systemctl status postgresql

# Check Redis
sudo systemctl status redis
redis-cli ping  # Should return PONG
```

## 2. Clone and Setup Project

```bash
# Clone the repository
git clone <repository-url>
cd review-pro

# Install Python dependencies using pixi
pixi install

# This creates a .pixi directory with your environment
# All subsequent commands should be run with 'pixi run' or 'pixi shell'
```

## 3. Database Setup

```bash
# Create PostgreSQL user and database
sudo -u postgres createuser -s $USER
createdb review_pro

# Alternatively, use psql:
sudo -u postgres psql
# In psql:
# CREATE USER your_username WITH SUPERUSER PASSWORD 'your_password';
# CREATE DATABASE review_pro OWNER your_username;
# \q
```

## 4. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
vim .env  # or nano, or your preferred editor
```

**Critical environment variables to set:**

```bash
# Django
SECRET_KEY=your-secret-key-here-generate-new-one
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (adjust if needed)
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/review_pro

# Redis
REDIS_URL=redis://localhost:6379/0

# Optional: GitHub OAuth (for authentication)
# GITHUB_CLIENT_ID=your-github-oauth-client-id
# GITHUB_CLIENT_SECRET=your-github-oauth-client-secret

# Optional: S3/MinIO (for SARIF storage)
# USE_S3=False
# AWS_ACCESS_KEY_ID=minioadmin
# AWS_SECRET_ACCESS_KEY=minioadmin
# AWS_STORAGE_BUCKET_NAME=review-pro
```

**Generate a new SECRET_KEY:**

```bash
# Using pixi shell
pixi shell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
exit
```

## 5. Run Migrations

```bash
# Run database migrations
pixi run migrate

# Create a superuser
pixi run createsuperuser
# Enter email: your-email@example.com
# Enter password: (choose a secure password)
```

## 6. Start Development Server

### Option A: Run all services separately (recommended)

Open multiple terminal windows/panes in Sway:

**Terminal 1 - Django development server:**
```bash
cd review-pro
pixi run runserver
```

**Terminal 2 - Celery worker:**
```bash
cd review-pro
pixi run celery-worker
```

**Terminal 3 - Celery beat (optional, for scheduled tasks):**
```bash
cd review-pro
pixi run celery-beat
```

### Option B: Run Celery worker with beat in one process

**Terminal 1 - Django server:**
```bash
pixi run runserver
```

**Terminal 2 - Celery with beat:**
```bash
pixi run celery-all
```

## 7. Verify Installation

### Test API Access

```bash
# Check API health
curl http://localhost:8000/api/schema/ | jq . | head

# Access admin interface
xdg-open http://localhost:8000/admin
```

Login with the superuser credentials you created.

### Run Tests

```bash
# Run all tests
pixi run test

# Run only unit tests
pixi run test-unit

# Run with coverage
pixi run test-cov
```

## 8. Development Workflow

### Available Pixi Tasks

```bash
# Start development server
pixi run runserver

# Django shell
pixi run shell

# Database operations
pixi run makemigrations
pixi run migrate

# Testing
pixi run test              # All tests
pixi run test-unit         # Unit tests only
pixi run test-cov          # With coverage report
pixi run test-verbose      # Verbose output

# Code quality
pixi run format           # Format code (black + isort)
pixi run lint             # Lint code (flake8)
pixi run typecheck        # Type checking (mypy)
pixi run check            # Run format, lint, and test

# Celery
pixi run celery-worker    # Start Celery worker
pixi run celery-beat      # Start Celery beat scheduler
pixi run celery-all       # Start both worker and beat
```

### Using Pixi Shell

For interactive development, you can activate the pixi environment:

```bash
# Enter pixi shell
pixi shell

# Now you can run commands directly
cd backend
python manage.py runserver
pytest
black .

# Exit shell
exit
```

## 9. Sway-Specific Tips

### Window Management

Create a workspace layout for development:

```bash
# Example Sway config snippet (~/.config/sway/config)
# Workspace 2 for dev
bindsym $mod+2 workspace 2
assign [class="Alacritty" title="review-pro.*"] workspace 2
```

### Terminal Layout for Development

```bash
# In Sway, open terminals and arrange them:
# 1. Open terminal: $mod+Enter
# 2. Split horizontally: $mod+b
# 3. Open another terminal: $mod+Enter
# 4. Split vertically: $mod+v
# 5. Open another terminal: $mod+Enter

# Layout:
# ┌──────────────┬──────────────┐
# │              │   Terminal   │
# │  runserver   │   celery     │
# │              ├──────────────┤
# │              │   Terminal   │
# │              │   shell/logs │
# └──────────────┴──────────────┘
```

## 10. Optional: MinIO for S3 Storage (Native)

If you want to test S3 storage locally without Docker:

```bash
# Install MinIO server
yay -S minio  # or download from minio.io

# Create data directory
mkdir -p ~/minio-data

# Start MinIO server
minio server ~/minio-data --console-address ":9001"

# Access MinIO Console at http://localhost:9001
# Default credentials: minioadmin / minioadmin

# Create bucket using mc (MinIO Client)
yay -S minio-client
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/review-pro
```

Update `.env`:
```bash
USE_S3=True
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_STORAGE_BUCKET_NAME=review-pro
AWS_S3_ENDPOINT_URL=http://localhost:9000
```

## 11. Troubleshooting

### PostgreSQL Connection Issues

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U $USER -d review_pro -c "SELECT version();"

# Check PostgreSQL logs
sudo journalctl -u postgresql -f
```

### Redis Connection Issues

```bash
# Check Redis is running
sudo systemctl status redis

# Test connection
redis-cli ping

# Check Redis logs
sudo journalctl -u redis -f
```

### Pixi Environment Issues

```bash
# Recreate pixi environment
rm -rf .pixi
pixi install

# Update pixi
pixi self-update
```

### Database Migration Issues

```bash
# Check migration status
pixi run shell
# In shell:
from django.db import connection
print(connection.ensure_connection())

# Reset migrations (CAUTION: This drops data!)
pixi shell
cd backend
python manage.py migrate --fake users zero
python manage.py migrate users
# Repeat for other apps as needed
```

## Next Steps

- Read the [Testing Guide](./TESTING_GUIDE.md) to run comprehensive tests
- Read the [Docker Guide](./DOCKER_GUIDE.md) for Docker-based development
- Check [Architecture Documentation](./docs/architecture/README.md) to understand the system design
- Review [API Documentation](http://localhost:8000/api/docs/) after starting the server

## Development Tips

1. **Use pixi shell** for active development sessions to avoid typing `pixi run` repeatedly
2. **Keep services running** in separate terminal panes for easier monitoring
3. **Watch logs** using `journalctl -f` for PostgreSQL and Redis issues
4. **Run tests frequently** with `pixi run test` before committing
5. **Use the admin interface** at http://localhost:8000/admin for quick data inspection

## Additional Resources

- [Pixi Documentation](https://pixi.sh/latest/)
- [Django Documentation](https://docs.djangoproject.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Sway WM](https://swaywm.org/)
