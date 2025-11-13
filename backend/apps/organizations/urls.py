"""
URL configuration for organizations app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrganizationViewSet, RepositoryViewSet, BranchViewSet

router = DefaultRouter()
router.register(r'', OrganizationViewSet, basename='organization')
router.register(r'repositories', RepositoryViewSet, basename='repository')
router.register(r'branches', BranchViewSet, basename='branch')

urlpatterns = [
    path('', include(router.urls)),
]
