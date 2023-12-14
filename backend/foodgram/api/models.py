from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

User = get_user_model()

# TODO сделать прилично
BLUE = "#0000FF"
ORANGE = "#FFA500"
GREEN = "#008000"
PURPLE = "#800080"
YELLOW = "#FFFF00"

COLOR_CHOICES = [
    (BLUE, "Синий"),
    (ORANGE, "Оранжевый"),
    (GREEN, "Зеленый"),
    (PURPLE, "Фиолетовый"),
    (YELLOW, "Желтый"),
]


class Tag(models.Model):
    name = models.CharField(
        verbose_name="Тэг",
        max_length=64,
        unique=True,
    )
    color = models.CharField(
        verbose_name="Цвет в HEX",
        max_length=7,
        choices=COLOR_CHOICES,
        unique=True,
        db_index=False,
    )
    slug = models.CharField(
        verbose_name="Слаг тэга",
        max_length=64,
        unique=True,
        db_index=False,
    )

    class Meta:
        verbose_name = "Тэг"
        verbose_name_plural = "Тэги"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Ingredient(models.Model):
    name = models.CharField("Название", max_length=256)
    measurement_unit = models.CharField("Единица измерения", max_length=32)

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        ordering = ["name"]
        constraints = (
            models.UniqueConstraint(
                fields=("name", "measurement_unit"),
                name="unique_for_ingredient",
            ),
        )

    def __str__(self) -> str:
        return f"{self.name}, {self.measurement_unit}"


class Recipe(models.Model):
    name = models.CharField(
        verbose_name="Название блюда",
        max_length=64,
    )
    author = models.ForeignKey(
        verbose_name="Автор рецепта",
        related_name="recipes",
        to=User,
        on_delete=models.SET_NULL,
        null=True,
    )
    tags = models.ManyToManyField(
        verbose_name="Тег",
        related_name="recipes",
        to="Tag",
    )
    ingredients = models.ManyToManyField(
        verbose_name="Ингредиенты блюда",
        related_name="recipes",
        to=Ingredient,
        through="AmountIngredient",
    )
    pub_date = models.DateTimeField(
        verbose_name="Дата публикации",
        auto_now_add=True,
        editable=False,
    )
    image = models.ImageField(
        verbose_name="Изображение блюда",
        upload_to="recipe_images/",
    )
    text = models.TextField(
        verbose_name="Описание блюда",
        max_length=256,
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name="Время приготовления",
        default=0,
        validators=(
            MinValueValidator(
                1,
                "Кажется уже готово!",
            ),
            MaxValueValidator(
                480,
                "Это ж полный рабочий день.. Слишком долго..",
            ),
        ),
    )

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"
        ordering = ("-pub_date",)
        constraints = (
            models.UniqueConstraint(
                fields=("name", "author"),
                name="unique_for_author",
            ),
        )

    def __str__(self) -> str:
        return f"{self.name}. Автор: {self.author.username}"


class AmountIngredient(models.Model):
    recipe = models.ForeignKey(
        verbose_name="В каких рецептах",
        related_name="ingredient",
        to=Recipe,
        on_delete=models.CASCADE,
    )
    ingredients = models.ForeignKey(
        verbose_name="Связанные ингредиенты",
        related_name="recipe",
        to=Ingredient,
        on_delete=models.CASCADE,
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name="Количество",
        default=0,
        validators=(
            MinValueValidator(
                1,
                "Нужен хотя бы один ингридиент!",
            ),
            MaxValueValidator(
                50,
                "Очень много!",
            ),
        ),
    )

    class Meta:
        verbose_name = "Ингридиент"
        verbose_name_plural = "Количество ингридиентов"
        ordering = ("recipe",)

    def __str__(self) -> str:
        return f"{self.amount} {self.ingredients}"
