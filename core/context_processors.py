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
    itens pendentes no inbox. Inclui também flags de papel para uso em
    templates (Fase 6 — auditoria e análise). Só popula se logado — sem
    query a mais para requests anônimas."""
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

    # Nomes de grupo só podem aparecer em core/permissoes.py — ADR 0024/0048.
    # Reusamos os literais via constantes para as flags por papel que os
    # templates consomem (admin vs chefe; ADR 0059 — 3 papéis).
    from core.permissoes import GRUPO_ADM, GRUPO_CG

    grupos = set(request.user.groups.values_list("name", flat=True))
    eh_admin = request.user.is_superuser or GRUPO_ADM in grupos
    eh_chefe = GRUPO_CG in grupos

    return {
        "topbar_pendencias_vencidas": vencidas,
        "topbar_inbox_pendentes": inbox_pendente,
        "papel_eh_admin": eh_admin,
        "papel_eh_chefe": eh_chefe,
        # Conveniência: CG+ (Admin ou Chefe de Gabinete).
        "papel_cg_plus": eh_admin or eh_chefe,
    }
