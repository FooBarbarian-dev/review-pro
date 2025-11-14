#!/usr/bin/env python3
"""
Generate a comprehensive coverage summary from backend and frontend coverage reports.
"""
import json
import os
from pathlib import Path


def load_backend_coverage():
    """Load backend coverage from coverage.json."""
    backend_path = Path(__file__).parent.parent / 'backend' / 'coverage.json'

    if not backend_path.exists():
        print("⚠ Backend coverage.json not found. Run backend tests first.")
        return None

    with open(backend_path) as f:
        data = json.load(f)

    totals = data.get('totals', {})
    return {
        'lines': totals.get('percent_covered', 0),
        'branches': totals.get('percent_covered_display', 0),
        'statements': totals.get('num_statements', 0),
        'missing': totals.get('missing_lines', 0),
    }


def load_frontend_coverage():
    """Load frontend coverage from coverage-summary.json."""
    frontend_path = Path(__file__).parent.parent / 'frontend' / 'coverage' / 'coverage-summary.json'

    if not frontend_path.exists():
        print("⚠ Frontend coverage summary not found. Run frontend tests first.")
        return None

    with open(frontend_path) as f:
        data = json.load(f)

    totals = data.get('total', {})

    return {
        'lines': totals.get('lines', {}).get('pct', 0),
        'branches': totals.get('branches', {}).get('pct', 0),
        'functions': totals.get('functions', {}).get('pct', 0),
        'statements': totals.get('statements', {}).get('pct', 0),
    }


def print_coverage_table(backend, frontend):
    """Print a formatted coverage table."""
    print("\n" + "="*70)
    print("📊 Test Coverage Summary")
    print("="*70 + "\n")

    # Backend
    print("Backend (Python/Django)")
    print("-" * 70)
    if backend:
        print(f"  Lines:       {backend['lines']:.2f}%")
        print(f"  Branches:    {backend.get('branches', 0):.2f}%")
        print(f"  Statements:  {backend.get('statements', 0)}")
        print(f"  Missing:     {backend.get('missing', 0)}")

        # Status indicator
        if backend['lines'] >= 90:
            status = "✅ Excellent"
        elif backend['lines'] >= 80:
            status = "✓ Good"
        elif backend['lines'] >= 70:
            status = "⚠ Fair"
        else:
            status = "❌ Needs Improvement"
        print(f"  Status:      {status}")
    else:
        print("  No data available")

    print()

    # Frontend
    print("Frontend (React/TypeScript)")
    print("-" * 70)
    if frontend:
        print(f"  Lines:       {frontend['lines']:.2f}%")
        print(f"  Branches:    {frontend['branches']:.2f}%")
        print(f"  Functions:   {frontend['functions']:.2f}%")
        print(f"  Statements:  {frontend['statements']:.2f}%")

        # Status indicator
        avg = (frontend['lines'] + frontend['branches'] + frontend['functions'] + frontend['statements']) / 4
        if avg >= 80:
            status = "✅ Excellent"
        elif avg >= 70:
            status = "✓ Good"
        elif avg >= 60:
            status = "⚠ Fair"
        else:
            status = "❌ Needs Improvement"
        print(f"  Status:      {status}")
    else:
        print("  No data available")

    print("\n" + "="*70)

    # Overall status
    if backend and frontend:
        overall = (backend['lines'] + frontend['lines']) / 2
        print(f"\n📈 Overall Coverage: {overall:.2f}%")

        if overall >= 85:
            print("✅ Excellent! Coverage meets target (85%+)")
        elif overall >= 75:
            print("✓ Good! Close to target")
        elif overall >= 65:
            print("⚠ Fair. Recommend adding more tests")
        else:
            print("❌ Coverage below recommended level")

    print("\n" + "="*70 + "\n")

    # Recommendations
    print("📝 Recommendations:")
    if backend and backend['lines'] < 85:
        print("  • Add more backend tests (models, views, serializers)")
    if frontend and frontend['lines'] < 80:
        print("  • Add more frontend tests (components, hooks, utils)")
    if backend and backend.get('branches', 0) < 75:
        print("  • Improve backend branch coverage (test error paths)")
    if frontend and frontend['branches'] < 75:
        print("  • Improve frontend branch coverage (test edge cases)")

    print("\n📁 Detailed Reports:")
    print("  • Backend:  backend/htmlcov/index.html")
    print("  • Frontend: frontend/coverage/index.html")
    print()


def main():
    """Main function."""
    backend_coverage = load_backend_coverage()
    frontend_coverage = load_frontend_coverage()

    if not backend_coverage and not frontend_coverage:
        print("\n❌ No coverage data found!")
        print("Run tests first:")
        print("  • Backend:  cd backend && pytest --cov")
        print("  • Frontend: cd frontend && npm run test:coverage")
        return 1

    print_coverage_table(backend_coverage, frontend_coverage)

    return 0


if __name__ == '__main__':
    exit(main())
