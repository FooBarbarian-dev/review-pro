"""
Interactive retrieval agent for dynamic context gathering.

This agent can request additional code context when analyzing findings,
implementing the interactive retrieval pattern where the LLM dynamically
determines what information it needs.

Pattern: Interactive Retrieval (LLM → Request Context → LLM)
"""

import json
import logging
import re
import time
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from langroid.agent.chat_agent import ChatAgent, ChatAgentConfig
from langroid.agent.tool_message import ToolMessage
from langroid.language_models.openai_gpt import OpenAIGPTConfig

logger = logging.getLogger(__name__)


class GetCodeContextTool(ToolMessage):
    """Tool for requesting additional code context."""

    request: str = "get_code_context"
    purpose: str = """
    Request additional code context to better analyze a security finding.
    Use this when you need more information about:
    - Function definitions
    - Class definitions
    - Variable usage
    - Imports and dependencies
    """

    file_path: str
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    line_range: Optional[tuple] = None

    @classmethod
    def examples(cls) -> List["ToolMessage"]:
        return [
            cls(
                file_path="app/database.py",
                function_name="execute_query",
            ),
            cls(
                file_path="app/models.py",
                class_name="User",
            ),
            cls(
                file_path="app/utils.py",
                line_range=(10, 50),
            ),
        ]


class GetImportsTool(ToolMessage):
    """Tool for checking imports and dependencies."""

    request: str = "get_imports"
    purpose: str = """
    Check what modules and functions are imported in a file.
    Use this to understand dependencies and available utilities.
    """

    file_path: str


class GetCallersTool(ToolMessage):
    """Tool for finding where a function is called."""

    request: str = "get_callers"
    purpose: str = """
    Find where a function is called to understand its usage context.
    Use this to determine if user input reaches a vulnerable function.
    """

    function_name: str
    file_path: str


INTERACTIVE_SYSTEM_PROMPT = """You are a security expert analyzing code to identify true vulnerabilities.

You have access to tools to request additional code context:
- get_code_context: Get function/class definitions or specific line ranges
- get_imports: Check what modules are imported
- get_callers: Find where a function is called

Process:
1. Review the initial finding and code snippet
2. If you need more context, use the tools to request it
3. After gathering sufficient context, make your verdict

Respond with JSON:
{
    "verdict": "true_positive" | "false_positive" | "uncertain",
    "confidence": 0.0-1.0,
    "reasoning": "Explanation based on gathered context",
    "cwe_id": "CWE-XXX" (if applicable),
    "recommendation": "Fix suggestion"
}
"""


class InteractiveRetrievalAgent:
    """
    Agent that dynamically requests code context during analysis.

    Implements the interactive retrieval pattern where the LLM decides
    what additional information it needs to make an accurate assessment.
    """

    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o",
        code_root: Optional[Path] = None,
    ):
        """
        Initialize interactive agent.

        Args:
            provider: LLM provider
            model: Model name
            code_root: Root directory of code being analyzed
        """
        self.provider = provider
        self.model = model
        self.code_root = code_root

        # Create Langroid agent with tools
        if provider == "openai":
            llm_config = OpenAIGPTConfig(
                chat_model=model,
                chat_context_length=128000,
                temperature=0.0,
                max_output_tokens=2000,
            )

            agent_config = ChatAgentConfig(
                name=f"InteractiveAgent-{model}",
                llm=llm_config,
                system_message=INTERACTIVE_SYSTEM_PROMPT,
            )

            self.agent = ChatAgent(agent_config)

            # Enable tools
            self.agent.enable_message(GetCodeContextTool)
            self.agent.enable_message(GetImportsTool)
            self.agent.enable_message(GetCallersTool)
        else:
            raise ValueError(f"Provider {provider} not yet supported for interactive agent")

        logger.info(f"Initialized interactive agent with {provider}/{model}")

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
        Adjudicate a finding with interactive context retrieval.

        Args:
            finding_description: Description of issue
            code_snippet: Initial code context
            file_path: Path to file
            line_number: Line number
            tool_name: SA tool name
            severity: Severity level
            rule_id: Rule ID

        Returns:
            Dictionary with verdict and metadata
        """
        logger.info(
            f"Interactive adjudication: {rule_id} at {file_path}:{line_number}"
        )

        # Build initial prompt
        initial_prompt = f"""Analyze this security finding:

Tool: {tool_name}
Rule ID: {rule_id}
Severity: {severity}
Location: {file_path}:{line_number}
Finding: {finding_description}

Initial Code Context:
```
{code_snippet or "No code snippet available"}
```

