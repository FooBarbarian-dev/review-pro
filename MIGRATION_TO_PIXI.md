# Migration Guide: Traditional Setup → Pixi

This guide helps you migrate from the traditional `venv` + `pip` setup to modern Pixi-based development.

## Why Migrate to Pixi?

✅ **Faster dependency resolution** - Uses Rattler (Rust-based solver from conda)
✅ **Reproducible environments** - Lock file ensures exact same versions across team
✅ **Cross-platform** - Works identically on Ubuntu, Arch, macOS, Windows
✅ **Built-in task runner** - No need for Makefiles or shell scripts
✅ **Better dependency management** - Handles both Python and system packages
✅ **Automatic environment activation** - No need to remember `source venv/bin/activate`

## Migration Steps

### 1. Install Pixi

**Ubuntu/Debian:**
```bash
curl -fsSL https://pixi.sh/install.sh | bash
export PATH="$HOME/.pixi/bin:$PATH"
```

**Arch Linux:**
```bash
yay -S pixi
# or
sudo pacman -S pixi  # if available in official repos
```

### 2. Remove Old Virtual Environment

```bash
# Deactivate if currently activated
deactivate

# Remove old virtual environment
rm -rf venv/
rm -rf .venv/
```

### 3. Install Dependencies with Pixi

```bash
# Install all dependencies (Python + system packages)
pixi install

# This creates .pixi/ directory with the environment
```

### 4. Update Your Workflow

**Before (Traditional):**
```bash
# Activate environment
source venv/bin/activate

# Run Django commands
python backend/manage.py migrate
python backend/manage.py runserver

# Run tests
pytest backend/

# Format code
black backend/
isort backend/

# Deactivate
deactivate
```

**After (Pixi):**
```bash
# No activation needed!

# Run Django commands
pixi run migrate
pixi run runserver

# Run tests
pixi run test

# Format code
pixi run format

# Or use pixi shell for interactive work
pixi shell
python backend/manage.py shell
exit
```

### 5. Update CI/CD Pipelines

**Before (GitHub Actions):**
```yaml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.11'

- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r backend/requirements.txt

- name: Run tests
  run: pytest backend/
```

**After (GitHub Actions with Pixi):**
```yaml
- name: Setup Pixi
  uses: prefix-dev/setup-pixi@v0.4.0
  with:
    pixi-version: latest

- name: Install dependencies
  run: pixi install

- name: Run tests
  run: pixi run test
```

### 6. Update .gitignore

Already updated! The `.pixi/` directory is ignored, but `pixi.lock` is committed.

### 7. Team Communication

Share this with your team:

```
🎉 We've migrated to Pixi for better dependency management!

Quick setup:
1. Install Pixi: curl -fsSL https://pixi.sh/install.sh | bash
2. Run: pixi install
3. Use: pixi run <task>

See DEVELOPMENT.md for details.
```

## Common Tasks Reference

| Task | Before | After |
|------|--------|-------|
| Setup | `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt` | `pixi install` |
| Activate | `source venv/bin/activate` | Not needed (or `pixi shell`) |
| Run server | `python backend/manage.py runserver` | `pixi run runserver` |
| Migrations | `python backend/manage.py migrate` | `pixi run migrate` |
| Tests | `pytest backend/` | `pixi run test` |
| Format | `black . && isort .` | `pixi run format` |
| Lint | `flake8 && mypy` | `pixi run lint` |
| Add dependency | Edit requirements.txt, `pip install -r requirements.txt` | Edit pyproject.toml, `pixi install` |
| Clean | `rm -rf venv/` | `rm -rf .pixi/` (rare) |

## Keeping requirements.txt Updated

For compatibility with tools that still use `requirements.txt`, you can export dependencies:

```bash
# Export current Pixi environment to requirements.txt
pixi list --explicit > backend/requirements.txt
```

Or manually keep `backend/requirements.txt` in sync with `pyproject.toml`.

## Troubleshooting

### "pixi: command not found"

```bash
# Add to PATH
export PATH="$HOME/.pixi/bin:$PATH"

# Make permanent
echo 'export PATH="$HOME/.pixi/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Slow initial install

First install downloads all dependencies and builds binary cache. Subsequent installs are much faster.

```bash
# Clean cache and retry
rm -rf ~/.pixi/cache
pixi install
```

### Build errors on Ubuntu

```bash
# Install system build tools
sudo apt update
sudo apt install -y build-essential libpq-dev python3-dev
pixi install --force-reinstall
```

### Build errors on Arch

```bash
# Install system build tools
sudo pacman -S base-devel postgresql-libs
pixi install --force-reinstall
```

### "Package not found" errors

Ensure package name is correct in `pyproject.toml`. Check PyPI vs conda-forge:

```toml
# PyPI packages go in [tool.pixi.pypi-dependencies]
[tool.pixi.pypi-dependencies]
Django = "==5.0.1"

# Conda packages go in [tool.pixi.dependencies]
[tool.pixi.dependencies]
python = "3.11.*"
postgresql = ">=15"
```

## Benefits You'll Notice

1. **Faster installs** - Binary cache means dependencies install in seconds, not minutes
2. **No "works on my machine"** - Lock file ensures everyone has identical versions
3. **Easier onboarding** - New developers: `pixi install` and they're ready
4. **Better task management** - `pixi task list` shows all available commands
5. **Simpler CI/CD** - One command: `pixi install`, works everywhere

## Reverting (If Needed)

If you need to go back to traditional setup:

```bash
# Remove Pixi environment
rm -rf .pixi/

# Recreate virtual environment
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

But we don't think you'll want to! 😊

## Questions?

- Check [DEVELOPMENT.md](./DEVELOPMENT.md) for detailed Pixi usage
- Read [Pixi documentation](https://prefix.dev/docs/pixi/overview)
- Ask in team chat or open an issue

Happy coding with Pixi! 🚀
