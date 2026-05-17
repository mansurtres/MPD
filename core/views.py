from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import ListView


def inicio(request):
    if request.user.is_authenticated:
        return render(request, "core/inicio_autenticado.html")
    return render(request, "core/inicio.html")


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
    """Painel de análise. CO+. Métricas textuais + gráficas (Chart.js
    via CDN — toggle por métrica). Não usa ListView de fato; reusa só o
    template/auth — context_data carrega as métricas."""

    template_name = "core/analise.html"

    def test_func(self):
        u = self.request.user
        return (
            u.is_superuser
            or u.groups.filter(
                name__in=["Administrador", "Chefe de Gabinete", "Coordenador"]
            ).exists()
        )

    def get_queryset(self):
        # Override exigido pelo ListView, mas não usado.
        from demandas.models import Demanda

        return Demanda.objects.none()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from datetime import timedelta

        from django.db.models import Count
        from django.db.models.functions import TruncMonth
        from django.utils import timezone as tz

        from demandas.models import Demanda, Encaminhamento

        # 1. Demandas por tema
        ctx["por_tema"] = list(
            Demanda.objects.values("temas__nome", "temas__cor")
            .annotate(total=Count("id"))
            .exclude(temas__nome__isnull=True)
            .order_by("-total")[:12]
        )

        # 2. Demandas por mês (últimos 12 meses)
        limite_mes = tz.now() - timedelta(days=365)
        ctx["por_mes"] = list(
            Demanda.objects.filter(criado_em__gte=limite_mes)
            .annotate(mes=TruncMonth("criado_em"))
            .values("mes")
            .annotate(total=Count("id"))
            .order_by("mes")
        )

        # 3. Demandas por coordenação
        ctx["por_coordenacao"] = list(
            Demanda.objects.values("coordenacao_responsavel")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        coord_display = dict(Demanda.COORDENACAO_CHOICES)
        for item in ctx["por_coordenacao"]:
            item["display"] = coord_display.get(
                item["coordenacao_responsavel"], item["coordenacao_responsavel"]
            )

        # 4. Top 20 pessoas com mais demandas (sem anônimas)
        from pessoas.models import Pessoa

        ctx["top_pessoas"] = list(
            Pessoa.objects.annotate(total=Count("demanda_pessoas"))
            .filter(total__gt=0)
            .order_by("-total")[:20]
            .values("nome", "sobrenome", "slug_publico", "total")
        )

        # 5. Encaminhamentos pendentes por órgão
        ctx["enc_por_orgao"] = list(
            Encaminhamento.objects.filter(
                status__in=[Encaminhamento.STATUS_ENVIADO, Encaminhamento.STATUS_PRAZO_VENCIDO]
            )
            .values("destinatario_orgao")
            .annotate(total=Count("id"))
            .order_by("-total")[:15]
        )

        # 6. Carga por assessor (responsável com demandas abertas/vencidas)
        from accounts.models import Usuario

        assessores = []
        for u in Usuario.objects.filter(is_active=True):
            abertas = Demanda.objects.filter(
                responsavel=u,
                status__in=[
                    Demanda.STATUS_NOVO,
                    Demanda.STATUS_EM_ANDAMENTO,
                    Demanda.STATUS_AGUARDANDO_TERCEIROS,
                    Demanda.STATUS_AGUARDANDO_PESSOA,
                ],
            ).count()
            vencidas = (
                Demanda.objects.filter(
                    responsavel=u,
                    prazo__lt=tz.now().date(),
                )
                .exclude(status__in=[Demanda.STATUS_CONCLUIDA, Demanda.STATUS_ARQUIVADO])
                .count()
            )
            if abertas > 0 or vencidas > 0:
                assessores.append(
                    {
                        "nome": u.nome_completo or u.email,
                        "abertas": abertas,
                        "vencidas": vencidas,
                    }
                )
        ctx["carga_assessores"] = sorted(assessores, key=lambda x: -x["abertas"])

        return ctx


class AuditoriaListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Lista entradas do auditlog cronologicamente. Restrito a Chefe de
    Gabinete + Administrador (CG+). Diff visual antes/depois renderizado
    a partir do JSON do auditlog."""

    template_name = "core/auditoria.html"
    context_object_name = "logs"
    paginate_by = 50

    def test_func(self):
        u = self.request.user
        return (
            u.is_superuser
            or u.groups.filter(name__in=["Administrador", "Chefe de Gabinete"]).exists()
        )

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
