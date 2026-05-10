"""Middleware para repassar request.user ao thread-local consumido pelos
signals automáticos do app demandas. Sem isso, mudanças de estado feitas
em uma view não conseguem identificar o autor da interação automática
gerada — o signal só vê a instância do model, não o request.

Padrão herdado do que o django-auditlog faz internamente (AuditlogMiddleware
seta `actor` em ContextVar). Aqui tem o seu próprio para isolar contratos.
"""

from .signals import set_usuario_atual


class UsuarioAtualMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            set_usuario_atual(user)
        try:
            return self.get_response(request)
        finally:
            set_usuario_atual(None)
