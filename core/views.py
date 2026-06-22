from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import ListView

from core.permissoes import eh_admin


def inicio(request):
    if not request.user.is_authenticated:
        return render(request, "core/inicio.html")

    # Contagem de demandas atribuídas ao usuário (apenas abertas) +
    # últimas 5 demandas visíveis para o painel "Demandas recentes" na home.
    from demandas.models import Demanda

    demandas_minhas_count = (
        Demanda.objects.filter(
            responsavel=request.user,
        )
        .exclude(
            status__in=[Demanda.STATUS_CONCLUIDA, Demanda.STATUS_ARQUIVADO],
        )
        .count()
    )

    demandas_recentes = list(
        Demanda.objects.visiveis_para(request.user).order_by("-atualizado_em", "-criado_em")[:5]
    )

    # Nomes de pessoas reais para popular o placeholder rotativo do composer.
    # Até 40 primeiros nomes embaralhados na request. Se a base ainda estiver
    # vazia, o JS cai na lista fictícia interna.
    import random as _random

    from pessoas.models import Pessoa

    nomes = list(
        Pessoa.objects.filter(ativo=True)
        .exclude(nome="")
        .values_list("nome", flat=True)
        .distinct()[:80]
    )
    _random.shuffle(nomes)
    nomes_placeholder = nomes[:40]

    return render(
        request,
        "core/inicio_autenticado.html",
        {
            "demandas_minhas_count": demandas_minhas_count,
            "demandas_recentes": demandas_recentes,
            "nomes_placeholder": nomes_placeholder,
        },
    )


@login_required
def configuracoes(request):
    """Hub de configurações administrativas. Cada card aparece conforme a
    permissão do usuário."""
    return render(request, "core/configuracoes.html")


def healthz(request):
    """Health check para monitoramento externo. Verifica conectividade ao
    banco. Público (sem login) — útil para hospedagem checar se o app
    está vivo. Retorna 200 se OK, 503 se DB inacessível."""
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:  # pragma: no cover — caminho de defesa
        return JsonResponse({"status": "error", "detail": str(exc)[:100]}, status=503)
    return JsonResponse({"status": "ok"})


# --- Fase 6: Auditoria UI ---


