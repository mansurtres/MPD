from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        from auditlog.registry import auditlog

        from .models import Usuario

        # Trilha LGPD: rastreia criação, alteração, desativação de usuário.
        # Exclui password (hash, mas é segredo de qualquer forma) e last_login
        # (rotineiro; ruído na trilha sem valor de auditoria).
        auditlog.register(Usuario, exclude_fields=["password", "last_login"])
