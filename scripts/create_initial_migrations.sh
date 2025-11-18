#!/bin/bash
# Script to create initial migrations for all apps in the correct order

set -e

cd "$(dirname "$0")/.."

echo "Creating initial migrations..."

# 1. Create users migration first (other apps depend on it)
echo "Creating users migration..."
python backend/manage.py makemigrations users

# 2. Create organizations migration (scans and findings depend on it)
echo "Creating organizations migration..."
python backend/manage.py makemigrations organizations

# 3. Create authentication migration
echo "Creating authentication migration..."
python backend/manage.py makemigrations authentication

# 4. Create scans migration
echo "Creating scans migration..."
python backend/manage.py makemigrations scans

# 5. Create findings migration
echo "Creating findings migration..."
python backend/manage.py makemigrations findings

echo "All initial migrations created successfully!"
echo "Now run: pixi run migrate"
