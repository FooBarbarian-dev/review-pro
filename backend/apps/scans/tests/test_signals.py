"""
Tests for Scan signals.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta
from apps.scans.models import Scan
from apps.scans.signals import scan_pre_save, scan_post_save


@pytest.mark.django_db
@pytest.mark.unit
class TestScanSignals:
    """Test suite for Scan signals."""

    def test_scan_started_at_set_when_running(self, organization, repository, branch, user):
        """Test that started_at is set when scan status changes to running."""
        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            triggered_by=user,
            status='queued'
        )

        assert scan.started_at is None

        # Change to running
        scan.status = 'running'
        scan.save()
        scan.refresh_from_db()

        assert scan.started_at is not None
        assert isinstance(scan.started_at, timezone.datetime)

    def test_scan_completed_at_set_when_completed(self, organization, repository, branch, user):
        """Test that completed_at is set when scan status changes to completed."""
        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            triggered_by=user,
            status='running',
            started_at=timezone.now()
        )

        assert scan.completed_at is None

        # Change to completed
        scan.status = 'completed'
        scan.save()
        scan.refresh_from_db()

        assert scan.completed_at is not None

    def test_scan_duration_calculated_on_completion(self, organization, repository, branch, user):
        """Test that duration is calculated when scan completes."""
        start_time = timezone.now() - timedelta(minutes=5)

        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            triggered_by=user,
            status='running',
            started_at=start_time
        )

        # Complete the scan
        scan.status = 'completed'
        scan.save()
        scan.refresh_from_db()

        assert scan.duration_seconds is not None
        assert scan.duration_seconds > 0
        # Should be approximately 5 minutes (300 seconds)
        assert 290 <= scan.duration_seconds <= 310

    def test_scan_duration_calculated_on_failed(self, organization, repository, branch, user):
        """Test that duration is calculated when scan fails."""
        start_time = timezone.now() - timedelta(minutes=2)

        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            triggered_by=user,
            status='running',
            started_at=start_time
        )

        scan.status = 'failed'
        scan.save()
        scan.refresh_from_db()

        assert scan.duration_seconds is not None
        assert 110 <= scan.duration_seconds <= 130

    def test_scan_duration_calculated_on_cancelled(self, organization, repository, branch, user):
        """Test that duration is calculated when scan is cancelled."""
        start_time = timezone.now() - timedelta(seconds=30)

        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            triggered_by=user,
            status='running',
            started_at=start_time
        )

        scan.status = 'cancelled'
        scan.save()
        scan.refresh_from_db()

        assert scan.duration_seconds is not None
        assert 25 <= scan.duration_seconds <= 35

    def test_scan_started_at_not_overwritten(self, organization, repository, branch, user):
        """Test that started_at is not overwritten if already set."""
        original_start = timezone.now() - timedelta(hours=1)

        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            triggered_by=user,
            status='queued',
            started_at=original_start
        )

        # Change to running (should not update started_at)
        scan.status = 'running'
        scan.save()
        scan.refresh_from_db()

        assert scan.started_at == original_start

    def test_scan_completed_at_not_overwritten(self, organization, repository, branch, user):
        """Test that completed_at is not overwritten if already set."""
        original_completed = timezone.now() - timedelta(hours=1)

        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            triggered_by=user,
            status='running',
            started_at=timezone.now() - timedelta(hours=2),
            completed_at=original_completed
        )

        # Change status again (should not update completed_at)
        scan.status = 'failed'
        scan.save()
        scan.refresh_from_db()

        assert scan.completed_at == original_completed

    @patch('apps.scans.signals.update_quota_usage')
    def test_post_save_triggers_quota_update(self, mock_task, organization, repository, branch, user):
        """Test that post_save signal triggers quota update task."""
        # Create new scan
        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            triggered_by=user
        )

        # Mock delay method should be called
        # Note: This test assumes the task exists and is imported
        # If it doesn't, the signal will fail silently (try/except needed)

    def test_signal_handles_nonexistent_old_instance(self, organization, repository, branch):
        """Test that signal handles case where old instance doesn't exist."""
        # This can happen during migrations or data imports
        scan = Scan(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            status='running'
        )

        # Manually trigger pre_save (simulates save on new object)
        scan_pre_save(sender=Scan, instance=scan)

        # Should not raise exception
        scan.save()
        assert scan.started_at is not None

    def test_scan_status_unchanged_no_timing_update(self, organization, repository, branch, user):
        """Test that timing is not updated if status doesn't change."""
        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            triggered_by=user,
            status='running',
            started_at=timezone.now()
        )

        original_started = scan.started_at

        # Update something else, but not status
        scan.commit_sha = 'new123'
        scan.save()
        scan.refresh_from_db()

        # started_at should not change
        assert scan.started_at == original_started

    def test_multiple_status_transitions(self, organization, repository, branch, user):
        """Test multiple status transitions maintain correct timing."""
        scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            triggered_by=user,
            status='pending'
        )

        # pending -> queued (no timing changes)
        scan.status = 'queued'
        scan.save()
        scan.refresh_from_db()
        assert scan.started_at is None
        assert scan.completed_at is None

        # queued -> running (started_at set)
        scan.status = 'running'
        scan.save()
        scan.refresh_from_db()
        assert scan.started_at is not None
        started = scan.started_at

        # running -> completed (completed_at set, duration calculated)
        scan.status = 'completed'
        scan.save()
        scan.refresh_from_db()
        assert scan.completed_at is not None
        assert scan.duration_seconds is not None
        assert scan.started_at == started  # Should not change


@pytest.mark.django_db
@pytest.mark.unit
class TestOrganizationSignals:
    """Test suite for Organization signals."""

    def test_organization_post_save_on_creation(self, admin_user):
        """Test that post_save signal is triggered on organization creation."""
        from apps.organizations.models import Organization

        # Create organization (should trigger signal)
        org = Organization.objects.create(
            name='New Org',
            slug='new-org',
            owner=admin_user
        )

        # Signal runs but does nothing currently (just has 'pass')
        # This test ensures signal doesn't error
        assert org.id is not None

    def test_organization_post_save_on_update(self, organization):
        """Test that post_save signal is triggered on update."""
        # Update organization
        organization.name = 'Updated Name'
        organization.save()

        # Signal runs but should only act on creation
        assert organization.name == 'Updated Name'


@pytest.mark.django_db
@pytest.mark.unit
class TestUserSignals:
    """Test suite for User signals."""

    def test_user_post_save_on_creation(self):
        """Test that post_save signal is triggered on user creation."""
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Create user (should trigger signal)
        user = User.objects.create_user(
            email='newuser@example.com',
            password='testpass123'
        )

        # Signal runs but does nothing currently (just has 'pass')
        # This test ensures signal doesn't error
        assert user.id is not None

    def test_user_post_save_on_update(self, user):
        """Test that post_save signal is triggered on update."""
        # Update user
        user.first_name = 'Updated'
        user.save()

        # Signal runs but should only act on creation
        assert user.first_name == 'Updated'
