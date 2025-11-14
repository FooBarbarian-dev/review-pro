"""
URL configuration for Scans API.
"""
from rest_framework.routers import DefaultRouter
from apps.scans.api.views import ScanViewSet

router = DefaultRouter()
router.register(r'', ScanViewSet, basename='scan')

urlpatterns = router.urls
