"""
Base agent configuration using Langroid framework.

Provides common configuration and utilities for all LLM agents.
"""

import logging
import os
from typing import Optional

from langroid.agent.chat_agent import ChatAgent, ChatAgentConfig
from langroid.language_models.openai_gpt import OpenAIChatModel, OpenAIGPTConfig

from langroid.utils.configuration import Settings

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating configured LLM agents."""

    @staticmethod
    def create_openai_agent(
        system_message: str,
        model: str = "gpt-4o",
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> ChatAgent:
        """
        Create an OpenAI-based agent.

        Args:
            system_message: System prompt for the agent
            model: OpenAI model name (default: gpt-4o)
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens in response

        Returns:
            Configured ChatAgent instance
        """
        # Configure OpenAI LLM
        llm_config = OpenAIGPTConfig(
            chat_model=model,
            chat_context_length=128000,  # GPT-4o context window
            temperature=temperature,
            max_output_tokens=max_tokens,
            api_key=os.environ.get('OPENAI_API_KEY'),
        )

        # Configure agent
        agent_config = ChatAgentConfig(
            name=f"OpenAI-{model}",
            llm=llm_config,
            system_message=system_message,
        )

        return ChatAgent(agent_config)

    @staticmethod
    def create_anthropic_agent(
        system_message: str,
        model: str = "claude-sonnet-4-20250514",
        temperature: float = 0.0,
        max_tokens: int = 4000,
    ) -> ChatAgent:
        """
        Create an Anthropic Claude-based agent.

        Args:
            system_message: System prompt for the agent
            model: Anthropic model name (default: claude-sonnet-4)
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens in response

        Returns:
            Configured ChatAgent instance
        """
        # Configure Anthropic LLM
        # Configure Anthropic LLM
        llm_config = OpenAIGPTConfig(
            chat_model=f"litellm/{model}",
            chat_context_length=200000,  # Claude context window
            temperature=temperature,
            max_output_tokens=max_tokens,
            # api_key=os.environ.get('ANTHROPIC_API_KEY'), # litellm reads from env
        )

        # Configure agent
        agent_config = ChatAgentConfig(
            name=f"Claude-{model}",
            llm=llm_config,
            system_message=system_message,
        )

        return ChatAgent(agent_config)

    @staticmethod
    def validate_api_keys() -> dict[str, bool]:
        """
        Validate that required API keys are present.

        Returns:
            Dictionary mapping provider names to availability status
        """
        return {
            'openai': bool(os.environ.get('OPENAI_API_KEY')),
            'anthropic': bool(os.environ.get('ANTHROPIC_API_KEY')),
            'google': bool(os.environ.get('GOOGLE_API_KEY')),
        }
