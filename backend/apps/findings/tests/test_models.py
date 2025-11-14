"""
Tests for Finding models.
"""
import pytest
import uuid
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.findings.models import (
    Finding, FindingComment, FindingStatusHistory, LLMVerdict,
    FindingCluster, FindingClusterMembership
)
from apps.scans.models import Scan
from apps.organizations.models import Organization, Repository, Branch

User = get_user_model()


@pytest.fixture
def repository(organization):
    """Create test repository."""
    return Repository.objects.create(
        organization=organization,
        name='test-repo',
        full_name='test-org/test-repo',
        github_repo_id='123456'
    )


@pytest.fixture
def branch(repository):
    """Create test branch."""
    return Branch.objects.create(
        repository=repository,
        name='main',
        sha='abc123'
    )


@pytest.fixture
def scan(organization, repository, branch, user):
    """Create test scan."""
    return Scan.objects.create(
        organization=organization,
        repository=repository,
        branch=branch,
        commit_sha='abc123',
        triggered_by=user
    )


@pytest.mark.django_db
@pytest.mark.unit
class TestFindingModel:
    """Test suite for Finding model."""

    def test_create_finding(self, organization, repository, scan):
        """Test creating a basic finding."""
        finding = Finding.objects.create(
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

        assert finding.id is not None
        assert isinstance(finding.id, uuid.UUID)
        assert finding.organization == organization
        assert finding.repository == repository
        assert finding.severity == 'high'
        assert finding.status == 'open'  # default
        assert finding.occurrence_count == 1  # default

    def test_finding_severity_choices(self, organization, repository, scan):
        """Test all valid severity choices."""
        severities = ['critical', 'high', 'medium', 'low', 'info']

        for severity in severities:
            finding = Finding.objects.create(
                organization=organization,
                repository=repository,
                first_seen_scan=scan,
                last_seen_scan=scan,
                fingerprint=f'fp-{severity}',
                rule_id=f'rule-{severity}',
                message='Test',
                severity=severity,
                file_path='test.py',
                start_line=1,
                tool_name='test'
            )
            assert finding.severity == severity

    def test_finding_status_choices(self, organization, repository, scan):
        """Test all valid status choices."""
        statuses = ['open', 'fixed', 'false_positive', 'accepted_risk', 'wont_fix']

        for status in statuses:
            finding = Finding.objects.create(
                organization=organization,
                repository=repository,
                first_seen_scan=scan,
                last_seen_scan=scan,
                fingerprint=f'fp-{status}',
                rule_id=f'rule-{status}',
                message='Test',
                severity='high',
                file_path='test.py',
                start_line=1,
                tool_name='test',
                status=status
            )
            assert finding.status == status

    def test_finding_generate_fingerprint(self):
        """Test fingerprint generation."""
        org_id = uuid.uuid4()
        fingerprint = Finding.generate_fingerprint(
            organization_id=org_id,
            rule_id='test/rule-1',
            file_path='src/main.py',
            start_line=10,
            start_column=5,
            message='SQL injection detected'
        )

        assert fingerprint is not None
        assert len(fingerprint) == 64  # SHA256 hex length
        assert isinstance(fingerprint, str)

        # Test deterministic nature
        fingerprint2 = Finding.generate_fingerprint(
            organization_id=org_id,
            rule_id='test/rule-1',
            file_path='src/main.py',
            start_line=10,
            start_column=5,
            message='SQL injection detected'
        )

        assert fingerprint == fingerprint2

    def test_finding_str_method(self, organization, repository, scan):
        """Test finding string representation."""
        finding = Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='test123',
            rule_id='bandit/B101',
            message='Test',
            severity='high',
            file_path='src/app.py',
            start_line=42,
            tool_name='bandit'
        )

        assert 'bandit/B101' in str(finding)
        assert 'src/app.py' in str(finding)
        assert '42' in str(finding)

    def test_finding_update_occurrence(self, organization, repository, scan, branch, user):
        """Test updating finding occurrence count."""
        finding = Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='test123',
            rule_id='test/rule',
            message='Test',
            severity='high',
            file_path='test.py',
            start_line=1,
            tool_name='test'
        )

        assert finding.occurrence_count == 1

        # Create new scan
        new_scan = Scan.objects.create(
            organization=organization,
            repository=repository,
            branch=branch,
            commit_sha='def456',
            triggered_by=user
        )

        # Update occurrence
        finding.update_occurrence(new_scan)

        assert finding.occurrence_count == 2
        assert finding.last_seen_scan == new_scan

    def test_finding_cwe_cve_fields(self, organization, repository, scan):
        """Test CWE and CVE JSON fields."""
        finding = Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='test123',
            rule_id='test/rule',
            message='Test',
            severity='high',
            file_path='test.py',
            start_line=1,
            tool_name='test',
            cwe_ids=['CWE-89', 'CWE-79'],
            cve_ids=['CVE-2023-1234']
        )

        assert finding.cwe_ids == ['CWE-89', 'CWE-79']
        assert finding.cve_ids == ['CVE-2023-1234']
        assert 'CWE-89' in finding.cwe_ids

    def test_finding_unique_constraint(self, organization, repository, scan):
        """Test that fingerprint is unique per organization."""
        Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='unique-fp-123',
            rule_id='test/rule',
            message='Test',
            severity='high',
            file_path='test.py',
            start_line=1,
            tool_name='test'
        )

        # Attempt to create duplicate should raise error
        with pytest.raises(Exception):  # IntegrityError
            Finding.objects.create(
                organization=organization,
                repository=repository,
                first_seen_scan=scan,
                last_seen_scan=scan,
                fingerprint='unique-fp-123',
                rule_id='test/rule',
                message='Test',
                severity='high',
                file_path='test.py',
                start_line=1,
                tool_name='test'
            )

    def test_finding_sarif_data(self, organization, repository, scan):
        """Test SARIF data JSON field."""
        sarif_data = {
            'level': 'warning',
            'ruleIndex': 0,
            'message': {'text': 'Test message'}
        }

        finding = Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='test123',
            rule_id='test/rule',
            message='Test',
            severity='high',
            file_path='test.py',
            start_line=1,
            tool_name='test',
            sarif_data=sarif_data
        )

        assert finding.sarif_data == sarif_data
        assert finding.sarif_data['level'] == 'warning'


