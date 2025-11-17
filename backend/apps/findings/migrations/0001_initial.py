# Generated manually - Initial migration for findings app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('organizations', '0001_initial'),
        ('scans', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Finding',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('fingerprint', models.CharField(db_index=True, max_length=64)),
                ('rule_id', models.CharField(db_index=True, max_length=255)),
                ('rule_name', models.CharField(blank=True, max_length=512, null=True)),
                ('message', models.TextField()),
                ('severity', models.CharField(choices=[('critical', 'Critical'), ('high', 'High'), ('medium', 'Medium'), ('low', 'Low'), ('info', 'Info')], db_index=True, max_length=20)),
                ('status', models.CharField(choices=[('open', 'Open'), ('fixed', 'Fixed'), ('false_positive', 'False Positive'), ('accepted_risk', 'Accepted Risk'), ('wont_fix', "Won't Fix")], db_index=True, default='open', max_length=20)),
                ('file_path', models.CharField(max_length=1024)),
                ('start_line', models.IntegerField()),
                ('start_column', models.IntegerField(default=1)),
                ('end_line', models.IntegerField(blank=True, null=True)),
                ('end_column', models.IntegerField(blank=True, null=True)),
                ('snippet', models.TextField(blank=True, null=True)),
                ('tool_name', models.CharField(max_length=255)),
                ('tool_version', models.CharField(blank=True, max_length=100, null=True)),
                ('cwe_ids', models.JSONField(blank=True, default=list)),
                ('cve_ids', models.JSONField(blank=True, default=list)),
                ('sarif_data', models.JSONField(blank=True, help_text='Full SARIF result object', null=True)),
                ('occurrence_count', models.IntegerField(default=1)),
                ('first_seen_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('last_seen_at', models.DateTimeField(auto_now=True)),
                ('fixed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.CASCADE, related_name='findings', to='organizations.organization')),
                ('repository', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='findings', to='organizations.repository')),
                ('first_seen_scan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='findings_first_seen', to='scans.scan')),
                ('last_seen_scan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='findings_last_seen', to='scans.scan')),
            ],
            options={
                'verbose_name': 'finding',
                'verbose_name_plural': 'findings',
                'db_table': 'findings',
                'ordering': ['-severity', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='FindingStatusHistory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('old_status', models.CharField(max_length=20)),
                ('new_status', models.CharField(max_length=20)),
                ('reason', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('finding', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_history', to='findings.finding')),
                ('changed_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='finding_status_changes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'finding status history',
                'verbose_name_plural': 'finding status histories',
                'db_table': 'finding_status_history',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='FindingComment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('finding', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='findings.finding')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='finding_comments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'finding comment',
                'verbose_name_plural': 'finding comments',
                'db_table': 'finding_comments',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='finding',
            index=models.Index(fields=['organization', 'status'], name='finding_org_status_idx'),
        ),
        migrations.AddIndex(
            model_name='finding',
            index=models.Index(fields=['repository', 'status'], name='finding_repo_status_idx'),
        ),
        migrations.AddIndex(
            model_name='finding',
            index=models.Index(fields=['fingerprint'], name='finding_fingerprint_idx'),
        ),
        migrations.AddIndex(
            model_name='finding',
            index=models.Index(fields=['severity'], name='finding_severity_idx'),
        ),
        migrations.AddIndex(
            model_name='finding',
            index=models.Index(fields=['rule_id'], name='finding_rule_idx'),
        ),
        migrations.AddIndex(
            model_name='finding',
            index=models.Index(fields=['first_seen_at'], name='finding_first_seen_idx'),
        ),
        migrations.AddIndex(
            model_name='finding',
            index=models.Index(fields=['organization', 'fingerprint'], name='finding_org_fp_idx'),
        ),
        migrations.AddConstraint(
            model_name='finding',
            constraint=models.UniqueConstraint(fields=('organization', 'fingerprint'), name='unique_org_fingerprint'),
        ),
    ]
