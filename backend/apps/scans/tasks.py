"""
Celery tasks for scan operations.
"""
from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task
def update_quota_usage(organization_id, scan_id=None):
    """
    Update quota usage for an organization.
    """
    from .models import QuotaUsage, Scan
    from apps.organizations.models import Organization

    try:
        organization = Organization.objects.get(id=organization_id)
        now = timezone.now()

        # Get or create quota usage for current month
        quota, created = QuotaUsage.objects.get_or_create(
            organization=organization,
            year=now.year,
            month=now.month,
            defaults={'scans_used': 0, 'storage_used_bytes': 0}
        )

        # Update scan count
        if scan_id:
            quota.scans_used += 1

        # Calculate total storage used
        total_storage = Scan.objects.filter(
            organization=organization,
            sarif_file_size__isnull=False
        ).aggregate(models.Sum('sarif_file_size'))['sarif_file_size__sum'] or 0

        quota.storage_used_bytes = total_storage
        quota.save()

        logger.info(f"Updated quota usage for {organization.name}: {quota.scans_used} scans, {quota.storage_used_gb:.2f} GB")

    except Exception as e:
        logger.error(f"Error updating quota usage: {e}")
        raise


@shared_task
def run_security_scan(scan_id):
    """
    Execute a security scan in a Docker container (ADR-004).
    """
    from .models import Scan, ScanLog
    import docker

    try:
        scan = Scan.objects.get(id=scan_id)
        scan.status = 'running'
        scan.save()

        # TODO: Implement actual scan execution
        # 1. Create ephemeral GitHub App token
        # 2. Start Docker container with security tools
        # 3. Run scan and collect SARIF output
        # 4. Upload SARIF to S3
        # 5. Parse SARIF and create findings
        # 6. Update scan status

        ScanLog.objects.create(
            scan=scan,
            level='info',
            message='Scan started'
        )

        logger.info(f"Started scan {scan_id}")

    except Exception as e:
        logger.error(f"Error running scan {scan_id}: {e}")
        try:
            scan = Scan.objects.get(id=scan_id)
            scan.status = 'failed'
            scan.error_message = str(e)
            scan.save()
        except:
            pass
        raise