@pytest.mark.django_db
@pytest.mark.unit
class TestFindingComment:
    """Test suite for FindingComment model."""

    @pytest.fixture
    def finding(self, organization, repository, scan):
        """Create test finding."""
        return Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='test123',
            rule_id='test/rule',
            message='Test',
            severity='high',
            file_path='test.py',
            start_line=1,
            tool_name='test'
        )

    def test_create_comment(self, finding, user):
        """Test creating a finding comment."""
        comment = FindingComment.objects.create(
            finding=finding,
            author=user,
            content='This is a false positive'
        )

        assert comment.id is not None
        assert comment.finding == finding
        assert comment.author == user
        assert comment.content == 'This is a false positive'

    def test_comment_str_method(self, finding, user):
        """Test comment string representation."""
        comment = FindingComment.objects.create(
            finding=finding,
            author=user,
            content='Test comment'
        )

        assert user.email in str(comment)
        assert finding.rule_id in str(comment)

    def test_comment_ordering(self, finding, user):
        """Test comments are ordered by creation time."""
        comment1 = FindingComment.objects.create(
            finding=finding,
            author=user,
            content='First comment'
        )
        comment2 = FindingComment.objects.create(
            finding=finding,
            author=user,
            content='Second comment'
        )

        comments = FindingComment.objects.filter(finding=finding)
        assert list(comments) == [comment1, comment2]


