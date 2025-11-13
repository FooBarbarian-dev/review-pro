"""
Tests for User model.
"""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Test suite for User model."""

    def test_create_user(self):
        """Test creating a user with email and password."""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        assert user.email == 'test@example.com'
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.check_password('testpass123')

    def test_create_superuser(self):
        """Test creating a superuser."""
        admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        assert admin_user.email == 'admin@example.com'
        assert admin_user.is_active is True
        assert admin_user.is_staff is True
        assert admin_user.is_superuser is True

    def test_user_str_method(self):
        """Test user string representation."""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        assert str(user) == 'test@example.com'

    def test_generate_api_key(self, user):
        """Test generating an API key for user."""
        assert user.api_key is None
        api_key = user.generate_api_key()
        assert api_key is not None
        assert len(api_key) > 0
        assert user.api_key == api_key
        assert user.api_key_created_at is not None

    def test_revoke_api_key(self, user):
        """Test revoking user's API key."""
        user.generate_api_key()
        assert user.api_key is not None
        user.revoke_api_key()
        assert user.api_key is None
        assert user.api_key_created_at is None
