"""
Celery configuration for Security Analysis Platform.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('secanalysis')

# Load configuration from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from installed apps
app.autodiscover_tasks()

# Periodic task schedule
app.conf.beat_schedule = {
    'cleanup-old-scans': {
        'task': 'apps.scans.tasks.cleanup_old_scans',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
    'update-github-repositories': {
        'task': 'apps.organizations.tasks.sync_github_repositories',
        'schedule': crontab(hour='*/6'),  # Run every 6 hours
    },
}

app.conf.timezone = 'UTC'


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery."""
    print(f'Request: {self.request!r}')
