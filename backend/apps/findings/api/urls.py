"""
URL configuration for Findings API.
"""
from rest_framework.routers import DefaultRouter
from apps.findings.api.views import FindingViewSet, FindingClusterViewSet

router = DefaultRouter()
router.register(r'findings', FindingViewSet, basename='finding')
router.register(r'clusters', FindingClusterViewSet, basename='cluster')

urlpatterns = router.urls
