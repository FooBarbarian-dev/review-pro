# Security Analysis Platform

A multi-tenant security analysis platform with SARIF support, built on Django with comprehensive architecture decision records (ADRs).

## Features

- **Multi-Tenancy**: Organization-based isolation with PostgreSQL Row-Level Security (RLS)
- **Security Scanning**: Automated security scans with Docker-isolated workers
- **Finding Deduplication**: Intelligent fingerprint-based deduplication
- **SARIF Support**: Full SARIF file support with hybrid storage (DB + S3)
- **Real-Time Updates**: Server-Sent Events (SSE) for live scan updates
- **GitHub Integration**: OAuth authentication and GitHub App integration
- **JWT Authentication**: Stateless authentication with refresh tokens
- **API Keys**: Programmatic access via API keys
- **Rate Limiting**: Redis-based rate limiting and quota management
- **Comprehensive API**: RESTful API with OpenAPI documentation

## Architecture

This platform is built following comprehensive Architecture Decision Records (ADRs). See [docs/architecture/](./docs/architecture/) for detailed documentation.

### Core Technologies

- **Backend**: Django 5.0, Django REST Framework
- **Database**: PostgreSQL 15+ with JSONB and Row-Level Security
- **Cache/Pub-Sub**: Redis 7
- **Object Storage**: AWS S3 / MinIO
- **Task Queue**: Celery
- **Container Runtime**: Docker
- **Authentication**: JWT (Simple JWT), GitHub OAuth

## Quick Start

### Prerequisites

