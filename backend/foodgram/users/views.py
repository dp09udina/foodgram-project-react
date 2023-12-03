from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404

from api.permissions import IsAdmin
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from .models import User
from .serializers import (
    ObtainTokenSerializer,
    RegistrationSerializer,
    UserEditSerializer,
    UserSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "delete"]
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAdmin,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ("username",)
    lookup_field = "username"

    @action(
        methods=["GET", "PATCH"],
        detail=False,
        url_path="me",
        permission_classes=(permissions.IsAuthenticated,),
        serializer_class=UserEditSerializer,
    )
    def user_detail(self, request):
        if request.method == "PATCH":
            serializer = self.get_serializer(
                request.user, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
        else:
            serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RegistrationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        email = request.data.get("email")
        username = request.data.get("username")
        user = User.objects.filter(email=email, username=username)
        if user.exists():
            user = user.get(email=email)
            code_generator(user)
            send_code_mail(user)
            return Response(data=f"{username},{email}", status=status.HTTP_200_OK)
        serializer.is_valid(raise_exception=True)
        user = User.objects.create(
            username=username, email=email
        )
        user.save()
        code_generator(user)
        send_code_mail(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuthTokenView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ObtainTokenSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.data["username"]
            confirmation_code = serializer.data["confirmation_code"]
            user = get_object_or_404(User, username=username)
            if not default_token_generator.check_token(user, confirmation_code):
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST,
                )
            token = AccessToken.for_user(user)
            return Response(
                {"token": str(token)}, status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def code_generator(user):
    code = default_token_generator.make_token(user)
    user.confirmation_code = code
    user.save()


def send_code_mail(user):
    send_mail(
        subject="Код подтверждения",
        message=f"Ваш код подтверждения: {user.confirmation_code}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
