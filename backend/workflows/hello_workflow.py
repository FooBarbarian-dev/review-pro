"""
Simple hello world workflow to verify Temporal setup.
"""

from datetime import timedelta
from temporalio import activity, workflow
from temporalio.common import RetryPolicy


@activity.defn
async def say_hello(name: str) -> str:
    """Activity that returns a greeting."""
    return f"Hello, {name}! Temporal is working."


@workflow.defn
class SayHello:
    """Simple workflow that executes a greeting activity."""

    @workflow.run
    async def run(self, name: str) -> str:
        """Execute the workflow."""
        # Execute activity with retry policy
        result = await workflow.execute_activity(
            say_hello,
            name,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
            ),
        )

        return result
