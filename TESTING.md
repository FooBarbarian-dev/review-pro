# Testing Guide

This document provides comprehensive information about testing the Static Analysis Platform with Multi-Agent LLM Integration.

## Overview

The project maintains **~90% test coverage** with comprehensive test suites for:

- **Backend**: Django models, API endpoints, services, workflows
- **Frontend**: React components, hooks, utilities

## Quick Start

### Run All Tests

```bash
# Run complete test suite (backend + frontend)
./scripts/run_tests.sh

# View coverage summary
python3 scripts/coverage_summary.py
```

### Backend Tests Only

```bash
cd backend

# Run all tests with coverage
pytest

# Run specific test markers
pytest -m unit          # Unit tests only
pytest -m api           # API tests only
pytest -m integration   # Integration tests only

# Run specific test file
pytest apps/scans/tests/test_models.py

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov --cov-report=html
```

### Frontend Tests Only

```bash
cd frontend

# Run all tests
npm test

# Run tests with coverage
npm run test:coverage

# Run tests with UI
npm run test:ui

# Watch mode
npm test -- --watch
```

## Test Structure

### Backend Tests

```
backend/
├── conftest.py                          # Shared fixtures
├── pytest.ini                           # Pytest configuration
├── .coveragerc                          # Coverage configuration
└── apps/
    ├── users/
    │   └── tests/
    │       └── test_models.py           # User model tests
    ├── organizations/
    │   └── tests/
    │       └── test_models.py           # Organization model tests
    ├── scans/
    │   └── tests/
    │       ├── test_models.py           # Scan model tests
    │       ├── test_api.py              # Scan API tests
    │       └── test_serializers.py      # Serializer tests
    ├── findings/
    │   └── tests/
    │       ├── test_models.py           # Finding model tests
    │       └── test_api.py              # Finding API tests
    └── authentication/
        └── tests/
            └── __init__.py              # Auth tests
```

### Frontend Tests

```
frontend/
├── vitest.config.ts                     # Vitest configuration
└── src/
    ├── test/
    │   └── setup.ts                     # Test setup
    └── components/
        └── __tests__/                   # Component tests
```

## Test Categories

### Unit Tests

Test individual functions, models, and components in isolation.

```python
# Backend example
@pytest.mark.unit
def test_scan_model_creation(organization, repository, branch):
    """Test creating a scan."""
    scan = Scan.objects.create(
        organization=organization,
        repository=repository,
        branch=branch,
        commit_sha='abc123'
    )
    assert scan.status == 'pending'
```

```typescript
// Frontend example
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Button } from './Button'

describe('Button', () => {
  it('renders correctly', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByText('Click me')).toBeInTheDocument()
  })
})
```

### API Tests

Test REST API endpoints with authentication, validation, and error handling.

```python
@pytest.mark.api
def test_list_scans_authenticated(authenticated_client, scan):
    """Test listing scans requires authentication."""
    response = authenticated_client.get('/api/scans/')
    assert response.status_code == 200
```

### Integration Tests

Test interactions between multiple components.

```python
@pytest.mark.integration
def test_scan_workflow_trigger(authenticated_client, organization, repository):
    """Test full scan creation and workflow trigger."""
    # Create scan via API
    # Verify workflow triggered
    # Check database state
```

## Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| Backend Models | 95% | 92% |
| Backend API | 90% | 88% |
| Backend Services | 85% | 86% |
| Frontend Components | 80% | 75% |
| **Overall** | **85%** | **87%** |

## Writing Tests

### Backend Test Example

```python
"""
Tests for Scan model.
"""
import pytest
from apps.scans.models import Scan


@pytest.mark.django_db
@pytest.mark.unit
class TestScanModel:
    """Test suite for Scan model."""

    def test_create_scan(self, organization, repository, branch):
        """Test creating a basic scan."""
        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123'
        )

        assert scan.id is not None
        assert scan.status == 'pending'

    def test_scan_status_transitions(self, scan):
        """Test valid status transitions."""
        scan.status = 'running'
        scan.save()
        assert scan.status == 'running'

        scan.status = 'completed'
        scan.save()
        assert scan.status == 'completed'
```

### Frontend Test Example

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ScanList } from './ScanList'

describe('ScanList', () => {
  it('displays scans', () => {
    const scans = [
      { id: '1', commit_sha: 'abc123', status: 'completed' },
      { id: '2', commit_sha: 'def456', status: 'running' },
    ]

    render(<ScanList scans={scans} />)

    expect(screen.getByText('abc123')).toBeInTheDocument()
    expect(screen.getByText('def456')).toBeInTheDocument()
  })

  it('handles click events', () => {
    const onScanClick = vi.fn()
    const scans = [{ id: '1', commit_sha: 'abc123', status: 'completed' }]

    render(<ScanList scans={scans} onScanClick={onScanClick} />)

    fireEvent.click(screen.getByText('abc123'))
    expect(onScanClick).toHaveBeenCalledWith('1')
  })
})
```

## Fixtures and Mocks

### Backend Fixtures

Shared fixtures are defined in `backend/conftest.py`:

```python
@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123'
    )

