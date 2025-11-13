"""
Signals for organization-related events.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Organization


@receiver(post_save, sender=Organization)
def organization_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for organization creation.
    """
    if created:
        # Initialize organization resources, quotas, etc.
        pass
