from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import AuthTokenView, RegistrationView, UserViewSet

app_name = "users"

router = DefaultRouter()
router.register(r"users", UserViewSet)


auth_urlpatterns = [
    path("signup/", RegistrationView.as_view(), name="signup"),
    path("token/", AuthTokenView.as_view(), name="auth"),
]

urlpatterns = [
    path("v1/auth/", include(auth_urlpatterns)),
    path("v1/", include(router.urls)),
]