**Option 1: Modern Development (Recommended)**
- [Pixi](https://prefix.dev/docs/pixi/overview) package manager
- Docker 24.0+ with Docker Compose V2
- Git 2.30+

**Option 2: Traditional Development**
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker and Docker Compose

> 💡 **New to Pixi?** See our comprehensive [DEVELOPMENT.md](./DEVELOPMENT.md) guide for Ubuntu/Arch setup instructions.

### Quick Start with Pixi (Recommended)

```bash
# Install Pixi (Ubuntu/Debian)
curl -fsSL https://pixi.sh/install.sh | bash
export PATH="$HOME/.pixi/bin:$PATH"

# Install Pixi (Arch Linux)
yay -S pixi

# Clone and setup
git clone <repository-url>
cd review-pro
pixi install

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start infrastructure and run migrations
pixi run docker-up
pixi run migrate
pixi run createsuperuser

# Start development server
pixi run runserver
```

**Available Pixi commands:**
- `pixi run runserver` - Start Django dev server
- `pixi run test` - Run tests
- `pixi run format` - Format code (Black + isort)
- `pixi run lint` - Lint code (flake8 + mypy)
- `pixi run celery-worker` - Start Celery worker
- `pixi task list` - See all available tasks

### Development Setup (Docker Compose)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd -jl-dx
   ```

2. **Copy environment configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services with Docker Compose**
   ```bash
   docker compose up -d
   ```

4. **Run migrations**
   ```bash
   docker compose exec web python manage.py migrate
   ```

5. **Create a superuser**
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

6. **Access the application**
   - API: http://localhost:8000
   - Admin: http://localhost:8000/admin
   - API Docs: http://localhost:8000/api/docs/
   - MinIO Console: http://localhost:9001

### Local Development (Manual Setup)

> 💡 **Prefer Pixi?** Use the Quick Start section above or see [DEVELOPMENT.md](./DEVELOPMENT.md) for the modern approach.

**Traditional setup with pip:**

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Set up local database**
   ```bash
   createdb secanalysis
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

8. **Run Celery worker (in another terminal)**
   ```bash
   celery -A config worker -l info
   ```

## Project Structure

```
-jl-dx/
├── backend/                    # Django backend
│   ├── apps/                   # Django applications
│   │   ├── authentication/     # JWT & GitHub OAuth
│   │   ├── organizations/      # Multi-tenancy & repos
│   │   ├── scans/              # Security scans
│   │   ├── findings/           # Security findings
│   │   └── users/              # User management
│   ├── config/                 # Django settings
│   │   ├── settings.py         # Main settings
│   │   ├── urls.py             # URL configuration
│   │   ├── celery.py           # Celery configuration
│   │   └── wsgi.py             # WSGI application
│   ├── manage.py               # Django management
│   └── requirements.txt        # Python dependencies
├── docs/                       # Documentation
│   └── architecture/           # ADRs
├── docker-compose.yml          # Docker Compose config
├── .env.example                # Environment template
└── README.md                   # This file
```

## API Documentation

The API is documented using OpenAPI/Swagger. Access the interactive documentation at:

- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/

### Main API Endpoints

- `POST /api/v1/auth/login/` - JWT login
- `POST /api/v1/auth/refresh/` - Refresh JWT token
- `GET /api/v1/auth/me/` - Current user info
- `GET /api/v1/organizations/` - List organizations
- `GET /api/v1/repositories/` - List repositories
- `GET /api/v1/scans/` - List scans
- `POST /api/v1/scans/` - Create new scan
- `GET /api/v1/findings/` - List findings
- `GET /api/v1/users/me/` - Current user profile

## Configuration

### Environment Variables

See `.env.example` for all available configuration options. Key variables:

- `DEBUG`: Enable debug mode (default: False)
- `SECRET_KEY`: Django secret key (change in production!)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `USE_S3`: Enable S3 storage (default: False)
- `GITHUB_CLIENT_ID`: GitHub OAuth client ID
- `GITHUB_CLIENT_SECRET`: GitHub OAuth client secret

### GitHub OAuth Setup

1. Create a GitHub OAuth App at https://github.com/settings/developers
2. Set the callback URL to `http://localhost:8000/auth/complete/github/`
3. Copy the Client ID and Client Secret to your `.env` file

### GitHub App Setup (for scan workers)

1. Create a GitHub App at https://github.com/settings/apps
2. Set required permissions (repository read access)
3. Install the app on your organization
4. Copy App ID, Private Key, and Installation ID to your `.env` file

## Testing

**With Pixi:**
```bash
# Run all tests
pixi run test

# With coverage report (HTML + terminal)
pixi run test-cov

# Verbose output
pixi run test-verbose

# Run last failed tests only
pixi run test-failed

# Run specific test file
pytest backend/apps/organizations/tests/test_models.py
```

**Manual:**
```bash
# All tests
pytest backend/

# With coverage
pytest backend/ --cov=apps --cov-report=html

# Specific app
pytest backend/apps/organizations/tests/
```

## Development

> 📖 **Comprehensive Guide**: See [DEVELOPMENT.md](./DEVELOPMENT.md) for detailed setup instructions for Ubuntu and Arch Linux.

### Code Quality

**With Pixi (recommended):**
```bash
# Format code (Black + isort)
pixi run format

# Lint code (flake8 + mypy)
pixi run lint

# Run all checks (format + lint + test)
pixi run check
```

**Manual:**
```bash
# Format code
black .

# Sort imports
isort .

# Lint
flake8

# Type checking
mypy .
```

### Database Migrations

**With Pixi:**
```bash
# Create migrations
pixi run makemigrations

# Apply migrations
pixi run migrate

# Show migration status
pixi run showmigrations
```

**Manual:**
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations
```

### Celery Tasks

**With Pixi:**
```bash
# Start worker
pixi run celery-worker

# Start beat (scheduled tasks)
pixi run celery-beat

# Both worker and beat
pixi run celery-all
```

**Manual:**
```bash
# Start worker
celery -A config worker -l info --workdir=backend

# Start beat (scheduled tasks)
celery -A config beat -l info --workdir=backend

# Both worker and beat
celery -A config worker --beat -l info --workdir=backend
```

## Architecture Decision Records

This project follows documented architecture decisions. See [docs/architecture/README.md](./docs/architecture/README.md) for:

- ADR-001: Multi-Tenancy Model
- ADR-002: Finding Deduplication
- ADR-003: Real-Time Communication
- ADR-004: Worker Security Model
- ADR-005: SARIF Storage Strategy
- ADR-006: Data Model Normalization
- ADR-007: Authentication & Authorization
- ADR-008: Rate Limiting & Quotas

## Contributing

1. Review the ADRs to understand architectural decisions
2. Follow the code style (Black, isort, flake8)
3. Write tests for new features
4. Update documentation as needed
5. Create a pull request

## License

[Add your license here]

## Support

For issues and questions, please open an issue on GitHub.
