"""Middleware de Correlation ID para o django-auditlog.

Gera um UUID único por request/response e seta no `correlation_id` ContextVar
do auditlog. Todas as entradas de LogEntry geradas dentro desta request
compartilham o mesmo CID — útil quando uma ação (ex: deletar Pessoa) cascateia
em vários models registrados (Telefone, EmailContato, RedeSocial, Site, Vinculo).
"""

import uuid

from auditlog.cid import correlation_id


class AuditlogCorrelationMiddleware:
    """Seta o correlation_id ContextVar do auditlog para cada request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = correlation_id.set(uuid.uuid4().hex)
        try:
            return self.get_response(request)
        finally:
            correlation_id.reset(token)
