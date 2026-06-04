from django.apps import AppConfig


class PessoasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pessoas"

    def ready(self):
        from auditlog.registry import auditlog

        from . import signals  # noqa: F401  (registra receivers via @receiver)
        from .models import (
            EmailContato,
            Entidade,
            Pessoa,
            RedeSocial,
            Site,
            Tag,
            Telefone,
            Vinculo,
        )

        auditlog.register(Pessoa)
        auditlog.register(Entidade)
        auditlog.register(Vinculo)
        auditlog.register(Tag)
        auditlog.register(Telefone)
        auditlog.register(EmailContato)
        auditlog.register(RedeSocial)
        auditlog.register(Site)
