#!/bin/bash
# Check langroid version in pixi environment

echo "Checking langroid version in pixi environment..."
echo ""

LANGROID_VERSION=$(pixi run python -c "import langroid; print(langroid.__version__)" 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "✓ Langroid is installed: version $LANGROID_VERSION"

    if [ "$LANGROID_VERSION" = "0.1.297" ]; then
        echo "✓ Correct version! (0.1.297)"
        exit 0
    else
        echo "✗ WRONG VERSION! Expected 0.1.297, got $LANGROID_VERSION"
        echo ""
        echo "To fix this, run:"
        echo "  rm -rf .pixi"
        echo "  pixi install"
        exit 1
    fi
else
    echo "✗ Langroid is not installed or import failed"
    echo ""
    echo "To fix this, run:"
    echo "  pixi install"
    exit 1
fi
