"""
User models for the Security Analysis Platform.
Implements custom user model with UUID primary key.
"""
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with an email and password."""
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with an email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model with UUID primary key and email as username.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    email = models.EmailField(_('email address'), unique=True)
    github_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    github_username = models.CharField(max_length=255, blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)

    # API Key for programmatic access (ADR-007)
    api_key = models.CharField(max_length=64, blank=True, null=True, unique=True, db_index=True)
    api_key_created_at = models.DateTimeField(blank=True, null=True)
    api_key_last_used_at = models.DateTimeField(blank=True, null=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['github_id']),
            models.Index(fields=['api_key']),
        ]

    def __str__(self):
        return self.email

    def generate_api_key(self):
        """Generate a new API key for this user."""
        import secrets
        from django.utils import timezone

        self.api_key = secrets.token_urlsafe(48)
        self.api_key_created_at = timezone.now()
        self.save(update_fields=['api_key', 'api_key_created_at'])
        return self.api_key

    def revoke_api_key(self):
        """Revoke the user's API key."""
        self.api_key = None
        self.api_key_created_at = None
        self.api_key_last_used_at = None
        self.save(update_fields=['api_key', 'api_key_created_at', 'api_key_last_used_at'])
