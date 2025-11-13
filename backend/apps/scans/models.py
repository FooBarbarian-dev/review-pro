"""
Scan models for security analysis.
Implements SARIF storage strategy (ADR-005) and worker security model (ADR-004).
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.organizations.models import Organization, Repository, Branch


class Scan(models.Model):
    """
    Scan model representing a security scan job.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='scans',
        db_index=True
    )
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name='scans'
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='scans'
    )

    # Scan details
    commit_sha = models.CharField(max_length=40, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)

    # Trigger information
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triggered_scans'
    )
    trigger_type = models.CharField(
        max_length=50,
        choices=[
            ('manual', 'Manual'),
            ('push', 'Push'),
            ('pull_request', 'Pull Request'),
            ('scheduled', 'Scheduled'),
        ],
        default='manual'
    )

    # SARIF storage (ADR-005)
    # Full SARIF is stored in S3, path to the file
    sarif_file_path = models.CharField(max_length=512, blank=True, null=True)
    sarif_file_size = models.BigIntegerField(blank=True, null=True, help_text="Size in bytes")

    # Scan statistics (derived from SARIF)
    total_findings = models.IntegerField(default=0)
    critical_count = models.IntegerField(default=0)
    high_count = models.IntegerField(default=0)
    medium_count = models.IntegerField(default=0)
    low_count = models.IntegerField(default=0)
    info_count = models.IntegerField(default=0)

    # Tool information
    tools_used = models.JSONField(default=list, help_text="List of security tools used in this scan")

    # Worker information (ADR-004)
    worker_id = models.CharField(max_length=255, blank=True, null=True)
    worker_container_id = models.CharField(max_length=255, blank=True, null=True)

    # Timing
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    duration_seconds = models.IntegerField(blank=True, null=True)

    # Error information
    error_message = models.TextField(blank=True, null=True)
    error_details = models.JSONField(blank=True, null=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'scans'
        verbose_name = _('scan')
        verbose_name_plural = _('scans')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'created_at']),
            models.Index(fields=['repository', 'branch']),
            models.Index(fields=['status']),
            models.Index(fields=['commit_sha']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Scan {self.id} - {self.repository.full_name}@{self.commit_sha[:7]}"


class ScanLog(models.Model):
    """
    Scan log entries for detailed scan execution logs.
    """
    LEVEL_CHOICES = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scan = models.ForeignKey(
        Scan,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='info')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # Additional context
    tool = models.CharField(max_length=100, blank=True, null=True)
    context = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'scan_logs'
        verbose_name = _('scan log')
        verbose_name_plural = _('scan logs')
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['scan', 'timestamp']),
            models.Index(fields=['level']),
        ]

    def __str__(self):
        return f"{self.level.upper()}: {self.message[:50]}"


class QuotaUsage(models.Model):
    """
    Track quota usage per organization (ADR-008).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='quota_usage'
    )

    # Period
    year = models.IntegerField(db_index=True)
    month = models.IntegerField(db_index=True)

    # Usage counts
    scans_used = models.IntegerField(default=0)
    storage_used_bytes = models.BigIntegerField(default=0)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quota_usage'
        verbose_name = _('quota usage')
        verbose_name_plural = _('quota usage')
        unique_together = [['organization', 'year', 'month']]
        ordering = ['-year', '-month']
        indexes = [
            models.Index(fields=['organization', 'year', 'month']),
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.year}/{self.month}"

    @property
    def storage_used_gb(self):
        """Convert storage from bytes to GB."""
        return self.storage_used_bytes / (1024 ** 3)

    def is_scan_quota_exceeded(self):
        """Check if scan quota is exceeded."""
        return self.scans_used >= self.organization.scan_quota_monthly

    def is_storage_quota_exceeded(self):
        """Check if storage quota is exceeded."""
        return self.storage_used_gb >= self.organization.storage_quota_gb
