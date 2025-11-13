"""
Serializers for User model.
"""
from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'github_username',
            'avatar_url', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for User model with API key info."""

    has_api_key = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'github_username',
            'avatar_url', 'is_active', 'has_api_key', 'api_key_created_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'has_api_key', 'api_key_created_at']

    def get_has_api_key(self, obj):
        return obj.api_key is not None


class APIKeySerializer(serializers.Serializer):
    """Serializer for API key generation response."""
    api_key = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
