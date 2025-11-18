#!/bin/bash
# Setup migrations, run them, and test - with clear error reporting

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Starting setup and test workflow..."
echo "========================================="

# Step 0: Upgrade dependencies (optional, keeps them current)
echo ""
echo "Step 0/4: Upgrading dependencies..."
echo "-----------------------------------------"
if pixi upgrade; then
    echo -e "${GREEN}✓ Step 0 PASSED: Dependencies upgraded successfully${NC}"
else
    echo -e "${YELLOW}⚠ Step 0 WARNING: Dependency upgrade had issues (continuing anyway)${NC}"
fi

# Step 1: Create initial migrations
echo ""
echo "Step 1/4: Creating initial migrations..."
echo "-----------------------------------------"
if pixi run setup-migrations; then
    echo -e "${GREEN}✓ Step 1 PASSED: Migrations created successfully${NC}"
else
    echo -e "${RED}✗ Step 1 FAILED: Migration creation failed${NC}"
    echo "Please check the error above and fix any model issues."
    exit 1
fi

# Step 2: Apply migrations
echo ""
echo "Step 2/4: Applying migrations..."
echo "-----------------------------------------"
if pixi run migrate; then
    echo -e "${GREEN}✓ Step 2 PASSED: Migrations applied successfully${NC}"
else
    echo -e "${RED}✗ Step 2 FAILED: Migration application failed${NC}"
    echo "Please check the error above. You may need to:"
    echo "  - Ensure PostgreSQL is running (pixi run docker-up)"
    echo "  - Check DATABASE_URL in .env"
    exit 2
fi

# Step 3: Run tests
echo ""
echo "Step 3/4: Running tests..."
echo "-----------------------------------------"
if pixi run test; then
    echo -e "${GREEN}✓ Step 3 PASSED: All tests passed${NC}"
else
    echo -e "${RED}✗ Step 3 FAILED: Tests failed${NC}"
    echo "Please check the test failures above."
    exit 3
fi

# Success!
echo ""
echo "========================================="
echo -e "${GREEN}✓ ALL STEPS COMPLETED SUCCESSFULLY!${NC}"
echo "========================================="
echo "Your development environment is ready!"
echo ""
echo "Next steps:"
echo "  - pixi run runserver    (start Django)"
echo "  - pixi run temporal-worker  (start worker)"
echo "  - cd frontend && npm run dev  (start frontend)"
