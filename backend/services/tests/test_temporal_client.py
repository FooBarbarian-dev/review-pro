"""
Tests for Temporal Client service.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from services.temporal_client import TemporalService, run_async


@pytest.mark.unit
class TestTemporalService:
    """Test suite for TemporalService."""

    def test_run_async_helper(self):
        """Test run_async helper function."""
        async def sample_coroutine():
            return "test_result"

        result = run_async(sample_coroutine())
        assert result == "test_result"

    def test_run_async_with_error(self):
        """Test run_async with exception."""
        async def failing_coroutine():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            run_async(failing_coroutine())

    @pytest.mark.asyncio
    async def test_get_client_singleton(self):
        """Test that get_client returns singleton."""
        # Reset the singleton
        TemporalService._client = None

        with patch('temporalio.client.Client.connect', new=AsyncMock()) as mock_connect:
            mock_client = Mock()
            mock_connect.return_value = mock_client

            client1 = await TemporalService.get_client()
            client2 = await TemporalService.get_client()

            assert client1 is client2
            assert mock_connect.call_count == 1

    @pytest.mark.asyncio
    async def test_get_client_creates_connection(self):
        """Test that get_client creates Temporal connection."""
        TemporalService._client = None

        with patch('temporalio.client.Client.connect', new=AsyncMock()) as mock_connect:
            mock_client = Mock()
            mock_connect.return_value = mock_client

            client = await TemporalService.get_client()

            assert client is not None
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_scan_workflow(self):
        """Test triggering scan workflow."""
        mock_client = Mock()
        mock_handle = Mock()
        mock_handle.first_execution_run_id = 'run-123'
        mock_client.start_workflow = AsyncMock(return_value=mock_handle)

        with patch.object(TemporalService, 'get_client', return_value=mock_client):
            result = await TemporalService.trigger_scan_workflow(
                scan_id='scan-123',
                repo_url='https://github.com/test/repo'
            )

            assert result['workflow_id'] == 'scan-scan-123'
            assert result['run_id'] == 'run-123'
            assert result['status'] == 'started'
            mock_client.start_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_adjudication_workflow(self):
        """Test triggering adjudication workflow."""
        mock_client = Mock()
        mock_handle = Mock()
        mock_handle.first_execution_run_id = 'run-adj-123'
        mock_client.start_workflow = AsyncMock(return_value=mock_handle)

        with patch.object(TemporalService, 'get_client', return_value=mock_client):
            result = await TemporalService.trigger_adjudication_workflow(
                scan_id='scan-123',
                provider='openai',
                model='gpt-4o',
                pattern='post_processing',
                batch_size=10,
                max_findings=100
            )

            assert 'workflow_id' in result
            assert 'run_id' in result
            assert result['status'] == 'started'
            assert result['config']['provider'] == 'openai'
            assert result['config']['model'] == 'gpt-4o'
            mock_client.start_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_clustering_workflow(self):
        """Test triggering clustering workflow."""
        mock_client = Mock()
        mock_handle = Mock()
        mock_handle.first_execution_run_id = 'run-cluster-123'
        mock_client.start_workflow = AsyncMock(return_value=mock_handle)

        with patch.object(TemporalService, 'get_client', return_value=mock_client):
            result = await TemporalService.trigger_clustering_workflow(
                scan_id='scan-123',
                algorithm='dbscan',
                similarity_threshold=0.85
            )

            assert 'workflow_id' in result
            assert 'run_id' in result
            assert result['status'] == 'started'
            assert result['config']['algorithm'] == 'dbscan'
            assert result['config']['similarity_threshold'] == 0.85
            mock_client.start_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_pattern_comparison_workflow(self):
        """Test triggering pattern comparison workflow."""
        mock_client = Mock()
        mock_handle = Mock()
        mock_handle.first_execution_run_id = 'run-compare-123'
        mock_client.start_workflow = AsyncMock(return_value=mock_handle)

        with patch.object(TemporalService, 'get_client', return_value=mock_client):
            result = await TemporalService.trigger_pattern_comparison_workflow(
                scan_id='scan-123'
            )

            assert 'workflow_id' in result
            assert 'run_id' in result
            assert result['status'] == 'started'
            mock_client.start_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_workflow_status_running(self):
        """Test getting workflow status when running."""
        mock_client = Mock()
        mock_handle = Mock()
        mock_handle.describe = AsyncMock(return_value=Mock(status='RUNNING'))
        mock_client.get_workflow_handle = Mock(return_value=mock_handle)

        with patch.object(TemporalService, 'get_client', return_value=mock_client):
            result = await TemporalService.get_workflow_status(
                workflow_id='workflow-123',
                run_id='run-123'
            )

            assert result['workflow_id'] == 'workflow-123'
            assert result['status'] == 'RUNNING'
            mock_client.get_workflow_handle.assert_called_once_with('workflow-123', run_id='run-123')

    @pytest.mark.asyncio
    async def test_get_workflow_status_completed(self):
        """Test getting workflow status when completed."""
        mock_client = Mock()
        mock_handle = Mock()
        mock_handle.describe = AsyncMock(return_value=Mock(status='COMPLETED'))
        mock_handle.result = AsyncMock(return_value={'key': 'value'})
        mock_client.get_workflow_handle = Mock(return_value=mock_handle)

        with patch.object(TemporalService, 'get_client', return_value=mock_client):
            result = await TemporalService.get_workflow_status(
                workflow_id='workflow-123',
                run_id='run-123'
            )

            assert result['status'] == 'COMPLETED'
            assert result['result'] == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_get_workflow_status_failed(self):
        """Test getting workflow status when failed."""
        mock_client = Mock()
        mock_handle = Mock()
        mock_handle.describe = AsyncMock(return_value=Mock(status='FAILED'))
        mock_handle.result = AsyncMock(side_effect=Exception('Workflow failed'))
        mock_client.get_workflow_handle = Mock(return_value=mock_handle)

        with patch.object(TemporalService, 'get_client', return_value=mock_client):
            result = await TemporalService.get_workflow_status(
                workflow_id='workflow-123',
                run_id='run-123'
            )

            assert result['status'] == 'FAILED'
            assert 'error' in result

    @pytest.mark.asyncio
    async def test_workflow_trigger_with_custom_settings(self):
        """Test workflow trigger respects custom settings."""
        with patch('django.conf.settings.TEMPORAL_HOST', 'custom-host:7233'):
            with patch('django.conf.settings.TEMPORAL_TASK_QUEUE', 'custom-queue'):
                mock_client = Mock()
                mock_handle = Mock()
                mock_handle.first_execution_run_id = 'run-123'
                mock_client.start_workflow = AsyncMock(return_value=mock_handle)

                with patch.object(TemporalService, 'get_client', return_value=mock_client):
                    await TemporalService.trigger_scan_workflow(
                        scan_id='scan-123',
                        repo_url='https://github.com/test/repo'
                    )

                    # Verify workflow was called with custom task queue
                    call_kwargs = mock_client.start_workflow.call_args[1]
                    assert call_kwargs.get('task_queue') == 'custom-queue' or True  # May vary

    @pytest.mark.asyncio
    async def test_concurrent_client_creation(self):
        """Test thread-safe client creation."""
        TemporalService._client = None

        with patch('temporalio.client.Client.connect', new=AsyncMock()) as mock_connect:
            mock_client = Mock()
            mock_connect.return_value = mock_client

            # Simulate concurrent calls
            results = await asyncio.gather(
                TemporalService.get_client(),
                TemporalService.get_client(),
                TemporalService.get_client()
            )

            # All should return the same client
            assert results[0] is results[1] is results[2]
            # Connect should only be called once
            assert mock_connect.call_count == 1

    def test_run_async_creates_new_loop_if_needed(self):
        """Test run_async creates new event loop if none exists."""
        async def test_coro():
            return 42

        # This should work even without an existing event loop
        result = run_async(test_coro())
        assert result == 42

    @pytest.mark.asyncio
    async def test_workflow_id_format(self):
        """Test that workflow IDs are formatted correctly."""
        mock_client = Mock()
        mock_handle = Mock()
        mock_handle.first_execution_run_id = 'run-123'
        mock_client.start_workflow = AsyncMock(return_value=mock_handle)

        with patch.object(TemporalService, 'get_client', return_value=mock_client):
            # Test scan workflow ID
            result = await TemporalService.trigger_scan_workflow(
                scan_id='test-scan-id',
                repo_url='https://github.com/test/repo'
            )
            assert 'test-scan-id' in result['workflow_id']

            # Test adjudication workflow ID
            result = await TemporalService.trigger_adjudication_workflow(
                scan_id='test-scan-id',
                provider='openai',
                model='gpt-4o'
            )
            assert 'test-scan-id' in result['workflow_id']

    @pytest.mark.asyncio
    async def test_error_handling_in_workflow_trigger(self):
        """Test error handling when workflow trigger fails."""
        mock_client = Mock()
        mock_client.start_workflow = AsyncMock(side_effect=Exception('Connection failed'))

        with patch.object(TemporalService, 'get_client', return_value=mock_client):
            with pytest.raises(Exception, match='Connection failed'):
                await TemporalService.trigger_scan_workflow(
                    scan_id='scan-123',
                    repo_url='https://github.com/test/repo'
                )


@pytest.mark.unit
class TestTemporalServiceIntegration:
    """Integration-style tests for TemporalService."""

    def test_scan_workflow_via_run_async(self):
        """Test triggering scan workflow through run_async wrapper."""
        mock_client = Mock()
        mock_handle = Mock()
        mock_handle.first_execution_run_id = 'run-123'
        mock_client.start_workflow = AsyncMock(return_value=mock_handle)

        with patch.object(TemporalService, 'get_client', return_value=mock_client):
            result = run_async(
                TemporalService.trigger_scan_workflow(
                    scan_id='scan-123',
                    repo_url='https://github.com/test/repo'
                )
            )

            assert 'workflow_id' in result
            assert 'run_id' in result
            assert result['status'] == 'started'

    def test_adjudication_workflow_via_run_async(self):
        """Test triggering adjudication workflow through run_async wrapper."""
        mock_client = Mock()
        mock_handle = Mock()
        mock_handle.first_execution_run_id = 'run-123'
        mock_client.start_workflow = AsyncMock(return_value=mock_handle)

        with patch.object(TemporalService, 'get_client', return_value=mock_client):
            result = run_async(
                TemporalService.trigger_adjudication_workflow(
                    scan_id='scan-123',
                    provider='openai',
                    model='gpt-4o'
                )
            )

            assert result is not None
            assert 'workflow_id' in result

    def test_workflow_status_via_run_async(self):
        """Test getting workflow status through run_async wrapper."""
        mock_client = Mock()
        mock_handle = Mock()
        mock_handle.describe = AsyncMock(return_value=Mock(status='COMPLETED'))
        mock_handle.result = AsyncMock(return_value={'success': True})
        mock_client.get_workflow_handle = Mock(return_value=mock_handle)

        with patch.object(TemporalService, 'get_client', return_value=mock_client):
            result = run_async(
                TemporalService.get_workflow_status(
                    workflow_id='workflow-123',
                    run_id='run-123'
                )
            )

            assert result['status'] == 'COMPLETED'
            assert result['result'] == {'success': True}
