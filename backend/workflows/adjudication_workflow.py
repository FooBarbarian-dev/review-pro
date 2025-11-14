"""
Adjudication workflow for LLM-based finding triage.

This workflow processes security findings through LLM agents to determine
if they are true positives, false positives, or uncertain.

Pattern: Post-Processing Filter (SA Tool → LLM Filter)
"""

import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import Dict, List

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

# Django setup for activities
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.findings.models import Finding, LLMVerdict
from apps.scans.models import Scan
from agents.adjudicator import FindingAdjudicator


@activity.defn
async def adjudicate_finding(
    finding_id: str,
    provider: str = "openai",
    model: str = "gpt-4o",
) -> Dict:
    """
    Adjudicate a single finding using an LLM.

    Args:
        finding_id: UUID of the Finding object
        provider: LLM provider (openai, anthropic)
        model: Model name

    Returns:
        Dictionary with adjudication results
    """
    activity.logger.info(f"Adjudicating finding {finding_id}")

    try:
        # Get finding from database
        finding = Finding.objects.get(id=finding_id)

        # Create adjudicator
        adjudicator = FindingAdjudicator(
            provider=provider,
            model=model,
            temperature=0.0,
        )

        # Adjudicate
        result = adjudicator.adjudicate_finding(
            finding_description=finding.message,
            code_snippet=finding.snippet or "No code snippet available",
            file_path=finding.file_path,
            line_number=finding.start_line,
            tool_name=finding.tool_name,
            severity=finding.severity,
            rule_id=finding.rule_id,
        )

        if not result.get('success'):
            return {
                'success': False,
                'finding_id': str(finding_id),
                'error': result.get('error'),
            }

        # Store verdict in database
        verdict = LLMVerdict.objects.create(
            finding=finding,
            verdict=result['verdict'],
            confidence=result['confidence'],
            reasoning=result['reasoning'],
            cwe_id=result.get('cwe_id'),
            recommendation=result.get('recommendation'),
            llm_provider=result['llm_provider'],
            llm_model=result['llm_model'],
            agent_pattern=result['agent_pattern'],
            prompt_tokens=result['prompt_tokens'],
            completion_tokens=result['completion_tokens'],
            total_tokens=result['total_tokens'],
            estimated_cost_usd=result['estimated_cost_usd'],
            processing_time_ms=result['processing_time_ms'],
            raw_response=result.get('raw_response'),
        )

        activity.logger.info(
            f"Verdict stored: {verdict.verdict} "
            f"(confidence: {verdict.confidence:.2f})"
        )

        # Update finding status if high-confidence false positive
        if verdict.should_filter:
            finding.status = 'false_positive'
            finding.save(update_fields=['status'])
            activity.logger.info(
                f"Finding marked as false positive (confidence >= 0.7)"
            )

        return {
            'success': True,
            'finding_id': str(finding_id),
            'verdict_id': str(verdict.id),
            'verdict': result['verdict'],
            'confidence': result['confidence'],
            'should_filter': verdict.should_filter,
            'cost_usd': float(result['estimated_cost_usd']),
            'processing_time_ms': result['processing_time_ms'],
        }

    except Finding.DoesNotExist:
        activity.logger.error(f"Finding {finding_id} not found")
        return {
            'success': False,
            'finding_id': str(finding_id),
            'error': f'Finding {finding_id} not found',
        }
    except Exception as e:
        activity.logger.error(f"Adjudication failed: {e}", exc_info=True)
        return {
            'success': False,
            'finding_id': str(finding_id),
            'error': str(e),
        }


@activity.defn
async def get_scan_findings(scan_id: str, limit: int = 100) -> List[str]:
    """
    Get finding IDs for a scan.

    Args:
        scan_id: UUID of the Scan object
        limit: Maximum number of findings to return

    Returns:
        List of finding IDs
    """
    activity.logger.info(f"Fetching findings for scan {scan_id}")

    try:
        scan = Scan.objects.get(id=scan_id)

        # Get findings without LLM verdicts
        findings = Finding.objects.filter(
            first_seen_scan=scan
        ).exclude(
            llm_verdicts__isnull=False
        )[:limit]

        finding_ids = [str(f.id) for f in findings]

        activity.logger.info(
            f"Found {len(finding_ids)} findings without verdicts"
        )

        return finding_ids

    except Scan.DoesNotExist:
        activity.logger.error(f"Scan {scan_id} not found")
        return []
    except Exception as e:
        activity.logger.error(f"Failed to fetch findings: {e}", exc_info=True)
        return []


