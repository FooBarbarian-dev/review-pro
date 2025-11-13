"""
Custom permissions for organization access control.
"""
from rest_framework import permissions
from .models import OrganizationMembership


class IsOrganizationMember(permissions.BasePermission):
    """
    Permission class to check if user is a member of the organization.
    """

    def has_object_permission(self, request, view, obj):
        # Get the organization from the object
        if hasattr(obj, 'organization'):
            organization = obj.organization
        elif hasattr(obj, 'repository'):
            organization = obj.repository.organization
        else:
            organization = obj

        # Check if user is a member
        return OrganizationMembership.objects.filter(
            organization=organization,
            user=request.user
        ).exists()


class IsOrganizationAdmin(permissions.BasePermission):
    """
    Permission class to check if user is an admin or owner of the organization.
    """

    def has_object_permission(self, request, view, obj):
        # Get the organization from the object
        if hasattr(obj, 'organization'):
            organization = obj.organization
        else:
            organization = obj

        # Check if user is an admin or owner
        membership = OrganizationMembership.objects.filter(
            organization=organization,
            user=request.user,
            role__in=['admin', 'owner']
        ).first()

        return membership is not None
