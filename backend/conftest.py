"""
Pytest configuration and shared fixtures.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.organizations.models import Organization, OrganizationMembership, Repository, Branch

User = get_user_model()


@pytest.fixture
def api_client():
    """Return an API client instance."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create and return a test user."""
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )


@pytest.fixture
def admin_user(db):
    """Create and return an admin user."""
    return User.objects.create_superuser(
        email='admin@example.com',
        password='adminpass123',
        first_name='Admin',
        last_name='User'
    )


@pytest.fixture
def organization(db):
    """Create and return a test organization."""
    return Organization.objects.create(
        name='Test Organization',
        slug='test-org',
        plan='free'
    )


@pytest.fixture
def organization_membership(user, organization):
    """Create organization membership for user."""
    return OrganizationMembership.objects.create(
        user=user,
        organization=organization,
        role='member'
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Return an authenticated admin API client."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def repository(organization):
    """Create and return a test repository."""
    return Repository.objects.create(
        organization=organization,
        name='test-repo',
        full_name='test-org/test-repo',
        github_repo_id='123456',
        clone_url='https://github.com/test-org/test-repo.git'
    )


@pytest.fixture
def branch(repository):
    """Create and return a test branch."""
    return Branch.objects.create(
        repository=repository,
        name='main',
        sha='abc123def456'
    )
