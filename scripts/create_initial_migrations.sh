#!/bin/bash
# Script to create initial migrations for all apps in the correct order
# NOTE: Prefer using 'pixi run setup-migrations' instead of running this directly

set -e

cd "$(dirname "$0")/.."

echo "Creating initial migrations..."

# Use pixi run to ensure correct environment
# 1. Create users migration first (other apps depend on it)
echo "Creating users migration..."
pixi run makemigrations-users

# 2. Create organizations migration (scans and findings depend on it)
echo "Creating organizations migration..."
pixi run makemigrations-organizations

# 3. Create authentication migration
echo "Creating authentication migration..."
pixi run makemigrations-authentication

# 4. Create scans migration
echo "Creating scans migration..."
pixi run makemigrations-scans

# 5. Create findings migration
echo "Creating findings migration..."
pixi run makemigrations-findings

echo "All initial migrations created successfully!"
echo "Now run: pixi run migrate"
