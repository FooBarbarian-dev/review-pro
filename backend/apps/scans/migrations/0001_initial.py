# Generated manually - Initial migration for scans app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('organizations', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Scan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('queued', 'Queued'), ('running', 'Running'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], db_index=True, default='pending', max_length=20)),
                ('sarif_file_path', models.CharField(blank=True, max_length=512, null=True)),
                ('sarif_file_size', models.BigIntegerField(blank=True, null=True)),
                ('findings_count', models.IntegerField(default=0)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scans', to='organizations.organization')),
                ('repository', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scans', to='organizations.repository')),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scans', to='organizations.branch')),
                ('triggered_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='triggered_scans', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'scan',
                'verbose_name_plural': 'scans',
                'db_table': 'scans',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='QuotaUsage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('year', models.IntegerField()),
                ('month', models.IntegerField()),
                ('scans_used', models.IntegerField(default=0)),
                ('storage_used_bytes', models.BigIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quota_usage', to='organizations.organization')),
            ],
            options={
                'verbose_name': 'quota usage',
                'verbose_name_plural': 'quota usages',
                'db_table': 'quota_usage',
            },
        ),
        migrations.CreateModel(
            name='ScanLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('level', models.CharField(choices=[('info', 'Info'), ('warning', 'Warning'), ('error', 'Error'), ('success', 'Success')], default='info', max_length=20)),
                ('message', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('scan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='scans.scan')),
            ],
            options={
                'verbose_name': 'scan log',
                'verbose_name_plural': 'scan logs',
                'db_table': 'scan_logs',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='scan',
            index=models.Index(fields=['organization', 'status'], name='scan_org_status_idx'),
        ),
        migrations.AddIndex(
            model_name='scan',
            index=models.Index(fields=['repository'], name='scan_repo_idx'),
        ),
        migrations.AddIndex(
            model_name='scan',
            index=models.Index(fields=['status'], name='scan_status_idx'),
        ),
        migrations.AddIndex(
            model_name='scan',
            index=models.Index(fields=['created_at'], name='scan_created_idx'),
        ),
        migrations.AddConstraint(
            model_name='quotausage',
            constraint=models.UniqueConstraint(fields=('organization', 'year', 'month'), name='unique_org_year_month'),
        ),
        migrations.AddIndex(
            model_name='quotausage',
            index=models.Index(fields=['organization', 'year', 'month'], name='quota_org_ym_idx'),
        ),
        migrations.AddIndex(
            model_name='scanlog',
            index=models.Index(fields=['scan', 'created_at'], name='scanlog_scan_created_idx'),
        ),
    ]
