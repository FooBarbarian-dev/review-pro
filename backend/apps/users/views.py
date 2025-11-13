"""
Views for User management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import User
from .serializers import UserSerializer, UserDetailSerializer, APIKeySerializer


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing and managing users.
    """
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve' or self.action == 'me':
            return UserDetailSerializer
        return UserSerializer

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get the current authenticated user."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def generate_api_key(self, request):
        """Generate a new API key for the current user."""
        user = request.user
        api_key = user.generate_api_key()
        return Response(
            APIKeySerializer({
                'api_key': api_key,
                'created_at': user.api_key_created_at
            }).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['delete'])
    def revoke_api_key(self, request):
        """Revoke the current user's API key."""
        request.user.revoke_api_key()
        return Response(status=status.HTTP_204_NO_CONTENT)
