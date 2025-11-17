"""
URL configuration for scans app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ScanViewSet, QuotaUsageViewSet
from .sse import scan_events_view, scan_status_view

router = DefaultRouter()
router.register(r'', ScanViewSet, basename='scan')
router.register(r'quota', QuotaUsageViewSet, basename='quota')

urlpatterns = [
    path('', include(router.urls)),

    # SSE endpoints (must come after router to avoid conflicts)
    path('<uuid:scan_id>/events/', scan_events_view, name='scan-events'),
    path('<uuid:scan_id>/status/', scan_status_view, name='scan-status'),
]
