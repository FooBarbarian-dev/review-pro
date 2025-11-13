"""
URL configuration for findings app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FindingViewSet, FindingCommentViewSet

router = DefaultRouter()
router.register(r'', FindingViewSet, basename='finding')
router.register(r'comments', FindingCommentViewSet, basename='finding-comment')

urlpatterns = [
    path('', include(router.urls)),
]
