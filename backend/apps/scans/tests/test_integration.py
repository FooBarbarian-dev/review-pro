"""
Integration tests for end-to-end scan workflows.
"""
import pytest
from unittest.mock import patch, AsyncMock, Mock
from rest_framework import status
from apps.scans.models import Scan
from apps.findings.models import Finding, LLMVerdict
from apps.organizations.models import Repository, Branch


@pytest.mark.django_db
@pytest.mark.integration
class TestScanWorkflowIntegration:
    """Integration tests for complete scan workflows."""

    @patch('services.temporal_client.TemporalService.trigger_scan_workflow')
    def test_create_scan_end_to_end(self, mock_workflow, authenticated_client, organization, repository, branch):
        """Test creating a scan triggers workflow and creates database record."""
        mock_workflow.return_value = {
            'workflow_id': 'scan-123',
            'run_id': 'run-456',
            'status': 'started'
        }

        data = {
            'organization': str(organization.id),
            'repository': str(repository.id),
            'branch': str(branch.id),
            'commit_sha': 'integration123'
        }

        # Create scan
        response = authenticated_client.post('/api/scans/', data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'workflow' in response.data

        # Verify scan in database
        scan = Scan.objects.get(commit_sha='integration123')
        assert scan.status == 'queued'
        assert scan.organization == organization
        assert scan.repository == repository

        # Verify workflow was triggered
        mock_workflow.assert_called_once()

    @patch('services.temporal_client.TemporalService.trigger_adjudication_workflow')
    def test_scan_to_adjudication_workflow(self, mock_workflow, authenticated_client, scan):
        """Test complete flow from scan creation to LLM adjudication."""
        # Mark scan as completed
        scan.status = 'completed'
        scan.save()

        # Create findings
        finding1 = Finding.objects.create(
            organization=scan.organization,
            repository=scan.repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='fp1',
            rule_id='sql-injection',
            message='SQL injection found',
            severity='high',
            file_path='api/db.py',
            start_line=42,
            tool_name='bandit'
        )

        finding2 = Finding.objects.create(
            organization=scan.organization,
            repository=scan.repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='fp2',
            rule_id='xss',
            message='XSS vulnerability',
            severity='medium',
            file_path='templates/view.html',
            start_line=15,
            tool_name='semgrep'
        )

        # Trigger adjudication
        mock_workflow.return_value = {
            'workflow_id': 'adjudicate-123',
            'run_id': 'run-789',
            'status': 'started'
        }

        response = authenticated_client.post(
            f'/api/scans/{scan.id}/adjudicate/',
            {
                'provider': 'openai',
                'model': 'gpt-4o',
                'pattern': 'post_processing',
                'max_findings': 100
            },
            format='json'
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        mock_workflow.assert_called_once()

        # Simulate LLM verdicts being added
        LLMVerdict.objects.create(
            finding=finding1,
            verdict='true_positive',
            confidence=0.95,
            reasoning='Confirmed SQL injection',
            llm_provider='openai',
            llm_model='gpt-4o',
            prompt_tokens=500,
            completion_tokens=200,
            total_tokens=700
        )

        LLMVerdict.objects.create(
            finding=finding2,
            verdict='false_positive',
            confidence=0.88,
            reasoning='Output is escaped',
            llm_provider='openai',
            llm_model='gpt-4o',
            prompt_tokens=450,
            completion_tokens=180,
            total_tokens=630
        )

        # Verify verdicts
        assert finding1.llm_verdicts.count() == 1
        assert finding2.llm_verdicts.count() == 1

        verdict1 = finding1.llm_verdicts.first()
        assert verdict1.verdict == 'true_positive'
        assert verdict1.confidence == 0.95

    @patch('services.temporal_client.TemporalService.trigger_clustering_workflow')
    def test_scan_to_clustering_workflow(self, mock_workflow, authenticated_client, scan):
        """Test complete flow from scan to semantic clustering."""
        scan.status = 'completed'
        scan.save()

        # Create multiple similar findings
        for i in range(5):
            Finding.objects.create(
                organization=scan.organization,
                repository=scan.repository,
                first_seen_scan=scan,
                last_seen_scan=scan,
                fingerprint=f'fp-cluster-{i}',
                rule_id='sql-injection',
                message=f'SQL injection variant {i}',
                severity='high',
                file_path=f'api/controller{i}.py',
                start_line=10 + i,
                tool_name='bandit'
            )

        mock_workflow.return_value = {
            'workflow_id': 'cluster-123',
            'run_id': 'run-abc',
            'status': 'started'
        }

        response = authenticated_client.post(
            f'/api/scans/{scan.id}/cluster/',
            {
                'algorithm': 'dbscan',
                'threshold': 0.85
            },
            format='json'
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        mock_workflow.assert_called_once()

        # Verify findings are available for clustering
        findings = Finding.objects.filter(last_seen_scan=scan)
        assert findings.count() == 5

    @patch('services.temporal_client.TemporalService.trigger_scan_workflow')
    def test_rescan_workflow(self, mock_workflow, authenticated_client, scan):
        """Test rescan creates new scan instance and triggers workflow."""
        original_scan_count = Scan.objects.count()

        mock_workflow.return_value = {
            'workflow_id': 'rescan-123',
            'run_id': 'run-def',
            'status': 'started'
        }

        response = authenticated_client.post(f'/api/scans/{scan.id}/rescan/', format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['original_scan_id'] == str(scan.id)

        # Verify new scan was created
        assert Scan.objects.count() == original_scan_count + 1

        new_scan = Scan.objects.latest('created_at')
        assert new_scan.commit_sha == scan.commit_sha
        assert new_scan.repository == scan.repository
        assert new_scan.branch == scan.branch
        assert new_scan.id != scan.id

    def test_finding_deduplication_across_scans(self, organization, repository, branch, user):
        """Test that findings with same fingerprint are deduplicated."""
        # First scan
        scan1 = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='scan1',
            triggered_by=user
        )

        fingerprint = Finding.generate_fingerprint(
            organization.id, 'rule-1', 'file.py', 10, 5, 'Test message'
        )

        finding1 = Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan1,
            last_seen_scan=scan1,
            fingerprint=fingerprint,
            rule_id='rule-1',
            message='Test message',
            severity='high',
            file_path='file.py',
            start_line=10,
            start_column=5,
            tool_name='test'
        )

        assert finding1.occurrence_count == 1

        # Second scan with same finding
        scan2 = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='scan2',
            triggered_by=user
        )

        # Simulate finding same issue
        finding1.update_occurrence(scan2)

        assert finding1.occurrence_count == 2
        assert finding1.last_seen_scan == scan2
        assert finding1.first_seen_scan == scan1

    @patch('services.temporal_client.TemporalService.trigger_pattern_comparison_workflow')
    def test_pattern_comparison_workflow(self, mock_workflow, authenticated_client, scan):
        """Test pattern comparison workflow."""
        scan.status = 'completed'
        scan.save()

        mock_workflow.return_value = {
            'workflow_id': 'compare-123',
            'run_id': 'run-xyz',
            'status': 'started'
        }

        response = authenticated_client.post(
            f'/api/scans/{scan.id}/compare_patterns/',
            format='json'
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert 'workflow_id' in response.data
        mock_workflow.assert_called_once()


@pytest.mark.django_db
@pytest.mark.integration
class TestFindingLifecycle:
    """Integration tests for finding lifecycle from creation to resolution."""

    def test_finding_status_transitions(self, organization, repository, scan, user):
        """Test complete finding status lifecycle."""
        from apps.findings.models import FindingStatusHistory

        finding = Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='lifecycle-test',
            rule_id='test/rule',
            message='Test finding',
            severity='high',
            status='open',
            file_path='test.py',
            start_line=1,
            tool_name='test'
        )

        assert finding.status == 'open'

        # Mark as false positive
        FindingStatusHistory.objects.create(
            finding=finding,
            changed_by=user,
            old_status='open',
            new_status='false_positive',
            reason='Confirmed by manual review'
        )

        finding.status = 'false_positive'
        finding.save()

        assert finding.status == 'false_positive'
        assert finding.status_history.count() == 1

        history = finding.status_history.first()
        assert history.old_status == 'open'
        assert history.new_status == 'false_positive'
        assert history.changed_by == user

    def test_finding_with_multiple_llm_verdicts(self, organization, repository, scan):
        """Test finding can have multiple LLM verdicts from different models."""
        finding = Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='multi-verdict',
            rule_id='test/rule',
            message='Test',
            severity='high',
            file_path='test.py',
            start_line=1,
            tool_name='test'
        )

        # GPT-4 verdict
        LLMVerdict.objects.create(
            finding=finding,
            verdict='true_positive',
            confidence=0.92,
            reasoning='GPT-4 analysis',
            llm_provider='openai',
            llm_model='gpt-4o',
            prompt_tokens=500,
            completion_tokens=200,
            total_tokens=700
        )

        # Claude verdict
        LLMVerdict.objects.create(
            finding=finding,
            verdict='false_positive',
            confidence=0.88,
            reasoning='Claude analysis',
            llm_provider='anthropic',
            llm_model='claude-3-opus',
            prompt_tokens=550,
            completion_tokens=220,
            total_tokens=770
        )

        # Gemini verdict
        LLMVerdict.objects.create(
            finding=finding,
            verdict='uncertain',
            confidence=0.65,
            reasoning='Gemini analysis',
            llm_provider='google',
            llm_model='gemini-pro',
            prompt_tokens=480,
            completion_tokens=190,
            total_tokens=670
        )

        assert finding.llm_verdicts.count() == 3

        # Verify different providers
        providers = set(finding.llm_verdicts.values_list('llm_provider', flat=True))
        assert providers == {'openai', 'anthropic', 'google'}


