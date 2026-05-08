from django.apps import AppConfig


class PessoasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pessoas"

    def ready(self):
        from auditlog.registry import auditlog

        from .models import Entidade, Pessoa, Tag, Vinculo

        auditlog.register(Pessoa)
        auditlog.register(Entidade)
        auditlog.register(Vinculo)
        auditlog.register(Tag)
