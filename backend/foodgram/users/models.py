from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator

from .utils import UserRoles

username_validator = UnicodeUsernameValidator()


class User(AbstractUser):
    username = models.CharField(
        verbose_name="Имя пользователя",
        max_length=128,
        unique=True,
        # validators=(
        #     MinValueValidator(
        #         3,
        #         "Логин должен быть от 3 букв.",
        #     ),
        #     username_validator,
        # ),
    )
    email = models.EmailField(
        verbose_name="Почта",
        max_length=254,
        unique=True,
        error_messages={
            "unique": "Пользователь с такой почтой уже существует!",
        },
    )
    role = models.CharField(
        max_length=25,
        verbose_name="Роль",
        choices=UserRoles.choice(),
        default=UserRoles.user.name,
    )
    first_name = models.CharField(
        verbose_name="Имя",
        max_length=150,
        null=True,
        blank=True,
    )
    last_name = models.CharField(
        verbose_name="Фамилия",
        max_length=156,
        null=True,
        blank=True,
    )
    password = models.CharField(
        verbose_name=("Пароль"),
        max_length=128,
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["username", "email"], name="unique_user"
            )
        ]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __str__(self) -> str:
        return f"{self.username}: {self.email}"