@pytest.mark.django_db
@pytest.mark.integration
class TestDashboardIntegration:
    """Integration tests for dashboard with real data."""

    def test_dashboard_with_complete_data(self, authenticated_client, organization, repository, branch, user):
        """Test dashboard statistics with complete scan and finding data."""
        # Create multiple scans
        scan1 = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='dash1',
            status='completed',
            triggered_by=user
        )

        scan2 = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='dash2',
            status='running',
            triggered_by=user
        )

        # Create findings with different severities
        Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan1,
            last_seen_scan=scan1,
            fingerprint='dash-fp1',
            rule_id='critical-1',
            message='Critical issue',
            severity='critical',
            status='open',
            file_path='critical.py',
            start_line=1,
            tool_name='bandit'
        )

        Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan1,
            last_seen_scan=scan1,
            fingerprint='dash-fp2',
            rule_id='high-1',
            message='High issue',
            severity='high',
            status='false_positive',
            file_path='high.py',
            start_line=1,
            tool_name='semgrep'
        )

        Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan1,
            last_seen_scan=scan1,
            fingerprint='dash-fp3',
            rule_id='medium-1',
            message='Medium issue',
            severity='medium',
            status='open',
            file_path='medium.py',
            start_line=1,
            tool_name='eslint'
        )

        # Get dashboard stats
        response = authenticated_client.get('/api/dashboard/stats/')

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert data['total_scans'] >= 2
        assert data['total_findings'] >= 3
        assert data['open_findings'] >= 2
        assert data['false_positives'] >= 1

        # Verify aggregations
        if 'findings_by_severity' in data:
            severity_data = data['findings_by_severity']
            assert 'critical' in str(severity_data) or len(severity_data) > 0

    def test_api_filtering_and_pagination(self, authenticated_client, organization, repository, scan):
        """Test API filtering works across multiple findings."""
        # Create 25 findings
        for i in range(25):
            Finding.objects.create(
                organization=organization,
                repository=repository,
                first_seen_scan=scan,
                last_seen_scan=scan,
                fingerprint=f'filter-test-{i}',
                rule_id=f'rule-{i}',
                message='Test',
                severity='high' if i % 2 == 0 else 'low',
                status='open' if i % 3 == 0 else 'false_positive',
                file_path='test.py',
                start_line=i,
                tool_name='bandit' if i % 2 == 0 else 'semgrep'
            )

        # Test filtering by severity
        response = authenticated_client.get('/api/findings/?severity=high')
        assert response.status_code == status.HTTP_200_OK

        # Test filtering by status
        response = authenticated_client.get('/api/findings/?status=open')
        assert response.status_code == status.HTTP_200_OK

        # Test filtering by tool
        response = authenticated_client.get('/api/findings/?tool_name=bandit')
        assert response.status_code == status.HTTP_200_OK

        # Test pagination
        response = authenticated_client.get('/api/findings/')
        assert response.status_code == status.HTTP_200_OK
        if 'results' in response.data:
            assert 'next' in response.data or 'count' in response.data
