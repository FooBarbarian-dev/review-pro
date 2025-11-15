# Generated manually - Initial migration for organizations app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('slug', models.SlugField(db_index=True, max_length=255, unique=True)),
                ('github_org_id', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('github_org_name', models.CharField(blank=True, max_length=255, null=True)),
                ('scan_quota_monthly', models.IntegerField(default=100, help_text='Monthly scan quota')),
                ('storage_quota_gb', models.IntegerField(default=10, help_text='Storage quota in GB')),
                ('plan', models.CharField(choices=[('free', 'Free'), ('starter', 'Starter'), ('professional', 'Professional'), ('enterprise', 'Enterprise')], default='free', max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'organization',
                'verbose_name_plural': 'organizations',
                'db_table': 'organizations',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Repository',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('github_repo_id', models.CharField(db_index=True, max_length=100, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('full_name', models.CharField(max_length=512)),
                ('default_branch', models.CharField(default='main', max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('is_private', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='repositories', to='organizations.organization')),
            ],
            options={
                'verbose_name': 'repository',
                'verbose_name_plural': 'repositories',
                'db_table': 'repositories',
                'ordering': ['full_name'],
            },
        ),
        migrations.CreateModel(
            name='OrganizationMembership',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('role', models.CharField(choices=[('owner', 'Owner'), ('admin', 'Admin'), ('member', 'Member'), ('viewer', 'Viewer')], default='member', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='organizations.organization')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='organization_memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'organization membership',
                'verbose_name_plural': 'organization memberships',
                'db_table': 'organization_memberships',
            },
        ),
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('sha', models.CharField(max_length=40)),
                ('is_default', models.BooleanField(default=False)),
                ('is_protected', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_scan_at', models.DateTimeField(blank=True, null=True)),
                ('repository', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='branches', to='organizations.repository')),
            ],
            options={
                'verbose_name': 'branch',
                'verbose_name_plural': 'branches',
                'db_table': 'branches',
                'ordering': ['-is_default', 'name'],
            },
        ),
        migrations.AddIndex(
            model_name='organization',
            index=models.Index(fields=['slug'], name='org_slug_idx'),
        ),
        migrations.AddIndex(
            model_name='organization',
            index=models.Index(fields=['github_org_id'], name='org_github_id_idx'),
        ),
        migrations.AddIndex(
            model_name='organization',
            index=models.Index(fields=['created_at'], name='org_created_idx'),
        ),
        migrations.AddConstraint(
            model_name='organizationmembership',
            constraint=models.UniqueConstraint(fields=('organization', 'user'), name='unique_org_user'),
        ),
        migrations.AddIndex(
            model_name='organizationmembership',
            index=models.Index(fields=['organization', 'user'], name='orgmem_org_user_idx'),
        ),
        migrations.AddIndex(
            model_name='organizationmembership',
            index=models.Index(fields=['user'], name='orgmem_user_idx'),
        ),
        migrations.AddIndex(
            model_name='organizationmembership',
            index=models.Index(fields=['role'], name='orgmem_role_idx'),
        ),
        migrations.AddIndex(
            model_name='repository',
            index=models.Index(fields=['organization', 'name'], name='repo_org_name_idx'),
        ),
        migrations.AddIndex(
            model_name='repository',
            index=models.Index(fields=['github_repo_id'], name='repo_github_id_idx'),
        ),
        migrations.AddIndex(
            model_name='repository',
            index=models.Index(fields=['is_active'], name='repo_active_idx'),
        ),
        migrations.AddConstraint(
            model_name='branch',
            constraint=models.UniqueConstraint(fields=('repository', 'name'), name='unique_repo_branch'),
        ),
        migrations.AddIndex(
            model_name='branch',
            index=models.Index(fields=['repository', 'name'], name='branch_repo_name_idx'),
        ),
        migrations.AddIndex(
            model_name='branch',
            index=models.Index(fields=['sha'], name='branch_sha_idx'),
        ),
        migrations.AddIndex(
            model_name='branch',
            index=models.Index(fields=['is_default'], name='branch_default_idx'),
        ),
    ]