class AnaliseView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Painel de análise. Apenas Admin (ADR 0059 — visão agregada é
    governança, concentrada numa pessoa). Métricas textuais + gráficas
    (Chart.js via CDN — toggle por métrica). Não usa ListView de fato;
    reusa só o template/auth — context_data carrega as métricas."""

    template_name = "core/analise.html"

    def test_func(self):
        return eh_admin(self.request.user)

    def get_queryset(self):
        # Override exigido pelo ListView, mas não usado.
        from demandas.models import Demanda

        return Demanda.objects.none()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from datetime import timedelta

        from django.db.models import Count, Q
        from django.db.models.functions import TruncMonth
        from django.utils import timezone as tz

        from demandas.models import Demanda, Encaminhamento

        # ADR 0049/0059: as métricas filtram por demandas visíveis ao usuário
        # (defesa em profundidade — embora /analise hoje seja exclusivo do Admin).
        demandas_visiveis = Demanda.objects.visiveis_para(self.request.user)

        # 1. Demandas por tema
        ctx["por_tema"] = list(
            demandas_visiveis.values("temas__nome", "temas__cor")
            .annotate(total=Count("id"))
            .exclude(temas__nome__isnull=True)
            .order_by("-total")[:12]
        )

        # 2. Demandas por mês (últimos 12 meses)
        limite_mes = tz.now() - timedelta(days=365)
        ctx["por_mes"] = list(
            demandas_visiveis.filter(criado_em__gte=limite_mes)
            .annotate(mes=TruncMonth("criado_em"))
            .values("mes")
            .annotate(total=Count("id"))
            .order_by("mes")
        )

        # 3. Top 20 pessoas com mais demandas (era métrica 4) — agregação condicional para
        #    contar apenas demandas visíveis ao usuário. Sem isso, count
        #    incluía restritas (vazamento de PII associada a caso sigiloso).
        from pessoas.models import Pessoa

        filtro_visivel = Q(demanda_pessoas__demanda__in=demandas_visiveis)
        ctx["top_pessoas"] = list(
            Pessoa.objects.annotate(total=Count("demanda_pessoas", filter=filtro_visivel))
            .filter(total__gt=0)
            .order_by("-total")[:20]
            .values("nome", "sobrenome", "slug_publico", "total")
        )

        # 5. Encaminhamentos pendentes por órgão — filtra por demandas visíveis
        ctx["enc_por_orgao"] = list(
            Encaminhamento.objects.filter(
                demanda__in=demandas_visiveis,
                status__in=[Encaminhamento.STATUS_ENVIADO, Encaminhamento.STATUS_PRAZO_VENCIDO],
            )
            .values("destinatario_orgao")
            .annotate(total=Count("id"))
            .order_by("-total")[:15]
        )

        # 6. Carga por assessor — uma annotate em vez de N+1 (Tarefa 3.3).
        from accounts.models import Usuario

        status_abertos = [
            Demanda.STATUS_NOVO,
            Demanda.STATUS_EM_ANDAMENTO,
            Demanda.STATUS_AGUARDANDO_TERCEIROS,
            Demanda.STATUS_AGUARDANDO_PESSOA,
        ]
        status_fechados = [Demanda.STATUS_CONCLUIDA, Demanda.STATUS_ARQUIVADO]
        hoje = tz.now().date()
        # Materializa os ids visíveis em uma lista para usar como filtro
        # no Count(filter=...). Subquery direto também funcionaria, mas
        # `values_list` é mais legível e o cardinality fica explícito.
        ids_visiveis = list(demandas_visiveis.values_list("id", flat=True))
        filtro_abertas = Q(
            demandas_responsavel__in=ids_visiveis,
            demandas_responsavel__status__in=status_abertos,
        )
        filtro_vencidas = (
            Q(demandas_responsavel__in=ids_visiveis)
            & Q(demandas_responsavel__prazo__lt=hoje)
            & ~Q(demandas_responsavel__status__in=status_fechados)
        )
        assessores_qs = (
            Usuario.objects.filter(is_active=True)
            .annotate(
                qtd_abertas=Count("demandas_responsavel", filter=filtro_abertas, distinct=True),
                qtd_vencidas=Count("demandas_responsavel", filter=filtro_vencidas, distinct=True),
            )
            .filter(Q(qtd_abertas__gt=0) | Q(qtd_vencidas__gt=0))
            .order_by("-qtd_abertas")
        )
        ctx["carga_assessores"] = [
            {
                "nome": u.nome_completo or u.email,
                "abertas": u.qtd_abertas,
                "vencidas": u.qtd_vencidas,
            }
            for u in assessores_qs
        ]

        return ctx


class AuditoriaListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Lista entradas do auditlog cronologicamente. Restrito a
    Administrador. Diff visual antes/depois renderizado a partir do
    JSON do auditlog."""

    template_name = "core/auditoria.html"
    context_object_name = "logs"
    paginate_by = 50

    def test_func(self):
        return eh_admin(self.request.user)

    def get_queryset(self):
        from auditlog.models import LogEntry

        qs = LogEntry.objects.select_related("content_type", "actor").order_by("-timestamp")

        params = self.request.GET
        usuario = params.get("usuario", "").strip()
        if usuario:
            qs = qs.filter(actor__email__icontains=usuario)
        ct = params.get("modelo", "").strip()
        if ct:
            qs = qs.filter(content_type_id=ct)
        acao = params.get("acao", "").strip()
        if acao:
            qs = qs.filter(action=acao)
        desde = params.get("desde", "").strip()
        if desde:
            qs = qs.filter(timestamp__date__gte=desde)
        ate = params.get("ate", "").strip()
        if ate:
            qs = qs.filter(timestamp__date__lte=ate)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from auditlog.models import LogEntry

        ctx["usuario_atual"] = self.request.GET.get("usuario", "")
        ctx["modelo_atual"] = self.request.GET.get("modelo", "")
        ctx["acao_atual"] = self.request.GET.get("acao", "")
        ctx["desde"] = self.request.GET.get("desde", "")
        ctx["ate"] = self.request.GET.get("ate", "")
        # Modelos disponíveis para filtro: só os que têm logs registrados.
        ctx["modelos"] = ContentType.objects.filter(
            pk__in=LogEntry.objects.values_list("content_type_id", flat=True).distinct()
        ).order_by("model")
        ctx["acoes"] = [
            (LogEntry.Action.CREATE, "Criou"),
            (LogEntry.Action.UPDATE, "Alterou"),
            (LogEntry.Action.DELETE, "Excluiu"),
            (LogEntry.Action.ACCESS, "Acessou"),
        ]
        return ctx


