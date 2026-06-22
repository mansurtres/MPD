"""Views de Inbox GTD e Pendências: captura, lista, processar, descartar,
pendências pessoais e reuniões."""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import ListView, View

from ..forms import (
    DemandaEntidadeFormSet,
    DemandaForm,
    DemandaPessoaFormSet,
    DescartarInboxForm,
    InboxItemForm,
)
from ..models import Demanda, Interacao, ItemInbox


class CapturarInboxView(LoginRequiredMixin, View):
    """Captura rápida — qualquer usuário logado pode capturar.
    GET renderiza a página standalone (/inbox/capturar/). POST cria
    o ItemInbox. Se a request veio via fetch/HTMX (header HX-Request
    ou param ?ajax=1), responde JSON 201; senão redireciona."""

    def get(self, request):
        return render(
            request,
            "demandas/inbox/capturar.html",
            {"form": InboxItemForm()},
        )

    def post(self, request):
        form = InboxItemForm(request.POST)
        eh_ajax = request.headers.get("HX-Request") or request.GET.get("ajax") == "1"
        if not form.is_valid():
            if eh_ajax:
                return JsonResponse({"errors": form.errors}, status=400)
            return render(request, "demandas/inbox/capturar.html", {"form": form}, status=400)
        item = form.save(commit=False)
        item.autor = request.user
        item.save()
        if eh_ajax:
            # Retorna o novo total de pendentes para o JS atualizar o badge
            # da topbar sem precisar recarregar a página.
            inbox_pendentes = ItemInbox.objects.filter(status=ItemInbox.STATUS_PENDENTE).count()
            return JsonResponse(
                {"ok": True, "id": str(item.pk), "inbox_pendentes": inbox_pendentes},
                status=201,
            )
        messages.success(request, "Capturado no inbox.")
        return redirect("demandas:inbox_lista")


class InboxListView(LoginRequiredMixin, ListView):
    """Lista do inbox — pendentes por default; outros via querystring."""

    model = ItemInbox
    template_name = "demandas/inbox/lista.html"
    context_object_name = "itens"
    paginate_by = 30

    def get_queryset(self):
        qs = ItemInbox.objects.select_related("autor", "demanda_gerada", "processado_por").order_by(
            "-criado_em"
        )
        status = self.request.GET.get("status", "pendente")
        if status == "todos":
            pass
        elif status in dict(ItemInbox.STATUS_CHOICES):
            qs = qs.filter(status=status)
        else:
            qs = qs.filter(status=ItemInbox.STATUS_PENDENTE)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_atual"] = self.request.GET.get("status", "pendente")
        ctx["status_choices"] = ItemInbox.STATUS_CHOICES
        hoje = timezone.now().date()
        ctx["hoje"] = hoje
        ctx["limite_7d"] = hoje - timedelta(days=7)
        ctx["limite_30d"] = hoje - timedelta(days=30)
        # Counts por status — exibidos no header e nos chips de filtro.
        # Sempre calculados sobre o universo total (não respeitam o filtro
        # corrente; queremos saber quanto tem em cada balde).
        counts = dict(
            ItemInbox.objects.values_list("status")
            .annotate(n=Count("status"))
            .values_list("status", "n")
        )
        ctx["count_pendentes"] = counts.get(ItemInbox.STATUS_PENDENTE, 0)
        ctx["count_processados"] = counts.get(ItemInbox.STATUS_PROCESSADO, 0)
        ctx["count_descartados"] = counts.get(ItemInbox.STATUS_DESCARTADO, 0)
        ctx["count_total"] = sum(counts.values())
        return ctx


