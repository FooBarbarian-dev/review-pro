"""
Views for Scan management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Scan, ScanLog, QuotaUsage
from .serializers import (
    ScanSerializer, ScanDetailSerializer, ScanCreateSerializer,
    ScanLogSerializer, QuotaUsageSerializer
)
from apps.organizations.permissions import IsOrganizationMember


class ScanViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing scans.
    """
    queryset = Scan.objects.all()
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get_queryset(self):
        """Filter scans to only those in organizations the user is a member of."""
        user = self.request.user
        if user.is_superuser:
            return Scan.objects.all()
        return Scan.objects.filter(
            organization__memberships__user=user
        ).select_related(
            'organization', 'repository', 'branch', 'triggered_by'
        ).distinct()

    def get_serializer_class(self):
        if self.action == 'create':
            return ScanCreateSerializer
        elif self.action == 'retrieve':
            return ScanDetailSerializer
        return ScanSerializer

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """Get logs for a specific scan."""
        scan = self.get_object()
        logs = scan.logs.all()
        serializer = ScanLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a running scan."""
        scan = self.get_object()
        if scan.status in ['pending', 'queued', 'running']:
            scan.status = 'cancelled'
            scan.save()
            return Response({'status': 'cancelled'})
        return Response(
            {'error': 'Scan cannot be cancelled in current status'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['get'])
    def sarif(self, request, pk=None):
        """Download the SARIF file for this scan."""
        scan = self.get_object()
        if not scan.sarif_file_path:
            return Response(
                {'error': 'SARIF file not available'},
                status=status.HTTP_404_NOT_FOUND
            )

        # TODO: Generate presigned URL for S3 download
        # from .utils import generate_sarif_download_url
        # url = generate_sarif_download_url(scan.sarif_file_path)
        # return Response({'download_url': url})

        return Response({'sarif_file_path': scan.sarif_file_path})


class QuotaUsageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing quota usage.
    """
    queryset = QuotaUsage.objects.all()
    serializer_class = QuotaUsageSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get_queryset(self):
        """Filter quota usage to only those for user's organizations."""
        user = self.request.user
        if user.is_superuser:
            return QuotaUsage.objects.all()
        return QuotaUsage.objects.filter(
            organization__memberships__user=user
        ).select_related('organization').distinct()
