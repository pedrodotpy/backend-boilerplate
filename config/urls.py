from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView
from rest_framework.routers import DefaultRouter

from apps.users.api.views import (
    EmailTokenObtainPairView,
    EmailTokenRefreshView,
    ForgotPasswordView,
    LogoutView,
    MeView,
    ResendCodeView,
    ResetPasswordView,
    VerifyCodeView,
)
from apps.users.routes import routes as users_routes

router = DefaultRouter()
for route in users_routes:
    router.register(route["regex"], route["viewset"], basename=route["basename"])

auth_urlpatterns = [
    path("token/", EmailTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", EmailTokenRefreshView.as_view(), name="token_refresh"),
    path("verify-code/", VerifyCodeView.as_view(), name="verify_code"),
    path("resend-code/", ResendCodeView.as_view(), name="resend_code"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset_password"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include(auth_urlpatterns)),
    path("api/v1/", include(router.urls)),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
]
