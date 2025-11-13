"""
Views for Organization management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Organization, OrganizationMembership, Repository, Branch
from .serializers import (
    OrganizationSerializer, OrganizationMembershipSerializer,
    RepositorySerializer, RepositoryDetailSerializer, BranchSerializer
)
from .permissions import IsOrganizationMember, IsOrganizationAdmin


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing organizations.
    """
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'

    def get_queryset(self):
        """Filter organizations to only those the user is a member of."""
        user = self.request.user
        if user.is_superuser:
            return Organization.objects.all()
        return Organization.objects.filter(
            memberships__user=user
        ).distinct()

    @action(detail=True, methods=['get'])
    def members(self, request, slug=None):
        """List all members of an organization."""
        organization = self.get_object()
        memberships = organization.memberships.select_related('user')
        serializer = OrganizationMembershipSerializer(memberships, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOrganizationAdmin])
    def add_member(self, request, slug=None):
        """Add a new member to the organization."""
        organization = self.get_object()
        serializer = OrganizationMembershipSerializer(data={
            **request.data,
            'organization': organization.id
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated, IsOrganizationAdmin])
    def remove_member(self, request, slug=None):
        """Remove a member from the organization."""
        organization = self.get_object()
        user_id = request.data.get('user_id')
        membership = get_object_or_404(
            OrganizationMembership,
            organization=organization,
            user_id=user_id
        )
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RepositoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing repositories.
    """
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get_queryset(self):
        """Filter repositories to only those in organizations the user is a member of."""
        user = self.request.user
        if user.is_superuser:
            return Repository.objects.all()
        return Repository.objects.filter(
            organization__memberships__user=user
        ).distinct()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RepositoryDetailSerializer
        return RepositorySerializer

    @action(detail=True, methods=['get'])
    def branches(self, request, pk=None):
        """List all branches of a repository."""
        repository = self.get_object()
        branches = repository.branches.all()
        serializer = BranchSerializer(branches, many=True)
        return Response(serializer.data)


class BranchViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing branches.
    """
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get_queryset(self):
        """Filter branches to only those in repositories the user has access to."""
        user = self.request.user
        if user.is_superuser:
            return Branch.objects.all()
        return Branch.objects.filter(
            repository__organization__memberships__user=user
        ).distinct()