# --- Busca global do topbar ---


@login_required
def buscar_global_json(request):
    """Endpoint de busca global usado pelo input do topbar.

    Pesquisa em três categorias respeitando permissões e visibilidade:
    - Pessoa (nome, sobrenome, nome_social) — exige `pessoas.view_pessoa`.
    - Entidade (nome, nome_fantasia, cnpj) — exige `pessoas.view_entidade`.
    - Demanda (numero, titulo, descricao) — exige `demandas.view_demanda`,
      e respeita `Demanda.objects.visiveis_para(user)` (ADR 0059 — só
      mostra as demandas que o usuário pode ver).

    Resposta:
        {"resultados": [
            {"categoria": "Pessoa", "label": "...", "sublabel": "...", "url": "..."},
            ...
        ]}

    Limite de 5 por categoria, ordenado pela categoria mais provável de uso
    (Demanda primeiro porque o number lookup `D-AAMM-NNNNN` — ADR 0056 — é o
    caso mais comum de busca direta).
    """
    q = request.GET.get("q", "").strip()
    resultados = []

    if not q or len(q) < 2:
        return JsonResponse({"resultados": []})

    # 1. Demandas — número primeiro (caso mais comum: D-2605-72918, ADR 0056)
    if request.user.has_perm("demandas.view_demanda"):
        from demandas.models import Demanda

        demandas_qs = (
            Demanda.objects.visiveis_para(request.user)
            .filter(Q(numero__icontains=q) | Q(titulo__icontains=q) | Q(descricao__icontains=q))
            .select_related("responsavel")
            .order_by("-criado_em")[:5]
        )
        for d in demandas_qs:
            sublabel_parts = [d.get_status_display()]
            if d.responsavel:
                sublabel_parts.append(d.responsavel.nome_completo or d.responsavel.email)
            resultados.append(
                {
                    "categoria": "Demanda",
                    "label": f"{d.numero} — {d.titulo}",
                    "sublabel": " · ".join(sublabel_parts),
                    "url": reverse("demandas:demanda_detalhe", args=[d.slug_publico]),
                }
            )

    # 2. Pessoas
    if request.user.has_perm("pessoas.view_pessoa"):
        from pessoas.models import Pessoa

        pessoas_qs = (
            Pessoa.objects.filter(ativo=True)
            .filter(Q(nome__icontains=q) | Q(sobrenome__icontains=q) | Q(nome_social__icontains=q))
            .order_by("nome", "sobrenome")[:5]
        )
        for p in pessoas_qs:
            sublabel = " · ".join(filter(None, [p.bairro, p.cidade])) or "Pessoa"
            resultados.append(
                {
                    "categoria": "Pessoa",
                    "label": p.nome_exibicao,
                    "sublabel": sublabel,
                    "url": reverse("pessoas:pessoa_detalhe", args=[p.slug_publico]),
                }
            )

    # 3. Entidades
    if request.user.has_perm("pessoas.view_entidade"):
        from pessoas.models import Entidade

        entidades_qs = (
            Entidade.objects.filter(ativo=True)
            .filter(Q(nome__icontains=q) | Q(nome_fantasia__icontains=q) | Q(cnpj__icontains=q))
            .order_by("nome")[:5]
        )
        for e in entidades_qs:
            resultados.append(
                {
                    "categoria": "Entidade",
                    "label": e.nome,
                    "sublabel": e.get_tipo_display(),
                    "url": reverse("pessoas:entidade_detalhe", args=[e.slug_publico]),
                }
            )

    return JsonResponse({"resultados": resultados, "termo": q})
