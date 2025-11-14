"""
Django management command to test Temporal workflow execution.

Usage:
    python manage.py test_temporal [--name NAME]
"""

import asyncio
import logging
from django.core.management.base import BaseCommand
from temporalio.client import Client

from workflows.hello_workflow import SayHello

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test Temporal workflow execution with a simple hello world workflow'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            default='World',
            help='Name to greet in the hello workflow',
        )

    def handle(self, *args, **options):
        """Execute the command."""
        name = options['name']

        self.stdout.write(
            self.style.WARNING(f'Testing Temporal workflow with name: {name}')
        )

        try:
            result = asyncio.run(self.run_workflow(name))
            self.stdout.write(self.style.SUCCESS(f'✓ Workflow result: {result}'))
            self.stdout.write(self.style.SUCCESS('✓ Temporal is working correctly!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Workflow failed: {e}'))
            logger.error(f"Temporal test failed: {e}", exc_info=True)
            raise

    async def run_workflow(self, name: str) -> str:
        """
        Connect to Temporal and execute the hello world workflow.

        Args:
            name: Name to pass to the workflow

        Returns:
            Workflow result string
        """
        # Connect to Temporal server
        self.stdout.write('Connecting to Temporal server...')
        client = await Client.connect('localhost:7233')

        # Execute workflow
        self.stdout.write('Starting workflow...')
        result = await client.execute_workflow(
            SayHello.run,
            name,
            id=f'test-hello-{name}',
            task_queue='code-analysis',
        )

        return result
