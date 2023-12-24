from typing import Any
from django.contrib.auth import get_user_model
from django_filters.rest_framework import FilterSet, filters
from rest_framework.filters import SearchFilter

from api.models import Ingredient, Recipe

User = get_user_model()


class IngredientSearchFilter(SearchFilter):
    search_param = "name"

    class Meta:
        model = Ingredient
        fields = ("name",)


class TagFilter(FilterSet):
    tags = filters.AllValuesMultipleFilter(field_name="tags__slug")
    author = filters.ModelChoiceFilter(queryset=User.objects.all())
    is_favorited = filters.BooleanFilter(method="filter_is_favorited")
    is_in_shopping_cart = filters.BooleanFilter(
        method="filter_is_in_shopping_cart"
    )

    def filter_is_favorited(self, queryset, name, value) -> Any:
        if value and self.request.user.is_authenticated:
            return queryset.filter(favorites__user=self.request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value) -> Any:
        if value and self.request.user.is_authenticated:
            return queryset.filter(cart__user=self.request.user)
        return queryset

    class Meta:
        model = Recipe
        fields = ("tags", "author")
