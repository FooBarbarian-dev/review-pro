"""
Serializers for the Findings API.
"""
from rest_framework import serializers
from apps.findings.models import (
    Finding, LLMVerdict, FindingCluster, FindingClusterMembership,
    FindingComment, FindingStatusHistory
)


class LLMVerdictSerializer(serializers.ModelSerializer):
    """Serializer for LLM verdicts."""

    class Meta:
        model = LLMVerdict
        fields = [
            'id', 'finding', 'verdict', 'confidence', 'reasoning',
            'cwe_id', 'recommendation', 'llm_provider', 'llm_model',
            'agent_pattern', 'prompt_tokens', 'completion_tokens',
            'total_tokens', 'estimated_cost_usd', 'processing_time_ms',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FindingClusterMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for clusters (used in finding details)."""

    class Meta:
        model = FindingCluster
        fields = ['id', 'cluster_label', 'size', 'algorithm']


class FindingClusterMembershipSerializer(serializers.ModelSerializer):
    """Serializer for cluster membership."""

    cluster = FindingClusterMinimalSerializer(read_only=True)

    class Meta:
        model = FindingClusterMembership
        fields = ['id', 'cluster', 'distance_to_centroid', 'created_at']


class FindingListSerializer(serializers.ModelSerializer):
    """Serializer for listing findings (compact view)."""

    class Meta:
        model = Finding
        fields = [
            'id', 'rule_id', 'rule_name', 'message', 'severity', 'status',
            'file_path', 'start_line', 'start_column', 'tool_name',
            'cwe_ids', 'occurrence_count', 'first_seen_at', 'last_seen_at'
        ]


class FindingDetailSerializer(serializers.ModelSerializer):
    """Serializer for finding details (full view with related data)."""

    llm_verdicts = LLMVerdictSerializer(many=True, read_only=True)
    cluster_memberships = FindingClusterMembershipSerializer(many=True, read_only=True)

    class Meta:
        model = Finding
        fields = [
            'id', 'organization', 'repository', 'first_seen_scan', 'last_seen_scan',
            'fingerprint', 'rule_id', 'rule_name', 'message', 'severity', 'status',
            'file_path', 'start_line', 'start_column', 'end_line', 'end_column',
            'snippet', 'tool_name', 'tool_version', 'cwe_ids', 'cve_ids',
            'sarif_data', 'occurrence_count', 'first_seen_at', 'last_seen_at',
            'fixed_at', 'created_at', 'updated_at', 'llm_verdicts', 'cluster_memberships'
        ]


class FindingUpdateSerializer(serializers.Serializer):
    """Serializer for updating finding status."""

    status = serializers.ChoiceField(
        choices=[
            'open', 'fixed', 'false_positive', 'accepted_risk', 'wont_fix'
        ]
    )


class FindingMinimalSerializer(serializers.ModelSerializer):
    """Minimal finding serializer for cluster details."""

    class Meta:
        model = Finding
        fields = [
            'id', 'rule_id', 'message', 'severity', 'status',
            'file_path', 'start_line', 'tool_name'
        ]


class FindingClusterSerializer(serializers.ModelSerializer):
    """Serializer for cluster details."""

    representative_finding = FindingMinimalSerializer(read_only=True)

    class Meta:
        model = FindingCluster
        fields = [
            'id', 'organization', 'cluster_label', 'representative_finding',
            'size', 'avg_similarity', 'cohesion_score', 'algorithm',
            'similarity_threshold', 'primary_rule_id', 'primary_severity',
            'primary_tool', 'statistics', 'created_at', 'updated_at'
        ]


class FindingCommentSerializer(serializers.ModelSerializer):
    """Serializer for finding comments."""

    author_email = serializers.EmailField(source='author.email', read_only=True)

    class Meta:
        model = FindingComment
        fields = ['id', 'finding', 'author_email', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class FindingStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for finding status history."""

    changed_by_email = serializers.EmailField(source='changed_by.email', read_only=True)

    class Meta:
        model = FindingStatusHistory
        fields = [
            'id', 'finding', 'changed_by_email', 'old_status',
            'new_status', 'reason', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
