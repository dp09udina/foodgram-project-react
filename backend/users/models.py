from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models


class User(AbstractUser):
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = (
        "username",
        "first_name",
        "last_name",
    )

    username = models.CharField(
        verbose_name="Логин",
        max_length=150,
        unique=True,
        validators=(UnicodeUsernameValidator(),),
    )
    email = models.EmailField(
        verbose_name="Почта",
        max_length=254,
        unique=True,
        error_messages={
            "unique": "Пользователь с такой почтой уже существует!",
        },
    )
    first_name = models.CharField(
        verbose_name="Имя",
        max_length=150,
    )
    last_name = models.CharField(
        verbose_name="Фамилия",
        max_length=150,
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

    def __str__(self) -> str:
        return self.username


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="follower",
        verbose_name="Подписчик",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="following",
        verbose_name="Автор рецепта",
    )

    class Meta:
        ordering = ["-id"]
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "author"],
                name="unique follow",
            )
        ]
