from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)
from .views import (
    RegistrationView,
    ContactViewSet,
    SearchView,
    SpamViewSet,
    health_check
)

# Create a router for viewsets
router = DefaultRouter()
router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'spam', SpamViewSet, basename='spam')

# Auth URLs
auth_urls = [
    path('register/', RegistrationView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify/', TokenVerifyView.as_view(), name='token_verify'),
]

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Auth endpoints
    path('auth/', include((auth_urls, 'auth'))),
    
    # Search endpoint
    path('search/', SearchView.as_view(), name='search'),

    # Health check endpoint
    path('health/', health_check, name='health_check'),
] 