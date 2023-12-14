from typing import Any, Literal
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAuthorOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj) -> Any | Literal[True]:
        return request.method in SAFE_METHODS or obj.author == request.user


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view) -> Any | Literal[True]:
        return (
            request.method in SAFE_METHODS
            or request.user
            and request.user.is_staff
        )
