# Quick Start Guide

Platform-specific instructions for getting started with the Static Analysis Platform.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
  - [Using pixi (Recommended)](#using-pixi-recommended)
  - [Using Docker Compose](#using-docker-compose)
  - [Native Installation](#native-installation)
- [Platform-Specific Setup](#platform-specific-setup)
  - [Arch Linux / Manjaro (Sway + Wayland)](#arch-linux--manjaro-sway--wayland)
  - [Ubuntu / Debian](#ubuntu--debian)
- [Running the Platform](#running-the-platform)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

**Minimum Requirements:**
- **RAM**: 8GB (16GB recommended)
- **Disk**: 10GB free space
- **CPU**: 4 cores (8 cores recommended)

**Required Ports**: 3000, 5432, 6333, 6379, 7233, 8000, 8233, 9000, 9001

---

## Installation Methods

### Using pixi (Recommended)

[pixi](https://pixi.sh) is a modern package manager that handles Python, Node.js, and system dependencies automatically.

#### Install pixi

```bash
# Linux/macOS
curl -fsSL https://pixi.sh/install.sh | bash

# Or with package managers
# Arch/Manjaro
yay -S pixi

# Ubuntu (via Homebrew)
brew install pixi
```

#### Setup Project

```bash
# Clone repository
git clone https://github.com/your-org/review-pro.git
cd review-pro

# Initialize pixi environment
pixi init

# Add dependencies
pixi add python=3.11 nodejs=20 postgresql=15 redis=7

# Create pixi.toml (if not exists)
cat > pixi.toml <<EOF
[project]
name = "review-pro"
version = "0.1.0"
channels = ["conda-forge"]

[dependencies]
python = "3.11.*"
nodejs = "20.*"
postgresql = "15.*"
redis = "7.*"

[tasks]
setup-backend = "cd backend && pip install -r requirements.txt"
setup-frontend = "cd frontend && npm install"
migrate = "cd backend && python manage.py migrate"
test = "pytest backend/apps"
start-services = "docker compose up -d db redis temporal qdrant minio"
dev = "docker compose up"
EOF

# Install all dependencies
pixi install

# Setup backend
pixi run setup-backend

# Setup frontend
pixi run setup-frontend

# Start services
pixi run start-services

# Run migrations
pixi run migrate

# Create sample data
cd backend && pixi run python manage.py create_sample_data
```

#### Run with pixi

```bash
# Start all services
pixi run dev

# Or individually
pixi shell  # Activate environment
cd backend && python manage.py runserver &
cd frontend && npm run dev &
```

---

### Using Docker Compose

#### Install Docker

**Arch/Manjaro:**
```bash
sudo pacman -S docker docker-compose docker-buildx
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
# Logout and login for group changes
```

**Ubuntu:**
```bash
# Official Docker installation
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
sudo systemctl enable --now docker
# Logout and login
```

#### Start Platform

```bash
cd review-pro

# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f

# Run migrations
docker compose exec web python manage.py migrate

# Create sample data
docker compose exec web python manage.py create_sample_data
```

Access:
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs/

---

### Native Installation

#### System Dependencies

**Arch/Manjaro:**
```bash
sudo pacman -S python python-pip python-virtualenv nodejs npm \
  postgresql postgresql-libs redis git
```

**Ubuntu:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv nodejs npm \
  postgresql postgresql-contrib redis-server git
```

#### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Setup PostgreSQL
sudo -u postgres psql -c "CREATE DATABASE secanalysis;"
sudo -u postgres psql -c "CREATE USER secuser WITH PASSWORD 'secpass';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE secanalysis TO secuser;"

# Configure environment
cp ../.env.example ../.env
# Edit .env with your settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Create sample data
python manage.py create_sample_data

# Run development server
python manage.py runserver
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

---

## Platform-Specific Setup

### Arch Linux / Manjaro (Sway + Wayland)

#### System Preparation

```bash
# Update system
sudo pacman -Syu

# Install base-devel if not present
sudo pacman -S base-devel

# Install yay (AUR helper) if needed
cd /tmp
git clone https://aur.archlinux.org/yay.git
cd yay
makepkg -si
```

#### Install Docker (Wayland-compatible)

```bash
# Install Docker
sudo pacman -S docker docker-compose docker-buildx

# Start Docker service
sudo systemctl enable --now docker

# Add user to docker group
sudo usermod -aG docker $USER

# For Wayland/Sway: no additional configuration needed
# Docker works the same on Wayland as on X11

# Verify installation (after logout/login)
docker --version
docker compose version
```

#### Install pixi (Arch/Manjaro)

```bash
# Via yay
yay -S pixi

# Or via cargo
cargo install --locked pixi

# Or via script
curl -fsSL https://pixi.sh/install.sh | bash
```

#### Wayland-Specific Notes

- Docker containers run headless (no GUI needed)
- Browser access works normally through Wayland
- VS Code/Editors work with Wayland natively
- No X11 forwarding required for this project

#### Sway Workspace Setup (Optional)

```bash
# Add to ~/.config/sway/config for dedicated workspace

# Workspace for Review Pro
set $ws_review "9:review"

# Assign applications
assign [title="Review Pro.*Firefox"] $ws_review
for_window [title="localhost:3000"] move to workspace $ws_review

# Keybindings
bindsym $mod+9 workspace $ws_review
```

#### Resource Management

```bash
# Check available resources
free -h
df -h

# Monitor Docker resources
docker stats

# Clean up if needed
docker system prune -a
```

---

### Ubuntu / Debian

#### System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y build-essential curl git wget
```

#### Install Docker

```bash
# Official Docker installation
curl -fsSL https://get.docker.com | sudo sh

# Add user to docker group
sudo usermod -aG docker $USER

# Start Docker
sudo systemctl enable --now docker

# Verify (after logout/login)
docker --version
```

#### Install pixi (Ubuntu)

```bash
# Via Homebrew (recommended)
# Install Homebrew first
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Add Homebrew to PATH
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.bashrc
source ~/.bashrc

# Install pixi
brew install pixi

# Or via script
curl -fsSL https://pixi.sh/install.sh | bash
```

#### PostgreSQL Setup (Ubuntu)

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Start service
sudo systemctl enable --now postgresql

# Create database
sudo -u postgres createdb secanalysis
sudo -u postgres createuser -s $USER

# Set password
sudo -u postgres psql -c "ALTER USER $USER WITH PASSWORD 'yourpassword';"
```

#### Node.js Setup (Ubuntu)

```bash
# Install Node.js 20 via NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
node --version
npm --version
```

#### Python Setup (Ubuntu)

```bash
# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip

# Set as default (optional)
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

---

## Running the Platform

### Quick Start (Docker)

```bash
# Start everything
docker compose up -d

# Wait for services to be healthy
docker compose ps

# Access platform
open http://localhost:3000  # Linux: xdg-open
```

### Development Mode

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate  # or pixi shell
python manage.py runserver

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Temporal Worker (optional)
cd backend
source venv/bin/activate
python workers/temporal_worker.py
```

### With pixi

```bash
# One command to rule them all
pixi run dev

# Or step by step
pixi run start-services    # Start dependencies
pixi shell                 # Activate environment
cd backend && python manage.py runserver &
cd frontend && npm run dev &
```

### Testing

```bash
# Full test suite
./scripts/run_tests.sh

# Backend only
cd backend
pixi run pytest  # or: pytest

# Frontend only
cd frontend
npm test

# Coverage report
python3 scripts/coverage_summary.py
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
sudo lsof -i :8000  # or :3000, :5432, etc.

# Kill process
sudo kill -9 <PID>

# Or change port in .env
# Backend: Add DJANGO_PORT=8001
# Frontend: Change vite.config.ts
```

### Docker Permission Denied (Linux)

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Apply changes
newgrp docker

# Or logout and login
```

### PostgreSQL Connection Refused

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Start if not running
sudo systemctl start postgresql

# Check connection
psql -U postgres -c "SELECT version();"
```

### Wayland/Sway Specific Issues

```bash
# If browser won't open
# Set BROWSER environment variable
export BROWSER=firefox  # or chromium, brave, etc.

# For electron apps (VS Code)
code --enable-features=UseOzonePlatform --ozone-platform=wayland
```

### Out of Memory

```bash
# Check memory usage
free -h
docker stats

# Increase swap (temporary)
sudo swapoff -a
sudo dd if=/dev/zero of=/swapfile bs=1G count=8
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Or limit Docker memory
docker compose down
# Edit docker-compose.yml: add "mem_limit: 4g" to services
docker compose up -d
```

### pixi Environment Issues

```bash
# Clean pixi cache
pixi clean

# Reinstall
rm -rf .pixi
pixi install

# Reset completely
pixi global uninstall review-pro
pixi install
```

### Frontend Build Failures

```bash
# Clear caches
cd frontend
rm -rf node_modules package-lock.json dist
npm install

# Try with legacy OpenSSL
export NODE_OPTIONS=--openssl-legacy-provider
npm run build
```

### Database Migration Errors

```bash
# Reset migrations (CAREFUL: deletes data)
docker compose exec web python manage.py flush --no-input
docker compose exec web python manage.py migrate

# Or manually
docker compose exec db psql -U postgres -c "DROP DATABASE secanalysis;"
docker compose exec db psql -U postgres -c "CREATE DATABASE secanalysis;"
docker compose exec web python manage.py migrate
```

---

## Next Steps

After successful installation:

1. **Access the Platform**: http://localhost:3000
2. **Login**: admin@example.com / admin123
3. **Explore UI**: Dashboard, Scans, Findings
4. **Read Documentation**: Check `SETUP.md` for detailed info
5. **Run Tests**: `./scripts/run_tests.sh`
6. **Configure LLM APIs**: Add keys to `.env`

## Resources

- **Main Documentation**: [SETUP.md](SETUP.md)
- **Testing Guide**: [TESTING.md](TESTING.md)
- **API Documentation**: http://localhost:8000/api/docs/
- **Temporal UI**: http://localhost:8233

## Support

- GitHub Issues: https://github.com/your-org/review-pro/issues
- Documentation: https://docs.review-pro.io
- Community: Discord/Slack link

---

## Platform Comparison

| Feature | Docker | pixi | Native |
|---------|--------|------|--------|
| Setup Time | Fast | Medium | Slow |
| Isolation | Excellent | Good | Poor |
| Resource Usage | High | Medium | Low |
| Hot Reload | Yes | Yes | Yes |
| Best For | Production | Development | CI/CD |

**Recommendation:**
- **Development**: pixi or Docker
- **Production**: Docker + Kubernetes
- **CI/CD**: Native or Docker
- **Quick Demo**: Docker

Enjoy using the Static Analysis Platform! 🚀
