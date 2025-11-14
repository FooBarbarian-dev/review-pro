"""
Temporal worker for executing code analysis workflows.

This worker connects to the Temporal server and executes workflows
and activities for the security analysis platform.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add backend directory to Python path for Django imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Configure Django settings before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from temporalio.client import Client
from temporalio.worker import Worker

# Import workflows and activities
from workflows.hello_workflow import SayHello, say_hello
from workflows.llm_test_workflow import TestLLMWorkflow, call_llm_agent

logger = logging.getLogger(__name__)


async def main():
    """Start the Temporal worker."""
    # Get configuration from environment
    temporal_host = os.environ.get('TEMPORAL_HOST', 'localhost:7233')
    task_queue = os.environ.get('TEMPORAL_TASK_QUEUE', 'code-analysis')

    logger.info(f"Connecting to Temporal server at {temporal_host}")

    # Connect to Temporal server
    client = await Client.connect(temporal_host)

    logger.info(f"Starting worker on task queue: {task_queue}")

    # Create worker
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[SayHello, TestLLMWorkflow],
        activities=[say_hello, call_llm_agent],
    )

    logger.info("Worker started successfully. Press Ctrl+C to exit.")

    # Run the worker
    await worker.run()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        sys.exit(1)
