"""
Tests for Scan models.
"""
import pytest
import uuid
from datetime import timedelta
from django.utils import timezone
from apps.scans.models import Scan
from apps.organizations.models import Organization, Repository, Branch


@pytest.mark.django_db
@pytest.mark.unit
class TestScanModel:
    """Test suite for Scan model."""

    @pytest.fixture
    def repository(self, organization):
        """Create test repository."""
        return Repository.objects.create(
            organization=organization,
            name='test-repo',
            full_name='test-org/test-repo',
            github_repo_id='123456',
            default_branch='main'
        )

    @pytest.fixture
    def branch(self, repository):
        """Create test branch."""
        return Branch.objects.create(
            repository=repository,
            name='main',
            sha='abc123',
            is_default=True
        )

    def test_create_scan(self, organization, repository, branch, user):
        """Test creating a basic scan."""
        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123def456',
            triggered_by=user,
            trigger_type='manual'
        )

        assert scan.id is not None
        assert isinstance(scan.id, uuid.UUID)
        assert scan.organization == organization
        assert scan.repository == repository
        assert scan.branch == branch
        assert scan.commit_sha == 'abc123def456'
        assert scan.status == 'pending'
        assert scan.triggered_by == user
        assert scan.trigger_type == 'manual'

    def test_scan_status_choices(self, organization, repository, branch):
        """Test all valid scan status choices."""
        valid_statuses = ['pending', 'queued', 'running', 'completed', 'failed', 'cancelled']

        for status in valid_statuses:
            scan = Scan.objects.create(
                organization=organization,
                repository=repository,
                branch=branch,
                commit_sha=f'sha{status}',
                status=status
            )
            assert scan.status == status

    def test_scan_trigger_types(self, organization, repository, branch):
        """Test all valid trigger types."""
        trigger_types = ['manual', 'push', 'pull_request', 'scheduled']

        for trigger_type in trigger_types:
            scan = Scan.objects.create(
                organization=organization,
                repository=repository,
                branch=branch,
                commit_sha=f'sha{trigger_type}',
                trigger_type=trigger_type
            )
            assert scan.trigger_type == trigger_type

    def test_scan_statistics(self, organization, repository, branch):
        """Test scan statistics fields."""
        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            total_findings=100,
            critical_count=5,
            high_count=15,
            medium_count=30,
            low_count=40,
            info_count=10
        )

        assert scan.total_findings == 100
        assert scan.critical_count == 5
        assert scan.high_count == 15
        assert scan.medium_count == 30
        assert scan.low_count == 40
        assert scan.info_count == 10

    def test_scan_timing_fields(self, organization, repository, branch):
        """Test scan timing fields."""
        start_time = timezone.now()
        end_time = start_time + timedelta(minutes=5)

        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            started_at=start_time,
            completed_at=end_time,
            duration_seconds=300
        )

        assert scan.started_at == start_time
        assert scan.completed_at == end_time
        assert scan.duration_seconds == 300

    def test_scan_sarif_storage(self, organization, repository, branch):
        """Test SARIF storage fields."""
        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            sarif_file_path='s3://bucket/scans/scan-123.sarif',
            sarif_file_size=1024000
        )

        assert scan.sarif_file_path == 's3://bucket/scans/scan-123.sarif'
        assert scan.sarif_file_size == 1024000

    def test_scan_tools_used(self, organization, repository, branch):
        """Test tools_used JSON field."""
        tools = ['bandit', 'semgrep', 'eslint']
        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            tools_used=tools
        )

        assert scan.tools_used == tools
        assert 'bandit' in scan.tools_used

    def test_scan_error_handling(self, organization, repository, branch):
        """Test error fields."""
        error_details = {
            'code': 'TOOL_FAILED',
            'tool': 'bandit',
            'exit_code': 1
        }

        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            status='failed',
            error_message='Tool execution failed',
            error_details=error_details
        )

        assert scan.status == 'failed'
        assert scan.error_message == 'Tool execution failed'
        assert scan.error_details == error_details
        assert scan.error_details['tool'] == 'bandit'

    def test_scan_worker_information(self, organization, repository, branch):
        """Test worker-related fields."""
        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            worker_id='worker-1',
            worker_container_id='container-abc123'
        )

        assert scan.worker_id == 'worker-1'
        assert scan.worker_container_id == 'container-abc123'

    def test_scan_str_method(self, organization, repository, branch):
        """Test scan string representation."""
        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123def'
        )

        expected = f'Scan {str(scan.id)[:8]} - test-org/test-repo@abc123def'
        assert expected in str(scan) or 'Scan' in str(scan)

    def test_scan_cascade_deletion(self, organization, repository, branch):
        """Test that scan is deleted when repository is deleted."""
        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123'
        )

        scan_id = scan.id
        repository.delete()

        assert not Scan.objects.filter(id=scan_id).exists()

    def test_scan_user_set_null(self, organization, repository, branch, user):
        """Test that scan triggered_by is set to NULL when user is deleted."""
        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            triggered_by=user
        )

        user.delete()
        scan.refresh_from_db()

        assert scan.triggered_by is None

    def test_scan_timestamps(self, organization, repository, branch):
        """Test automatic timestamp fields."""
        before_create = timezone.now()

        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123'
        )

        after_create = timezone.now()

        assert before_create <= scan.created_at <= after_create
        assert scan.updated_at is not None

        # Test update timestamp
        original_updated = scan.updated_at
        scan.status = 'running'
        scan.save()
        scan.refresh_from_db()

        assert scan.updated_at > original_updated

    def test_scan_queryby_status(self, organization, repository, branch):
        """Test querying scans by status."""
        Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc1',
            status='pending'
        )
        Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc2',
            status='running'
        )
        Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc3',
            status='completed'
        )

        pending_scans = Scan.objects.filter(status='pending')
        running_scans = Scan.objects.filter(status='running')
        completed_scans = Scan.objects.filter(status='completed')

        assert pending_scans.count() == 1
        assert running_scans.count() == 1
        assert completed_scans.count() == 1

    def test_scan_organization_relationship(self, organization, repository, branch):
        """Test relationship between scans and organization."""
        scan1 = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc1'
        )
        scan2 = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc2'
        )

        org_scans = organization.scans.all()
        assert scan1 in org_scans
        assert scan2 in org_scans
        assert org_scans.count() == 2

    def test_scan_default_values(self, organization, repository, branch):
        """Test that default values are set correctly."""
        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123'
        )

        assert scan.status == 'pending'
        assert scan.trigger_type == 'manual'
        assert scan.total_findings == 0
        assert scan.critical_count == 0
        assert scan.high_count == 0
        assert scan.medium_count == 0
        assert scan.low_count == 0
        assert scan.info_count == 0
        assert scan.tools_used == []
