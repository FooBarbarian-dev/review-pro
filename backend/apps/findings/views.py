"""
Views for Finding management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Finding, FindingComment, FindingStatusHistory
from .serializers import (
    FindingSerializer, FindingDetailSerializer, FindingCommentSerializer,
    FindingStatusHistorySerializer, FindingStatusUpdateSerializer
)
from apps.organizations.permissions import IsOrganizationMember


class FindingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing findings.
    """
    queryset = Finding.objects.all()
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get_queryset(self):
        """Filter findings to only those in organizations the user is a member of."""
        user = self.request.user
        if user.is_superuser:
            return Finding.objects.all()
        return Finding.objects.filter(
            organization__memberships__user=user
        ).select_related(
            'organization', 'repository', 'first_seen_scan', 'last_seen_scan'
        ).distinct()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return FindingDetailSerializer
        return FindingSerializer

    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        """Get comments for a specific finding."""
        finding = self.get_object()
        comments = finding.comments.all()
        serializer = FindingCommentSerializer(comments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """Add a comment to a finding."""
        finding = self.get_object()
        serializer = FindingCommentSerializer(data={
            **request.data,
            'finding': finding.id,
            'author': request.user.id
        })
        serializer.is_valid(raise_exception=True)
        comment = FindingComment.objects.create(
            finding=finding,
            author=request.user,
            content=request.data.get('content')
        )
        return Response(
            FindingCommentSerializer(comment).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update the status of a finding."""
        finding = self.get_object()
        serializer = FindingStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = finding.status
        new_status = serializer.validated_data['status']
        reason = serializer.validated_data.get('reason', '')

        if old_status != new_status:
            # Create status history entry
            FindingStatusHistory.objects.create(
                finding=finding,
                changed_by=request.user,
                old_status=old_status,
                new_status=new_status,
                reason=reason
            )

            # Update finding status
            finding.status = new_status
            if new_status == 'fixed':
                finding.fixed_at = timezone.now()
            finding.save()

        return Response(FindingDetailSerializer(finding).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get statistics about findings."""
        queryset = self.get_queryset()

        stats = {
            'total': queryset.count(),
            'by_severity': {
                'critical': queryset.filter(severity='critical').count(),
                'high': queryset.filter(severity='high').count(),
                'medium': queryset.filter(severity='medium').count(),
                'low': queryset.filter(severity='low').count(),
                'info': queryset.filter(severity='info').count(),
            },
            'by_status': {
                'open': queryset.filter(status='open').count(),
                'fixed': queryset.filter(status='fixed').count(),
                'false_positive': queryset.filter(status='false_positive').count(),
                'accepted_risk': queryset.filter(status='accepted_risk').count(),
                'wont_fix': queryset.filter(status='wont_fix').count(),
            }
        }

        return Response(stats)


class FindingCommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing finding comments.
    """
    queryset = FindingComment.objects.all()
    serializer_class = FindingCommentSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get_queryset(self):
        """Filter comments to only those for findings the user has access to."""
        user = self.request.user
        if user.is_superuser:
            return FindingComment.objects.all()
        return FindingComment.objects.filter(
            finding__organization__memberships__user=user
        ).select_related('finding', 'author').distinct()

    def perform_create(self, serializer):
        """Set the author to the current user."""
        serializer.save(author=self.request.user)
