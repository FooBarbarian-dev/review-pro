"""
Workflow for comparing agent patterns empirically.

Runs all three patterns on a set of findings and compares results.
"""

import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import Dict, List

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

# Django setup
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.findings.models import Finding, LLMVerdict
from apps.scans.models import Scan
from agents.pattern_comparison import PatternComparator, PatternResult


@activity.defn
async def compare_finding_with_patterns(
    finding_id: str,
    patterns_to_test: List[str],
) -> Dict:
    """
    Run all patterns on a single finding.

    Args:
        finding_id: UUID of the Finding
        patterns_to_test: List of patterns to test

    Returns:
        Comparison results
    """
    activity.logger.info(f"Comparing patterns for finding {finding_id}")

    try:
        finding = Finding.objects.get(id=finding_id)

        # Create comparator
        comparator = PatternComparator()

        # Run comparison
        results = comparator.compare_on_finding(
            finding_description=finding.message,
            code_snippet=finding.snippet or "No code snippet",
            file_path=finding.file_path,
            line_number=finding.start_line,
            tool_name=finding.tool_name,
            severity=finding.severity,
            rule_id=finding.rule_id,
            patterns_to_test=patterns_to_test,
        )

        # Store verdicts in database
        stored_verdicts = {}

        for pattern_name, result in results.items():
            if result.success:
                verdict = LLMVerdict.objects.create(
                    finding=finding,
                    verdict=result.verdict,
                    confidence=result.confidence,
                    reasoning=result.reasoning,
                    llm_provider='comparison',
                    llm_model=f'{pattern_name}_pattern',
                    agent_pattern=pattern_name,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    estimated_cost_usd=result.estimated_cost_usd,
                    processing_time_ms=result.processing_time_ms,
                    raw_response=result.metadata or {},
                )

                stored_verdicts[pattern_name] = str(verdict.id)

        # Convert results to serializable format
        results_dict = {}
        for pattern_name, result in results.items():
            results_dict[pattern_name] = {
                'verdict': result.verdict,
                'confidence': result.confidence,
                'reasoning': result.reasoning[:200],  # Truncate for size
                'processing_time_ms': result.processing_time_ms,
                'estimated_cost_usd': float(result.estimated_cost_usd),
                'success': result.success,
                'error': result.error,
            }

        return {
            'success': True,
            'finding_id': str(finding_id),
            'results': results_dict,
            'verdict_ids': stored_verdicts,
        }

    except Finding.DoesNotExist:
        activity.logger.error(f"Finding {finding_id} not found")
        return {
            'success': False,
            'finding_id': str(finding_id),
            'error': 'Finding not found',
        }
    except Exception as e:
        activity.logger.error(f"Pattern comparison failed: {e}", exc_info=True)
        return {
            'success': False,
            'finding_id': str(finding_id),
            'error': str(e),
        }


@activity.defn
async def calculate_pattern_metrics(
    scan_id: str,
    pattern_names: List[str],
) -> Dict:
    """
    Calculate comparative metrics for all patterns.

    Args:
        scan_id: UUID of the Scan
        pattern_names: List of patterns to evaluate

    Returns:
        Metrics for each pattern
    """
    activity.logger.info(f"Calculating pattern metrics for scan {scan_id}")

    try:
        scan = Scan.objects.get(id=scan_id)

        metrics = {}

        for pattern_name in pattern_names:
            # Get verdicts for this pattern
            verdicts = LLMVerdict.objects.filter(
                finding__first_seen_scan=scan,
                agent_pattern=pattern_name,
            )

            if not verdicts.exists():
                continue

            # Calculate stats
            total = verdicts.count()
            tp = verdicts.filter(verdict='true_positive').count()
            fp = verdicts.filter(verdict='false_positive').count()
            uncertain = verdicts.filter(verdict='uncertain').count()

            total_cost = sum(float(v.estimated_cost_usd) for v in verdicts)
            avg_cost = total_cost / total if total > 0 else 0.0

            total_time = sum(v.processing_time_ms for v in verdicts)
            avg_time = total_time // total if total > 0 else 0

            fp_reduction_rate = (fp / total * 100) if total > 0 else 0.0

            metrics[pattern_name] = {
                'total_findings': total,
                'true_positives': tp,
                'false_positives': fp,
                'uncertain': uncertain,
                'total_cost_usd': total_cost,
                'avg_cost_per_finding': avg_cost,
                'total_time_ms': total_time,
                'avg_time_per_finding_ms': avg_time,
                'false_positive_reduction_rate': fp_reduction_rate,
            }

        return {
            'success': True,
            'metrics': metrics,
        }

    except Scan.DoesNotExist:
        return {
            'success': False,
            'error': 'Scan not found',
        }
    except Exception as e:
        activity.logger.error(f"Metrics calculation failed: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
        }


@workflow.defn
class CompareAgentPatternsWorkflow:
    """
    Workflow for empirical comparison of agent patterns.

    Runs multiple patterns on findings and compares:
    - Accuracy (precision, recall, F1)
    - Cost (USD per finding)
    - Latency (ms per finding)
    - False positive reduction rate
    """

    @workflow.run
    async def run(
        self,
        scan_id: str,
        patterns_to_test: List[str] = None,
        max_findings: int = 20,
    ) -> Dict:
        """
        Execute pattern comparison.

        Args:
            scan_id: UUID of scan to analyze
            patterns_to_test: List of patterns (default: all)
            max_findings: Max findings to test

        Returns:
            Comparison results with metrics
        """
        if patterns_to_test is None:
            patterns_to_test = ['post_processing', 'interactive', 'multi_agent']

        workflow.logger.info(
            f"Starting pattern comparison for scan {scan_id}"
        )

        # Get finding IDs (reuse from adjudication workflow)
        from workflows.adjudication_workflow import get_scan_findings

        finding_ids = await workflow.execute_activity(
            get_scan_findings,
            args=[scan_id, max_findings],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        if not finding_ids:
            return {
                'success': False,
                'error': 'No findings to compare',
            }

        workflow.logger.info(
            f"Comparing {len(finding_ids)} findings across {len(patterns_to_test)} patterns"
        )

        # Compare each finding with all patterns
        results = []

        for finding_id in finding_ids:
            result = await workflow.execute_activity(
                compare_finding_with_patterns,
                args=[finding_id, patterns_to_test],
                start_to_close_timeout=timedelta(minutes=3),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )

            results.append(result)

        # Calculate metrics
        metrics_result = await workflow.execute_activity(
            calculate_pattern_metrics,
            args=[scan_id, patterns_to_test],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        # Summarize
        successful = sum(1 for r in results if r.get('success'))
        failed = len(results) - successful

        return {
            'success': True,
            'scan_id': scan_id,
            'patterns_tested': patterns_to_test,
            'total_findings': len(results),
            'successful': successful,
            'failed': failed,
            'metrics': metrics_result.get('metrics', {}),
        }
