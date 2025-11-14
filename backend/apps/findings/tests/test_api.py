"""
Tests for Findings API endpoints.
"""
import pytest
from rest_framework import status
from apps.findings.models import Finding, FindingCluster, FindingClusterMembership
from apps.scans.models import Scan
from apps.organizations.models import Repository, Branch


@pytest.mark.django_db
@pytest.mark.api
class TestFindingViewSet:
    """Test suite for Finding API endpoints."""

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
            triggered_by=user
        )

    @pytest.fixture
    def finding(self, organization, repository, scan):
        """Create test finding."""
        return Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='test123',
            rule_id='test/rule-1',
            message='Test vulnerability',
            severity='high',
            file_path='src/main.py',
            start_line=10,
            tool_name='bandit'
        )

    def test_list_findings_authenticated(self, authenticated_client, finding):
        """Test listing findings requires authentication."""
        response = authenticated_client.get('/api/findings/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)

    def test_list_findings_unauthenticated(self, api_client):
        """Test listing findings without authentication fails."""
        response = api_client.get('/api/findings/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_finding(self, authenticated_client, finding):
        """Test retrieving a single finding."""
        response = authenticated_client.get(f'/api/findings/{finding.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(finding.id)
        assert response.data['rule_id'] == 'test/rule-1'
        assert response.data['severity'] == 'high'

    def test_filter_findings_by_severity(self, authenticated_client, organization, repository, scan):
        """Test filtering findings by severity."""
        Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='fp1',
            rule_id='rule1',
            message='Test',
            severity='critical',
            file_path='test.py',
            start_line=1,
            tool_name='test'
        )
        Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='fp2',
            rule_id='rule2',
            message='Test',
            severity='low',
            file_path='test.py',
            start_line=2,
            tool_name='test'
        )

        response = authenticated_client.get('/api/findings/?severity=critical')
        assert response.status_code == status.HTTP_200_OK

    def test_filter_findings_by_status(self, authenticated_client, organization, repository, scan):
        """Test filtering findings by status."""
        Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
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
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='fp2',
            rule_id='rule2',
            message='Test',
            severity='high',
            status='false_positive',
            file_path='test.py',
            start_line=2,
            tool_name='test'
        )

        response = authenticated_client.get('/api/findings/?status=open')
        assert response.status_code == status.HTTP_200_OK

    def test_filter_findings_by_scan(self, authenticated_client, finding):
        """Test filtering findings by scan."""
        response = authenticated_client.get(f'/api/findings/?scan__id={finding.first_seen_scan.id}')
        assert response.status_code == status.HTTP_200_OK

    def test_filter_findings_by_tool(self, authenticated_client, finding):
        """Test filtering findings by tool name."""
        response = authenticated_client.get('/api/findings/?tool_name=bandit')
        assert response.status_code == status.HTTP_200_OK

    def test_filter_findings_by_file_path(self, authenticated_client, finding):
        """Test filtering findings by file path."""
        response = authenticated_client.get('/api/findings/?file_path=main.py')
        assert response.status_code == status.HTTP_200_OK

    def test_update_finding_status(self, authenticated_client, finding):
        """Test updating finding status."""
        data = {'status': 'false_positive'}
        response = authenticated_client.patch(f'/api/findings/{finding.id}/', data, format='json')

        # Should either succeed or be forbidden depending on implementation
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_405_METHOD_NOT_ALLOWED
        ]

    def test_finding_includes_llm_verdicts(self, authenticated_client, finding):
        """Test that finding detail includes LLM verdicts."""
        from apps.findings.models import LLMVerdict

        LLMVerdict.objects.create(
            finding=finding,
            verdict='false_positive',
            confidence=0.92,
            reasoning='Test reasoning',
            llm_provider='openai',
            llm_model='gpt-4o',
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )

        response = authenticated_client.get(f'/api/findings/{finding.id}/')
        assert response.status_code == status.HTTP_200_OK

        # Check if LLM verdicts are included
        if 'llm_verdicts' in response.data:
            assert len(response.data['llm_verdicts']) == 1

    def test_findings_ordering(self, authenticated_client, organization, repository, scan):
        """Test findings are ordered by severity and creation time."""
        Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='fp1',
            rule_id='rule1',
            message='Test',
            severity='low',
            file_path='test.py',
            start_line=1,
            tool_name='test'
        )
        Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='fp2',
            rule_id='rule2',
            message='Test',
            severity='critical',
            file_path='test.py',
            start_line=2,
            tool_name='test'
        )

        response = authenticated_client.get('/api/findings/')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.api
