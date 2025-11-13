"""
Signals for scan-related events.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Scan


@receiver(pre_save, sender=Scan)
def scan_pre_save(sender, instance, **kwargs):
    """
    Update timing information when scan status changes.
    """
    if instance.pk:
        try:
            old_instance = Scan.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                if instance.status == 'running' and not instance.started_at:
                    instance.started_at = timezone.now()
                elif instance.status in ['completed', 'failed', 'cancelled']:
                    if not instance.completed_at:
                        instance.completed_at = timezone.now()
                    if instance.started_at and instance.completed_at:
                        delta = instance.completed_at - instance.started_at
                        instance.duration_seconds = int(delta.total_seconds())
        except Scan.DoesNotExist:
            pass


@receiver(post_save, sender=Scan)
def scan_post_save(sender, instance, created, **kwargs):
    """
    Update quota usage when scan is created or completed.
    """
    if created:
        from .tasks import update_quota_usage
        update_quota_usage.delay(instance.organization.id, instance.id)
