from django.conf import settings
from django.utils import timezone


def mandato(request):
    return {
        "NOME_DO_MANDATO": settings.NOME_DO_MANDATO,
        "NOME_CURTO_DO_MANDATO": settings.NOME_CURTO_DO_MANDATO,
        "SIGLA_MANDATO": settings.SIGLA_MANDATO,
    }


def pendencias_usuario(request):
    """Contadores para topbar (Fase 5): pendências vencidas do usuário e
    itens pendentes no inbox. Só popula se logado — sem query a mais para
    requests anônimas."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    # Imports tardios para evitar circularidade com apps que ainda não
    # carregaram quando o módulo é importado pela primeira vez.
    from demandas.models import Interacao, ItemInbox

    vencidas = Interacao.objects.filter(
        autor=request.user,
        status=Interacao.STATUS_AGENDADA,
        data_ocorrencia__lt=timezone.now(),
    ).count()
    inbox_pendente = ItemInbox.objects.filter(status=ItemInbox.STATUS_PENDENTE).count()
    return {
        "topbar_pendencias_vencidas": vencidas,
        "topbar_inbox_pendentes": inbox_pendente,
    }
