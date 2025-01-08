from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import UserViewSet, ContactViewSet, SpamReportViewSet, SearchView

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'spam-reports', SpamReportViewSet, basename='spam-report')

urlpatterns = [
    path('', include(router.urls)),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('search/', SearchView.as_view(), name='search'),
] 