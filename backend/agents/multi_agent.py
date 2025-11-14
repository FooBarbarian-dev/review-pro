"""
Multi-agent collaboration system for security analysis.

Implements a three-agent pipeline:
1. Triage Agent (GPT-4o): Fast initial classification
2. Explainer Agent (Claude Sonnet): Detailed analysis and explanation
3. Fixer Agent (Claude Sonnet): Generate fix recommendations

Pattern: Multi-Agent Collaboration (Triage → Explainer → Fixer)
"""

import json
import logging
import re
import time
from decimal import Decimal
from typing import Dict, Optional

from agents.base_agent import AgentFactory

logger = logging.getLogger(__name__)


TRIAGE_PROMPT = """You are a security triage agent. Quickly classify this finding as:
- CRITICAL: Obvious security vulnerability, needs immediate attention
- REVIEW: Potential issue, needs detailed analysis
- FALSE_POSITIVE: Clearly not a security issue

Respond with JSON:
{
    "classification": "CRITICAL" | "REVIEW" | "FALSE_POSITIVE",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation"
}"""


EXPLAINER_PROMPT = """You are a security analysis expert. Provide a detailed explanation of this finding.

Analyze:
1. What is the vulnerability?
2. How can it be exploited?
3. What is the potential impact?
4. Is this a true positive or false positive?

Respond with JSON:
{
    "verdict": "true_positive" | "false_positive" | "uncertain",
    "confidence": 0.0-1.0,
    "explanation": "Detailed technical explanation",
    "cwe_id": "CWE-XXX" (if applicable),
    "severity_justification": "Why this severity is appropriate",
    "exploitability": "How this could be exploited",
    "impact": "Potential damage if exploited"
}"""


FIXER_PROMPT = """You are a security remediation expert. Generate a fix recommendation for this vulnerability.

Provide:
1. Specific code changes needed
2. Alternative approaches
3. Best practices to prevent similar issues

Respond with JSON:
{
    "fix_recommendation": "Detailed fix with code examples",
    "alternative_approaches": ["Alternative 1", "Alternative 2"],
    "prevention_guidance": "Best practices to avoid this",
    "estimated_effort": "LOW" | "MEDIUM" | "HIGH"
}"""