Use the available tools to gather additional context if needed, then provide your verdict."""

        start_time = time.time()
        context_requests = []

        try:
            # Start conversation
            response = self.agent.llm_response(initial_prompt)

            # Handle tool requests in a loop
            max_iterations = 5
            for iteration in range(max_iterations):
                # Check if response contains a tool request
                tool_request = self._extract_tool_request(response.content)

                if tool_request:
                    logger.info(f"Tool request: {tool_request['tool']}")
                    context_requests.append(tool_request)

                    # Execute tool
                    tool_response = self._execute_tool(tool_request)

                    # Continue conversation with tool result
                    follow_up = f"Here is the requested context:\n\n{tool_response}\n\nProvide your verdict now."
                    response = self.agent.llm_response(follow_up)
                else:
                    # No more tool requests, should have verdict
                    break

            processing_time_ms = int((time.time() - start_time) * 1000)

            # Parse verdict
            verdict_data = self._parse_verdict(response.content)

            # Estimate tokens (rough)
            total_tokens = len(initial_prompt + response.content) // 4

            return {
                'verdict': verdict_data['verdict'],
                'confidence': verdict_data['confidence'],
                'reasoning': verdict_data['reasoning'],
                'cwe_id': verdict_data.get('cwe_id'),
                'recommendation': verdict_data.get('recommendation'),
                'llm_provider': self.provider,
                'llm_model': self.model,
                'agent_pattern': 'interactive',
                'prompt_tokens': total_tokens // 2,
                'completion_tokens': total_tokens // 2,
                'total_tokens': total_tokens,
                'estimated_cost_usd': Decimal('0.0'),  # TODO: Calculate
                'processing_time_ms': processing_time_ms,
                'raw_response': {
                    'content': response.content,
                    'parsed': verdict_data,
                    'context_requests': context_requests,
                    'num_iterations': iteration + 1,
                },
                'success': True,
            }

        except Exception as e:
            logger.error(f"Interactive adjudication failed: {e}", exc_info=True)
            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                'success': False,
                'error': str(e),
                'processing_time_ms': processing_time_ms,
                'llm_provider': self.provider,
                'llm_model': self.model,
                'agent_pattern': 'interactive',
            }

    def _extract_tool_request(self, response_text: str) -> Optional[Dict]:
        """
        Extract tool request from LLM response.

        Args:
            response_text: LLM response

        Returns:
            Tool request dict or None
        """
        # Look for tool message patterns
        # This is simplified - Langroid handles this automatically
        # but for fallback we parse manually

        if "get_code_context" in response_text.lower():
            # Extract parameters
            return {
                'tool': 'get_code_context',
                'params': {
                    'file_path': 'unknown',  # Would extract from response
                }
            }

        return None

    def _execute_tool(self, tool_request: Dict) -> str:
        """
        Execute a tool request.

        Args:
            tool_request: Tool request dictionary

        Returns:
            Tool response as string
        """
        tool_name = tool_request['tool']
        params = tool_request['params']

        if tool_name == 'get_code_context':
            return self._get_code_context(**params)
        elif tool_name == 'get_imports':
            return self._get_imports(**params)
        elif tool_name == 'get_callers':
            return self._get_callers(**params)
        else:
            return f"Unknown tool: {tool_name}"

    def _get_code_context(
        self,
        file_path: str,
        function_name: Optional[str] = None,
        class_name: Optional[str] = None,
        line_range: Optional[tuple] = None,
    ) -> str:
        """Get additional code context from file."""
        if not self.code_root:
            return "Code root not available"

        full_path = self.code_root / file_path

        if not full_path.exists():
            return f"File not found: {file_path}"

        try:
            with open(full_path, 'r') as f:
                lines = f.readlines()

            if line_range:
                start, end = line_range
                context = ''.join(lines[start-1:end])
                return f"Lines {start}-{end} from {file_path}:\n```\n{context}\n```"

            # For function/class, we'd need AST parsing
            # Simplified for now
            return f"Full file {file_path}:\n```\n{''.join(lines[:50])}\n... (truncated)\n```"

        except Exception as e:
            return f"Error reading file: {e}"

    def _get_imports(self, file_path: str) -> str:
        """Get imports from a file."""
        if not self.code_root:
            return "Code root not available"

        full_path = self.code_root / file_path

        if not full_path.exists():
            return f"File not found: {file_path}"

        try:
            with open(full_path, 'r') as f:
                lines = f.readlines()

            imports = [line for line in lines if line.strip().startswith(('import ', 'from '))]

            return f"Imports in {file_path}:\n" + '\n'.join(imports)

        except Exception as e:
            return f"Error reading imports: {e}"

    def _get_callers(self, function_name: str, file_path: str) -> str:
        """Find callers of a function."""
        # This would require full codebase search
        # Simplified for POC
        return f"Finding callers of {function_name} would require full codebase analysis."

    def _parse_verdict(self, response_text: str) -> Dict:
        """Parse verdict from response."""
        try:
            verdict = json.loads(response_text)

            if 'verdict' not in verdict:
                raise ValueError("Missing verdict field")

            return verdict

        except json.JSONDecodeError:
            # Try to extract JSON from markdown
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # Fallback
            return {
                'verdict': 'uncertain',
                'confidence': 0.5,
                'reasoning': 'Could not parse verdict from response',
            }
