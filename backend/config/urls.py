"""
URL configuration for Security Analysis Platform.
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from api.views import DashboardStatsView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # API (New - for frontend)
    path('api/dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('api/scans/', include('apps.scans.api.urls')),
    path('api/', include('apps.findings.api.urls')),  # Includes /api/findings/ and /api/clusters/

    # API v1 (Legacy - keep for backward compatibility)
    path('api/v1/auth/', include('apps.authentication.urls')),
    path('api/v1/organizations/', include('apps.organizations.urls')),
    path('api/v1/scans/', include('apps.scans.urls')),
    path('api/v1/findings/', include('apps.findings.urls')),
    path('api/v1/users/', include('apps.users.urls')),

    # Social Auth (GitHub OAuth)
    path('auth/', include('social_django.urls', namespace='social')),
]
