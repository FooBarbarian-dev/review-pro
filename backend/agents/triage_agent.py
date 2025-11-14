"""
Triage agent for initial security finding classification.

Uses GPT-4o for fast, cost-effective triage of security findings.
Pattern: Post-Processing Filter (SA Tool → LLM Filter)
"""

import logging
from typing import Optional

from agents.base_agent import AgentFactory

logger = logging.getLogger(__name__)


TRIAGE_SYSTEM_PROMPT = """You are a security expert analyzing static analysis findings to filter false positives.

Your task is to determine if a security finding is a true positive or false positive based on:
1. The finding description and severity
2. The code context where the issue was detected
3. Common false positive patterns in static analysis tools

Respond with a JSON object:
{
    "verdict": "true_positive" | "false_positive" | "uncertain",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of your decision",
    "cwe_id": "CWE-XXX" (if applicable),
    "recommendation": "Brief fix suggestion for true positives"
}

Be conservative: mark as "uncertain" if you need more context.
"""


class TriageAgent:
    """Agent for triaging security findings using GPT-4o."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0.0):
        """
        Initialize the triage agent.

        Args:
            model: OpenAI model to use (default: gpt-4o)
            temperature: Sampling temperature (0.0 = deterministic)
        """
        self.agent = AgentFactory.create_openai_agent(
            system_message=TRIAGE_SYSTEM_PROMPT,
            model=model,
            temperature=temperature,
            max_tokens=1000,
        )
        self.model = model

    async def analyze_finding(
        self,
        finding_description: str,
        code_snippet: str,
        file_path: str,
        line_number: int,
        tool_name: str,
    ) -> dict:
        """
        Analyze a security finding to determine if it's a true positive.

        Args:
            finding_description: Description of the security issue
            code_snippet: Code context around the finding
            file_path: Path to the file containing the issue
            line_number: Line number where issue was detected
            tool_name: Name of the static analysis tool that found it

        Returns:
            Dictionary with verdict, confidence, and reasoning
        """
        # Construct analysis prompt
        prompt = f"""Analyze this security finding:

Tool: {tool_name}
File: {file_path}:{line_number}
Finding: {finding_description}

Code Context:
```
{code_snippet}
```

Is this a true positive or false positive?"""

        logger.info(
            f"Triaging finding from {tool_name} at {file_path}:{line_number}"
        )

        # Get LLM response
        response = self.agent.llm_response(prompt)

        logger.info(f"Triage complete: {response.content[:100]}...")

        return {
            'llm_response': response.content,
            'model': self.model,
            'tool': tool_name,
            'file': file_path,
            'line': line_number,
        }

    def test_connection(self) -> dict:
        """
        Test the connection to the LLM API.

        Returns:
            Dictionary with test results
        """
        try:
            response = self.agent.llm_response("Say 'Hello from Langroid!'")
            return {
                'success': True,
                'model': self.model,
                'response': response.content,
            }
        except Exception as e:
            logger.error(f"LLM connection test failed: {e}")
            return {
                'success': False,
                'error': str(e),
            }
