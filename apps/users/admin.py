from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """UserAdmin sem username — o acesso é pelo e-mail."""

    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "cargo", "is_staff")
    list_filter = ("cargo", "is_staff", "is_superuser", "is_active")
    search_fields = ("email", "first_name", "last_name", "cnpj")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Informações pessoais"), {"fields": ("first_name", "last_name", "cnpj", "telefone", "cargo")}),
        (_("Permissões"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Datas importantes"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "cargo"),
        }),
    )
