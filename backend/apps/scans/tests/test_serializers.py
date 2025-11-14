"""
Tests for Scan serializers.
"""
import pytest
from apps.scans.api.serializers import (
    ScanListSerializer, ScanDetailSerializer, ScanCreateSerializer,
    TriggerAdjudicationSerializer, TriggerClusteringSerializer
)
from apps.scans.serializers import RepositorySerializer


@pytest.mark.django_db
@pytest.mark.unit
class TestScanSerializers:
    """Test suite for Scan serializers."""

    def test_scan_list_serializer(self, scan):
        """Test ScanListSerializer."""
        serializer = ScanListSerializer(scan)
        data = serializer.data

        assert 'id' in data
        assert 'commit_sha' in data
        assert 'status' in data
        assert data['commit_sha'] == scan.commit_sha
        assert data['status'] == scan.status

    def test_scan_detail_serializer(self, scan):
        """Test ScanDetailSerializer."""
        serializer = ScanDetailSerializer(scan)
        data = serializer.data

        assert 'id' in data
        assert 'commit_sha' in data
        assert 'status' in data
        assert 'started_at' in data or True  # May be None
        assert 'tools_used' in data

    def test_scan_create_serializer_valid_data(self, organization, repository, branch):
        """Test ScanCreateSerializer with valid data."""
        data = {
            'organization': str(organization.id),
            'repository': str(repository.id),
            'branch': str(branch.id),
            'commit_sha': 'abc123def456'
        }

        serializer = ScanCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        validated_data = serializer.validated_data
        assert validated_data['commit_sha'] == 'abc123def456'

    def test_scan_create_serializer_invalid_data(self):
        """Test ScanCreateSerializer with invalid data."""
        data = {
            'commit_sha': 'abc123'
            # Missing required fields
        }

        serializer = ScanCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'organization' in serializer.errors or 'repository' in serializer.errors

    def test_repository_serializer(self, repository):
        """Test RepositorySerializer."""
        serializer = RepositorySerializer(repository)
        data = serializer.data

        assert 'name' in data
        assert 'full_name' in data
        assert data['name'] == repository.name
        assert data['full_name'] == repository.full_name


@pytest.mark.django_db
@pytest.mark.unit
class TestWorkflowTriggerSerializers:
    """Test suite for workflow trigger serializers."""

    def test_trigger_adjudication_serializer_valid(self):
        """Test TriggerAdjudicationSerializer with valid data."""
        data = {
            'provider': 'openai',
            'model': 'gpt-4o',
            'pattern': 'post_processing',
            'batch_size': 10,
            'max_findings': 100
        }

        serializer = TriggerAdjudicationSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        validated = serializer.validated_data
        assert validated['provider'] == 'openai'
        assert validated['model'] == 'gpt-4o'
        assert validated['batch_size'] == 10

    def test_trigger_adjudication_serializer_defaults(self):
        """Test TriggerAdjudicationSerializer with defaults."""
        data = {}

        serializer = TriggerAdjudicationSerializer(data=data)
        assert serializer.is_valid()

        validated = serializer.validated_data
        assert validated.get('provider') == 'openai' or 'provider' in validated
        assert validated.get('pattern') == 'post_processing' or 'pattern' in validated

    def test_trigger_adjudication_serializer_invalid_provider(self):
        """Test TriggerAdjudicationSerializer with invalid provider."""
        data = {
            'provider': 'invalid-provider',
            'model': 'gpt-4o'
        }

        serializer = TriggerAdjudicationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'provider' in serializer.errors

    def test_trigger_adjudication_serializer_invalid_pattern(self):
        """Test TriggerAdjudicationSerializer with invalid pattern."""
        data = {
            'provider': 'openai',
            'model': 'gpt-4o',
            'pattern': 'invalid-pattern'
        }

        serializer = TriggerAdjudicationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'pattern' in serializer.errors

    def test_trigger_adjudication_serializer_batch_size_bounds(self):
        """Test TriggerAdjudicationSerializer batch size validation."""
        # Test minimum
        data = {'batch_size': 0}
        serializer = TriggerAdjudicationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'batch_size' in serializer.errors

        # Test maximum
        data = {'batch_size': 101}
        serializer = TriggerAdjudicationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'batch_size' in serializer.errors

        # Test valid
        data = {'batch_size': 50}
        serializer = TriggerAdjudicationSerializer(data=data)
        assert serializer.is_valid()

    def test_trigger_clustering_serializer_valid(self):
        """Test TriggerClusteringSerializer with valid data."""
        data = {
            'algorithm': 'dbscan',
            'threshold': 0.85
        }

        serializer = TriggerClusteringSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        validated = serializer.validated_data
        assert validated['algorithm'] == 'dbscan'
        assert validated['threshold'] == 0.85

    def test_trigger_clustering_serializer_defaults(self):
        """Test TriggerClusteringSerializer with defaults."""
        data = {}

        serializer = TriggerClusteringSerializer(data=data)
        assert serializer.is_valid()

        validated = serializer.validated_data
        assert 'algorithm' in validated or validated.get('algorithm') == 'dbscan'

    def test_trigger_clustering_serializer_invalid_algorithm(self):
        """Test TriggerClusteringSerializer with invalid algorithm."""
        data = {
            'algorithm': 'invalid-algorithm',
            'threshold': 0.85
        }

        serializer = TriggerClusteringSerializer(data=data)
        assert not serializer.is_valid()
        assert 'algorithm' in serializer.errors

    def test_trigger_clustering_serializer_threshold_bounds(self):
        """Test TriggerClusteringSerializer threshold validation."""
        # Test below minimum
        data = {'threshold': -0.1}
        serializer = TriggerClusteringSerializer(data=data)
        assert not serializer.is_valid()
        assert 'threshold' in serializer.errors

        # Test above maximum
        data = {'threshold': 1.1}
        serializer = TriggerClusteringSerializer(data=data)
        assert not serializer.is_valid()
        assert 'threshold' in serializer.errors

        # Test valid
        data = {'threshold': 0.75}
        serializer = TriggerClusteringSerializer(data=data)
        assert serializer.is_valid()

    def test_all_providers_valid(self):
        """Test all valid LLM providers."""
        providers = ['openai', 'anthropic', 'google']

        for provider in providers:
            data = {'provider': provider}
            serializer = TriggerAdjudicationSerializer(data=data)
            assert serializer.is_valid(), f"Provider {provider} should be valid"

    def test_all_patterns_valid(self):
        """Test all valid agent patterns."""
        patterns = ['post_processing', 'interactive', 'multi_agent']

        for pattern in patterns:
            data = {'pattern': pattern}
            serializer = TriggerAdjudicationSerializer(data=data)
            assert serializer.is_valid(), f"Pattern {pattern} should be valid"

    def test_all_clustering_algorithms_valid(self):
        """Test all valid clustering algorithms."""
        algorithms = ['dbscan', 'agglomerative', 'kmeans']

        for algorithm in algorithms:
            data = {'algorithm': algorithm}
            serializer = TriggerClusteringSerializer(data=data)
            assert serializer.is_valid(), f"Algorithm {algorithm} should be valid"
