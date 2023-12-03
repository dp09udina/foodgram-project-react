from django.shortcuts import get_object_or_404

from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "bio",
            "role",
        )

    def validate(self, data):
        if data.get("username") != "me":
            return data
        raise serializers.ValidationError("Запрещенное имя пользователя")


class UserEditSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        read_only_fields = ("role",)


class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "email",
            "username",
        )

    def validate_username(self, value):
        if value == "me":
            raise serializers.ValidationError(
                "Невозможно создать пользователя с таким именем"
            )
        return value


class ObtainTokenSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=150)
    confirmation_code = serializers.CharField(max_length=60)

    class Meta:
        model = User
        fields = ("username", "confirmation_code")

        def validate(self, data):
            username = data["username"]
            user = get_object_or_404(User, username=username)
            if user.confirmation_code != data["confirmation_code"]:
                raise serializers.ValidationError(
                    "Код подтверждения не верен!"
                )
            return data
