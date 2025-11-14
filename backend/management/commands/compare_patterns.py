"""
Django management command to compare agent patterns empirically.

Usage:
    # Compare all patterns on a scan
    python manage.py compare_patterns --scan-id <uuid>

    # Compare specific patterns
    python manage.py compare_patterns --scan-id <uuid> --patterns post_processing multi_agent

    # Limit findings for faster testing
    python manage.py compare_patterns --scan-id <uuid> --max-findings 10
"""

import asyncio
import logging
from django.core.management.base import BaseCommand
from temporalio.client import Client

from apps.scans.models import Scan
from workflows.pattern_comparison_workflow import CompareAgentPatternsWorkflow

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Compare agent patterns (post-processing, interactive, multi-agent) empirically'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scan-id',
            type=str,
            required=True,
            help='Scan ID to compare patterns on',
        )
        parser.add_argument(
            '--patterns',
            nargs='+',
            choices=['post_processing', 'interactive', 'multi_agent'],
            default=['post_processing', 'interactive', 'multi_agent'],
            help='Patterns to compare (default: all)',
        )
        parser.add_argument(
            '--max-findings',
            type=int,
            default=10,
            help='Maximum findings to compare (default: 10)',
        )

    def handle(self, *args, **options):
        """Execute the command."""
        scan_id = options['scan_id']
        patterns = options['patterns']
        max_findings = options['max_findings']

        # Verify scan exists
        try:
            scan = Scan.objects.get(id=scan_id)
        except Scan.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Error: Scan {scan_id} not found')
            )
            return

        self.stdout.write(
            self.style.WARNING('Comparing agent patterns...')
        )
        self.stdout.write(f'  Scan ID: {scan_id}')
        self.stdout.write(f'  Patterns: {", ".join(patterns)}')
        self.stdout.write(f'  Max findings: {max_findings}')

        try:
            # Run workflow
            result = asyncio.run(
                self.run_comparison_workflow(
                    scan_id=scan_id,
                    patterns=patterns,
                    max_findings=max_findings,
                )
            )

            if result.get('success'):
                self.stdout.write(self.style.SUCCESS('\n✓ Comparison completed!'))

                self.stdout.write(f'\nResults:')
                self.stdout.write(f'  Total findings: {result.get("total_findings", 0)}')
                self.stdout.write(f'  Successful: {result.get("successful", 0)}')
                self.stdout.write(f'  Failed: {result.get("failed", 0)}')

                # Display metrics for each pattern
                metrics = result.get('metrics', {})

                if metrics:
                    self.stdout.write(f'\n{"Pattern":<20} {"TP":<6} {"FP":<6} {"Unc":<6} {"FP%":<8} {"Cost":<10} {"Time":<10}')
                    self.stdout.write('-' * 80)

                    for pattern_name, pattern_metrics in metrics.items():
                        tp = pattern_metrics.get('true_positives', 0)
                        fp = pattern_metrics.get('false_positives', 0)
                        unc = pattern_metrics.get('uncertain', 0)
                        fp_rate = pattern_metrics.get('false_positive_reduction_rate', 0)
                        cost = pattern_metrics.get('avg_cost_per_finding', 0)
                        time_ms = pattern_metrics.get('avg_time_per_finding_ms', 0)

                        self.stdout.write(
                            f'{pattern_name:<20} '
                            f'{tp:<6} '
                            f'{fp:<6} '
                            f'{unc:<6} '
                            f'{fp_rate:<7.1f}% '
                            f'${cost:<9.4f} '
                            f'{time_ms:<9}ms'
                        )

                    # Analysis
                    self.stdout.write('\nAnalysis:')

                    # Find best pattern by FP reduction
                    best_fp_reduction = max(
                        metrics.items(),
                        key=lambda x: x[1].get('false_positive_reduction_rate', 0)
                    )
                    self.stdout.write(
                        f'  Best FP reduction: {best_fp_reduction[0]} '
                        f'({best_fp_reduction[1].get("false_positive_reduction_rate", 0):.1f}%)'
                    )

                    # Find fastest pattern
                    fastest = min(
                        metrics.items(),
                        key=lambda x: x[1].get('avg_time_per_finding_ms', float('inf'))
                    )
                    self.stdout.write(
                        f'  Fastest: {fastest[0]} '
                        f'({fastest[1].get("avg_time_per_finding_ms", 0)}ms avg)'
                    )

                    # Find cheapest pattern
                    cheapest = min(
                        metrics.items(),
                        key=lambda x: x[1].get('avg_cost_per_finding', float('inf'))
                    )
                    self.stdout.write(
                        f'  Cheapest: {cheapest[0]} '
                        f'(${cheapest[1].get("avg_cost_per_finding", 0):.4f} per finding)'
                    )

                self.stdout.write(f'\nView in Temporal UI:')
                self.stdout.write(f'  http://localhost:8233')
                self.stdout.write(f'\nView verdicts in Django admin:')
                self.stdout.write(f'  http://localhost:8000/admin/findings/llmverdict/')

            else:
                self.stdout.write(
                    self.style.ERROR(f'\n✗ Comparison failed: {result.get("error")}')
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Comparison failed: {e}'))
            logger.error(f"Pattern comparison failed: {e}", exc_info=True)
            raise

    async def run_comparison_workflow(
        self,
        scan_id: str,
        patterns: list,
        max_findings: int,
    ) -> dict:
        """
        Execute the pattern comparison workflow.

        Args:
            scan_id: UUID of the scan
            patterns: List of patterns to compare
            max_findings: Maximum findings to compare

        Returns:
            Workflow result dictionary
        """
        self.stdout.write('\nConnecting to Temporal server...')
        client = await Client.connect('localhost:7233')

        self.stdout.write('Starting pattern comparison workflow...')
        self.stdout.write('  (This may take several minutes)')
        self.stdout.write('  Watch progress in Temporal UI: http://localhost:8233\n')

        result = await client.execute_workflow(
            CompareAgentPatternsWorkflow.run,
            args=[scan_id, patterns, max_findings],
            id=f'compare-patterns-{scan_id}',
            task_queue='code-analysis',
        )

        return result
