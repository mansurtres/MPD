from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ["email", "nome_completo", "cargo", "coordenacao", "is_staff", "is_active"]
    list_filter = ["is_staff", "is_active", "coordenacao"]
    search_fields = ["email", "nome_completo"]
    ordering = ["email"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informações pessoais", {"fields": ("nome_completo", "cargo", "coordenacao")}),
        (
            "Permissões",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Datas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "nome_completo", "password1", "password2"),
            },
        ),
    )
