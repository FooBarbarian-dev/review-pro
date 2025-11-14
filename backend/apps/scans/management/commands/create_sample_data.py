"""
Management command to create sample data for testing the platform.

Usage:
    python manage.py create_sample_data
    python manage.py create_sample_data --reset  # Delete existing data first
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random
import uuid

from apps.organizations.models import Organization, Repository, Branch
from apps.scans.models import Scan
from apps.findings.models import Finding, LLMVerdict, FindingCluster, FindingClusterMembership
from apps.users.models import OrganizationMembership

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample data for testing the Security Analysis Platform'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete all existing data before creating sample data',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('Deleting existing data...'))
            self.reset_data()

        self.stdout.write(self.style.SUCCESS('Creating sample data...'))

        # Create users
        self.stdout.write('Creating users...')
        admin_user = self.create_admin_user()
        demo_user = self.create_demo_user()

        # Create organization
        self.stdout.write('Creating organization...')
        org = self.create_organization(admin_user)

        # Add demo user to organization
        OrganizationMembership.objects.create(
            user=demo_user,
            organization=org,
            role='member'
        )

        # Create repositories
        self.stdout.write('Creating repositories...')
        repos = self.create_repositories(org)

        # Create scans and findings
        self.stdout.write('Creating scans and findings...')
        for repo in repos:
            self.create_scans_for_repo(repo, admin_user)

        self.stdout.write(self.style.SUCCESS('✓ Sample data created successfully!'))
        self.stdout.write('')
        self.stdout.write('Login credentials:')
        self.stdout.write(f'  Admin: admin@example.com / admin123')
        self.stdout.write(f'  Demo:  demo@example.com / demo123')

    def reset_data(self):
        """Delete all existing data."""
        Finding.objects.all().delete()
        Scan.objects.all().delete()
        Branch.objects.all().delete()
        Repository.objects.all().delete()
        OrganizationMembership.objects.all().delete()
        Organization.objects.all().delete()
        User.objects.filter(email__in=['admin@example.com', 'demo@example.com']).delete()

    def create_admin_user(self):
        """Create admin user."""
        user, created = User.objects.get_or_create(
            email='admin@example.com',
            defaults={
                'username': 'admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            user.set_password('admin123')
            user.save()
        return user

    def create_demo_user(self):
        """Create demo user."""
        user, created = User.objects.get_or_create(
            email='demo@example.com',
            defaults={
                'username': 'demo',
            }
        )
        if created:
            user.set_password('demo123')
            user.save()
        return user

    def create_organization(self, owner):
        """Create a sample organization."""
        org, created = Organization.objects.get_or_create(
            name='Demo Corporation',
            defaults={
                'slug': 'demo-corp',
                'owner': owner,
            }
        )
        return org

    def create_repositories(self, org):
        """Create sample repositories."""
        repos_data = [
            {
                'name': 'web-app',
                'description': 'Main web application',
                'clone_url': 'https://github.com/demo-corp/web-app.git',
            },
            {
                'name': 'api-service',
                'description': 'REST API microservice',
                'clone_url': 'https://github.com/demo-corp/api-service.git',
            },
            {
                'name': 'mobile-app',
                'description': 'React Native mobile app',
                'clone_url': 'https://github.com/demo-corp/mobile-app.git',
            },
        ]

        repos = []
        for repo_data in repos_data:
            repo, created = Repository.objects.get_or_create(
                organization=org,
                name=repo_data['name'],
                defaults={
                    'description': repo_data['description'],
                    'clone_url': repo_data['clone_url'],
                    'default_branch': 'main',
                }
            )

            # Create branches
            for branch_name in ['main', 'develop', 'staging']:
                Branch.objects.get_or_create(
                    repository=repo,
                    name=branch_name,
                )

            repos.append(repo)

        return repos

    def create_scans_for_repo(self, repo, user):
        """Create sample scans and findings for a repository."""
        main_branch = repo.branches.get(name='main')

        # Create 3 scans with different statuses
        statuses = ['completed', 'completed', 'running']

        for i, status in enumerate(statuses):
            days_ago = i + 1
            scan = Scan.objects.create(
                organization=repo.organization,
                repository=repo,
                branch=main_branch,
                commit_sha=self.generate_commit_sha(),
                status=status,
                triggered_by=user,
                trigger_type='manual',
                started_at=timezone.now() - timedelta(days=days_ago),
                completed_at=timezone.now() - timedelta(days=days_ago) + timedelta(hours=1) if status == 'completed' else None,
            )

            if status == 'completed':
                self.create_findings_for_scan(scan)

    def create_findings_for_scan(self, scan):
        """Create sample findings for a scan."""
        tools = ['bandit', 'semgrep', 'eslint', 'gosec']
        severities = ['critical', 'high', 'medium', 'low', 'info']
        statuses = ['open', 'open', 'open', 'false_positive', 'fixed']

        file_paths = [
            'src/auth/login.py',
            'src/api/users.py',
            'src/utils/crypto.py',
            'frontend/components/Auth.tsx',
            'frontend/utils/api.ts',
            'backend/models/user.py',
            'config/settings.py',
        ]

        rule_ids = [
            'sql-injection',
            'xss-vulnerability',
            'hardcoded-credentials',
            'insecure-crypto',
            'path-traversal',
            'command-injection',
            'xxe-vulnerability',
        ]

        descriptions = [
            'Potential SQL injection vulnerability detected',
            'Cross-site scripting (XSS) vulnerability found',
            'Hardcoded credentials or API keys detected',
            'Use of weak or broken cryptographic algorithm',
            'Path traversal vulnerability detected',
            'Command injection vulnerability found',
            'XML external entity (XXE) vulnerability detected',
        ]

        # Create 15-25 findings per scan
        num_findings = random.randint(15, 25)

        for _ in range(num_findings):
            tool = random.choice(tools)
            severity = random.choice(severities)
            status = random.choice(statuses)
            file_path = random.choice(file_paths)
            rule_id = random.choice(rule_ids)
            description = random.choice(descriptions)

            finding = Finding.objects.create(
                repository=scan.repository,
                first_seen_scan=scan,
                last_seen_scan=scan,
                tool_name=tool,
                rule_id=f'{tool}/{rule_id}',
                severity=severity,
                status=status,
                title=f'{rule_id.replace("-", " ").title()} in {file_path}',
                description=description,
                file_path=file_path,
                start_line=random.randint(10, 500),
                end_line=random.randint(10, 500),
                start_column=random.randint(1, 80),
                end_column=random.randint(1, 80),
                fingerprint=str(uuid.uuid4()),
            )

            # Create LLM verdict for some findings
            if random.random() < 0.6:  # 60% of findings have LLM verdicts
                self.create_llm_verdict(finding)

    def create_llm_verdict(self, finding):
        """Create an LLM verdict for a finding."""
        verdicts = ['true_positive', 'false_positive', 'needs_review']
        providers = ['openai', 'anthropic', 'google']
        models = {
            'openai': ['gpt-4o', 'gpt-4-turbo'],
            'anthropic': ['claude-3-opus', 'claude-3-sonnet'],
            'google': ['gemini-pro', 'gemini-ultra'],
        }
        patterns = ['post_processing', 'interactive', 'multi_agent']

        verdict = random.choice(verdicts)
        provider = random.choice(providers)
        model = random.choice(models[provider])
        pattern = random.choice(patterns)
        confidence = random.uniform(0.6, 0.99)

        reasoning_options = [
            'This appears to be a legitimate security issue that should be addressed.',
            'The code pattern is safe in this context due to input validation.',
            'This is a false positive - the variable is never user-controlled.',
            'The vulnerability exists but is mitigated by framework-level protections.',
            'Further analysis needed to determine exploitability.',
        ]

        recommendation_options = [
            'Use parameterized queries to prevent SQL injection.',
            'Sanitize and validate all user inputs before processing.',
            'Replace with a cryptographically secure algorithm.',
            'Implement proper access controls and path validation.',
            'Review and update the code to use secure practices.',
        ]

        LLMVerdict.objects.create(
            finding=finding,
            verdict=verdict,
            confidence=confidence,
            reasoning=random.choice(reasoning_options),
            cwe_id=random.choice(['CWE-89', 'CWE-79', 'CWE-798', 'CWE-327', 'CWE-22']),
            recommendation=random.choice(recommendation_options),
            llm_provider=provider,
            llm_model=model,
            agent_pattern=pattern,
            prompt_tokens=random.randint(500, 1500),
            completion_tokens=random.randint(100, 500),
            total_tokens=random.randint(600, 2000),
            estimated_cost_usd=random.uniform(0.001, 0.05),
            processing_time_ms=random.randint(500, 3000),
        )

    def generate_commit_sha(self):
        """Generate a realistic looking commit SHA."""
        import hashlib
        return hashlib.sha1(str(uuid.uuid4()).encode()).hexdigest()
