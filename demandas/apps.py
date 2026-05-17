from django.apps import AppConfig


class DemandasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "demandas"

    def ready(self):
        from auditlog.registry import auditlog

        from . import signals  # noqa: F401  (registra receivers via @receiver)
        from .models import Anexo, Demanda, Encaminhamento, Interacao, ItemInbox, Tema

        auditlog.register(Demanda)
        auditlog.register(Encaminhamento)
        auditlog.register(Anexo)
        auditlog.register(Tema)
        # ADR 0050: timeline e inbox entram na trilha (revisita ADR 0029).
        # Interações automáticas geram volume — aceito como custo de auditoria
        # correta (quem mudou o quê quando). Se ficar barulhento em produção,
        # considerar exclude_fields ou filtro no AuditlogCorrelationMiddleware.
        auditlog.register(Interacao)
        auditlog.register(ItemInbox)