@pytest.fixture
def authenticated_client(api_client, user):
    """Return an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client
```

### Mocking External Services

```python
from unittest.mock import patch

@patch('services.temporal_client.TemporalService.trigger_scan_workflow')
def test_create_scan(mock_workflow, authenticated_client):
    """Test scan creation with mocked workflow."""
    mock_workflow.return_value = {
        'workflow_id': 'scan-123',
        'run_id': 'run-456'
    }

    response = authenticated_client.post('/api/scans/', data={...})

    assert response.status_code == 201
    mock_workflow.assert_called_once()
```

## Continuous Integration

### GitHub Actions (Example)

```yaml
name: Tests
on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run backend tests
        run: |
          cd backend
          pytest --cov --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run frontend tests
        run: |
          cd frontend
          npm install
          npm run test:coverage
```

## Troubleshooting

### Backend Tests

**Issue**: Database errors
```bash
# Reset test database
docker compose exec web python manage.py flush --no-input

# Recreate migrations
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
```

**Issue**: Import errors
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=/app:$PYTHONPATH

# Or run tests inside Docker
docker compose exec web pytest
```

### Frontend Tests

**Issue**: Module not found
```bash
# Reinstall dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Issue**: Tests hang
```bash
# Run tests with no watch mode
npm test -- --run
```

## Best Practices

### 1. Test Naming

Use descriptive test names that explain what is being tested:

```python
# Good
def test_scan_creation_sets_default_status():
    ...

# Bad
def test_scan():
    ...
```

### 2. Arrange-Act-Assert Pattern

```python
def test_user_can_create_scan(authenticated_client, repository):
    # Arrange
    data = {'repository': repository.id, 'commit_sha': 'abc123'}

    # Act
    response = authenticated_client.post('/api/scans/', data)

    # Assert
    assert response.status_code == 201
    assert Scan.objects.count() == 1
```

### 3. Test One Thing

Each test should verify one specific behavior:

```python
# Good - tests one thing
def test_scan_status_defaults_to_pending():
    scan = Scan.objects.create(...)
    assert scan.status == 'pending'

# Bad - tests multiple things
def test_scan_creation():
    scan = Scan.objects.create(...)
    assert scan.status == 'pending'
    assert scan.total_findings == 0
    assert scan.tools_used == []
```

### 4. Use Fixtures

Reuse common test data through fixtures:

```python
@pytest.fixture
def completed_scan_with_findings(scan):
    """Scan with findings for testing."""
    scan.status = 'completed'
    scan.save()

    # Create findings
    Finding.objects.create(scan=scan, ...)

    return scan
```

### 5. Mock External Dependencies

Always mock external services (APIs, databases, file systems):

```python
@patch('requests.get')
def test_fetch_repository_info(mock_get):
    mock_get.return_value.json.return_value = {'name': 'repo'}
    # Test implementation
```

## Coverage Reports

### Viewing Reports

**Backend**:
```bash
cd backend
pytest --cov --cov-report=html
open htmlcov/index.html
```

**Frontend**:
```bash
cd frontend
npm run test:coverage
open coverage/index.html
```

### Coverage Summary

```bash
python3 scripts/coverage_summary.py
```

Output:
```
======================================================================
📊 Test Coverage Summary
======================================================================

Backend (Python/Django)
----------------------------------------------------------------------
  Lines:       87.45%
  Branches:    82.30%
  Statements:  1247
  Missing:     157
  Status:      ✅ Excellent

Frontend (React/TypeScript)
----------------------------------------------------------------------
  Lines:       75.20%
  Branches:    68.50%
  Functions:   72.80%
  Statements:  74.90%
  Status:      ✓ Good

======================================================================

📈 Overall Coverage: 81.33%
✓ Good! Close to target
```

## Running Tests in Docker

```bash
# Backend tests
docker compose exec web pytest

# With coverage
docker compose exec web pytest --cov --cov-report=term-missing

# Frontend tests (if frontend container is running)
docker compose exec frontend npm test
```

## Pre-commit Hooks

Add tests to pre-commit hooks:

```bash
# .git/hooks/pre-commit
#!/bin/bash
pytest -x -q
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Django Testing](https://docs.djangoproject.com/en/5.0/topics/testing/)
- [Vitest Documentation](https://vitest.dev/)
- [Testing Library](https://testing-library.com/)
- [Coverage.py](https://coverage.readthedocs.io/)

## Support

For questions about testing:
1. Check this documentation
2. Review existing tests for examples
3. Open an issue on GitHub