@pytest.mark.django_db
@pytest.mark.unit
class TestFindingStatusHistory:
    """Test suite for FindingStatusHistory model."""

    @pytest.fixture
    def finding(self, organization, repository, scan):
        """Create test finding."""
        return Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='test123',
            rule_id='test/rule',
            message='Test',
            severity='high',
            file_path='test.py',
            start_line=1,
            tool_name='test'
        )

    def test_create_status_history(self, finding, user):
        """Test creating status history entry."""
        history = FindingStatusHistory.objects.create(
            finding=finding,
            changed_by=user,
            old_status='open',
            new_status='false_positive',
            reason='Verified as FP by manual review'
        )

        assert history.id is not None
        assert history.finding == finding
        assert history.changed_by == user
        assert history.old_status == 'open'
        assert history.new_status == 'false_positive'
        assert history.reason == 'Verified as FP by manual review'

    def test_status_history_str_method(self, finding, user):
        """Test status history string representation."""
        history = FindingStatusHistory.objects.create(
            finding=finding,
            changed_by=user,
            old_status='open',
            new_status='fixed'
        )

        assert 'open' in str(history)
        assert 'fixed' in str(history)
        assert user.email in str(history)

    def test_status_history_ordering(self, finding, user):
        """Test status history is ordered newest first."""
        history1 = FindingStatusHistory.objects.create(
            finding=finding,
            changed_by=user,
            old_status='open',
            new_status='wont_fix'
        )
        history2 = FindingStatusHistory.objects.create(
            finding=finding,
            changed_by=user,
            old_status='wont_fix',
            new_status='fixed'
        )

        histories = FindingStatusHistory.objects.filter(finding=finding)
        # Should be newest first
        assert list(histories) == [history2, history1]


@pytest.mark.django_db
@pytest.mark.unit
class TestLLMVerdict:
    """Test suite for LLMVerdict model."""

    @pytest.fixture
    def finding(self, organization, repository, scan):
        """Create test finding."""
        return Finding.objects.create(
            organization=organization,
            repository=repository,
            first_seen_scan=scan,
            last_seen_scan=scan,
            fingerprint='test123',
            rule_id='test/rule',
            message='Test',
            severity='high',
            file_path='test.py',
            start_line=1,
            tool_name='test'
        )

    def test_create_llm_verdict(self, finding):
        """Test creating an LLM verdict."""
        verdict = LLMVerdict.objects.create(
            finding=finding,
            verdict='false_positive',
            confidence=0.92,
            reasoning='Input is validated upstream',
            cwe_id='CWE-89',
            recommendation='No action needed',
            llm_provider='openai',
            llm_model='gpt-4o',
            agent_pattern='post_processing',
            prompt_tokens=500,
            completion_tokens=100,
            total_tokens=600,
            estimated_cost_usd=0.015,
            processing_time_ms=1500
        )

        assert verdict.id is not None
        assert verdict.finding == finding
        assert verdict.verdict == 'false_positive'
        assert verdict.confidence == 0.92
        assert verdict.cwe_id == 'CWE-89'
        assert verdict.llm_provider == 'openai'
        assert verdict.llm_model == 'gpt-4o'

    def test_llm_verdict_choices(self, finding):
        """Test all valid verdict choices."""
        verdicts = ['true_positive', 'false_positive', 'uncertain']

        for verdict_type in verdicts:
            verdict = LLMVerdict.objects.create(
                finding=finding,
                verdict=verdict_type,
                confidence=0.8,
                reasoning='Test reasoning',
                llm_provider='openai',
                llm_model='gpt-4',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150
            )
            assert verdict.verdict == verdict_type

    def test_llm_verdict_agent_patterns(self, finding):
        """Test all valid agent pattern choices."""
        patterns = ['post_processing', 'interactive', 'multi_agent']

        for pattern in patterns:
            # Create unique finding for each test
            finding_instance = Finding.objects.create(
                organization=finding.organization,
                repository=finding.repository,
                first_seen_scan=finding.first_seen_scan,
                last_seen_scan=finding.last_seen_scan,
                fingerprint=f'fp-{pattern}',
                rule_id='test/rule',
                message='Test',
                severity='high',
                file_path='test.py',
                start_line=1,
                tool_name='test'
            )

            verdict = LLMVerdict.objects.create(
                finding=finding_instance,
                verdict='true_positive',
                confidence=0.8,
                reasoning='Test',
                llm_provider='openai',
                llm_model='gpt-4',
                agent_pattern=pattern,
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150
            )
            assert verdict.agent_pattern == pattern

    def test_llm_verdict_cost_tracking(self, finding):
        """Test cost and token tracking fields."""
        verdict = LLMVerdict.objects.create(
            finding=finding,
            verdict='true_positive',
            confidence=0.95,
            reasoning='Test',
            llm_provider='anthropic',
            llm_model='claude-3-opus',
            prompt_tokens=1200,
            completion_tokens=400,
            total_tokens=1600,
            estimated_cost_usd=0.048,
            processing_time_ms=2500
        )

        assert verdict.prompt_tokens == 1200
        assert verdict.completion_tokens == 400
        assert verdict.total_tokens == 1600
        assert verdict.estimated_cost_usd == 0.048
        assert verdict.processing_time_ms == 2500

    def test_llm_verdict_multiple_per_finding(self, finding):
        """Test that a finding can have multiple LLM verdicts."""
        verdict1 = LLMVerdict.objects.create(
            finding=finding,
            verdict='false_positive',
            confidence=0.7,
            reasoning='Test 1',
            llm_provider='openai',
            llm_model='gpt-4',
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )

        verdict2 = LLMVerdict.objects.create(
            finding=finding,
            verdict='true_positive',
            confidence=0.9,
            reasoning='Test 2',
            llm_provider='anthropic',
            llm_model='claude-3-opus',
            prompt_tokens=120,
            completion_tokens=60,
            total_tokens=180
        )

        verdicts = finding.llm_verdicts.all()
        assert verdicts.count() == 2
        assert verdict1 in verdicts
        assert verdict2 in verdicts


