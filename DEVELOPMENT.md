# Development Guide

This guide covers local development setup for Review Pro using modern tools: **Pixi** for Python package management and **Docker Compose** for infrastructure.

## Table of Contents

- [System Requirements](#system-requirements)
- [Installing Pixi](#installing-pixi)
  - [Ubuntu/Debian](#ubuntudebian)
  - [Arch Linux](#arch-linux)
  - [Universal (curl)](#universal-curl)
- [Quick Start with Pixi](#quick-start-with-pixi)
- [Development Workflow](#development-workflow)
- [Docker Compose Setup](#docker-compose-setup)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

- **Python**: 3.11+ (managed by Pixi)
- **Docker**: 24.0+ with Docker Compose V2
- **PostgreSQL**: 18+ (via Docker or system package)
- **Redis**: 7+ (via Docker or system package)
- **Git**: 2.30+

---

## Installing Pixi

[Pixi](https://prefix.dev/docs/pixi/overview) is a modern, fast package manager that replaces virtualenv/pip/conda. It provides:
- ✅ Fast dependency resolution (uses rattler from conda)
- ✅ Reproducible environments across Ubuntu and Arch
- ✅ Built-in task runner (no need for Makefiles)
- ✅ Cross-platform binary cache

### Ubuntu/Debian

```bash
# Update package list
sudo apt update

# Install required dependencies
sudo apt install -y curl git build-essential libpq-dev

# Install Pixi
curl -fsSL https://pixi.sh/install.sh | bash

# Add Pixi to PATH (add to ~/.bashrc for persistence)
export PATH="$HOME/.pixi/bin:$PATH"

# Verify installation
pixi --version
```

### Arch Linux

```bash
# Install from AUR using yay (or your preferred AUR helper)
yay -S pixi

# Or install from official repositories (if available)
sudo pacman -S pixi

# Alternatively, use the universal installer
curl -fsSL https://pixi.sh/install.sh | bash

# Verify installation
pixi --version
```

**Arch-specific dependencies:**
```bash
# Install PostgreSQL development headers (needed for psycopg2)
sudo pacman -S postgresql-libs base-devel
```

### Universal (curl)

Works on any Linux distribution:

```bash
# Install Pixi
curl -fsSL https://pixi.sh/install.sh | bash

# Reload shell configuration
source ~/.bashrc  # or ~/.zshrc

# Verify
pixi --version
```

---

## Quick Start with Pixi

Once Pixi is installed, getting started is simple:

```bash
# 1. Clone the repository
git clone <repository-url>
cd review-pro

# 2. Install all dependencies (Python + system packages)
pixi install

# 3. Set up environment variables
pixi run setup-env
# Edit .env with your configuration (GitHub keys, etc.)

# 4. Start infrastructure (PostgreSQL, Redis, MinIO)
pixi run docker-up

# 5. Run database migrations
pixi run migrate

# 6. Create a superuser
pixi run createsuperuser

# 7. Start the development server
pixi run runserver
```

That's it! The API is now running at **http://localhost:8000**

---

## Development Workflow

### Activate Pixi Environment

Pixi environments are automatically activated when you run tasks, but you can also activate manually:

```bash
# Activate the default environment
pixi shell

# Now you can run Django commands directly
python backend/manage.py shell

# Exit the environment
exit
```

### Available Pixi Tasks

View all available tasks:
```bash
pixi task list
```

**Common tasks:**

| Task | Command | Description |
|------|---------|-------------|
| `pixi run runserver` | `python backend/manage.py runserver` | Start Django dev server |
| `pixi run migrate` | `python backend/manage.py migrate` | Apply database migrations |
| `pixi run makemigrations` | `python backend/manage.py makemigrations` | Create new migrations |
| `pixi run shell` | `python backend/manage.py shell` | Django shell |
| `pixi run test` | `pytest backend/` | Run all tests |
| `pixi run test-cov` | `pytest --cov` | Run tests with coverage |
| `pixi run format` | `black && isort` | Format code |
| `pixi run lint` | `flake8 && mypy` | Lint code |
| `pixi run check` | Format + Lint + Test | Full check before commit |
| `pixi run temporal-worker` | Start Temporal worker | Start Temporal worker |
| `pixi run docker-up` | `docker compose up -d` | Start infrastructure |
| `pixi run docker-down` | `docker compose down` | Stop infrastructure |

### Development Environment (Extra Tools)

For enhanced development experience:

```bash
# Install dev environment (includes IPython, Django Debug Toolbar, etc.)
pixi install --environment dev

# Activate dev environment
pixi shell --environment dev

# Use Django shell_plus (enhanced shell)
pixi run --environment dev shell-plus

# Run Jupyter notebook with Django
pixi run --environment dev notebook
```

---

## Docker Compose Setup

For full stack development with all services:

### Start All Services

```bash
# Start PostgreSQL, Redis, MinIO, web server, Celery worker, and beat
docker compose up -d

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f web
```

### Service URLs

- **API**: http://localhost:8000
- **Admin**: http://localhost:8000/admin
- **API Docs (Swagger)**: http://localhost:8000/api/docs/
- **API Docs (ReDoc)**: http://localhost:8000/api/redoc/
- **MinIO Console**: http://localhost:9001 (user: `minioadmin`, pass: `minioadmin`)
- **PostgreSQL**: localhost:5432 (user: `postgres`, pass: `postgres`)
- **Redis**: localhost:6379

### Stop Services

```bash
# Stop all services
docker compose down

# Stop and remove volumes (⚠️ deletes all data)
docker compose down -v
```

---

## Common Tasks

### Database Management

```bash
# Create new migrations after model changes
pixi run makemigrations

# Apply migrations
pixi run migrate

# View migration status
pixi run showmigrations

# Access PostgreSQL directly (via Docker)
docker compose exec db psql -U postgres -d secanalysis

# Or via Pixi (if using system PostgreSQL)
psql postgresql://postgres:postgres@localhost:5432/secanalysis
```

### Running Tests

```bash
# Run all tests
pixi run test

# Run with coverage report
pixi run test-cov
# Open htmlcov/index.html in browser to view coverage

# Run specific test file
pixi run test backend/apps/organizations/tests/test_models.py

# Run tests matching a pattern
pixi run test -k "test_organization"

# Run last failed tests
pixi run test-failed

# Run tests in parallel (faster)
pixi run test -n auto  # requires pytest-xdist
```

### Code Quality

```bash
# Format code (Black + isort)
pixi run format

# Lint code (flake8 + mypy)
pixi run lint

# Run all checks before committing
pixi run check

# Check what Black would change (dry-run)
pixi run format-black --check --diff
```

### Temporal Workers

```bash
# Start Temporal worker
pixi run temporal-worker

# Monitor Temporal workflows via Temporal UI
# Access at http://localhost:8233
```

### Static Files

```bash
# Collect static files for production
pixi run collectstatic

# Static files will be in backend/staticfiles/
```

---

## Project Structure with Pixi

```
review-pro/
├── pyproject.toml           # Pixi configuration + Python metadata
├── pixi.lock                # Lock file (auto-generated, commit to git)
├── .pixi/                   # Pixi environment (gitignored)
├── backend/                 # Django application
│   ├── apps/                # Django apps
│   ├── config/              # Django settings
│   └── manage.py
├── docker-compose.yml       # Infrastructure services
├── .env                     # Environment variables (gitignored)
├── .env.example             # Environment template
└── README.md                # User documentation
```

---

## Troubleshooting

### Pixi Issues

**Problem**: `pixi: command not found`
```bash
# Ensure Pixi is in PATH
export PATH="$HOME/.pixi/bin:$PATH"

# Add to ~/.bashrc or ~/.zshrc for persistence
echo 'export PATH="$HOME/.pixi/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Problem**: Slow dependency resolution
```bash
# Clear Pixi cache
rm -rf ~/.pixi/cache

# Reinstall
pixi install
```

**Problem**: `psycopg2` compilation errors on Ubuntu
```bash
# Install PostgreSQL development headers
sudo apt install -y libpq-dev python3-dev build-essential

# Reinstall
pixi install --force-reinstall
```

**Problem**: `psycopg2` compilation errors on Arch
```bash
# Install PostgreSQL libraries
sudo pacman -S postgresql-libs base-devel

# Reinstall
pixi install --force-reinstall
```

### Docker Issues

**Problem**: `docker compose` not found
```bash
# Check Docker version (need 24.0+)
docker --version

# Install Docker Compose V2 plugin (Ubuntu)
sudo apt update
sudo apt install docker-compose-plugin

# Verify
docker compose version
```

**Problem**: Permission denied on `/var/run/docker.sock`
```bash
# Add your user to docker group
sudo usermod -aG docker $USER

# Log out and log back in, or run:
newgrp docker
```

**Problem**: Port already in use (8000, 5432, 6379)
```bash
# Find process using port
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>

# Or change port in docker-compose.yml
```

### Database Issues

**Problem**: Database connection refused
```bash
# Check if PostgreSQL is running
docker compose ps db

# Check logs
docker compose logs db

# Restart database
docker compose restart db
```

**Problem**: Migrations out of sync
```bash
# Reset database (⚠️ deletes all data)
docker compose down -v
docker compose up -d db
pixi run migrate

# Or use fake migrations (advanced)
pixi run migrate --fake
```

### Django Issues

**Problem**: `SECRET_KEY` errors
```bash
# Ensure .env file exists
cp .env.example .env

# Generate a new secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Problem**: Static files not loading
```bash
# Collect static files
pixi run collectstatic

# Check STATIC_ROOT in settings.py
# Ensure DEBUG=True for development
```

---

## Platform-Specific Notes

### Ubuntu/Debian

- Use `apt` for system packages
- PostgreSQL service may auto-start: `sudo systemctl stop postgresql`
- Docker typically requires `sudo` unless user is in `docker` group

### Arch Linux

- Use `pacman` or `yay` for system packages
- PostgreSQL uses different directory structure: `/var/lib/postgres/data`
- Docker works out-of-box for users in `docker` group

### Common to Both

- Pixi handles Python and most dependencies identically
- Docker Compose works the same way
- Environment variables in `.env` are platform-agnostic

---

## Next Steps

1. **Configure GitHub OAuth**: See [README.md](./README.md#github-oauth-setup)
2. **Read Architecture Docs**: See [docs/architecture/](./docs/architecture/)
3. **Run Tests**: `pixi run test-cov` to ensure everything works
4. **Start Coding**: Check open issues or ADRs for what to build next

---

## Additional Resources

- [Pixi Documentation](https://prefix.dev/docs/pixi/overview)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)

For questions or issues, open a GitHub issue or consult the team.