class ProcessarInboxView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Triagem: GET renderiza form de Demanda pré-preenchido com o
    conteúdo do item; POST cria a Demanda em transação atômica e marca
    o ItemInbox como processado apontando para ela."""

    permission_required = "demandas.add_demanda"

    def _redirecionar_se_ja_processado(self, request, item):
        """Se outro usuário já processou (ou descartou) o item, sai com
        mensagem e redireciona — em vez de devolver 404 vazio (Tarefa 2.5)."""
        if item.status == ItemInbox.STATUS_PENDENTE:
            return None
        if item.processado_por:
            nome = item.processado_por.nome_completo or item.processado_por.email
        else:
            nome = "outro usuário"
        messages.info(request, f"Este item já foi processado por {nome}.")
        if item.demanda_gerada_id:
            slug = Demanda.objects.values_list("slug_publico", flat=True).get(
                pk=item.demanda_gerada_id
            )
            return redirect("demandas:demanda_detalhe", slug=slug)
        return redirect("demandas:inbox_lista")

    def get(self, request, pk):
        item = get_object_or_404(ItemInbox, pk=pk)
        redirecionar = self._redirecionar_se_ja_processado(request, item)
        if redirecionar:
            return redirecionar
        # Pré-preenchimento: conteúdo do item vira descrição inicial;
        # título é os primeiros 80 chars (usuário ajusta).
        inicial = {"descricao": item.conteudo, "titulo": item.conteudo[:80]}
        form = DemandaForm(initial=inicial)
        return render(
            request,
            "demandas/form.html",
            {
                "item_inbox": item,
                "form": form,
                "formsets": {
                    "pessoas": DemandaPessoaFormSet(prefix="dp"),
                    "entidades": DemandaEntidadeFormSet(prefix="de"),
                },
            },
        )

    def post(self, request, pk):
        item = get_object_or_404(ItemInbox, pk=pk)
        redirecionar = self._redirecionar_se_ja_processado(request, item)
        if redirecionar:
            return redirecionar
        form = DemandaForm(request.POST)
        formsets = {
            "pessoas": DemandaPessoaFormSet(request.POST, prefix="dp"),
            "entidades": DemandaEntidadeFormSet(request.POST, prefix="de"),
        }
        if not (form.is_valid() and all(fs.is_valid() for fs in formsets.values())):
            return render(
                request,
                "demandas/form.html",
                {"item_inbox": item, "form": form, "formsets": formsets},
                status=400,
            )
        try:
            with transaction.atomic():
                demanda = form.save(commit=False)
                demanda.criado_por = request.user
                if not demanda.coordenacao_responsavel and getattr(
                    request.user, "coordenacao", None
                ):
                    demanda.coordenacao_responsavel = request.user.coordenacao
                demanda.save()
                form.save_m2m()
                for fs in formsets.values():
                    fs.instance = demanda
                    fs.save()
                if not demanda.anonimo and not demanda.tem_partes():
                    form.add_error(
                        None,
                        "Demanda não-anônima exige ao menos uma parte (pessoa ou entidade).",
                    )
                    transaction.set_rollback(True)
                    return render(
                        request,
                        "demandas/form.html",
                        {"item_inbox": item, "form": form, "formsets": formsets},
                        status=400,
                    )
                item.status = ItemInbox.STATUS_PROCESSADO
                item.demanda_gerada = demanda
                item.processado_em = timezone.now()
                item.processado_por = request.user
                item.full_clean()
                item.save()
        except ValidationError as e:
            for erro in e.messages:
                messages.error(request, erro)
            return redirect("demandas:inbox_processar", pk=item.pk)
        messages.success(request, f"Demanda {demanda.numero} criada a partir do inbox.")
        return redirect("demandas:demanda_detalhe", slug=demanda.slug_publico)


class DescartarInboxView(LoginRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(ItemInbox, pk=pk, status=ItemInbox.STATUS_PENDENTE)
        form = DescartarInboxForm(request.POST, instance=item)
        if not form.is_valid():
            messages.error(request, "Motivo do descarte é obrigatório.")
            return redirect("demandas:inbox_lista")
        item = form.save(commit=False)
        item.status = ItemInbox.STATUS_DESCARTADO
        item.processado_em = timezone.now()
        item.processado_por = request.user
        try:
            item.full_clean()
        except ValidationError as e:
            for erro in e.messages:
                messages.error(request, erro)
            return redirect("demandas:inbox_lista")
        item.save()
        messages.success(request, "Item descartado.")
        return redirect("demandas:inbox_lista")


class MinhasPendenciasView(LoginRequiredMixin, ListView):
    """Interações agendadas do usuário, agrupadas por horizonte temporal.
    Vencidas no topo."""

    template_name = "demandas/pendencias/lista.html"
    context_object_name = "pendencias"

    def get_queryset(self):
        return (
            Interacao.objects.filter(
                autor=self.request.user,
                status=Interacao.STATUS_AGENDADA,
            )
            .select_related("demanda")
            .order_by("data_ocorrencia")
        )

    def _bucket(self, dt, hoje):
        """Retorna (ordem, label) para agrupar a interacao por horizonte."""
        d = dt.date() if hasattr(dt, "date") else dt
        if dt < timezone.now():
            return (0, "Vencidas")
        if d == hoje:
            return (1, "Hoje")
        if d == hoje + timedelta(days=1):
            return (2, "Amanhã")
        if d <= hoje + timedelta(days=7):
            return (3, "Esta semana")
        return (4, "Próximas")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        hoje = timezone.now().date()
        agora = timezone.now()
        grupos = {}
        for p in ctx["pendencias"]:
            ordem, label = self._bucket(p.data_ocorrencia, hoje)
            grupos.setdefault((ordem, label), []).append(p)
        ctx["grupos"] = [
            {"label": label, "itens": itens}
            for (ordem, label), itens in sorted(grupos.items(), key=lambda kv: kv[0][0])
        ]
        ctx["agora"] = agora
        ctx["total_pendencias"] = len(ctx["pendencias"])
        ctx["total_vencidas"] = len(grupos.get((0, "Vencidas"), []))
        return ctx


class MinhasReunioesView(MinhasPendenciasView):
    """Filtra pendências por tipo=reuniao nos próximos 30 dias."""

    template_name = "demandas/pendencias/reunioes.html"

    def get_queryset(self):
        limite = timezone.now() + timedelta(days=30)
        return (
            Interacao.objects.filter(
                autor=self.request.user,
                status=Interacao.STATUS_AGENDADA,
                tipo=Interacao.TIPO_REUNIAO,
                data_ocorrencia__lte=limite,
            )
            .select_related("demanda")
            .order_by("data_ocorrencia")
        )
