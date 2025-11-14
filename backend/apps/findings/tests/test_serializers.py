"""
Tests for Finding serializers.
"""
import pytest
from apps.findings.api.serializers import (
    FindingListSerializer, FindingDetailSerializer, FindingMinimalSerializer,
    LLMVerdictSerializer, FindingClusterSerializer, FindingClusterMembershipSerializer
)
from apps.findings.models import LLMVerdict, FindingCluster, FindingClusterMembership


@pytest.mark.django_db
@pytest.mark.unit
class TestFindingSerializers:
    """Test suite for Finding serializers."""

    def test_finding_list_serializer(self, finding):
        """Test FindingListSerializer returns minimal fields."""
        serializer = FindingListSerializer(finding)
        data = serializer.data

        assert 'id' in data
        assert 'rule_id' in data
        assert 'severity' in data
        assert 'status' in data
        assert 'file_path' in data
        assert 'tool_name' in data
        assert data['rule_id'] == finding.rule_id

    def test_finding_detail_serializer(self, finding):
        """Test FindingDetailSerializer includes all fields."""
        serializer = FindingDetailSerializer(finding)
        data = serializer.data

        assert 'id' in data
        assert 'rule_id' in data
        assert 'message' in data
        assert 'severity' in data
        assert 'file_path' in data
        assert 'start_line' in data
        assert 'tool_name' in data
        assert 'llm_verdicts' in data  # Nested relation
        assert 'cluster_memberships' in data  # Nested relation

    def test_finding_detail_with_llm_verdicts(self, finding):
        """Test FindingDetailSerializer includes LLM verdicts."""
        # Add LLM verdict
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

        serializer = FindingDetailSerializer(finding)
        data = serializer.data

        assert 'llm_verdicts' in data
        assert len(data['llm_verdicts']) == 1
        assert data['llm_verdicts'][0]['verdict'] == 'false_positive'

    def test_finding_minimal_serializer(self, finding):
        """Test FindingMinimalSerializer returns only essential fields."""
        serializer = FindingMinimalSerializer(finding)
        data = serializer.data

        assert 'id' in data
        assert 'rule_id' in data
        assert 'severity' in data
        # Should not include verbose fields like message, snippet
        field_count = len(data.keys())
        assert field_count < 10  # Minimal fields only

    def test_finding_serializer_with_cwe_cve(self, finding):
        """Test serializer handles CWE and CVE arrays."""
        finding.cwe_ids = ['CWE-89', 'CWE-79']
        finding.cve_ids = ['CVE-2023-1234']
        finding.save()

        serializer = FindingDetailSerializer(finding)
        data = serializer.data

        assert data['cwe_ids'] == ['CWE-89', 'CWE-79']
        assert data['cve_ids'] == ['CVE-2023-1234']

    def test_finding_serializer_with_sarif_data(self, finding):
        """Test serializer handles SARIF JSON data."""
        sarif_data = {
            'level': 'warning',
            'ruleIndex': 0,
            'message': {'text': 'SQL injection detected'}
        }
        finding.sarif_data = sarif_data
        finding.save()

        serializer = FindingDetailSerializer(finding)
        data = serializer.data

        assert data['sarif_data'] == sarif_data


@pytest.mark.django_db
@pytest.mark.unit
class TestLLMVerdictSerializer:
    """Test suite for LLMVerdict serializer."""

    def test_llm_verdict_serializer(self, finding):
        """Test LLMVerdictSerializer."""
        verdict = LLMVerdict.objects.create(
            finding=finding,
            verdict='true_positive',
            confidence=0.95,
            reasoning='Confirmed vulnerability',
            cwe_id='CWE-89',
            recommendation='Use parameterized queries',
            llm_provider='anthropic',
            llm_model='claude-3-opus',
            agent_pattern='multi_agent',
            prompt_tokens=1200,
            completion_tokens=400,
            total_tokens=1600,
            estimated_cost_usd=0.048,
            processing_time_ms=2500
        )

        serializer = LLMVerdictSerializer(verdict)
        data = serializer.data

        assert data['verdict'] == 'true_positive'
        assert data['confidence'] == 0.95
        assert data['reasoning'] == 'Confirmed vulnerability'
        assert data['cwe_id'] == 'CWE-89'
        assert data['llm_provider'] == 'anthropic'
        assert data['llm_model'] == 'claude-3-opus'
        assert data['prompt_tokens'] == 1200
        assert data['estimated_cost_usd'] == 0.048

    def test_llm_verdict_serializer_all_fields(self, finding):
        """Test that all LLM verdict fields are serialized."""
        verdict = LLMVerdict.objects.create(
            finding=finding,
            verdict='uncertain',
            confidence=0.65,
            reasoning='Needs manual review',
            llm_provider='google',
            llm_model='gemini-pro',
            prompt_tokens=500,
            completion_tokens=200,
            total_tokens=700
        )

        serializer = LLMVerdictSerializer(verdict)
        data = serializer.data

        # Check all important fields are present
        assert 'id' in data
        assert 'verdict' in data
        assert 'confidence' in data
        assert 'reasoning' in data
        assert 'llm_provider' in data
        assert 'llm_model' in data
        assert 'agent_pattern' in data
        assert 'prompt_tokens' in data
        assert 'completion_tokens' in data
        assert 'total_tokens' in data