class MultiAgentAnalyzer:
    """
    Multi-agent system for comprehensive security analysis.

    Uses three specialized agents in sequence:
    1. Triage (GPT-4o): Fast classification
    2. Explainer (Claude Sonnet): Detailed analysis
    3. Fixer (Claude Sonnet): Fix recommendations
    """

    def __init__(self):
        """Initialize the multi-agent system."""
        # Triage agent: Fast, cost-effective
        self.triage_agent = AgentFactory.create_openai_agent(
            system_message=TRIAGE_PROMPT,
            model="gpt-4o",
            temperature=0.0,
            max_tokens=500,
        )

        # Explainer agent: Thorough, high-quality
        self.explainer_agent = AgentFactory.create_anthropic_agent(
            system_message=EXPLAINER_PROMPT,
            model="claude-sonnet-4-20250514",
            temperature=0.0,
            max_tokens=2000,
        )

        # Fixer agent: Detailed recommendations
        self.fixer_agent = AgentFactory.create_anthropic_agent(
            system_message=FIXER_PROMPT,
            model="claude-sonnet-4-20250514",
            temperature=0.0,
            max_tokens=2000,
        )

        logger.info("Initialized multi-agent system (GPT-4o + Claude Sonnet)")

    def adjudicate_finding(
        self,
        finding_description: str,
        code_snippet: str,
        file_path: str,
        line_number: int,
        tool_name: str,
        severity: str,
        rule_id: str,
    ) -> Dict:
        """
        Adjudicate a finding using the multi-agent pipeline.

        Args:
            finding_description: Description of issue
            code_snippet: Code context
            file_path: Path to file
            line_number: Line number
            tool_name: SA tool name
            severity: Severity level
            rule_id: Rule ID

        Returns:
            Dictionary with verdict and metadata
        """
        logger.info(
            f"Multi-agent analysis: {rule_id} at {file_path}:{line_number}"
        )

        start_time = time.time()

        # Build context for all agents
        context = f"""Tool: {tool_name}
Rule ID: {rule_id}
Severity: {severity}
Location: {file_path}:{line_number}
Finding: {finding_description}

Code Context:
```
{code_snippet or "No code snippet available"}
```"""

        try:
            # Phase 1: Triage
            triage_start = time.time()
            triage_response = self.triage_agent.llm_response(
                f"Classify this security finding:\n\n{context}"
            )
            triage_time = int((time.time() - triage_start) * 1000)

            triage_result = self._parse_json(triage_response.content)
            classification = triage_result.get('classification', 'REVIEW')

            logger.info(
                f"Triage: {classification} "
                f"(confidence: {triage_result.get('confidence', 0):.2f}, "
                f"time: {triage_time}ms)"
            )

            # Early exit for clear false positives
            if classification == 'FALSE_POSITIVE' and triage_result.get('confidence', 0) >= 0.9:
                processing_time_ms = int((time.time() - start_time) * 1000)

                return {
                    'verdict': 'false_positive',
                    'confidence': triage_result.get('confidence', 0.9),
                    'reasoning': f"Triage agent: {triage_result.get('reasoning', 'False positive')}",
                    'cwe_id': None,
                    'recommendation': None,
                    'llm_provider': 'multi_agent',
                    'llm_model': 'gpt-4o+claude-sonnet',
                    'agent_pattern': 'multi_agent',
                    'prompt_tokens': 500,  # Estimate
                    'completion_tokens': 200,
                    'total_tokens': 700,
                    'estimated_cost_usd': Decimal('0.0025'),
                    'processing_time_ms': processing_time_ms,
                    'raw_response': {
                        'triage': triage_result,
                        'explainer': None,
                        'fixer': None,
                        'pipeline': 'early_exit_after_triage',
                    },
                    'success': True,
                }

            # Phase 2: Detailed Explanation
            explainer_start = time.time()
            explainer_response = self.explainer_agent.llm_response(
                f"Analyze this security finding in detail:\n\n{context}\n\n"
                f"Triage classification: {classification} ({triage_result.get('reasoning', '')})"
            )
            explainer_time = int((time.time() - explainer_start) * 1000)

            explainer_result = self._parse_json(explainer_response.content)

            logger.info(
                f"Explainer: {explainer_result.get('verdict', 'unknown')} "
                f"(confidence: {explainer_result.get('confidence', 0):.2f}, "
                f"time: {explainer_time}ms)"
            )

            # Phase 3: Fix Recommendation (only for true positives)
            fixer_result = None
            fixer_time = 0

            if explainer_result.get('verdict') == 'true_positive':
                fixer_start = time.time()
                fixer_response = self.fixer_agent.llm_response(
                    f"Generate fix recommendation for this vulnerability:\n\n{context}\n\n"
                    f"Analysis: {explainer_result.get('explanation', '')}"
                )
                fixer_time = int((time.time() - fixer_start) * 1000)

                fixer_result = self._parse_json(fixer_response.content)

                logger.info(
                    f"Fixer: Generated recommendation "
                    f"(effort: {fixer_result.get('estimated_effort', 'UNKNOWN')}, "
                    f"time: {fixer_time}ms)"
                )

            processing_time_ms = int((time.time() - start_time) * 1000)

            # Combine results
            recommendation = None
            if fixer_result:
                recommendation = fixer_result.get('fix_recommendation', '')
                # Add alternative approaches
                alternatives = fixer_result.get('alternative_approaches', [])
                if alternatives:
                    recommendation += "\n\nAlternative approaches:\n"
                    recommendation += "\n".join(f"- {alt}" for alt in alternatives)

            # Estimate tokens and cost
            total_tokens = 2000  # Rough estimate
            estimated_cost = Decimal('0.015')  # ~$0.015 for full pipeline

            return {
                'verdict': explainer_result.get('verdict', 'uncertain'),
                'confidence': explainer_result.get('confidence', 0.5),
                'reasoning': explainer_result.get('explanation', ''),
                'cwe_id': explainer_result.get('cwe_id'),
                'recommendation': recommendation,
                'llm_provider': 'multi_agent',
                'llm_model': 'gpt-4o+claude-sonnet',
                'agent_pattern': 'multi_agent',
                'prompt_tokens': total_tokens // 2,
                'completion_tokens': total_tokens // 2,
                'total_tokens': total_tokens,
                'estimated_cost_usd': estimated_cost,
                'processing_time_ms': processing_time_ms,
                'raw_response': {
                    'triage': triage_result,
                    'explainer': explainer_result,
                    'fixer': fixer_result,
                    'pipeline': 'full_pipeline',
                    'timing': {
                        'triage_ms': triage_time,
                        'explainer_ms': explainer_time,
                        'fixer_ms': fixer_time,
                    },
                },
                'success': True,
            }

        except Exception as e:
            logger.error(f"Multi-agent analysis failed: {e}", exc_info=True)
            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                'success': False,
                'error': str(e),
                'processing_time_ms': processing_time_ms,
                'llm_provider': 'multi_agent',
                'llm_model': 'gpt-4o+claude-sonnet',
                'agent_pattern': 'multi_agent',
            }

    def _parse_json(self, response_text: str) -> Dict:
        """Parse JSON from LLM response."""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract from markdown
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # Fallback
            logger.warning(f"Could not parse JSON from response: {response_text[:200]}")
            return {}
