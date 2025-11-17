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

Choose your preferred development environment:

### Option 1: Native Development (Manjaro + Sway - Recommended)

For native development with pixi package manager on Manjaro Linux with Sway:

**See [QUICKSTART.md](./QUICKSTART.md) for detailed instructions.**

Quick setup:
```bash
# Install pixi, PostgreSQL, and Redis
curl -fsSL https://pixi.sh/install.sh | bash
sudo pacman -S postgresql redis

# Clone and setup
git clone <repository-url>
cd review-pro
pixi install

# Setup database and run
pixi run migrate
pixi run createsuperuser
pixi run runserver
```

### Option 2: Docker Development

For containerized development with Docker Compose:

**See [DOCKER_GUIDE.md](./DOCKER_GUIDE.md) for detailed instructions.**

Quick setup:
```bash
# Clone and setup
git clone <repository-url>
cd review-pro
cp .env.example .env

# Start services
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

Access the application:
- API: http://localhost:8000
- Admin: http://localhost:8000/admin
- API Docs: http://localhost:8000/api/docs/
- MinIO Console: http://localhost:9001

## Project Structure

```
review-pro/
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

**See [TESTING_GUIDE.md](./TESTING_GUIDE.md) for comprehensive testing instructions.**

Quick test commands:

```bash
# Native environment
pixi run test          # All tests
pixi run test-unit     # Unit tests only
pixi run test-cov      # With coverage

# Docker environment
docker-compose exec web pytest
docker-compose exec web pytest -m unit
docker-compose exec web pytest --cov=apps
```

## Development

### Code Quality

```bash
# Native environment
pixi run format      # Format code (black + isort)
pixi run lint        # Lint code (flake8)
pixi run typecheck   # Type checking (mypy)
pixi run check       # Run all checks + tests

# Docker environment
docker-compose exec web black .
docker-compose exec web isort .
docker-compose exec web flake8
docker-compose exec web mypy .
```

### Database Migrations

```bash
# Native environment
pixi run makemigrations
pixi run migrate

# Docker environment
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
```

### Celery Tasks

```bash
# Native environment
pixi run celery-worker    # Start worker
pixi run celery-beat      # Start beat scheduler
pixi run celery-all       # Both worker and beat

# Docker environment
docker-compose up celery_worker
docker-compose up celery_beat
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
