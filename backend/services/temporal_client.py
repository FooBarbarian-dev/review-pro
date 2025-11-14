"""
Temporal client service for triggering workflows from Django.

This service provides a bridge between Django REST API and Temporal workflows,
allowing API endpoints to trigger background workflows for scans, adjudication,
clustering, and pattern comparison.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from temporalio.client import Client

logger = logging.getLogger(__name__)


class TemporalService:
    """
    Service for interacting with Temporal workflows.

    This is a singleton-like service that maintains a connection to the
    Temporal server and provides methods to trigger various workflows.
    """

    _client: Optional[Client] = None
    _connection_lock = asyncio.Lock()

    @classmethod
    async def get_client(cls) -> Client:
        """
        Get or create a Temporal client.

        Returns a connected Temporal client, reusing existing connection
        if available.
        """
        if cls._client is None:
            async with cls._connection_lock:
                if cls._client is None:  # Double-check after acquiring lock
                    temporal_host = getattr(settings, 'TEMPORAL_HOST', 'localhost:7233')
                    logger.info(f"Connecting to Temporal at {temporal_host}")

                    try:
                        cls._client = await Client.connect(temporal_host)
                        logger.info("Successfully connected to Temporal")
                    except Exception as e:
                        logger.error(f"Failed to connect to Temporal: {e}")
                        raise

        return cls._client

    @classmethod
    async def trigger_scan_workflow(
        cls,
        scan_id: str,
        repo_url: Optional[str] = None,
        local_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Trigger a scan repository workflow.

        Args:
            scan_id: UUID of the scan record
            repo_url: Optional repository URL to clone
            local_path: Optional local path to scan

        Returns:
            Dictionary with workflow execution details
        """
        from workflows.scan_workflow import ScanRepositoryWorkflow

        client = await cls.get_client()
        task_queue = getattr(settings, 'TEMPORAL_TASK_QUEUE', 'code-analysis')

        workflow_id = f"scan-{scan_id}"

        try:
            handle = await client.start_workflow(
                ScanRepositoryWorkflow.run,
                args=[scan_id, repo_url, local_path],
                id=workflow_id,
                task_queue=task_queue,
            )

            logger.info(f"Started scan workflow: {workflow_id}")

            return {
                'workflow_id': workflow_id,
                'run_id': handle.first_execution_run_id,
                'status': 'started'
            }
        except Exception as e:
            logger.error(f"Failed to start scan workflow: {e}")
            raise

    @classmethod
    async def trigger_adjudication_workflow(
        cls,
        scan_id: str,
        provider: str = "openai",
        model: str = "gpt-4o",
        pattern: str = "post_processing",
        batch_size: int = 10,
        max_findings: int = 100
    ) -> Dict[str, Any]:
        """
        Trigger LLM adjudication workflow for a scan's findings.

        Args:
            scan_id: UUID of the scan
            provider: LLM provider (openai, anthropic, google)
            model: LLM model name
            pattern: Agent pattern (post_processing, interactive, multi_agent)
            batch_size: Number of findings to process in parallel
            max_findings: Maximum number of findings to adjudicate

        Returns:
            Dictionary with workflow execution details
        """
        from workflows.adjudication_workflow import AdjudicateFindingsWorkflow

        client = await cls.get_client()
        task_queue = getattr(settings, 'TEMPORAL_TASK_QUEUE', 'code-analysis')

        workflow_id = f"adjudicate-{scan_id}-{pattern}"

        try:
            handle = await client.start_workflow(
                AdjudicateFindingsWorkflow.run,
                args=[scan_id, provider, model, pattern, batch_size, max_findings],
                id=workflow_id,
                task_queue=task_queue,
            )

            logger.info(f"Started adjudication workflow: {workflow_id}")

            return {
                'workflow_id': workflow_id,
                'run_id': handle.first_execution_run_id,
                'status': 'started',
                'config': {
                    'provider': provider,
                    'model': model,
                    'pattern': pattern,
                    'batch_size': batch_size,
                    'max_findings': max_findings
                }
            }
        except Exception as e:
            logger.error(f"Failed to start adjudication workflow: {e}")
            raise

    @classmethod
    async def trigger_clustering_workflow(
        cls,
        scan_id: str,
        algorithm: str = "dbscan",
        similarity_threshold: float = 0.85
    ) -> Dict[str, Any]:
        """
        Trigger semantic clustering workflow for a scan's findings.

        Args:
            scan_id: UUID of the scan
            algorithm: Clustering algorithm (dbscan, agglomerative)
            similarity_threshold: Similarity threshold (0.0-1.0)

        Returns:
            Dictionary with workflow execution details
        """
        from workflows.clustering_workflow import ClusterFindingsWorkflow

        client = await cls.get_client()
        task_queue = getattr(settings, 'TEMPORAL_TASK_QUEUE', 'code-analysis')

        workflow_id = f"cluster-{scan_id}-{algorithm}"

        try:
            handle = await client.start_workflow(
                ClusterFindingsWorkflow.run,
                args=[scan_id, algorithm, similarity_threshold],
                id=workflow_id,
                task_queue=task_queue,
            )

            logger.info(f"Started clustering workflow: {workflow_id}")

            return {
                'workflow_id': workflow_id,
                'run_id': handle.first_execution_run_id,
                'status': 'started',
                'config': {
                    'algorithm': algorithm,
                    'similarity_threshold': similarity_threshold
                }
            }
        except Exception as e:
            logger.error(f"Failed to start clustering workflow: {e}")
            raise

    @classmethod
    async def trigger_pattern_comparison_workflow(
        cls,
        scan_id: str
    ) -> Dict[str, Any]:
        """
        Trigger pattern comparison workflow for a scan.

        Runs all three agent patterns and compares their performance.

        Args:
            scan_id: UUID of the scan

        Returns:
            Dictionary with workflow execution details
        """
        from workflows.pattern_comparison_workflow import CompareAgentPatternsWorkflow

        client = await cls.get_client()
        task_queue = getattr(settings, 'TEMPORAL_TASK_QUEUE', 'code-analysis')

        workflow_id = f"compare-patterns-{scan_id}"

        try:
            handle = await client.start_workflow(
                CompareAgentPatternsWorkflow.run,
                args=[scan_id],
                id=workflow_id,
                task_queue=task_queue,
            )

            logger.info(f"Started pattern comparison workflow: {workflow_id}")

            return {
                'workflow_id': workflow_id,
                'run_id': handle.first_execution_run_id,
                'status': 'started'
            }
        except Exception as e:
            logger.error(f"Failed to start pattern comparison workflow: {e}")
            raise

    @classmethod
    async def get_workflow_status(cls, workflow_id: str) -> Dict[str, Any]:
        """
        Get the status of a running workflow.

        Args:
            workflow_id: ID of the workflow to check

        Returns:
            Dictionary with workflow status information
        """
        client = await cls.get_client()

        try:
            handle = client.get_workflow_handle(workflow_id)

            # Try to get result (non-blocking check)
            try:
                result = await asyncio.wait_for(handle.result(), timeout=0.1)
                return {
                    'workflow_id': workflow_id,
                    'status': 'completed',
                    'result': result
                }
            except asyncio.TimeoutError:
                return {
                    'workflow_id': workflow_id,
                    'status': 'running'
                }
        except Exception as e:
            logger.error(f"Failed to get workflow status: {e}")
            return {
                'workflow_id': workflow_id,
                'status': 'error',
                'error': str(e)
            }


# Helper function for synchronous Django views
def run_async(coroutine):
    """
    Run an async coroutine in a new event loop.

    This is a helper for calling async Temporal methods from
    synchronous Django views.

    Args:
        coroutine: The async coroutine to run

    Returns:
        The result of the coroutine
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an event loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(coroutine)
    finally:
        # Don't close the loop, it might be reused
        pass
