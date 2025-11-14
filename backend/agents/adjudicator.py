"""
Enhanced triage agent for security finding adjudication.

Uses LLMs to classify findings as true positives, false positives, or uncertain.
Implements the post-processing filter pattern with structured output.
"""

import json
import logging
import re
import time
from decimal import Decimal
from typing import Dict, Optional

from agents.base_agent import AgentFactory

logger = logging.getLogger(__name__)


ADJUDICATION_SYSTEM_PROMPT = """You are a security expert analyzing static analysis findings to filter false positives.

Your task is to determine if a security finding is a true positive, false positive, or uncertain based on:
1. The finding description and severity
2. The code context where the issue was detected
3. Common false positive patterns in static analysis tools
4. Best security practices

Guidelines:
- TRUE POSITIVE: Clear security vulnerability that should be fixed
- FALSE POSITIVE: The tool flagged safe code or a non-issue
- UNCERTAIN: Need more context or complex to determine

Respond ONLY with a valid JSON object (no markdown, no extra text):
{
    "verdict": "true_positive" | "false_positive" | "uncertain",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of your decision",
    "cwe_id": "CWE-XXX" (if applicable, or null),
    "recommendation": "Brief fix suggestion for true positives" (or null for false positives)
}

Be conservative: mark as "uncertain" if you need more context.
"""


