"""
URL configuration for scans app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ScanViewSet, QuotaUsageViewSet

router = DefaultRouter()
router.register(r'', ScanViewSet, basename='scan')
router.register(r'quota', QuotaUsageViewSet, basename='quota')

urlpatterns = [
    path('', include(router.urls)),
]
