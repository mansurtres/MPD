from django.apps import AppConfig


class DemandasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "demandas"

    def ready(self):
        from auditlog.registry import auditlog

        from . import signals  # noqa: F401  (registra receivers via @receiver)
        from .models import Anexo, Demanda, Encaminhamento

        auditlog.register(Demanda)
        auditlog.register(Encaminhamento)
        auditlog.register(Anexo)
