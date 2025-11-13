"""
Tests for Organization models.
"""
import pytest
from apps.organizations.models import (
    Organization, OrganizationMembership, Repository, Branch
)


@pytest.mark.django_db
class TestOrganizationModel:
    """Test suite for Organization model."""

    def test_create_organization(self):
        """Test creating an organization."""
        org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            plan='free'
        )
        assert org.name == 'Test Org'
        assert org.slug == 'test-org'
        assert org.is_active is True
        assert str(org) == 'Test Org'

    def test_organization_membership(self, user, organization):
        """Test creating organization membership."""
        membership = OrganizationMembership.objects.create(
            user=user,
            organization=organization,
            role='member'
        )
        assert membership.user == user
        assert membership.organization == organization
        assert membership.role == 'member'

    def test_membership_permissions(self, organization_membership):
        """Test membership permission checking."""
        assert organization_membership.has_permission('read') is True
        assert organization_membership.has_permission('write') is True
        assert organization_membership.has_permission('admin') is False
        assert organization_membership.has_permission('billing') is False


@pytest.mark.django_db
class TestRepositoryModel:
    """Test suite for Repository model."""

    def test_create_repository(self, organization):
        """Test creating a repository."""
        repo = Repository.objects.create(
            organization=organization,
            github_repo_id='123456',
            name='test-repo',
            full_name='test-org/test-repo',
            is_active=True
        )
        assert repo.name == 'test-repo'
        assert repo.full_name == 'test-org/test-repo'
        assert repo.organization == organization
        assert str(repo) == 'test-org/test-repo'


@pytest.mark.django_db
class TestBranchModel:
    """Test suite for Branch model."""

    def test_create_branch(self, organization):
        """Test creating a branch."""
        repo = Repository.objects.create(
            organization=organization,
            github_repo_id='123456',
            name='test-repo',
            full_name='test-org/test-repo'
        )
        branch = Branch.objects.create(
            repository=repo,
            name='main',
            sha='abc123',
            is_default=True
        )
        assert branch.name == 'main'
        assert branch.repository == repo
        assert branch.is_default is True
        assert str(branch) == 'test-org/test-repo:main'
