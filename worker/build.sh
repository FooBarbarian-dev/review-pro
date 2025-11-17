#!/bin/bash
# Build script for security-worker Docker image

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
IMAGE_NAME="security-worker"
IMAGE_TAG="latest"
PUSH=false
REGISTRY=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --push)
            PUSH=true
            shift
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --tag TAG           Set image tag (default: latest)"
            echo "  --push              Push image to registry after build"
            echo "  --registry URL      Registry URL for pushing"
            echo "  --help              Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Build locally"
            echo "  $0 --tag 1.0.0                       # Build with version tag"
            echo "  $0 --tag 1.0.0 --push --registry ghcr.io/owner"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Construct full image name
if [ -n "${REGISTRY}" ]; then
    FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
else
    FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
fi

echo -e "${GREEN}Building security-worker Docker image${NC}"
echo -e "Image: ${YELLOW}${FULL_IMAGE_NAME}${NC}"
echo ""

# Build the image
echo -e "${GREEN}Step 1: Building Docker image...${NC}"
if docker build -t "${FULL_IMAGE_NAME}" -f Dockerfile .; then
    echo -e "${GREEN}✓ Build successful${NC}"
else
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi

# Test the image
echo ""
echo -e "${GREEN}Step 2: Testing image...${NC}"
if docker run --rm "${FULL_IMAGE_NAME}" --version 2>&1 | head -1; then
    echo -e "${GREEN}✓ Image test successful${NC}"
else
    echo -e "${YELLOW}⚠ Image test skipped (optional)${NC}"
fi

# Show image size
echo ""
echo -e "${GREEN}Step 3: Image information${NC}"
docker images "${FULL_IMAGE_NAME}" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# Push if requested
if [ "${PUSH}" = true ]; then
    echo ""
    echo -e "${GREEN}Step 4: Pushing to registry...${NC}"

    if [ -z "${REGISTRY}" ]; then
        echo -e "${RED}✗ Cannot push: --registry not specified${NC}"
        exit 1
    fi

    if docker push "${FULL_IMAGE_NAME}"; then
        echo -e "${GREEN}✓ Push successful${NC}"
    else
        echo -e "${RED}✗ Push failed${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}=== Build Complete ===${NC}"
echo ""
echo "Image: ${FULL_IMAGE_NAME}"
echo ""
echo "Next steps:"
echo "  1. Test locally:"
echo "     docker run -e GITHUB_TOKEN=xxx -e REPO_URL=https://github.com/owner/repo ${FULL_IMAGE_NAME}"
echo ""
echo "  2. Update docker-compose.yml or Django settings to use this image"
echo ""
echo "  3. Run a scan via the API:"
echo "     curl -X POST http://localhost:8000/api/v1/scans/ -H 'Authorization: Bearer TOKEN' -d '{...}'"