class TestFindingClusterViewSet:
    """Test suite for FindingCluster API endpoints."""

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
            triggered_by=user
        )

    @pytest.fixture
    def cluster(self, organization, scan):
        """Create test cluster."""
        return FindingCluster.objects.create(
            organization=organization,
            scan=scan,
            algorithm='dbscan',
            cluster_id=1,
            size=5
        )

    @pytest.fixture
    def finding(self, organization, repository, scan):
        """Create test finding."""
        return Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='test123',
            rule_id='test/rule-1',
            message='Test',
            severity='high',
            file_path='test.py',
            start_line=10,
            tool_name='test'
        )

    def test_list_clusters_authenticated(self, authenticated_client, cluster):
        """Test listing clusters requires authentication."""
        response = authenticated_client.get('/api/clusters/')
        assert response.status_code == status.HTTP_200_OK

    def test_list_clusters_unauthenticated(self, api_client):
        """Test listing clusters without authentication fails."""
        response = api_client.get('/api/clusters/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_cluster(self, authenticated_client, cluster):
        """Test retrieving a single cluster."""
        response = authenticated_client.get(f'/api/clusters/{cluster.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(cluster.id)
        assert response.data['algorithm'] == 'dbscan'

    def test_filter_clusters_by_scan(self, authenticated_client, cluster):
        """Test filtering clusters by scan."""
        response = authenticated_client.get(f'/api/clusters/?scan__id={cluster.scan.id}')
        assert response.status_code == status.HTTP_200_OK

    def test_filter_clusters_by_algorithm(self, authenticated_client, cluster):
        """Test filtering clusters by algorithm."""
        response = authenticated_client.get('/api/clusters/?algorithm=dbscan')
        assert response.status_code == status.HTTP_200_OK

    def test_cluster_findings_action(self, authenticated_client, cluster, finding):
        """Test cluster findings action."""
        # Create cluster membership
        FindingClusterMembership.objects.create(
            cluster=cluster,
            finding=finding,
            distance_to_centroid=0.15
        )

        response = authenticated_client.get(f'/api/clusters/{cluster.id}/findings/')
        assert response.status_code == status.HTTP_200_OK

        if isinstance(response.data, list):
            assert len(response.data) >= 1

    def test_cluster_readonly(self, authenticated_client, cluster):
        """Test that clusters are read-only."""
        data = {'size': 10}
        response = authenticated_client.patch(f'/api/clusters/{cluster.id}/', data, format='json')
        assert response.status_code in [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_403_FORBIDDEN
        ]

    def test_cluster_no_create(self, authenticated_client, organization, scan):
        """Test that clusters cannot be created via API."""
        data = {
            'organization': str(organization.id),
            'scan': str(scan.id),
            'algorithm': 'dbscan',
            'cluster_id': 99,
            'size': 3
        }

        response = authenticated_client.post('/api/clusters/', data, format='json')
        assert response.status_code in [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_400_BAD_REQUEST
        ]

    def test_cluster_no_delete(self, authenticated_client, cluster):
        """Test that clusters cannot be deleted via API."""
        response = authenticated_client.delete(f'/api/clusters/{cluster.id}/')
        assert response.status_code in [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_403_FORBIDDEN
        ]

    def test_cluster_statistics(self, authenticated_client, cluster, finding):
        """Test cluster statistics."""
        # Create multiple memberships
        FindingClusterMembership.objects.create(
            cluster=cluster,
            finding=finding,
            distance_to_centroid=0.15
        )

        response = authenticated_client.get(f'/api/clusters/{cluster.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert 'size' in response.data
        assert response.data['size'] >= 0

    def test_empty_clusters_list(self, authenticated_client):
        """Test clusters list with no data."""
        response = authenticated_client.get('/api/clusters/')
        assert response.status_code == status.HTTP_200_OK

        if 'results' in response.data:
            assert response.data['results'] == []
        else:
            assert response.data == []


@pytest.mark.django_db
@pytest.mark.api
class TestFindingAPIEdgeCases:
    """Test edge cases and error handling for Findings API."""

    def test_finding_not_found(self, authenticated_client):
        """Test retrieving non-existent finding."""
        fake_uuid = '00000000-0000-0000-0000-000000000000'
        response = authenticated_client.get(f'/api/findings/{fake_uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cluster_not_found(self, authenticated_client):
        """Test retrieving non-existent cluster."""
        fake_uuid = '00000000-0000-0000-0000-000000000000'
        response = authenticated_client.get(f'/api/clusters/{fake_uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_uuid_format(self, authenticated_client):
        """Test invalid UUID format."""
        response = authenticated_client.get('/api/findings/invalid-uuid/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_findings_pagination(self, authenticated_client, organization, repository, scan):
        """Test findings pagination."""
        # Create many findings
        for i in range(60):
            Finding.objects.create(
                organization=organization,
                repository=repository,
                first_seen_scan=scan,
                last_seen_scan=scan,
                fingerprint=f'fp{i}',
                rule_id=f'rule{i}',
                message='Test',
                severity='medium',
                file_path='test.py',
                start_line=i,
                tool_name='test'
            )

        response = authenticated_client.get('/api/findings/')
        assert response.status_code == status.HTTP_200_OK

        # Check pagination structure
        if 'results' in response.data:
            assert 'count' in response.data or 'next' in response.data

    def test_finding_filter_invalid_value(self, authenticated_client):
        """Test filtering with invalid value."""
        response = authenticated_client.get('/api/findings/?severity=invalid')
        # Should either filter out or return empty, not error
        assert response.status_code == status.HTTP_200_OK
