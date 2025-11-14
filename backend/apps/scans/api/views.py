"""
Views for the Scans API.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.scans.models import Scan
from apps.scans.api.serializers import (
    ScanListSerializer, ScanDetailSerializer, ScanCreateSerializer,
    TriggerAdjudicationSerializer, TriggerClusteringSerializer
)
from services.temporal_client import TemporalService, run_async
import logging

logger = logging.getLogger(__name__)


class ScanViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Scan model.

    Provides CRUD operations and custom actions for scans.
    """
    queryset = Scan.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return ScanListSerializer
        elif self.action == 'create':
            return ScanCreateSerializer
        return ScanDetailSerializer

    def get_queryset(self):
        """Filter scans with query parameters."""
        queryset = Scan.objects.select_related('repository', 'branch').all()

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by repository
        repository_id = self.request.query_params.get('repository_id')
        if repository_id:
            queryset = queryset.filter(repository_id=repository_id)

        return queryset.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """
        Create a new scan and trigger the scan workflow.

        This will:
        1. Create a Scan record
        2. Trigger the Temporal ScanRepositoryWorkflow
        3. Return the scan details
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create the scan record
        scan = serializer.save(
            triggered_by=request.user if request.user.is_authenticated else None,
            status='queued'
        )

        try:
            # Trigger the scan workflow
            repository = scan.repository
            repo_url = repository.clone_url if hasattr(repository, 'clone_url') else None

            result = run_async(
                TemporalService.trigger_scan_workflow(
                    scan_id=str(scan.id),
                    repo_url=repo_url
                )
            )

            # Return the created scan details with workflow info
            response_data = ScanDetailSerializer(scan).data
            response_data['workflow'] = result

            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Failed to trigger scan workflow: {e}")
            # Update scan status to failed
            scan.status = 'failed'
            scan.error_message = str(e)
            scan.save()

            return Response(
                {
                    "error": "Failed to start scan workflow",
                    "detail": str(e),
                    "scan_id": str(scan.id)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def rescan(self, request, pk=None):
        """Trigger a re-scan for the same repository/branch/commit."""
        original_scan = self.get_object()

        # Create a new scan with the same parameters
        new_scan = Scan.objects.create(
            organization=original_scan.organization,
            repository=original_scan.repository,
            branch=original_scan.branch,
            commit_sha=original_scan.commit_sha,
            triggered_by=request.user if request.user.is_authenticated else original_scan.triggered_by,
            trigger_type='manual',
            status='queued'
        )

        try:
            # Trigger the scan workflow
            repository = new_scan.repository
            repo_url = repository.clone_url if hasattr(repository, 'clone_url') else None

            result = run_async(
                TemporalService.trigger_scan_workflow(
                    scan_id=str(new_scan.id),
                    repo_url=repo_url
                )
            )

            # Return the new scan details with workflow info
            response_data = ScanDetailSerializer(new_scan).data
            response_data['workflow'] = result
            response_data['original_scan_id'] = str(original_scan.id)

            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Failed to trigger rescan workflow: {e}")
            # Update scan status to failed
            new_scan.status = 'failed'
            new_scan.error_message = str(e)
            new_scan.save()

            return Response(
                {
                    "error": "Failed to start rescan workflow",
                    "detail": str(e),
                    "scan_id": str(new_scan.id),
                    "original_scan_id": str(original_scan.id)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def adjudicate(self, request, pk=None):
        """
        Trigger LLM adjudication for findings in this scan.

        Expected body:
        {
            "provider": "openai|anthropic|google",
            "model": "gpt-4o|claude-sonnet-4|...",
            "pattern": "post_processing|interactive|multi_agent",
            "batch_size": 10,
            "max_findings": 100
        }
        """
        scan = self.get_object()
        serializer = TriggerAdjudicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Trigger the adjudication workflow
            result = run_async(
                TemporalService.trigger_adjudication_workflow(
                    scan_id=str(scan.id),
                    provider=serializer.validated_data.get('provider', 'openai'),
                    model=serializer.validated_data.get('model', 'gpt-4o'),
                    pattern=serializer.validated_data.get('pattern', 'post_processing'),
                    batch_size=serializer.validated_data.get('batch_size', 10),
                    max_findings=serializer.validated_data.get('max_findings', 100)
                )
            )

            return Response(result, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.error(f"Failed to trigger adjudication workflow: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def cluster(self, request, pk=None):
        """
        Trigger semantic clustering for findings in this scan.

        Expected body:
        {
            "algorithm": "dbscan|agglomerative",
            "threshold": 0.85
        }
        """
        scan = self.get_object()
        serializer = TriggerClusteringSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Trigger the clustering workflow
            result = run_async(
                TemporalService.trigger_clustering_workflow(
                    scan_id=str(scan.id),
                    algorithm=serializer.validated_data.get('algorithm', 'dbscan'),
                    similarity_threshold=serializer.validated_data.get('threshold', 0.85)
                )
            )

            return Response(result, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.error(f"Failed to trigger clustering workflow: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def compare_patterns(self, request, pk=None):
        """Run pattern comparison for this scan's findings."""
        scan = self.get_object()

        try:
            # Trigger the pattern comparison workflow
            result = run_async(
                TemporalService.trigger_pattern_comparison_workflow(
                    scan_id=str(scan.id)
                )
            )

            return Response(result, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.error(f"Failed to trigger pattern comparison workflow: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='pattern-comparison')
    def pattern_comparison(self, request, pk=None):
        """Get pattern comparison results for this scan."""
        scan = self.get_object()

        # TODO: Query pattern comparison results from database
        # For now, return empty array
        return Response([], status=status.HTTP_200_OK)
