"""
Views for Scan management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Scan, ScanLog, QuotaUsage
from .serializers import (
    ScanSerializer, ScanDetailSerializer, ScanCreateSerializer,
    ScanLogSerializer, QuotaUsageSerializer
)
from apps.organizations.permissions import IsOrganizationMember
from .tasks import run_security_scan
from .storage import get_storage
import logging

logger = logging.getLogger(__name__)


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

    def perform_create(self, serializer):
        """
        Create scan with quota enforcement (ADR-008).

        Checks:
        1. Organization is active
        2. Scan quota not exceeded
        3. Storage quota not exceeded (if applicable)
        """
        repository = serializer.validated_data['repository']
        organization = repository.organization

        # Check if organization is active
        if not organization.is_active:
            raise ValidationError({
                'organization': 'Organization is not active'
            })

        # Get or create quota usage for current month
        now = timezone.now()
        quota, _ = QuotaUsage.objects.get_or_create(
            organization=organization,
            year=now.year,
            month=now.month,
            defaults={'scans_used': 0, 'storage_used_bytes': 0}
        )

        # Check scan quota
        if quota.scans_used >= organization.scan_quota_monthly:
            raise ValidationError({
                'quota': f'Monthly scan quota exceeded. Used {quota.scans_used} of {organization.scan_quota_monthly}.',
                'quota_limit': organization.scan_quota_monthly,
                'quota_used': quota.scans_used
            })

        # Check storage quota (warning only, enforced after scan)
        storage_gb_used = quota.storage_used_gb
        if storage_gb_used >= organization.storage_quota_gb:
            logger.warning(
                f"Organization {organization.slug} is at storage limit: "
                f"{storage_gb_used:.2f}/{organization.storage_quota_gb} GB"
            )

        # Create scan with status 'pending'
        scan = serializer.save(
            organization=organization,
            triggered_by=self.request.user,
            status='pending'
        )

        logger.info(
            f"Scan {scan.id} created for {repository.full_name} "
            f"by {self.request.user.email}"
        )

        # Trigger async scan task
        try:
            run_security_scan.delay(str(scan.id))
            scan.status = 'queued'
            scan.save(update_fields=['status'])
            logger.info(f"Scan task queued for scan {scan.id}")
        except Exception as e:
            logger.error(f"Failed to queue scan task: {e}")
            scan.status = 'failed'
            scan.error_message = f'Failed to queue scan task: {e}'
            scan.save(update_fields=['status', 'error_message'])

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
        """
        Download the SARIF file for this scan via presigned URL.

        Returns a temporary authenticated URL for downloading the SARIF file
        from S3/MinIO without exposing credentials.
        """
        scan = self.get_object()
        if not scan.sarif_file_path:
            return Response(
                {'error': 'SARIF file not available'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            # Generate presigned URL (valid for 1 hour)
            storage = get_storage()
            filename = f"scan_{scan.id}.sarif"
            download_url = storage.get_presigned_url(
                s3_key=scan.sarif_file_path,
                expiry=3600,  # 1 hour
                filename=filename
            )

            return Response({
                'download_url': download_url,
                'expires_in': 3600,
                'filename': filename,
                'file_size': scan.sarif_file_size
            })

        except Exception as e:
            logger.error(f"Failed to generate presigned URL for scan {scan.id}: {e}")
            return Response(
                {'error': 'Failed to generate download URL'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
