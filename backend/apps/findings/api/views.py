"""
Views for the Findings API.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from apps.findings.models import Finding, FindingCluster
from apps.findings.api.serializers import (
    FindingListSerializer, FindingDetailSerializer, FindingUpdateSerializer,
    FindingClusterSerializer, FindingMinimalSerializer
)


class FindingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Finding model.

    Provides CRUD operations and filtering.
    """
    queryset = Finding.objects.all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['scan__id', 'severity', 'status', 'tool_name', 'repository']
    ordering_fields = ['created_at', 'severity', 'first_seen_at']
    ordering = ['-first_seen_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return FindingListSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return FindingUpdateSerializer
        return FindingDetailSerializer

    def get_queryset(self):
        """
        Filter findings with query parameters.

        Supports:
        - scan_id: Filter by scan
        - severity: Filter by severity (critical, high, medium, low, info)
        - status: Filter by status (open, fixed, false_positive, etc.)
        - tool_name: Filter by tool (semgrep, bandit, ruff)
        - file_path: Filter by file path (contains)
        """
        queryset = Finding.objects.select_related(
            'repository', 'first_seen_scan', 'last_seen_scan'
        ).prefetch_related(
            'llm_verdicts', 'cluster_memberships__cluster'
        ).all()

        # Additional custom filters
        file_path = self.request.query_params.get('file_path')
        if file_path:
            queryset = queryset.filter(file_path__icontains=file_path)

        scan_id = self.request.query_params.get('scan_id')
        if scan_id:
            queryset = queryset.filter(
                models.Q(first_seen_scan_id=scan_id) |
                models.Q(last_seen_scan_id=scan_id)
            )

        return queryset

    def update(self, request, *args, **kwargs):
        """Update finding (typically just status)."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Update the status
        instance.status = serializer.validated_data['status']
        if instance.status == 'fixed':
            from django.utils import timezone
            instance.fixed_at = timezone.now()
        instance.save()

        # Return full detail view
        return Response(FindingDetailSerializer(instance).data)

    def partial_update(self, request, *args, **kwargs):
        """Partial update (PATCH)."""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class FindingClusterViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for FindingCluster model (read-only).

    Clusters are created by the clustering workflow, not manually.
    """
    queryset = FindingCluster.objects.all()
    serializer_class = FindingClusterSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['organization']
    ordering_fields = ['size', 'created_at', 'avg_similarity']
    ordering = ['-size', '-created_at']

    def get_queryset(self):
        """
        Filter clusters with query parameters.

        Supports:
        - scan_id: Filter clusters containing findings from this scan
        - min_size: Minimum cluster size
        """
        queryset = FindingCluster.objects.select_related(
            'representative_finding'
        ).all()

        # Filter by minimum size
        min_size = self.request.query_params.get('min_size')
        if min_size:
            try:
                queryset = queryset.filter(size__gte=int(min_size))
            except ValueError:
                pass

        # Filter by scan (clusters containing findings from this scan)
        scan_id = self.request.query_params.get('scan_id')
        if scan_id:
            queryset = queryset.filter(
                members__finding__first_seen_scan_id=scan_id
            ).distinct()

        return queryset

    @action(detail=True, methods=['get'])
    def findings(self, request, pk=None):
        """Get all findings in this cluster."""
        cluster = self.get_object()

        # Get all findings through membership relationship
        findings = Finding.objects.filter(
            cluster_memberships__cluster=cluster
        ).select_related('repository', 'first_seen_scan')

        # Annotate with distance to centroid
        from django.db import models
        findings = findings.annotate(
            distance=models.Subquery(
                cluster.members.filter(finding=models.OuterRef('pk')).values('distance_to_centroid')[:1]
            )
        ).order_by('distance')

        serializer = FindingMinimalSerializer(findings, many=True)
        return Response(serializer.data)
