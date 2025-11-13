"""
Serializers for Organization models.
"""
from rest_framework import serializers
from .models import Organization, OrganizationMembership, Repository, Branch


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model."""
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'github_org_name', 'plan',
            'scan_quota_monthly', 'storage_quota_gb', 'is_active',
            'member_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'member_count']

    def get_member_count(self, obj):
        return obj.memberships.count()


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    """Serializer for OrganizationMembership model."""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationMembership
        fields = [
            'id', 'organization', 'user', 'user_email', 'user_name',
            'role', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email


class BranchSerializer(serializers.ModelSerializer):
    """Serializer for Branch model."""

    class Meta:
        model = Branch
        fields = [
            'id', 'repository', 'name', 'sha', 'is_default',
            'is_protected', 'last_scan_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RepositorySerializer(serializers.ModelSerializer):
    """Serializer for Repository model."""
    branch_count = serializers.SerializerMethodField()
    default_branch_name = serializers.CharField(source='default_branch', read_only=True)

    class Meta:
        model = Repository
        fields = [
            'id', 'organization', 'github_repo_id', 'name', 'full_name',
            'default_branch_name', 'branch_count', 'is_active', 'is_private',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'branch_count']

    def get_branch_count(self, obj):
        return obj.branches.count()


class RepositoryDetailSerializer(RepositorySerializer):
    """Detailed serializer for Repository with branches."""
    branches = BranchSerializer(many=True, read_only=True)

    class Meta(RepositorySerializer.Meta):
        fields = RepositorySerializer.Meta.fields + ['branches']