class FindingAdjudicator:
    """
    Agent for adjudicating security findings using LLMs.

    Supports multiple LLM providers (OpenAI, Anthropic) and returns
    structured verdicts with confidence scores.
    """

    # Token pricing (USD per 1K tokens) - as of Jan 2025
    TOKEN_PRICES = {
        'gpt-4o': {'input': 0.0025, 'output': 0.01},
        'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
        'claude-sonnet-4-20250514': {'input': 0.003, 'output': 0.015},
        'claude-haiku-3-20250201': {'input': 0.00025, 'output': 0.00125},
    }

    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o",
        temperature: float = 0.0,
    ):
        """
        Initialize the adjudicator agent.

        Args:
            provider: LLM provider ("openai" or "anthropic")
            model: Model name (e.g., "gpt-4o", "claude-sonnet-4")
            temperature: Sampling temperature (0.0 = deterministic)
        """
        self.provider = provider
        self.model = model
        self.temperature = temperature

        # Create agent based on provider
        if provider == "openai":
            self.agent = AgentFactory.create_openai_agent(
                system_message=ADJUDICATION_SYSTEM_PROMPT,
                model=model,
                temperature=temperature,
                max_tokens=1000,
            )
        elif provider == "anthropic":
            self.agent = AgentFactory.create_anthropic_agent(
                system_message=ADJUDICATION_SYSTEM_PROMPT,
                model=model,
                temperature=temperature,
                max_tokens=1000,
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        logger.info(f"Initialized adjudicator with {provider}/{model}")

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
        Adjudicate a security finding to determine if it's a true positive.

        Args:
            finding_description: Description of the security issue
            code_snippet: Code context around the finding
            file_path: Path to the file containing the issue
            line_number: Line number where issue was detected
            tool_name: Name of the static analysis tool that found it
            severity: Severity level (critical, high, medium, low, info)
            rule_id: Rule ID from the static analysis tool

        Returns:
            Dictionary with verdict data and metadata
        """
        # Construct analysis prompt
        prompt = f"""Analyze this security finding:

Tool: {tool_name}
Rule ID: {rule_id}
Severity: {severity}
Location: {file_path}:{line_number}
Finding: {finding_description}

Code Context:
```
{code_snippet or "No code snippet available"}
```

Provide your verdict as JSON."""

        logger.info(
            f"Adjudicating finding: {rule_id} from {tool_name} "
            f"at {file_path}:{line_number}"
        )

        # Track timing
        start_time = time.time()

        try:
            # Get LLM response
            response = self.agent.llm_response(prompt)
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Parse JSON response
            verdict_data = self._parse_verdict(response.content)

            # Extract token usage (if available)
            token_data = self._extract_token_usage(response)

            # Calculate cost
            cost = self._calculate_cost(
                token_data['prompt_tokens'],
                token_data['completion_tokens']
            )

            logger.info(
                f"Verdict: {verdict_data['verdict']} "
                f"(confidence: {verdict_data['confidence']:.2f}, "
                f"time: {processing_time_ms}ms, "
                f"tokens: {token_data['total_tokens']}, "
                f"cost: ${cost:.6f})"
            )

            return {
                # Verdict details
                'verdict': verdict_data['verdict'],
                'confidence': verdict_data['confidence'],
                'reasoning': verdict_data['reasoning'],
                'cwe_id': verdict_data.get('cwe_id'),
                'recommendation': verdict_data.get('recommendation'),

                # LLM metadata
                'llm_provider': self.provider,
                'llm_model': self.model,
                'agent_pattern': 'post_processing',

                # Token usage
                'prompt_tokens': token_data['prompt_tokens'],
                'completion_tokens': token_data['completion_tokens'],
                'total_tokens': token_data['total_tokens'],
                'estimated_cost_usd': cost,

                # Performance
                'processing_time_ms': processing_time_ms,

                # Raw response
                'raw_response': {
                    'content': response.content,
                    'parsed': verdict_data,
                },

                # Success flag
                'success': True,
            }

        except Exception as e:
            logger.error(f"Adjudication failed: {e}", exc_info=True)
            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                'success': False,
                'error': str(e),
                'processing_time_ms': processing_time_ms,
                'llm_provider': self.provider,
                'llm_model': self.model,
            }

    def _parse_verdict(self, response_text: str) -> Dict:
        """
        Parse LLM response to extract verdict JSON.

        Args:
            response_text: Raw response from LLM

        Returns:
            Parsed verdict dictionary

        Raises:
            ValueError: If response cannot be parsed
        """
        try:
            # Try to parse as JSON directly
            verdict = json.loads(response_text)

            # Validate required fields
            if 'verdict' not in verdict:
                raise ValueError("Missing 'verdict' field")
            if 'confidence' not in verdict:
                raise ValueError("Missing 'confidence' field")
            if 'reasoning' not in verdict:
                raise ValueError("Missing 'reasoning' field")

            # Validate verdict value
            if verdict['verdict'] not in ['true_positive', 'false_positive', 'uncertain']:
                raise ValueError(f"Invalid verdict: {verdict['verdict']}")

            # Validate confidence range
            if not 0.0 <= verdict['confidence'] <= 1.0:
                raise ValueError(f"Confidence out of range: {verdict['confidence']}")

            return verdict

        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # Try to find JSON object in text
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))

            raise ValueError(f"Could not parse verdict from response: {response_text[:200]}")

    def _extract_token_usage(self, response) -> Dict:
        """
        Extract token usage from LLM response.

        Args:
            response: LLM response object

        Returns:
            Dictionary with token counts
        """
        # Try to extract from response metadata
        # (Langroid may expose this differently based on provider)
        try:
            if hasattr(response, 'usage'):
                usage = response.usage
                return {
                    'prompt_tokens': getattr(usage, 'prompt_tokens', 0),
                    'completion_tokens': getattr(usage, 'completion_tokens', 0),
                    'total_tokens': getattr(usage, 'total_tokens', 0),
                }
        except:
            pass

        # Estimate based on content length (rough approximation)
        # 1 token ≈ 4 characters for English text
        completion_tokens = len(response.content) // 4

        return {
            'prompt_tokens': 0,  # Don't have accurate prompt count
            'completion_tokens': completion_tokens,
            'total_tokens': completion_tokens,
        }

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> Decimal:
        """
        Calculate estimated cost for LLM call.

        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Estimated cost in USD
        """
        if self.model not in self.TOKEN_PRICES:
            logger.warning(f"No pricing data for model: {self.model}")
            return Decimal('0.0')

        pricing = self.TOKEN_PRICES[self.model]

        prompt_cost = (prompt_tokens / 1000) * pricing['input']
        completion_cost = (completion_tokens / 1000) * pricing['output']

        return Decimal(str(prompt_cost + completion_cost))

    def test_connection(self) -> Dict:
        """
        Test the connection to the LLM API.

        Returns:
            Dictionary with test results
        """
        try:
            response = self.agent.llm_response("Say 'Hello from Langroid!'")
            return {
                'success': True,
                'provider': self.provider,
                'model': self.model,
                'response': response.content,
            }
        except Exception as e:
            logger.error(f"LLM connection test failed: {e}")
            return {
                'success': False,
                'provider': self.provider,
                'model': self.model,
                'error': str(e),
            }
