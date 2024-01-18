from rest_framework.permissions import SAFE_METHODS, BasePermission


class AuthorPermission(BasePermission):
    """Разрешает изменение и добавление объектов
    только их автору"""

    def has_object_permission(self, request, view, obj) -> bool:
        return request.method in SAFE_METHODS or obj.author == request.user


class IsSubscribeOnly(BasePermission):
    """Разрешает удаление только для действий с подписками."""

    def has_permission(self, request, view) -> bool:
        return view.action == "subscribe"
