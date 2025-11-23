"""
Serializers for the Scans API.
"""
from rest_framework import serializers
from apps.scans.models import Scan, ScanLog
from apps.organizations.models import Repository, Branch


class RepositorySerializer(serializers.ModelSerializer):
    """Serializer for Repository model."""

    class Meta:
        model = Repository
        fields = ['id', 'full_name', 'github_repo_id', 'default_branch', 'is_active', 'created_at']


class BranchSerializer(serializers.ModelSerializer):
    """Serializer for Branch model."""

    class Meta:
        model = Branch
        fields = ['id', 'name', 'is_default']


class ScanListSerializer(serializers.ModelSerializer):
    """Serializer for listing scans (compact view)."""

    repository = RepositorySerializer(read_only=True)
    branch = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = Scan
        fields = [
            'id', 'repository', 'branch', 'commit_sha', 'status',
            'total_findings', 'critical_count', 'high_count', 'medium_count',
            'low_count', 'info_count', 'tools_used', 'started_at',
            'completed_at', 'duration_seconds', 'created_at'
        ]


class ScanDetailSerializer(serializers.ModelSerializer):
    """Serializer for scan details (full view)."""

    repository = RepositorySerializer(read_only=True)
    branch = BranchSerializer(read_only=True)

    class Meta:
        model = Scan
        fields = [
            'id', 'organization', 'repository', 'branch', 'commit_sha',
            'status', 'triggered_by', 'trigger_type', 'sarif_file_path',
            'sarif_file_size', 'total_findings', 'critical_count',
            'high_count', 'medium_count', 'low_count', 'info_count',
            'tools_used', 'worker_id', 'worker_container_id',
            'started_at', 'completed_at', 'duration_seconds',
            'error_message', 'error_details', 'created_at', 'updated_at'
        ]


class ScanCreateSerializer(serializers.Serializer):
    """Serializer for creating a new scan."""

    repository_id = serializers.UUIDField()
    branch = serializers.CharField(max_length=255, required=False)
    commit_sha = serializers.CharField(max_length=40, required=False)

    def validate_repository_id(self, value):
        """Validate repository exists."""
        if not Repository.objects.filter(id=value).exists():
            raise serializers.ValidationError("Repository not found")
        return value

    def create(self, validated_data):
        """Create a new scan instance."""
        repository_id = validated_data.pop('repository_id')
        repository = Repository.objects.get(id=repository_id)
        
        # Get or create branch
        branch_name = validated_data.pop('branch', repository.default_branch)
        # We don't have SHA for branch creation if it's new, but we can update it later or use scan commit_sha
        branch, _ = Branch.objects.get_or_create(
            repository=repository,
            name=branch_name,
            defaults={'sha': validated_data.get('commit_sha', '')}
        )
        
        # Create scan
        scan = Scan.objects.create(
            organization=repository.organization,
            repository=repository,
            branch=branch,
            **validated_data
        )
        return scan


class TriggerAdjudicationSerializer(serializers.Serializer):
    """Serializer for triggering LLM adjudication."""

    provider = serializers.ChoiceField(
        choices=['openai', 'anthropic', 'google'],
        default='openai'
    )
    model = serializers.CharField(max_length=100, default='gpt-4o')
    pattern = serializers.ChoiceField(
        choices=['post_processing', 'interactive', 'multi_agent'],
        default='post_processing'
    )
    batch_size = serializers.IntegerField(default=10, min_value=1, max_value=100)
    max_findings = serializers.IntegerField(default=100, min_value=1, max_value=1000)


class TriggerClusteringSerializer(serializers.Serializer):
    """Serializer for triggering clustering."""

    algorithm = serializers.ChoiceField(
        choices=['dbscan', 'agglomerative'],
        default='dbscan'
    )
    threshold = serializers.FloatField(default=0.85, min_value=0.0, max_value=1.0)


class ScanLogSerializer(serializers.ModelSerializer):
    """Serializer for scan logs."""

    class Meta:
        model = ScanLog
        fields = ['id', 'scan', 'level', 'message', 'timestamp', 'tool', 'context']
