"""
Test workflow for LLM integration via Temporal.

Demonstrates calling Langroid agents from Temporal workflows.
"""

from datetime import timedelta
from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from agents.triage_agent import TriageAgent


@activity.defn
async def call_llm_agent(test_message: str) -> dict:
    """
    Activity that calls an LLM agent and returns the response.

    Args:
        test_message: Test message to send to the LLM

    Returns:
        Dictionary with LLM response and metadata
    """
    # Create triage agent
    agent = TriageAgent()

    # Test simple connection
    if test_message == "test_connection":
        return agent.test_connection()

    # Test with a mock security finding
    result = await agent.analyze_finding(
        finding_description="SQL Injection: Unsanitized user input used in SQL query",
        code_snippet="""
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)
        """,
        file_path="app/database.py",
        line_number=42,
        tool_name="bandit",
    )

    return result


@workflow.defn
class TestLLMWorkflow:
    """Workflow that tests LLM integration."""

    @workflow.run
    async def run(self, test_message: str = "test_connection") -> dict:
        """
        Execute the LLM test workflow.

        Args:
            test_message: Message to send to LLM or "test_connection" for basic test

        Returns:
            Dictionary with test results
        """
        # Execute LLM activity with retry policy
        result = await workflow.execute_activity(
            call_llm_agent,
            test_message,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=2),
                maximum_interval=timedelta(seconds=10),
            ),
        )

        return {
            'workflow': 'TestLLMWorkflow',
            'status': 'completed',
            'llm_result': result,
        }
