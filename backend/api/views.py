from django.db.models import Sum
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

import api.constraints
from recipes.models import (
    Favorite,
    Ingredient,
    IngredientRecipe,
    Recipe,
    ShoppingCart,
    Tag,
)
from users.models import Follow, User

from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPagination
from .permissions import AuthorPermission
from .serializers import (
    CreateRecipeSerializer,
    FavoriteSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    ShoppingCartSerializer,
    SubscribeListSerializer,
    TagSerializer,
    UserSerializer,
)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вывод ингредиентов"""

    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (IngredientFilter,)
    search_fields = ("^name",)
    pagination_class = None


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вывод тегов"""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """Вывод работы с рецептами"""

    serializer_class = CreateRecipeSerializer
    permission_classes = (
        AuthorPermission,
        IsAuthenticatedOrReadOnly,
    )
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_queryset(self):
        return Recipe.objects.select_related("author").prefetch_related(
            "ingredients", "tags"
        )

    def get_serializer_class(
        self,
    ):
        if self.request.method == "GET":
            return RecipeReadSerializer
        return CreateRecipeSerializer

    @staticmethod
    def send_message(ingredients) -> HttpResponse:
        shopping_list = "Купить в магазине:"
        for ingredient in ingredients:
            shopping_list += (
                f"\n{ingredient['ingredient__name']} "
                f"({ingredient['ingredient__measurement_unit']}) - "
                f"{ingredient['amount']}"
            )
        file = api.constraints.SHOPPING_LIST_NAME
        response = HttpResponse(shopping_list, content_type="text/plain")
        response["Content-Disposition"] = f'attachment; filename="{file}.txt"'
        return response

    @action(detail=False, methods=["GET"])
    def download_shopping_cart(self, request) -> HttpResponse:
        ingredients = (
            IngredientRecipe.objects.filter(
                recipe__shopping_list__user=request.user
            )
            .order_by("ingredient__name")
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(amount=Sum("amount"))
        )
        return self.send_message(ingredients)

    @action(
        detail=True, methods=("POST",), permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk):
        if not Recipe.objects.filter(id=pk).first():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        recipe = get_object_or_404(Recipe, id=pk)
        data = {"user": request.user.id, "recipe": recipe.id}
        if ShoppingCart.objects.filter(
            user=request.user, recipe=recipe
        ).first():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        serializer = ShoppingCartSerializer(
            data=data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def destroy_shopping_cart(self, request, pk) -> Response:
        recipe = get_object_or_404(Recipe, id=pk)
        if not ShoppingCart.objects.filter(
            user=request.user.id, recipe=recipe
        ).first():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        ShoppingCart.objects.filter(
            user=request.user.id, recipe=recipe
        ).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True, methods=("POST",), permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk):
        if Recipe.objects.filter(id=pk).exists():
            recipe = get_object_or_404(Recipe, id=pk)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        data = {"user": request.user.id, "recipe": recipe.id}
        serializer = FavoriteSerializer(
            data=data, context={"request": request}
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def destroy_favorite(self, request, pk) -> Response:
        recipe = get_object_or_404(Recipe, id=pk)
        if Favorite.objects.filter(user=request.user, recipe=recipe).first():
            Favorite.objects.filter(user=request.user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = CustomPagination

    def get_permissions(
        self,
    ):
        if self.request.method == "DELETE" or self.action in [
            "me",
            "subscriptions",
            "subscribe",
        ]:
            return [IsAuthenticated()]
        return [AllowAny()]

    @action(
        detail=True,
        methods=["POST"],
    )
    def subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(User, pk=id)

        serializer = SubscribeListSerializer(
            author, data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        Follow.objects.create(user=user, author=author)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, id):
        author = get_object_or_404(User, pk=id)

        if not Follow.objects.filter(user=request.user, author=author).first():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        following = get_object_or_404(Follow, user=request.user, author=author)
        following.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False)
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(following__user=user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscribeListSerializer(
            pages, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)
