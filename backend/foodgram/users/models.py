from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models

from .utils import UserRoles

username_validator = UnicodeUsernameValidator()


class User(AbstractUser):
    username = models.CharField(
        "Имя пользователя",
        max_length=150,
        unique=True,
        validators=[username_validator],
        error_messages={
            "unique": "Пользователь с таким именем уже существует!",
        },
    )
    email = models.EmailField(
        "Почта",
        max_length=254,
        unique=True,
        error_messages={
            'unique': "Пользователь с такой почтой уже существует!",
        },
    )
    role = models.CharField(
        max_length=25,
        verbose_name="Роль",
        choices=UserRoles.choice(),
        default=UserRoles.user.name,
    )
    first_name = models.CharField(
        "Имя", max_length=150, null=True, blank=True)
    last_name = models.CharField(
        "Фамилия", max_length=150, null=True, blank=True
    )
    confirmation_code = models.CharField(
        "Код авторизациии",
        max_length=60,
        blank=True,
        null=True,
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

    @property
    def is_admin(self) -> bool:
        return self.role == UserRoles.admin.name or self.is_superuser

    @property
    def is_user(self) -> bool:
        return self.role == UserRoles.user.name

    @property
    def is_guest(self) -> bool:
        return self.role == UserRoles.guest.name
