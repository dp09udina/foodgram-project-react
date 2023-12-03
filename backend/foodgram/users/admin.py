from django.contrib import admin

from .models import User


@admin.register(User)
class UsersAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {"fields": ("username", "email")}),
        (
            "Personal information",
            {
                "fields": (
                    "first_name",
                    "last_name",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login",)}),
    )
    list_display = (
        "id",
        "username",
        "full_name",
    )
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
    )
    search_fields = (
        "full_name",
        "id",
        "email",
    )
    ordering = ("-id",)
    filter_horizontal = ("user_permissions",)
    readonly_fields = ("last_login",)