@activity.defn
async def calculate_adjudication_metrics(scan_id: str) -> Dict:
    """
    Calculate metrics for adjudication results.

    Args:
        scan_id: UUID of the Scan object

    Returns:
        Dictionary with metrics
    """
    activity.logger.info(f"Calculating metrics for scan {scan_id}")

    try:
        scan = Scan.objects.get(id=scan_id)

        # Get all findings for this scan
        findings = Finding.objects.filter(first_seen_scan=scan)
        total_findings = findings.count()

        # Get findings with verdicts
        verdicts = LLMVerdict.objects.filter(finding__first_seen_scan=scan)
        adjudicated_count = verdicts.count()

        # Count by verdict type
        true_positives = verdicts.filter(verdict='true_positive').count()
        false_positives = verdicts.filter(verdict='false_positive').count()
        uncertain = verdicts.filter(verdict='uncertain').count()

        # Count high-confidence false positives (should be filtered)
        filtered_count = verdicts.filter(
            verdict='false_positive',
            confidence__gte=0.7
        ).count()

        # Calculate total cost
        total_cost = sum(
            float(v.estimated_cost_usd) for v in verdicts
        )

        # Calculate average processing time
        avg_time_ms = (
            sum(v.processing_time_ms for v in verdicts) / adjudicated_count
            if adjudicated_count > 0 else 0
        )

        # Calculate false positive reduction rate
        fp_reduction_rate = (
            (filtered_count / total_findings * 100)
            if total_findings > 0 else 0
        )

        metrics = {
            'total_findings': total_findings,
            'adjudicated_count': adjudicated_count,
            'true_positives': true_positives,
            'false_positives': false_positives,
            'uncertain': uncertain,
            'filtered_count': filtered_count,
            'fp_reduction_rate': fp_reduction_rate,
            'total_cost_usd': total_cost,
            'avg_processing_time_ms': int(avg_time_ms),
        }

        activity.logger.info(
            f"Metrics: {adjudicated_count}/{total_findings} adjudicated, "
            f"{filtered_count} filtered ({fp_reduction_rate:.1f}% reduction), "
            f"cost: ${total_cost:.4f}"
        )

        return {
            'success': True,
            'metrics': metrics,
        }

    except Scan.DoesNotExist:
        activity.logger.error(f"Scan {scan_id} not found")
        return {
            'success': False,
            'error': f'Scan {scan_id} not found',
        }
    except Exception as e:
        activity.logger.error(f"Failed to calculate metrics: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
        }


@workflow.defn
class AdjudicateFindingsWorkflow:
    """
    Workflow for adjudicating security findings with LLM.

    Processes findings from a scan through an LLM agent to determine
    if they are true positives or false positives.

    Pattern: Post-Processing Filter
    """

    @workflow.run
    async def run(
        self,
        scan_id: str,
        provider: str = "openai",
        model: str = "gpt-4o",
        batch_size: int = 10,
        max_findings: int = 100,
    ) -> Dict:
        """
        Execute the adjudication workflow.

        Args:
            scan_id: UUID of the Scan object
            provider: LLM provider (openai, anthropic)
            model: Model name (gpt-4o, claude-sonnet-4)
            batch_size: Number of findings to process in parallel
            max_findings: Maximum number of findings to process

        Returns:
            Workflow result dictionary
        """
        workflow.logger.info(
            f"Starting adjudication workflow for scan {scan_id}"
        )

        # Step 1: Get finding IDs
        finding_ids = await workflow.execute_activity(
            get_scan_findings,
            args=[scan_id, max_findings],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        if not finding_ids:
            workflow.logger.warning("No findings to adjudicate")
            return {
                'success': True,
                'adjudicated_count': 0,
                'message': 'No findings to adjudicate',
            }

        workflow.logger.info(f"Processing {len(finding_ids)} findings")

        # Step 2: Adjudicate findings in batches
        results = []
        for i in range(0, len(finding_ids), batch_size):
            batch = finding_ids[i:i + batch_size]

            workflow.logger.info(
                f"Processing batch {i // batch_size + 1} "
                f"({len(batch)} findings)"
            )

            # Process batch in parallel
            batch_tasks = [
                workflow.execute_activity(
                    adjudicate_finding,
                    args=[finding_id, provider, model],
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=RetryPolicy(
                        maximum_attempts=3,
                        initial_interval=timedelta(seconds=1),
                    ),
                )
                for finding_id in batch
            ]

            batch_results = await workflow.wait_for_all(*batch_tasks)
            results.extend(batch_results)

        # Step 3: Calculate metrics
        metrics_result = await workflow.execute_activity(
            calculate_adjudication_metrics,
            args=[scan_id],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        # Summarize results
        successful = sum(1 for r in results if r.get('success'))
        failed = len(results) - successful

        filtered = sum(1 for r in results if r.get('should_filter', False))
        total_cost = sum(r.get('cost_usd', 0) for r in results)

        workflow.logger.info(
            f"Adjudication complete: {successful} succeeded, "
            f"{failed} failed, {filtered} filtered, "
            f"cost: ${total_cost:.4f}"
        )

        return {
            'success': True,
            'scan_id': scan_id,
            'total_processed': len(results),
            'successful': successful,
            'failed': failed,
            'filtered': filtered,
            'total_cost_usd': total_cost,
            'metrics': metrics_result.get('metrics', {}),
        }


@workflow.defn
class AdjudicateSingleFindingWorkflow:
    """
    Simple workflow for adjudicating a single finding.

    Useful for testing and on-demand adjudication.
    """

    @workflow.run
    async def run(
        self,
        finding_id: str,
        provider: str = "openai",
        model: str = "gpt-4o",
    ) -> Dict:
        """
        Adjudicate a single finding.

        Args:
            finding_id: UUID of the Finding object
            provider: LLM provider
            model: Model name

        Returns:
            Adjudication result
        """
        workflow.logger.info(f"Adjudicating single finding: {finding_id}")

        result = await workflow.execute_activity(
            adjudicate_finding,
            args=[finding_id, provider, model],
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        return result