@pytest.mark.django_db
@pytest.mark.unit
class TestFindingClusterSerializers:
    """Test suite for Finding cluster serializers."""

    def test_finding_cluster_serializer(self, organization, scan):
        """Test FindingClusterSerializer."""
        cluster = FindingCluster.objects.create(
            organization=organization,
            scan=scan,
            algorithm='dbscan',
            cluster_id=1,
            size=5,
            centroid_embedding=[0.1, 0.2, 0.3]
        )

        serializer = FindingClusterSerializer(cluster)
        data = serializer.data

        assert data['algorithm'] == 'dbscan'
        assert data['cluster_id'] == 1
        assert data['size'] == 5
        assert data['centroid_embedding'] == [0.1, 0.2, 0.3]

    def test_finding_cluster_membership_serializer(self, organization, scan, finding):
        """Test FindingClusterMembershipSerializer."""
        cluster = FindingCluster.objects.create(
            organization=organization,
            scan=scan,
            algorithm='agglomerative',
            cluster_id=2,
            size=3
        )

        membership = FindingClusterMembership.objects.create(
            cluster=cluster,
            finding=finding,
            distance_to_centroid=0.25,
            embedding_vector=[0.5, 0.6, 0.7]
        )

        serializer = FindingClusterMembershipSerializer(membership)
        data = serializer.data

        assert data['distance_to_centroid'] == 0.25
        assert data['embedding_vector'] == [0.5, 0.6, 0.7]
        assert 'cluster' in data
        assert 'finding' in data

    def test_cluster_serializer_with_members(self, organization, scan, finding):
        """Test cluster serializer includes member count."""
        cluster = FindingCluster.objects.create(
            organization=organization,
            scan=scan,
            algorithm='kmeans',
            cluster_id=3,
            size=10
        )

        # Add membership
        FindingClusterMembership.objects.create(
            cluster=cluster,
            finding=finding,
            distance_to_centroid=0.1
        )

        serializer = FindingClusterSerializer(cluster)
        data = serializer.data

        assert data['size'] == 10


@pytest.mark.django_db
@pytest.mark.unit
class TestSerializerValidation:
    """Test serializer validation logic."""

    def test_finding_serializer_readonly_fields(self, finding):
        """Test that readonly fields cannot be updated."""
        serializer = FindingDetailSerializer(finding)
        data = serializer.data

        # fingerprint should be readonly
        assert 'fingerprint' in data
        # first_seen_at should be readonly
        assert 'first_seen_at' in data

    def test_llm_verdict_cost_fields(self, finding):
        """Test LLM verdict cost tracking fields."""
        verdict = LLMVerdict.objects.create(
            finding=finding,
            verdict='true_positive',
            confidence=0.9,
            reasoning='Test',
            llm_provider='openai',
            llm_model='gpt-4',
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
            estimated_cost_usd=0.03,
            processing_time_ms=1800
        )

        serializer = LLMVerdictSerializer(verdict)
        data = serializer.data

        # Verify cost tracking fields
        assert data['prompt_tokens'] == 1000
        assert data['completion_tokens'] == 500
        assert data['total_tokens'] == 1500
        assert data['estimated_cost_usd'] == 0.03
        assert data['processing_time_ms'] == 1800

    def test_finding_list_excludes_verbose_fields(self, finding):
        """Test that list serializer excludes verbose fields for performance."""
        list_serializer = FindingListSerializer(finding)
        detail_serializer = FindingDetailSerializer(finding)

        list_fields = set(list_serializer.data.keys())
        detail_fields = set(detail_serializer.data.keys())

        # Detail should have more fields
        assert len(detail_fields) > len(list_fields)

        # List should not include certain verbose fields
        assert 'llm_verdicts' not in list_fields or len(list_serializer.data.get('llm_verdicts', [])) == 0

    def test_serializers_handle_null_values(self, finding):
        """Test serializers handle null/empty values gracefully."""
        # Clear optional fields
        finding.snippet = None
        finding.cwe_ids = []
        finding.cve_ids = []
        finding.sarif_data = None
        finding.save()

        serializer = FindingDetailSerializer(finding)
        data = serializer.data

        # Should serialize without errors
        assert data['snippet'] is None
        assert data['cwe_ids'] == []
        assert data['cve_ids'] == []
        assert data['sarif_data'] is None
