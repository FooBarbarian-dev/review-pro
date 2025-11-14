"""
Framework for comparing agent patterns empirically.

Compares three patterns:
1. Post-Processing Filter: SA Tool → LLM Filter
2. Interactive Retrieval: LLM → Request Context → LLM
3. Multi-Agent Collaboration: Triage → Explainer → Fixer

Metrics: Precision, Recall, F1, Cost, Latency
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

from agents.adjudicator import FindingAdjudicator
from agents.interactive_agent import InteractiveRetrievalAgent
from agents.multi_agent import MultiAgentAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class PatternResult:
    """Result from a single pattern evaluation."""

    pattern_name: str
    verdict: str
    confidence: float
    reasoning: str
    processing_time_ms: int
    estimated_cost_usd: Decimal
    success: bool
    error: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class ComparisonMetrics:
    """Metrics for comparing patterns."""

    pattern_name: str

    # Performance metrics
    total_findings: int
    true_positives: int
    false_positives: int
    true_negatives: int  # Correctly identified FPs
    false_negatives: int  # Missed vulnerabilities
    uncertain: int

    # Derived metrics
    precision: float  # TP / (TP + FP)
    recall: float  # TP / (TP + FN)
    f1_score: float  # 2 * (precision * recall) / (precision + recall)
    accuracy: float  # (TP + TN) / total

    # Cost metrics
    total_cost_usd: Decimal
    avg_cost_per_finding: Decimal

    # Performance metrics
    total_time_ms: int
    avg_time_per_finding_ms: int

    # Filter effectiveness
    false_positive_reduction_rate: float  # % of findings filtered as FP


class PatternComparator:
    """
    Compare agent patterns on the same set of findings.

    Runs all three patterns and computes comparative metrics.
    """

    def __init__(self):
        """Initialize comparator with all three patterns."""
        self.patterns = {
            'post_processing': None,  # Initialized on demand
            'interactive': None,
            'multi_agent': None,
        }

        logger.info("Pattern comparator initialized")

    def compare_on_finding(
        self,
        finding_description: str,
        code_snippet: str,
        file_path: str,
        line_number: int,
        tool_name: str,
        severity: str,
        rule_id: str,
        patterns_to_test: Optional[List[str]] = None,
    ) -> Dict[str, PatternResult]:
        """
        Run all patterns on a single finding.

        Args:
            finding_description: Description of issue
            code_snippet: Code context
            file_path: Path to file
            line_number: Line number
            tool_name: SA tool name
            severity: Severity level
            rule_id: Rule ID
            patterns_to_test: List of patterns to test (default: all)

        Returns:
            Dictionary mapping pattern names to results
        """
        if patterns_to_test is None:
            patterns_to_test = ['post_processing', 'interactive', 'multi_agent']

        logger.info(
            f"Comparing patterns on {rule_id} at {file_path}:{line_number}"
        )

        results = {}

        # Test post-processing pattern
        if 'post_processing' in patterns_to_test:
            results['post_processing'] = self._test_post_processing(
                finding_description, code_snippet, file_path,
                line_number, tool_name, severity, rule_id
            )

        # Test interactive pattern
        if 'interactive' in patterns_to_test:
            results['interactive'] = self._test_interactive(
                finding_description, code_snippet, file_path,
                line_number, tool_name, severity, rule_id
            )

        # Test multi-agent pattern
        if 'multi_agent' in patterns_to_test:
            results['multi_agent'] = self._test_multi_agent(
                finding_description, code_snippet, file_path,
                line_number, tool_name, severity, rule_id
            )

        return results

    def _test_post_processing(
        self,
        finding_description: str,
        code_snippet: str,
        file_path: str,
        line_number: int,
        tool_name: str,
        severity: str,
        rule_id: str,
    ) -> PatternResult:
        """Test post-processing filter pattern."""
        try:
            if not self.patterns['post_processing']:
                self.patterns['post_processing'] = FindingAdjudicator(
                    provider="openai",
                    model="gpt-4o",
                )

            result = self.patterns['post_processing'].adjudicate_finding(
                finding_description=finding_description,
                code_snippet=code_snippet,
                file_path=file_path,
                line_number=line_number,
                tool_name=tool_name,
                severity=severity,
                rule_id=rule_id,
            )

            if result.get('success'):
                return PatternResult(
                    pattern_name='post_processing',
                    verdict=result['verdict'],
                    confidence=result['confidence'],
                    reasoning=result['reasoning'],
                    processing_time_ms=result['processing_time_ms'],
                    estimated_cost_usd=result['estimated_cost_usd'],
                    success=True,
                    metadata=result.get('raw_response'),
                )
            else:
                return PatternResult(
                    pattern_name='post_processing',
                    verdict='uncertain',
                    confidence=0.0,
                    reasoning='',
                    processing_time_ms=result.get('processing_time_ms', 0),
                    estimated_cost_usd=Decimal('0.0'),
                    success=False,
                    error=result.get('error'),
                )

        except Exception as e:
            logger.error(f"Post-processing test failed: {e}", exc_info=True)
            return PatternResult(
                pattern_name='post_processing',
                verdict='uncertain',
                confidence=0.0,
                reasoning='',
                processing_time_ms=0,
                estimated_cost_usd=Decimal('0.0'),
                success=False,
                error=str(e),
            )

    def _test_interactive(
        self,
        finding_description: str,
        code_snippet: str,
        file_path: str,
        line_number: int,
        tool_name: str,
        severity: str,
        rule_id: str,
    ) -> PatternResult:
        """Test interactive retrieval pattern."""
        try:
            if not self.patterns['interactive']:
                self.patterns['interactive'] = InteractiveRetrievalAgent(
                    provider="openai",
                    model="gpt-4o",
                )

            result = self.patterns['interactive'].adjudicate_finding(
                finding_description=finding_description,
                code_snippet=code_snippet,
                file_path=file_path,
                line_number=line_number,
                tool_name=tool_name,
                severity=severity,
                rule_id=rule_id,
            )

            if result.get('success'):
                return PatternResult(
                    pattern_name='interactive',
                    verdict=result['verdict'],
                    confidence=result['confidence'],
                    reasoning=result['reasoning'],
                    processing_time_ms=result['processing_time_ms'],
                    estimated_cost_usd=result.get('estimated_cost_usd', Decimal('0.0')),
                    success=True,
                    metadata=result.get('raw_response'),
                )
            else:
                return PatternResult(
                    pattern_name='interactive',
                    verdict='uncertain',
                    confidence=0.0,
                    reasoning='',
                    processing_time_ms=result.get('processing_time_ms', 0),
                    estimated_cost_usd=Decimal('0.0'),
                    success=False,
                    error=result.get('error'),
                )

        except Exception as e:
            logger.error(f"Interactive test failed: {e}", exc_info=True)
            return PatternResult(
                pattern_name='interactive',
                verdict='uncertain',
                confidence=0.0,
                reasoning='',
                processing_time_ms=0,
                estimated_cost_usd=Decimal('0.0'),
                success=False,
                error=str(e),
            )

    def _test_multi_agent(
        self,
        finding_description: str,
        code_snippet: str,
        file_path: str,
        line_number: int,
        tool_name: str,
        severity: str,
        rule_id: str,
    ) -> PatternResult:
        """Test multi-agent collaboration pattern."""
        try:
            if not self.patterns['multi_agent']:
                self.patterns['multi_agent'] = MultiAgentAnalyzer()

            result = self.patterns['multi_agent'].adjudicate_finding(
                finding_description=finding_description,
                code_snippet=code_snippet,
                file_path=file_path,
                line_number=line_number,
                tool_name=tool_name,
                severity=severity,
                rule_id=rule_id,
            )

            if result.get('success'):
                return PatternResult(
                    pattern_name='multi_agent',
                    verdict=result['verdict'],
                    confidence=result['confidence'],
                    reasoning=result['reasoning'],
                    processing_time_ms=result['processing_time_ms'],
                    estimated_cost_usd=result['estimated_cost_usd'],
                    success=True,
                    metadata=result.get('raw_response'),
                )
            else:
                return PatternResult(
                    pattern_name='multi_agent',
                    verdict='uncertain',
                    confidence=0.0,
                    reasoning='',
                    processing_time_ms=result.get('processing_time_ms', 0),
                    estimated_cost_usd=Decimal('0.0'),
                    success=False,
                    error=result.get('error'),
                )

        except Exception as e:
            logger.error(f"Multi-agent test failed: {e}", exc_info=True)
            return PatternResult(
                pattern_name='multi_agent',
                verdict='uncertain',
                confidence=0.0,
                reasoning='',
                processing_time_ms=0,
                estimated_cost_usd=Decimal('0.0'),
                success=False,
                error=str(e),
            )

    @staticmethod
    def calculate_metrics(
        pattern_name: str,
        results: List[PatternResult],
        ground_truth: Optional[List[str]] = None,
    ) -> ComparisonMetrics:
        """
        Calculate comparative metrics for a pattern.

        Args:
            pattern_name: Name of the pattern
            results: List of pattern results
            ground_truth: Optional list of ground truth verdicts

        Returns:
            ComparisonMetrics with all calculated metrics
        """
        total = len(results)

        # Count verdicts
        tp = sum(1 for r in results if r.verdict == 'true_positive')
        fp = sum(1 for r in results if r.verdict == 'false_positive')
        uncertain = sum(1 for r in results if r.verdict == 'uncertain')

        # If we have ground truth, calculate precision/recall
        if ground_truth and len(ground_truth) == len(results):
            # Compare with ground truth
            true_tp = sum(
                1 for i, r in enumerate(results)
                if r.verdict == 'true_positive' and ground_truth[i] == 'true_positive'
            )
            true_tn = sum(
                1 for i, r in enumerate(results)
                if r.verdict == 'false_positive' and ground_truth[i] == 'false_positive'
            )
            false_fp = sum(
                1 for i, r in enumerate(results)
                if r.verdict == 'false_positive' and ground_truth[i] == 'true_positive'
            )
            false_fn = sum(
                1 for i, r in enumerate(results)
                if r.verdict == 'true_positive' and ground_truth[i] == 'false_positive'
            )

            # Calculate metrics
            precision = true_tp / (true_tp + false_fp) if (true_tp + false_fp) > 0 else 0.0
            recall = true_tp / (true_tp + false_fn) if (true_tp + false_fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            accuracy = (true_tp + true_tn) / total if total > 0 else 0.0

        else:
            # Without ground truth, we can't calculate these precisely
            precision = recall = f1 = accuracy = 0.0
            true_tp = tp
            true_tn = fp
            false_fp = 0
            false_fn = 0

        # Cost metrics
        total_cost = sum(r.estimated_cost_usd for r in results)
        avg_cost = total_cost / total if total > 0 else Decimal('0.0')

        # Time metrics
        total_time = sum(r.processing_time_ms for r in results)
        avg_time = total_time // total if total > 0 else 0

        # FP reduction rate
        fp_reduction_rate = (fp / total * 100) if total > 0 else 0.0

        return ComparisonMetrics(
            pattern_name=pattern_name,
            total_findings=total,
            true_positives=true_tp,
            false_positives=false_fp,
            true_negatives=true_tn,
            false_negatives=false_fn,
            uncertain=uncertain,
            precision=precision,
            recall=recall,
            f1_score=f1,
            accuracy=accuracy,
            total_cost_usd=total_cost,
            avg_cost_per_finding=avg_cost,
            total_time_ms=total_time,
            avg_time_per_finding_ms=avg_time,
            false_positive_reduction_rate=fp_reduction_rate,
        )
