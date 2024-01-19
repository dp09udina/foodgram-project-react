import base64

from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField

import api.constraints

from recipes.models import (
    Favorite,
    Ingredient,
    IngredientRecipe,
    Recipe,
    ShoppingCart,
    Tag,
)
from users.models import User


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
            )
        if user == author:
            raise ValidationError(
                detail="Нельзя подписаться на самого себя",
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


class IngredientInRecipeWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(write_only=True)

    class Meta:
        model = IngredientRecipe
        fields = ("id", "amount")


class CreateRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для рецептов."""

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    author = UserSerializer(read_only=True)
    ingredients = IngredientInRecipeWriteSerializer(many=True)
    image = Base64ImageField()

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
        if not tags:
            raise ValidationError(
                detail="Отсутствует тег",
            )
        if len(tags) != len(list(set(tags))):
            raise ValidationError(
                detail="Одинаковые теги",
            )
        return tags

    def validate_cooking_time(self, cooking_time):
        if cooking_time < api.constraints.COOKING_TIME_MIN_VALUE:
            raise serializers.ValidationError(
                "Время готовки должно быть не меньше одной минуты",
            )
        return cooking_time

    def validate_ingredients(self, ingredients):
        ingredients_list = []
        if not ingredients:
            raise serializers.ValidationError(
                "Отсутствуют ингридиенты",
            )
        for ingredient in ingredients:
            if ingredient["id"] in ingredients_list:
                raise serializers.ValidationError(
                    "Ингридиенты должны быть уникальны",
                    code=status.HTTP_400_BAD_REQUEST,
                )
            ingredients_list.append(ingredient["id"])
            if int(ingredient.get("amount")) < 1:
                raise serializers.ValidationError(
                    "Количество ингредиента больше 0",
                    code=status.HTTP_400_BAD_REQUEST,
                )
        return ingredients

    def create_ingredients_amounts(self, ingredients, recipe):
        ingredient_list = [
            IngredientRecipe(
                ingredient=Ingredient.objects.get(id=ingredient["id"]),
                recipe=recipe,
                amount=ingredient["amount"],
            )
            if Ingredient.objects.filter(id=ingredient["id"]).exists()
            else None
            for ingredient in ingredients
        ]
        if not all(ingredient_list):
            raise serializers.ValidationError(
                "Отсутствуют ингридиенты",
            )

        IngredientRecipe.objects.bulk_create(ingredient_list)

    def create(self, validated_data):
        if not validated_data.get("tags"):
            raise serializers.ValidationError(
                "Отсутствуют ингридиенты",
            )
        tags = validated_data.pop("tags")
        request = self.context.get("request", None)
        if not validated_data.get("ingredients"):
            raise serializers.ValidationError(
                "Отсутствуют ингридиенты",
            )
        ingredients = validated_data.pop("ingredients")
        recipe = Recipe.objects.create(author=request.user, **validated_data)
        recipe.tags.set(tags)
        if not ingredients:
            raise serializers.ValidationError(
                "Отсутствуют ингридиенты",
            )

        self.create_ingredients_amounts(recipe=recipe, ingredients=ingredients)
        return recipe

    def update(self, instance, validated_data):
        if not validated_data.get("ingredients"):
            raise serializers.ValidationError(
                "Отсутствуют ингридиенты",
            )
        if not validated_data.get("tags"):
            raise serializers.ValidationError(
                "Отсутствуют теги",
            )
        tags = validated_data.pop("tags")
        ingredients = validated_data.pop("ingredients")
        instance = super().update(instance, validated_data)
        instance.tags.clear()
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.create_ingredients_amounts(
            recipe=instance, ingredients=ingredients
        )
        instance.save()
        return instance

    def to_representation(self, instance):
        request = self.context.get("request")
        context = {"request": request}
        return RecipeReadSerializer(instance, context=context).data


class LiteRecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

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
            )
        return data

    def to_representation(self, instance):
        return LiteRecipeSerializer(
            instance.recipe, context={"request": self.context.get("request")}
        ).data
