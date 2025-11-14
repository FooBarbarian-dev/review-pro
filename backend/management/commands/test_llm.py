"""
Django management command to test LLM integration.

Usage:
    python manage.py test_llm [--provider PROVIDER] [--workflow]
"""

import asyncio
import logging
from django.core.management.base import BaseCommand
from temporalio.client import Client

from agents.base_agent import AgentFactory
from agents.triage_agent import TriageAgent
from workflows.llm_test_workflow import TestLLMWorkflow

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test LLM integration with Langroid agents'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provider',
            type=str,
            choices=['openai', 'anthropic', 'all'],
            default='openai',
            help='LLM provider to test (default: openai)',
        )
        parser.add_argument(
            '--workflow',
            action='store_true',
            help='Test LLM via Temporal workflow instead of direct call',
        )

    def handle(self, *args, **options):
        """Execute the command."""
        provider = options['provider']
        use_workflow = options['workflow']

        self.stdout.write(
            self.style.WARNING(f'Testing LLM integration (provider: {provider})')
        )

        # Check API keys
        api_keys = AgentFactory.validate_api_keys()
        self.stdout.write('\nAPI Key Status:')
        for provider_name, available in api_keys.items():
            status = '✓' if available else '✗'
            style = self.style.SUCCESS if available else self.style.ERROR
            self.stdout.write(style(f'  {status} {provider_name.upper()}: {"Available" if available else "Missing"}'))

        if use_workflow:
            self.stdout.write('\n' + self.style.WARNING('Testing via Temporal workflow...'))
            try:
                result = asyncio.run(self.test_via_workflow())
                self.stdout.write(self.style.SUCCESS(f'✓ Workflow test passed!'))
                self.stdout.write(f'  Result: {result}')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Workflow test failed: {e}'))
                logger.error(f"LLM workflow test failed: {e}", exc_info=True)
                raise
        else:
            self.stdout.write('\n' + self.style.WARNING('Testing direct LLM calls...'))
            if provider in ['openai', 'all'] and api_keys['openai']:
                self.test_openai()

            if provider in ['anthropic', 'all'] and api_keys['anthropic']:
                self.test_anthropic()

    def test_openai(self):
        """Test OpenAI GPT-4o integration."""
        self.stdout.write('\n' + self.style.WARNING('Testing OpenAI (GPT-4o)...'))

        try:
            agent = TriageAgent(model='gpt-4o')
            result = agent.test_connection()

            if result['success']:
                self.stdout.write(self.style.SUCCESS('✓ OpenAI connection successful'))
                self.stdout.write(f'  Response: {result["response"][:100]}...')
            else:
                self.stdout.write(self.style.ERROR(f'✗ OpenAI test failed: {result.get("error")}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ OpenAI test failed: {e}'))
            logger.error(f"OpenAI test failed: {e}", exc_info=True)

    def test_anthropic(self):
        """Test Anthropic Claude integration."""
        self.stdout.write('\n' + self.style.WARNING('Testing Anthropic (Claude)...'))

        try:
            agent = AgentFactory.create_anthropic_agent(
                system_message="You are a helpful assistant.",
                model="claude-sonnet-4-20250514",
            )
            response = agent.llm_response("Say 'Hello from Claude!'")

            self.stdout.write(self.style.SUCCESS('✓ Anthropic connection successful'))
            self.stdout.write(f'  Response: {response.content[:100]}...')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Anthropic test failed: {e}'))
            logger.error(f"Anthropic test failed: {e}", exc_info=True)

    async def test_via_workflow(self) -> dict:
        """
        Test LLM integration via Temporal workflow.

        Returns:
            Workflow result dictionary
        """
        # Connect to Temporal server
        self.stdout.write('Connecting to Temporal server...')
        client = await Client.connect('localhost:7233')

        # Execute LLM test workflow
        self.stdout.write('Starting LLM test workflow...')
        result = await client.execute_workflow(
            TestLLMWorkflow.run,
            'test_connection',
            id='test-llm-integration',
            task_queue='code-analysis',
        )

        return result
