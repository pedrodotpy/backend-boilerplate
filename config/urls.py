from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView
from rest_framework.routers import DefaultRouter

from apps.users.api.views import (
    EmailTokenObtainPairView,
    EmailTokenRefreshView,
    LogoutView,
    MeView,
)
from apps.users.routes import routes as users_routes

router = DefaultRouter()
for route in users_routes:
    router.register(route["regex"], route["viewset"], basename=route["basename"])

auth_urlpatterns = [
    path("token/", EmailTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", EmailTokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
]

urlpatterns = [
    path("api/v1/auth/", include(auth_urlpatterns)),
    path("api/v1/", include(router.urls)),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
]
