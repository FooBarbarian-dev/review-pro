"""
Serializers for Finding models.
"""
from rest_framework import serializers
from .models import Finding, FindingComment, FindingStatusHistory


class FindingCommentSerializer(serializers.ModelSerializer):
    """Serializer for FindingComment model."""
    author_email = serializers.EmailField(source='author.email', read_only=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = FindingComment
        fields = ['id', 'finding', 'author', 'author_email', 'author_name', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

    def get_author_name(self, obj):
        return f"{obj.author.first_name} {obj.author.last_name}".strip() or obj.author.email


class FindingStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for FindingStatusHistory model."""
    changed_by_email = serializers.EmailField(source='changed_by.email', read_only=True)

    class Meta:
        model = FindingStatusHistory
        fields = ['id', 'finding', 'changed_by', 'changed_by_email', 'old_status', 'new_status', 'reason', 'created_at']
        read_only_fields = ['id', 'changed_by', 'created_at']


class FindingSerializer(serializers.ModelSerializer):
    """Serializer for Finding model."""
    repository_name = serializers.CharField(source='repository.full_name', read_only=True)
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Finding
        fields = [
            'id', 'organization', 'repository', 'repository_name', 'fingerprint',
            'rule_id', 'rule_name', 'message', 'severity', 'status', 'file_path',
            'start_line', 'start_column', 'end_line', 'end_column', 'tool_name',
            'tool_version', 'cwe_ids', 'cve_ids', 'occurrence_count',
            'first_seen_at', 'last_seen_at', 'fixed_at', 'comment_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'fingerprint', 'occurrence_count', 'first_seen_at',
            'last_seen_at', 'fixed_at', 'created_at', 'updated_at', 'comment_count'
        ]

    def get_comment_count(self, obj):
        return obj.comments.count()


class FindingDetailSerializer(FindingSerializer):
    """Detailed serializer for Finding with related data."""
    comments = FindingCommentSerializer(many=True, read_only=True)
    status_history = FindingStatusHistorySerializer(many=True, read_only=True)
    first_seen_scan_id = serializers.UUIDField(source='first_seen_scan.id', read_only=True)
    last_seen_scan_id = serializers.UUIDField(source='last_seen_scan.id', read_only=True)

    class Meta(FindingSerializer.Meta):
        fields = FindingSerializer.Meta.fields + [
            'snippet', 'sarif_data', 'comments', 'status_history',
            'first_seen_scan_id', 'last_seen_scan_id'
        ]


class FindingStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating finding status."""
    status = serializers.ChoiceField(choices=Finding.STATUS_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True)
