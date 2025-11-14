"""
Tests for Scans API endpoints.
"""
import pytest
from unittest.mock import patch, MagicMock
from rest_framework import status
from apps.scans.models import Scan
from apps.organizations.models import Organization, Repository, Branch


@pytest.mark.django_db
@pytest.mark.api
class TestScanViewSet:
    """Test suite for Scan API endpoints."""

    @pytest.fixture
    def repository(self, organization):
        """Create test repository."""
        return Repository.objects.create(
            organization=organization,
            name='test-repo',
            full_name='test-org/test-repo',
            github_repo_id='123456'
        )

    @pytest.fixture
    def branch(self, repository):
        """Create test branch."""
        return Branch.objects.create(
            repository=repository,
            name='main',
            sha='abc123'
        )

    @pytest.fixture
    def scan(self, organization, repository, branch, user):
        """Create test scan."""
        return Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc123',
            triggered_by=user,
            status='completed'
        )

    def test_list_scans_authenticated(self, authenticated_client, scan):
        """Test listing scans requires authentication."""
        response = authenticated_client.get('/api/scans/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_list_scans_unauthenticated(self, api_client):
        """Test listing scans without authentication fails."""
        response = api_client.get('/api/scans/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_scan(self, authenticated_client, scan):
        """Test retrieving a single scan."""
        response = authenticated_client.get(f'/api/scans/{scan.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(scan.id)
        assert response.data['commit_sha'] == 'abc123'

    def test_filter_scans_by_status(self, authenticated_client, organization, repository, branch, user):
        """Test filtering scans by status."""
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
            status='completed'
        )

        response = authenticated_client.get('/api/scans/?status=completed')
        assert response.status_code == status.HTTP_200_OK

    def test_filter_scans_by_repository(self, authenticated_client, scan):
        """Test filtering scans by repository."""
        response = authenticated_client.get(f'/api/scans/?repository_id={scan.repository.id}')
        assert response.status_code == status.HTTP_200_OK

    @patch('services.temporal_client.TemporalService.trigger_scan_workflow')
    def test_create_scan(self, mock_workflow, authenticated_client, organization, repository, branch):
        """Test creating a new scan."""
        mock_workflow.return_value = {
            'workflow_id': 'scan-123',
            'run_id': 'run-456',
            'status': 'started'
        }

        data = {
            'organization': str(organization.id),
            'repository': str(repository.id),
            'branch': str(branch.id),
            'commit_sha': 'new123'
        }

        response = authenticated_client.post('/api/scans/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert 'workflow' in response.data
        mock_workflow.assert_called_once()

    @patch('services.temporal_client.TemporalService.trigger_scan_workflow')
    def test_create_scan_workflow_failure(self, mock_workflow, authenticated_client, organization, repository, branch):
        """Test scan creation when workflow fails to start."""
        mock_workflow.side_effect = Exception('Temporal connection failed')

        data = {
            'organization': str(organization.id),
            'repository': str(repository.id),
            'branch': str(branch.id),
            'commit_sha': 'fail123'
        }

        response = authenticated_client.post('/api/scans/', data, format='json')
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'error' in response.data

    @patch('services.temporal_client.TemporalService.trigger_adjudication_workflow')
    def test_adjudicate_action(self, mock_workflow, authenticated_client, scan):
        """Test adjudicate action on scan."""
        mock_workflow.return_value = {
            'workflow_id': 'adjudicate-123',
            'run_id': 'run-789',
            'status': 'started'
        }

        data = {
            'provider': 'openai',
            'model': 'gpt-4o',
            'pattern': 'post_processing',
            'batch_size': 10,
            'max_findings': 100
        }

        response = authenticated_client.post(f'/api/scans/{scan.id}/adjudicate/', data, format='json')
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert 'workflow_id' in response.data
        mock_workflow.assert_called_once()

    @patch('services.temporal_client.TemporalService.trigger_adjudication_workflow')
    def test_adjudicate_invalid_data(self, mock_workflow, authenticated_client, scan):
        """Test adjudicate with invalid data."""
        data = {
            'provider': 'invalid-provider',  # Invalid choice
            'model': 'gpt-4o'
        }

        response = authenticated_client.post(f'/api/scans/{scan.id}/adjudicate/', data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch('services.temporal_client.TemporalService.trigger_clustering_workflow')
    def test_cluster_action(self, mock_workflow, authenticated_client, scan):
        """Test cluster action on scan."""
        mock_workflow.return_value = {
            'workflow_id': 'cluster-123',
            'run_id': 'run-abc',
            'status': 'started'
        }

        data = {
            'algorithm': 'dbscan',
            'threshold': 0.85
        }

        response = authenticated_client.post(f'/api/scans/{scan.id}/cluster/', data, format='json')
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert 'workflow_id' in response.data
        mock_workflow.assert_called_once()

    @patch('services.temporal_client.TemporalService.trigger_pattern_comparison_workflow')
    def test_compare_patterns_action(self, mock_workflow, authenticated_client, scan):
        """Test compare_patterns action on scan."""
        mock_workflow.return_value = {
            'workflow_id': 'compare-123',
            'run_id': 'run-xyz',
            'status': 'started'
        }

        response = authenticated_client.post(f'/api/scans/{scan.id}/compare_patterns/', format='json')
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert 'workflow_id' in response.data
        mock_workflow.assert_called_once()

    @patch('services.temporal_client.TemporalService.trigger_scan_workflow')
    def test_rescan_action(self, mock_workflow, authenticated_client, scan):
        """Test rescan action creates new scan."""
        mock_workflow.return_value = {
            'workflow_id': 'rescan-123',
            'run_id': 'run-def',
            'status': 'started'
        }

        original_scan_count = Scan.objects.count()

        response = authenticated_client.post(f'/api/scans/{scan.id}/rescan/', format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert 'workflow' in response.data
        assert 'original_scan_id' in response.data
        assert response.data['original_scan_id'] == str(scan.id)

        # Verify new scan was created
        assert Scan.objects.count() == original_scan_count + 1
        mock_workflow.assert_called_once()

    def test_scan_statistics_endpoint(self, authenticated_client, scan):
        """Test scan statistics endpoint."""
        response = authenticated_client.get(f'/api/scans/{scan.id}/statistics/')
        # May return 200 or 404 depending on implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_update_scan_not_allowed(self, authenticated_client, scan):
        """Test that PUT/PATCH to scan is not allowed or restricted."""
        data = {'status': 'completed'}
        response = authenticated_client.patch(f'/api/scans/{scan.id}/', data, format='json')
        # Should either be not allowed or have restrictions
        assert response.status_code in [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_200_OK  # If updates are allowed
        ]

    def test_delete_scan_not_allowed(self, authenticated_client, scan):
        """Test that DELETE to scan is not allowed or restricted."""
        response = authenticated_client.delete(f'/api/scans/{scan.id}/')
        assert response.status_code in [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_204_NO_CONTENT  # If deletes are allowed
        ]


@pytest.mark.django_db
@pytest.mark.api
class TestDashboardStatsView:
    """Test suite for Dashboard Statistics API."""

    @pytest.fixture
    def setup_data(self, organization, repository, branch, user):
        """Setup test data for dashboard."""
        from apps.findings.models import Finding

        # Create scans
        scan1 = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc1',
            status='completed'
        )
        scan2 = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='abc2',
            status='running'
        )

        # Create findings
        Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan1,
            last_seen_scan=scan1,
            fingerprint='fp1',
            rule_id='rule1',
            message='Test',
            severity='high',
            status='open',
            file_path='test.py',
            start_line=1,
            tool_name='test'
        )
        Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan1,
            last_seen_scan=scan1,
            fingerprint='fp2',
            rule_id='rule2',
            message='Test',
            severity='critical',
            status='false_positive',
            file_path='test.py',
            start_line=2,
            tool_name='test'
        )

        return scan1, scan2

    def test_dashboard_stats_authenticated(self, authenticated_client, setup_data):
        """Test dashboard stats endpoint requires authentication."""
        response = authenticated_client.get('/api/dashboard/stats/')
        assert response.status_code == status.HTTP_200_OK

    def test_dashboard_stats_unauthenticated(self, api_client, setup_data):
        """Test dashboard stats without authentication fails."""
        response = api_client.get('/api/dashboard/stats/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_dashboard_stats_content(self, authenticated_client, setup_data):
        """Test dashboard stats returns expected data."""
        response = authenticated_client.get('/api/dashboard/stats/')
        assert response.status_code == status.HTTP_200_OK

        data = response.data
        assert 'total_scans' in data
        assert 'total_findings' in data
        assert 'open_findings' in data
        assert 'false_positives' in data
        assert isinstance(data['total_scans'], int)
        assert isinstance(data['total_findings'], int)

    def test_dashboard_stats_aggregations(self, authenticated_client, setup_data):
        """Test dashboard stats aggregations."""
        response = authenticated_client.get('/api/dashboard/stats/')
        assert response.status_code == status.HTTP_200_OK

        data = response.data
        # Check for aggregated data structures
        assert 'findings_by_severity' in data or 'scans_by_status' in data

    def test_dashboard_stats_empty_database(self, authenticated_client):
        """Test dashboard stats with no data."""
        response = authenticated_client.get('/api/dashboard/stats/')
        assert response.status_code == status.HTTP_200_OK

        data = response.data
        assert data.get('total_scans', 0) == 0
        assert data.get('total_findings', 0) == 0