@pytest.mark.django_db
@pytest.mark.unit
class TestFindingCluster:
    """Test suite for FindingCluster model."""

    def test_create_cluster(self, organization, scan):
        """Test creating a finding cluster."""
        cluster = FindingCluster.objects.create(
            organization=organization,
            scan=scan,
            algorithm='dbscan',
            cluster_id=1,
            size=5,
            centroid_embedding=[0.1, 0.2, 0.3]
        )

        assert cluster.id is not None
        assert cluster.organization == organization
        assert cluster.scan == scan
        assert cluster.algorithm == 'dbscan'
        assert cluster.cluster_id == 1
        assert cluster.size == 5
        assert cluster.centroid_embedding == [0.1, 0.2, 0.3]

    def test_cluster_algorithms(self, organization, scan):
        """Test all valid clustering algorithms."""
        algorithms = ['dbscan', 'agglomerative', 'kmeans']

        for algorithm in algorithms:
            cluster = FindingCluster.objects.create(
                organization=organization,
                scan=scan,
                algorithm=algorithm,
                cluster_id=1,
                size=3
            )
            assert cluster.algorithm == algorithm


@pytest.mark.django_db
@pytest.mark.unit
class TestFindingClusterMembership:
    """Test suite for FindingClusterMembership model."""

    @pytest.fixture
    def cluster(self, organization, scan):
        """Create test cluster."""
        return FindingCluster.objects.create(
            organization=organization,
            scan=scan,
            algorithm='dbscan',
            cluster_id=1,
            size=2
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
            rule_id='test/rule',
            message='Test',
            severity='high',
            file_path='test.py',
            start_line=1,
            tool_name='test'
        )

    def test_create_cluster_membership(self, cluster, finding):
        """Test creating cluster membership."""
        membership = FindingClusterMembership.objects.create(
            cluster=cluster,
            finding=finding,
            distance_to_centroid=0.15,
            embedding_vector=[0.2, 0.3, 0.4]
        )

        assert membership.id is not None
        assert membership.cluster == cluster
        assert membership.finding == finding
        assert membership.distance_to_centroid == 0.15
        assert membership.embedding_vector == [0.2, 0.3, 0.4]

    def test_cluster_membership_relationships(self, cluster, finding):
        """Test relationships between clusters and findings."""
        membership = FindingClusterMembership.objects.create(
            cluster=cluster,
            finding=finding,
            distance_to_centroid=0.1
        )

        # Test forward relationship
        assert membership in cluster.members.all()

        # Test reverse relationship
        assert membership in finding.cluster_memberships.all()
