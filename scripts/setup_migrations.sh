#!/bin/bash
# Script to create and apply Django migrations

set -e

echo "==> Setting up Django migrations..."

# Navigate to backend directory
cd "$(dirname "$0")/../backend"

# Create migrations directories for all apps
echo "==> Creating migrations directories..."
for app in apps/users apps/organizations apps/scans apps/findings apps/authentication; do
    if [ -d "$app" ]; then
        mkdir -p "$app/migrations"
        touch "$app/migrations/__init__.py"
        echo "Created migrations directory for $app"
    fi
done

echo ""
echo "==> Generating migrations..."
echo "Run: docker compose exec web python manage.py makemigrations"
echo ""
echo "==> Applying migrations..."
echo "Run: docker compose exec web python manage.py migrate"
echo ""
echo "==> Done! Migrations are ready to be created and applied."
