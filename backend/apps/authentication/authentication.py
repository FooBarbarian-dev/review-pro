"""
Custom authentication backends for API key authentication (ADR-007).
"""
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import authentication
from rest_framework import exceptions

User = get_user_model()


class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    API Key authentication backend.
    Clients can authenticate using X-API-Key header.
    """
    keyword = 'X-API-Key'

    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')

        if not api_key:
            return None

        try:
            user = User.objects.get(api_key=api_key, is_active=True)

            # Update last used timestamp
            user.api_key_last_used_at = timezone.now()
            user.save(update_fields=['api_key_last_used_at'])

            return (user, None)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid API key')
