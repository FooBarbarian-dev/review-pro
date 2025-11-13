"""
Authentication views with JWT and GitHub OAuth support (ADR-007).
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import get_user_model

User = get_user_model()


class LoginView(TokenObtainPairView):
    """
    JWT login endpoint.
    Returns access and refresh tokens.
    """
    permission_classes = [AllowAny]


class RefreshTokenView(TokenRefreshView):
    """
    JWT token refresh endpoint.
    """
    permission_classes = [AllowAny]


class LogoutView(APIView):
    """
    Logout endpoint to blacklist the refresh token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GitHubCallbackView(APIView):
    """
    GitHub OAuth callback handler.
    After successful OAuth, returns JWT tokens.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Handle GitHub OAuth callback.
        The social-auth-app-django handles the OAuth flow,
        this endpoint returns JWT tokens for the authenticated user.
        """
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication failed'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Generate JWT tokens for the user
        refresh = RefreshToken.for_user(request.user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': str(request.user.id),
                'email': request.user.email,
                'github_username': request.user.github_username,
            }
        })


class UserInfoView(APIView):
    """
    Get current user information.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': str(user.id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'github_username': user.github_username,
            'avatar_url': user.avatar_url,
        })
