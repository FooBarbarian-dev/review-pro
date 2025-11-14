"""
Django management command to test LLM adjudication.

Usage:
    # Adjudicate findings from a scan
    python manage.py test_adjudication --scan-id <uuid>

    # Adjudicate a single finding
    python manage.py test_adjudication --finding-id <uuid>

    # Use specific LLM
    python manage.py test_adjudication --scan-id <uuid> --provider anthropic --model claude-sonnet-4
"""

import asyncio
import logging
from django.core.management.base import BaseCommand
from temporalio.client import Client

from apps.findings.models import Finding, LLMVerdict
from apps.scans.models import Scan
from workflows.adjudication_workflow import (
    AdjudicateFindingsWorkflow,
    AdjudicateSingleFindingWorkflow,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test LLM adjudication on findings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scan-id',
            type=str,
            help='Scan ID to adjudicate all findings from',
        )
        parser.add_argument(
            '--finding-id',
            type=str,
            help='Single finding ID to adjudicate',
        )
        parser.add_argument(
            '--provider',
            type=str,
            default='openai',
            choices=['openai', 'anthropic'],
            help='LLM provider (default: openai)',
        )
        parser.add_argument(
            '--model',
            type=str,
            default='gpt-4o',
            help='LLM model (default: gpt-4o)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=5,
            help='Batch size for parallel processing (default: 5)',
        )
        parser.add_argument(
            '--max-findings',
            type=int,
            default=20,
            help='Maximum findings to process (default: 20)',
        )

    def handle(self, *args, **options):
        """Execute the command."""
        scan_id = options.get('scan_id')
        finding_id = options.get('finding_id')
        provider = options['provider']
        model = options['model']

        if not scan_id and not finding_id:
            self.stdout.write(
                self.style.ERROR('Error: Must provide either --scan-id or --finding-id')
            )
            return

        if scan_id and finding_id:
            self.stdout.write(
                self.style.ERROR('Error: Cannot provide both --scan-id and --finding-id')
            )
            return

        self.stdout.write(
            self.style.WARNING('Testing LLM adjudication...')
        )
        self.stdout.write(f'  Provider: {provider}')
        self.stdout.write(f'  Model: {model}')

        try:
            if finding_id:
                # Test single finding
                self._test_single_finding(finding_id, provider, model)
            else:
                # Test scan findings
                self._test_scan_findings(
                    scan_id,
                    provider,
                    model,
                    options['batch_size'],
                    options['max_findings'],
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Test failed: {e}'))
            logger.error(f"Adjudication test failed: {e}", exc_info=True)
            raise

    def _test_single_finding(
        self,
        finding_id: str,
        provider: str,
        model: str,
    ):
        """Test adjudication on a single finding."""
        # Verify finding exists
        try:
            finding = Finding.objects.get(id=finding_id)
        except Finding.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Error: Finding {finding_id} not found')
            )
            return

        self.stdout.write(f'\nFinding details:')
        self.stdout.write(f'  Rule: {finding.rule_id}')
        self.stdout.write(f'  File: {finding.file_path}:{finding.start_line}')
        self.stdout.write(f'  Severity: {finding.severity}')
        self.stdout.write(f'  Tool: {finding.tool_name}')

        # Run workflow
        result = asyncio.run(
            self.run_single_adjudication_workflow(
                finding_id=finding_id,
                provider=provider,
                model=model,
            )
        )

        if result.get('success'):
            self.stdout.write(self.style.SUCCESS('\n✓ Adjudication completed!'))
            self.stdout.write(f'\nVerdict:')
            self.stdout.write(f'  Decision: {result.get("verdict")}')
            self.stdout.write(f'  Confidence: {result.get("confidence", 0):.2f}')
            self.stdout.write(f'  Should filter: {result.get("should_filter")}')
            self.stdout.write(f'  Cost: ${result.get("cost_usd", 0):.6f}')
            self.stdout.write(f'  Time: {result.get("processing_time_ms", 0)}ms')

            # Get verdict details
            verdict_id = result.get('verdict_id')
            if verdict_id:
                verdict = LLMVerdict.objects.get(id=verdict_id)
                self.stdout.write(f'\nReasoning:')
                self.stdout.write(f'  {verdict.reasoning}')
                if verdict.recommendation:
                    self.stdout.write(f'\nRecommendation:')
                    self.stdout.write(f'  {verdict.recommendation}')
        else:
            self.stdout.write(
                self.style.ERROR(f'\n✗ Adjudication failed: {result.get("error")}')
            )

    def _test_scan_findings(
        self,
        scan_id: str,
        provider: str,
        model: str,
        batch_size: int,
        max_findings: int,
    ):
        """Test adjudication on all findings from a scan."""
        # Verify scan exists
        try:
            scan = Scan.objects.get(id=scan_id)
        except Scan.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Error: Scan {scan_id} not found')
            )
            return

        # Count findings
        findings = Finding.objects.filter(first_seen_scan=scan)
        total_findings = findings.count()
        unadjudicated = findings.exclude(llm_verdicts__isnull=False).count()

        self.stdout.write(f'\nScan details:')
        self.stdout.write(f'  Scan ID: {scan_id}')
        self.stdout.write(f'  Total findings: {total_findings}')
        self.stdout.write(f'  Unadjudicated: {unadjudicated}')
        self.stdout.write(f'  Will process: {min(unadjudicated, max_findings)}')
        self.stdout.write(f'  Batch size: {batch_size}')

        # Run workflow
        result = asyncio.run(
            self.run_adjudication_workflow(
                scan_id=scan_id,
                provider=provider,
                model=model,
                batch_size=batch_size,
                max_findings=max_findings,
            )
        )

        if result.get('success'):
            metrics = result.get('metrics', {})
            self.stdout.write(self.style.SUCCESS('\n✓ Adjudication completed!'))
            self.stdout.write(f'\nResults:')
            self.stdout.write(f'  Total processed: {result.get("total_processed", 0)}')
            self.stdout.write(f'  Successful: {result.get("successful", 0)}')
            self.stdout.write(f'  Failed: {result.get("failed", 0)}')

            self.stdout.write(f'\nVerdicts:')
            self.stdout.write(f'  True positives: {metrics.get("true_positives", 0)}')
            self.stdout.write(f'  False positives: {metrics.get("false_positives", 0)}')
            self.stdout.write(f'  Uncertain: {metrics.get("uncertain", 0)}')
            self.stdout.write(f'  Filtered (high-conf FP): {metrics.get("filtered_count", 0)}')

            self.stdout.write(f'\nPerformance:')
            self.stdout.write(f'  FP reduction rate: {metrics.get("fp_reduction_rate", 0):.1f}%')
            self.stdout.write(f'  Total cost: ${result.get("total_cost_usd", 0):.4f}')
            self.stdout.write(f'  Avg time: {metrics.get("avg_processing_time_ms", 0)}ms')

            self.stdout.write(f'\nView in Temporal UI:')
            self.stdout.write(f'  http://localhost:8233')
            self.stdout.write(f'\nView verdicts in Django admin:')
            self.stdout.write(f'  http://localhost:8000/admin/findings/llmverdict/')
        else:
            self.stdout.write(
                self.style.ERROR(f'\n✗ Adjudication failed: {result.get("error")}')
            )

    async def run_single_adjudication_workflow(
        self,
        finding_id: str,
        provider: str,
        model: str,
    ) -> dict:
        """Execute single finding adjudication workflow."""
        self.stdout.write('\nConnecting to Temporal server...')
        client = await Client.connect('localhost:7233')

        self.stdout.write('Starting adjudication workflow...')
        self.stdout.write('  Watch progress in Temporal UI: http://localhost:8233\n')

        result = await client.execute_workflow(
            AdjudicateSingleFindingWorkflow.run,
            args=[finding_id, provider, model],
            id=f'adjudicate-finding-{finding_id}',
            task_queue='code-analysis',
        )

        return result

    async def run_adjudication_workflow(
        self,
        scan_id: str,
        provider: str,
        model: str,
        batch_size: int,
        max_findings: int,
    ) -> dict:
        """Execute batch adjudication workflow."""
        self.stdout.write('\nConnecting to Temporal server...')
        client = await Client.connect('localhost:7233')

        self.stdout.write('Starting batch adjudication workflow...')
        self.stdout.write('  (This may take several minutes)')
        self.stdout.write('  Watch progress in Temporal UI: http://localhost:8233\n')

        result = await client.execute_workflow(
            AdjudicateFindingsWorkflow.run,
            args=[scan_id, provider, model, batch_size, max_findings],
            id=f'adjudicate-scan-{scan_id}',
            task_queue='code-analysis',
        )

        return result
