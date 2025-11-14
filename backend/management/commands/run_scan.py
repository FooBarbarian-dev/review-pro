"""
Django management command to run a security scan.

Usage:
    # Scan a local directory
    python manage.py run_scan --path /path/to/code

    # Scan a git repository
    python manage.py run_scan --repo https://github.com/user/repo

    # Test with example vulnerable code
    python manage.py run_scan --path examples/vulnerable_code.py
"""

import asyncio
import logging
import uuid
from pathlib import Path
from django.core.management.base import BaseCommand
from django.utils import timezone
from temporalio.client import Client

from apps.organizations.models import Organization, Repository, Branch
from apps.scans.models import Scan
from workflows.scan_workflow import ScanRepositoryWorkflow
from workflows.adjudication_workflow import AdjudicateFindingsWorkflow

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run a security scan on code using Temporal workflow'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            help='Local path to scan',
        )
        parser.add_argument(
            '--repo',
            type=str,
            help='Git repository URL to clone and scan',
        )
        parser.add_argument(
            '--org',
            type=str,
            default='test-org',
            help='Organization slug (default: test-org)',
        )
        parser.add_argument(
            '--repo-name',
            type=str,
            default='test-repo',
            help='Repository name (default: test-repo)',
        )
        parser.add_argument(
            '--adjudicate',
            action='store_true',
            help='Run LLM adjudication after scanning',
        )
        parser.add_argument(
            '--llm-provider',
            type=str,
            default='openai',
            choices=['openai', 'anthropic'],
            help='LLM provider for adjudication (default: openai)',
        )
        parser.add_argument(
            '--llm-model',
            type=str,
            default='gpt-4o',
            help='LLM model for adjudication (default: gpt-4o)',
        )

    def handle(self, *args, **options):
        """Execute the command."""
        path = options.get('path')
        repo_url = options.get('repo')
        org_slug = options['org']
        repo_name = options['repo_name']

        if not path and not repo_url:
            self.stdout.write(
                self.style.ERROR('Error: Must provide either --path or --repo')
            )
            return

        if path and repo_url:
            self.stdout.write(
                self.style.ERROR('Error: Cannot provide both --path and --repo')
            )
            return

        # Verify path exists if provided
        if path:
            path_obj = Path(path)
            if not path_obj.exists():
                self.stdout.write(
                    self.style.ERROR(f'Error: Path does not exist: {path}')
                )
                return
            path = str(path_obj.absolute())

        self.stdout.write(
            self.style.WARNING(f'Starting security scan...')
        )
        self.stdout.write(f'  Organization: {org_slug}')
        self.stdout.write(f'  Repository: {repo_name}')
        if path:
            self.stdout.write(f'  Local path: {path}')
        if repo_url:
            self.stdout.write(f'  Git repository: {repo_url}')

        try:
            # Setup database objects
            org, repo, scan = self._setup_scan(org_slug, repo_name, repo_url or path)

            self.stdout.write(
                self.style.SUCCESS(f'✓ Created scan: {scan.id}')
            )

            # Run workflow
            result = asyncio.run(
                self.run_scan_workflow(
                    scan_id=str(scan.id),
                    repo_url=repo_url,
                    local_path=path,
                )
            )

            if result.get('success'):
                stats = result.get('stats', {})
                self.stdout.write(self.style.SUCCESS('\n✓ Scan completed successfully!'))
                self.stdout.write(f'\nFindings:')
                self.stdout.write(f'  Total processed: {stats.get("total", 0)}')
                self.stdout.write(f'  New findings: {stats.get("new", 0)}')
                self.stdout.write(f'  Updated findings: {stats.get("updated", 0)}')
                self.stdout.write(f'  Errors: {stats.get("errors", 0)}')

                # Run adjudication if requested
                if options.get('adjudicate'):
                    self.stdout.write(f'\n{self.style.WARNING("Running LLM adjudication...")}')
                    adjudication_result = asyncio.run(
                        self.run_adjudication_workflow(
                            scan_id=str(scan.id),
                            provider=options.get('llm_provider'),
                            model=options.get('llm_model'),
                        )
                    )

                    if adjudication_result.get('success'):
                        metrics = adjudication_result.get('metrics', {})
                        self.stdout.write(self.style.SUCCESS('\n✓ Adjudication completed!'))
                        self.stdout.write(f'\nAdjudication Results:')
                        self.stdout.write(f'  Total processed: {adjudication_result.get("total_processed", 0)}')
                        self.stdout.write(f'  True positives: {metrics.get("true_positives", 0)}')
                        self.stdout.write(f'  False positives: {metrics.get("false_positives", 0)}')
                        self.stdout.write(f'  Uncertain: {metrics.get("uncertain", 0)}')
                        self.stdout.write(f'  Filtered (high-conf FP): {metrics.get("filtered_count", 0)}')
                        self.stdout.write(f'  FP reduction rate: {metrics.get("fp_reduction_rate", 0):.1f}%')
                        self.stdout.write(f'  Total cost: ${adjudication_result.get("total_cost_usd", 0):.4f}')
                        self.stdout.write(f'  Avg time: {metrics.get("avg_processing_time_ms", 0)}ms')
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'\n✗ Adjudication failed: {adjudication_result.get("error")}')
                        )

                self.stdout.write(f'\nView in Temporal UI:')
                self.stdout.write(f'  http://localhost:8233')
                self.stdout.write(f'\nView findings in Django admin:')
                self.stdout.write(f'  http://localhost:8000/admin/findings/finding/')
                if options.get('adjudicate'):
                    self.stdout.write(f'View verdicts:')
                    self.stdout.write(f'  http://localhost:8000/admin/findings/llmverdict/')
            else:
                self.stdout.write(
                    self.style.ERROR(f'\n✗ Scan failed: {result.get("error")}')
                )
                scan.status = 'failed'
                scan.save(update_fields=['status'])

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Scan failed: {e}'))
            logger.error(f"Scan failed: {e}", exc_info=True)
            raise

    def _setup_scan(
        self,
        org_slug: str,
        repo_name: str,
        url: str,
    ) -> tuple:
        """
        Create or get organization, repository, branch, and scan objects.

        Args:
            org_slug: Organization slug
            repo_name: Repository name
            url: Repository URL or local path

        Returns:
            Tuple of (organization, repository, scan)
        """
        # Get or create organization
        org, _ = Organization.objects.get_or_create(
            slug=org_slug,
            defaults={
                'name': org_slug.replace('-', ' ').title(),
            }
        )

        # Generate a unique github_repo_id for local repos
        is_local = not url.startswith('http')
        github_repo_id = f'local-{org_slug}-{repo_name}' if is_local else f'{org_slug}/{repo_name}'

        # Get or create repository
        repo, _ = Repository.objects.get_or_create(
            organization=org,
            name=repo_name,
            defaults={
                'github_repo_id': github_repo_id,
                'full_name': f'{org_slug}/{repo_name}',
                'default_branch': 'main',
            }
        )

        # Get or create branch
        branch, _ = Branch.objects.get_or_create(
            repository=repo,
            name='main',
            defaults={
                'sha': 'local' if is_local else 'HEAD',
                'is_default': True,
            }
        )

        # Create scan
        scan = Scan.objects.create(
            organization=org,
            repository=repo,
            branch=branch,
            commit_sha='local' if is_local else 'HEAD',
            status='pending',
            trigger_type='manual',
        )

        return org, repo, scan

    async def run_scan_workflow(
        self,
        scan_id: str,
        repo_url: str = None,
        local_path: str = None,
    ) -> dict:
        """
        Execute the scan workflow via Temporal.

        Args:
            scan_id: UUID of the scan
            repo_url: Git repository URL (optional)
            local_path: Local path to scan (optional)

        Returns:
            Workflow result dictionary
        """
        self.stdout.write('\nConnecting to Temporal server...')

        # Connect to Temporal server
        client = await Client.connect('localhost:7233')

        self.stdout.write('Starting scan workflow...')
        self.stdout.write('  (This may take several minutes)')
        self.stdout.write('  Watch progress in Temporal UI: http://localhost:8233\n')

        # Execute workflow
        result = await client.execute_workflow(
            ScanRepositoryWorkflow.run,
            args=[scan_id, repo_url, local_path],
            id=f'scan-{scan_id}',
            task_queue='code-analysis',
        )

        return result

    async def run_adjudication_workflow(
        self,
        scan_id: str,
        provider: str = "openai",
        model: str = "gpt-4o",
    ) -> dict:
        """
        Execute the adjudication workflow via Temporal.

        Args:
            scan_id: UUID of the scan
            provider: LLM provider
            model: LLM model

        Returns:
            Workflow result dictionary
        """
        self.stdout.write(f'  Provider: {provider}')
        self.stdout.write(f'  Model: {model}')
        self.stdout.write('  (This may take several minutes depending on finding count)\n')

        # Connect to Temporal server (reuse connection)
        client = await Client.connect('localhost:7233')

        # Execute workflow
        result = await client.execute_workflow(
            AdjudicateFindingsWorkflow.run,
            args=[scan_id, provider, model],
            id=f'adjudicate-{scan_id}',
            task_queue='code-analysis',
        )

        return result
