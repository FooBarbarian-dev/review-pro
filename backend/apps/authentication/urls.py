"""
URL configuration for authentication app.
"""
from django.urls import path
from .views import (
    LoginView, RefreshTokenView, LogoutView,
    GitHubCallbackView, UserInfoView
)

urlpatterns = [
    # JWT authentication
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', RefreshTokenView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # GitHub OAuth
    path('callback/', GitHubCallbackView.as_view(), name='github_callback'),

    # User info
    path('me/', UserInfoView.as_view(), name='user_info'),
]
