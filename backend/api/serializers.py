from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer

# from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import AnonymousUser

from recipes.models import (
    Favorite,
    Ingredient,
    IngredientRecipe,
    Recipe,
    ShoppingCart,
    Tag,
)
from users.models import User

import base64

from django.core.files.base import ContentFile


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:image"):
            format, imgstr = data.split(";base64,")
            ext = format.split("/")[-1]

            data = ContentFile(base64.b64decode(imgstr), name="temp." + ext)

        return super().to_internal_value(data)


class UserSerializer(UserSerializer):
    """Сериализатор пользователя"""

    is_subscribed = SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
        )

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if self.context.get("request").user.is_anonymous:
            return False
        return obj.following.filter(user=request.user).exists()


class UserCreateSerializer(UserCreateSerializer):
    """Сериализатор создания пользователя"""

    class Meta:
        model = User
        fields = (
            "email",
            "username",
            "first_name",
            "last_name",
            "password",
            "id",
        )


class SubscribeListSerializer(UserSerializer):
    """Сериализатор для получения подписок"""

    recipes_count = SerializerMethodField()
    recipes = SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ("recipes_count", "recipes")
        read_only_fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
        )

    def validate(self, data):
        author_id = (
            self.context.get("request").parser_context.get("kwargs").get("id")
        )
        author = get_object_or_404(User, id=author_id)
        if (
            not self.context.get("request").user
            or self.context.get("request").user.is_anonymous
        ):
            raise ValidationError(
                detail="Anonymous",
                code=status.HTTP_401_UNAUTHORIZED,
            )
        user = self.context.get("request").user
        if user.follower.filter(author=author_id).exists():
            raise ValidationError(
                detail="Подписка уже существует",
                code=status.HTTP_400_BAD_REQUEST,
            )
        if user == author:
            raise ValidationError(
                detail="Нельзя подписаться на самого себя",
                code=status.HTTP_400_BAD_REQUEST,
            )
        return data

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_recipes(self, obj):
        request = self.context.get("request")
        limit = request.GET.get("recipes_limit")
        recipes = obj.recipes.all()
        if limit:
            recipes = recipes[: int(limit)]
        serializer = LiteRecipeSerializer(recipes, many=True, read_only=True)
        return serializer.data


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор просмотра тегов"""

    class Meta:
        model = Tag
        fields = ("id", "name", "color", "slug")


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор просмотра ингридиентов"""

    class Meta:
        model = Ingredient
        fields = (
            "id",
            "name",
            "measurement_unit",
        )


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор связи ингридиентов и рецепта"""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit"
    )

    class Meta:
        model = IngredientRecipe
        fields = (
            "id",
            "name",
            "measurement_unit",
            "amount",
        )


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор просмотра рецепта"""

    tags = TagSerializer(read_only=False, many=True)
    author = UserSerializer(read_only=True, many=False)
    ingredients = IngredientRecipeSerializer(
        many=True, source="ingredienttorecipe"
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(max_length=None)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    def get_ingredients(self, obj):
        ingredients = IngredientRecipe.objects.filter(recipe=obj)
        return IngredientRecipeSerializer(ingredients, many=True).data

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        if not request or request.user.is_anonymous:
            return False
        return obj.favorites.filter(user=request.user).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get("request")
        if not request or request.user.is_anonymous:
            return False
        return obj.shopping_list.filter(user=request.user).exists()


class CreateRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для создания рецепта"""

    ingredients = IngredientRecipeSerializer(
        many=True,
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        # error_messages={"does_not_exist": "Указанного тега не существует"},
    )
    image = Base64ImageField(max_length=None)
    author = UserSerializer(read_only=True)
    cooking_time = serializers.IntegerField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    def validate_tags(self, tags):
        for tag in tags:
            if not Tag.objects.filter(id=tag.id).exists():
                raise serializers.ValidationError(
                    "Указанного тега не существует",
                    code=status.HTTP_400_BAD_REQUEST,
                )
        return tags

    def validate_cooking_time(self, cooking_time):
        if cooking_time < 1:
            raise serializers.ValidationError(
                "Время готовки должно быть не меньше одной минуты"
            )
        return cooking_time

    def validate_ingredients(self, ingredients):
        ingredients_list = []
        if not ingredients:
            raise serializers.ValidationError("Отсутствуют ингридиенты")
        for ingredient in ingredients:
            if ingredient["id"] in ingredients_list:
                raise serializers.ValidationError(
                    "Ингридиенты должны быть уникальны"
                )
            ingredients_list.append(ingredient["id"])
            if int(ingredient.get("amount")) < 1:
                raise serializers.ValidationError(
                    "Количество ингредиента больше 0"
                )
        return ingredients

    @staticmethod
    def create_ingredients(recipe, ingredients):
        ingredient_list = []
        for ingredient_data in ingredients:
            ingredient_list.append(
                IngredientRecipe(
                    ingredient=ingredient_data.pop("id"),
                    amount=ingredient_data.pop("amount"),
                    recipe=recipe,
                )
            )
        IngredientRecipe.objects.bulk_create(ingredient_list)

    def create(self, validated_data):
        request = self.context.get("request", None)
        if not request or request.user.is_anonymous:
            raise ValidationError(
                detail="Неавторизованный пользователь",
                code=status.HTTP_401_UNAUTHORIZED,
            )
        else:
            tags = validated_data.pop("tags")
            if tags != list(set(tags)):
                raise ValidationError(
                    detail="Одинаковые теги",
                    code=status.HTTP_400_BAD_REQUEST,
                )
            image = validated_data.get("image")
            if not tags:
                raise ValidationError(
                    detail="Отсутствует тег",
                    code=status.HTTP_400_BAD_REQUEST,
                )
            if not image:
                raise ValidationError(
                    detail="Отсутствует фото",
                    code=status.HTTP_400_BAD_REQUEST,
                )

            ingredients = validated_data.pop("ingredients")

            recipe = Recipe.objects.create(
                author=request.user, **validated_data
            )
            recipe.tags.set(tags)
            self.create_ingredients(recipe, ingredients)
            return recipe

    def update(self, instance, validated_data):
        instance.tags.clear()
        IngredientRecipe.objects.filter(recipe=instance).delete()
        if validated_data.get("tags"):
            if validated_data.get("tags") != list(
                set(validated_data.get("tags"))
            ):
                raise ValidationError(
                    detail="Одинаковые теги",
                    code=status.HTTP_400_BAD_REQUEST,
                )
            instance.tags.set(validated_data.get("tags"))
        else:
            raise ValidationError(
                detail="Отсутствует тэг",
                code=status.HTTP_400_BAD_REQUEST,
            )
        if validated_data.get("ingredients"):
            ingredients = validated_data.get("ingredients")
        else:
            raise ValidationError(
                detail="Отсутствует ингридиент",
                code=status.HTTP_400_BAD_REQUEST,
            )
        if not validated_data.get("image"):
            raise ValidationError(
                detail="Отсутствует фото",
                code=status.HTTP_400_BAD_REQUEST,
            )
        self.create_ingredients(instance, ingredients)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(
            instance, context={"request": self.context.get("request")}
        ).data


class LiteRecipeSerializer(serializers.ModelSerializer):
    # image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор избранных рецептов"""

    class Meta:
        model = Favorite
        fields = (
            "user",
            "recipe",
        )

    def validate(self, data):
        user = data["user"]
        print(user.favorites.filter(recipe=data["recipe"]))
        if user.favorites.filter(recipe=data["recipe"]).exists():
            raise serializers.ValidationError(
                "Рецепт уже добавлен в избранное."
            )
        return data

    def to_representation(self, instance):
        return LiteRecipeSerializer(
            instance.recipe, context={"request": self.context.get("request")}
        ).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для списка покупок"""

    class Meta:
        model = ShoppingCart
        fields = (
            "user",
            "recipe",
        )

    def validate(self, data):
        user = data["user"]
        if user.shopping_list.filter(recipe=data["recipe"]).exists():
            raise serializers.ValidationError(
                status="Рецепт уже добавлен в корзину",
                code=status.HTTP_400_BAD_REQUEST,
            )
        return data

    def to_representation(self, instance):
        return LiteRecipeSerializer(
            instance.recipe, context={"request": self.context.get("request")}
        ).data
