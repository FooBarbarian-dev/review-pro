"""
Organization models implementing multi-tenancy (ADR-001).
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Organization(models.Model):
    """
    Organization model for multi-tenancy.
    Each organization represents a separate tenant in the system.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)

    # GitHub integration
    github_org_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    github_org_name = models.CharField(max_length=255, blank=True, null=True)

    # Quotas (ADR-008)
    scan_quota_monthly = models.IntegerField(default=100, help_text="Monthly scan quota")
    storage_quota_gb = models.IntegerField(default=10, help_text="Storage quota in GB")

    # Billing
    plan = models.CharField(
        max_length=50,
        choices=[
            ('free', 'Free'),
            ('starter', 'Starter'),
            ('professional', 'Professional'),
            ('enterprise', 'Enterprise'),
        ],
        default='free'
    )

    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organizations'
        verbose_name = _('organization')
        verbose_name_plural = _('organizations')
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['github_org_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    """
    Membership relationship between users and organizations.
    Implements RBAC for organization access control (ADR-007).
    """
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organization_memberships'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organization_memberships'
        verbose_name = _('organization membership')
        verbose_name_plural = _('organization memberships')
        unique_together = [['organization', 'user']]
        indexes = [
            models.Index(fields=['organization', 'user']),
            models.Index(fields=['user']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.organization.name} ({self.role})"

    def has_permission(self, permission):
        """
        Check if the user has a specific permission based on their role.
        """
        role_permissions = {
            'owner': ['read', 'write', 'delete', 'admin', 'billing'],
            'admin': ['read', 'write', 'delete', 'admin'],
            'member': ['read', 'write'],
            'viewer': ['read'],
        }
        return permission in role_permissions.get(self.role, [])


class Repository(models.Model):
    """
    Repository model for tracking GitHub repositories.
    Normalized design as per ADR-006.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='repositories'
    )

    # GitHub info
    github_repo_id = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=512)  # e.g., "owner/repo"
    default_branch = models.CharField(max_length=255, default='main')

    # Repository metadata
    is_active = models.BooleanField(default=True)
    is_private = models.BooleanField(default=False)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'repositories'
        verbose_name = _('repository')
        verbose_name_plural = _('repositories')
        ordering = ['full_name']
        indexes = [
            models.Index(fields=['organization', 'name']),
            models.Index(fields=['github_repo_id']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.full_name


class Branch(models.Model):
    """
    Branch model for tracking repository branches.
    Normalized design as per ADR-006.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name='branches'
    )
    name = models.CharField(max_length=255)
    sha = models.CharField(max_length=40)  # Git commit SHA

    # Branch metadata
    is_default = models.BooleanField(default=False)
    is_protected = models.BooleanField(default=False)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_scan_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'branches'
        verbose_name = _('branch')
        verbose_name_plural = _('branches')
        unique_together = [['repository', 'name']]
        ordering = ['-is_default', 'name']
        indexes = [
            models.Index(fields=['repository', 'name']),
            models.Index(fields=['sha']),
            models.Index(fields=['is_default']),
        ]

    def __str__(self):
        return f"{self.repository.full_name}:{self.name}"
