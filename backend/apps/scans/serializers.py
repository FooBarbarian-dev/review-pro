"""
Serializers for Scan models.
"""
from rest_framework import serializers
from .models import Scan, ScanLog, QuotaUsage


class ScanLogSerializer(serializers.ModelSerializer):
    """Serializer for ScanLog model."""

    class Meta:
        model = ScanLog
        fields = ['id', 'scan', 'level', 'message', 'tool', 'context', 'timestamp']
        read_only_fields = ['id', 'timestamp']


class ScanSerializer(serializers.ModelSerializer):
    """Serializer for Scan model."""
    repository_name = serializers.CharField(source='repository.full_name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    triggered_by_email = serializers.EmailField(source='triggered_by.email', read_only=True)

    class Meta:
        model = Scan
        fields = [
            'id', 'organization', 'repository', 'repository_name', 'branch',
            'branch_name', 'commit_sha', 'status', 'triggered_by', 'triggered_by_email',
            'trigger_type', 'sarif_file_path', 'sarif_file_size', 'total_findings',
            'critical_count', 'high_count', 'medium_count', 'low_count', 'info_count',
            'tools_used', 'started_at', 'completed_at', 'duration_seconds',
            'error_message', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'sarif_file_path', 'sarif_file_size', 'total_findings',
            'critical_count', 'high_count', 'medium_count', 'low_count', 'info_count',
            'started_at', 'completed_at', 'duration_seconds', 'error_message',
            'created_at', 'updated_at'
        ]


class ScanDetailSerializer(ScanSerializer):
    """Detailed serializer for Scan with logs."""
    recent_logs = ScanLogSerializer(many=True, read_only=True, source='logs')

    class Meta(ScanSerializer.Meta):
        fields = ScanSerializer.Meta.fields + ['recent_logs', 'error_details', 'worker_id']


class ScanCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new scan."""

    class Meta:
        model = Scan
        fields = ['organization', 'repository', 'branch', 'commit_sha', 'trigger_type']

    def validate(self, data):
        """Validate that repository and branch belong to the organization."""
        if data['repository'].organization != data['organization']:
            raise serializers.ValidationError("Repository does not belong to this organization")
        if data['branch'].repository != data['repository']:
            raise serializers.ValidationError("Branch does not belong to this repository")
        return data


class QuotaUsageSerializer(serializers.ModelSerializer):
    """Serializer for QuotaUsage model."""
    storage_used_gb = serializers.FloatField(read_only=True)
    scan_quota_limit = serializers.IntegerField(source='organization.scan_quota_monthly', read_only=True)
    storage_quota_limit = serializers.IntegerField(source='organization.storage_quota_gb', read_only=True)
    is_scan_quota_exceeded = serializers.BooleanField(read_only=True)
    is_storage_quota_exceeded = serializers.BooleanField(read_only=True)

    class Meta:
        model = QuotaUsage
        fields = [
            'id', 'organization', 'year', 'month', 'scans_used', 'storage_used_bytes',
            'storage_used_gb', 'scan_quota_limit', 'storage_quota_limit',
            'is_scan_quota_exceeded', 'is_storage_quota_exceeded', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


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
