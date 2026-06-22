"""Views de Demanda: CRUD + ações de estado (Concluir, Arquivar, Reabrir)."""

from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from core.utils import flash_form_errors

from ..forms import (
    AnexoForm,
    ArquivarForm,
    ConcluirAcaoForm,
    ConcluirDemandaForm,
    EncaminhamentoForm,
    FollowupForm,
    InteracaoForm,
)
from ..models import Anexo, Demanda, Encaminhamento, Interacao, Tema
from ._shared import _DemandaFormMixin, _pode_exportar


class DemandaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "demandas.view_demanda"
    model = Demanda
    template_name = "demandas/lista.html"
    context_object_name = "demandas"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            Demanda.objects.all()
            .select_related("responsavel", "criado_por")
            .prefetch_related("temas", "demanda_pessoas__pessoa", "demanda_entidades__entidade")
        )
        qs = qs.visiveis_para(self.request.user)

        params = self.request.GET
        busca = (params.get("q") or "").strip()
        if busca:
            qs = qs.filter(
                Q(numero__icontains=busca)
                | Q(titulo__icontains=busca)
                | Q(descricao__icontains=busca)
            )
        status = params.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        resultado = params.get("resultado", "").strip()
        if resultado:
            qs = qs.filter(resultado=resultado)
        tema_id = params.get("tema", "").strip()
        if tema_id:
            qs = qs.filter(temas__id=tema_id)

        quick = params.get("filtro", "").strip()
        if quick == "minhas":
            qs = qs.filter(responsavel=self.request.user)
        elif quick == "vencidas":
            qs = qs.filter(prazo__lt=timezone.now().date()).exclude(
                status__in=[Demanda.STATUS_CONCLUIDA, Demanda.STATUS_ARQUIVADO]
            )
        elif quick == "sem_retorno_30d":
            # Demanda responsiva aberta há +30d sem Interação de devolutiva.
            limite = timezone.now() - timedelta(days=30)
            qs = (
                qs.filter(origem=Demanda.ORIGEM_RESPONSIVA, criado_em__lte=limite)
                .exclude(
                    interacoes__tipo=Interacao.TIPO_DEVOLUTIVA,
                    interacoes__status=Interacao.STATUS_REALIZADA,
                )
                .exclude(status__in=[Demanda.STATUS_CONCLUIDA, Demanda.STATUS_ARQUIVADO])
            )
        elif quick == "atendidas":
            qs = qs.filter(
                resultado__in=[
                    Demanda.RESULTADO_ATENDIDO,
                    Demanda.RESULTADO_ATENDIDO_PARCIALMENTE,
                ]
            )
        elif quick == "nao_atendidas":
            qs = qs.filter(resultado=Demanda.RESULTADO_NAO_ATENDIDO)
        elif quick == "sem_resultado":
            qs = qs.filter(resultado=Demanda.RESULTADO_PENDENTE)
        elif quick == "com_encaminhamento_aberto":
            qs = qs.filter(
                encaminhamentos__status__in=[
                    Encaminhamento.STATUS_ENVIADO,
                    Encaminhamento.STATUS_PRAZO_VENCIDO,
                ]
            ).distinct()
        elif quick == "sem_encaminhamento":
            qs = qs.filter(encaminhamentos__isnull=True)

        return qs.distinct() if (busca or tema_id) else qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["filtro"] = self.request.GET.get("filtro", "")
        ctx["status_atual"] = self.request.GET.get("status", "")
        ctx["resultado_atual"] = self.request.GET.get("resultado", "")
        ctx["tema_atual"] = self.request.GET.get("tema", "")
        ctx["status_choices"] = Demanda.STATUS_CHOICES
        ctx["resultado_choices"] = Demanda.RESULTADO_CHOICES
        ctx["temas_disponiveis"] = Tema.objects.filter(ativo=True)
        ctx["pode_exportar"] = _pode_exportar(self.request.user)
        ctx["hoje"] = timezone.now().date()
        return ctx


class DemandaDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "demandas.view_demanda"
    model = Demanda
    template_name = "demandas/detalhe.html"
    context_object_name = "demanda"
    slug_field = "slug_publico"
    slug_url_kwarg = "slug"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.pode_ser_visto_por(self.request.user):
            raise Http404("Demanda restrita.")
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        d = self.object
        u = self.request.user
        ctx["interacoes"] = (
            d.interacoes.select_related("autor", "encaminhamento", "interacao_origem")
            .prefetch_related("encaminhamento__anexos__enviado_por", "follow_ups")
            .order_by("data_ocorrencia", "criado_em")
        )
        ctx["partes_pessoas"] = d.demanda_pessoas.select_related("pessoa")
        ctx["partes_entidades"] = d.demanda_entidades.select_related("entidade")
        # Histórico do Assessor (ADR 0059): nas suas demandas já concluídas/
        # arquivadas, as partes aparecem só com o nome — sem link para a ficha
        # nem dados de contato. Admin/CG veem o contexto completo.
        from core.permissoes import eh_admin, eh_cg_plus

        ctx["mascarar_partes"] = (
            not eh_admin(u) and not eh_cg_plus(u) and d.status not in Demanda.STATUS_ATIVOS
        )
        ctx["encaminhamentos"] = d.encaminhamentos.select_related("criado_por").prefetch_related(
            "anexos__enviado_por"
        )
        ct = ContentType.objects.get_for_model(Demanda)
        ctx["anexos"] = Anexo.objects.filter(content_type=ct, object_id=d.pk).select_related(
            "enviado_por"
        )
        ctx["pode_editar"] = u.has_perm("demandas.change_demanda")
        ctx["pode_arquivar"] = u.has_perm("demandas.pode_arquivar_demanda")
        ctx["pode_arquivar_sem_responder"] = u.has_perm("demandas.pode_arquivar_sem_responder")
        ctx["pode_reabrir"] = u.has_perm("demandas.pode_reabrir_demanda")
        ctx["pode_atribuir"] = u.has_perm("demandas.pode_atribuir_responsavel")
        ctx["form_interacao"] = InteracaoForm()
        ctx["form_followup"] = FollowupForm(prefix="fu")
        ctx["form_encaminhamento"] = EncaminhamentoForm()
        ctx["form_anexo"] = AnexoForm()
        ctx["form_arquivar"] = ArquivarForm(instance=d)
        # Bifurcação por origem (ADR 0043): responsiva pede devolutiva + resultado;
        # proativa pede só resultado.
        if d.origem == Demanda.ORIGEM_RESPONSIVA:
            ctx["form_concluir"] = ConcluirDemandaForm()
        else:
            ctx["form_concluir"] = ConcluirAcaoForm(instance=d)
        ctx["pode_concluir"] = ctx["pode_editar"] and d.status not in (
            Demanda.STATUS_CONCLUIDA,
            Demanda.STATUS_ARQUIVADO,
        )
        return ctx


class DemandaCreateView(LoginRequiredMixin, PermissionRequiredMixin, _DemandaFormMixin, CreateView):
    permission_required = "demandas.add_demanda"
    model = Demanda

    def _salvar(self, form, formsets):
        form.instance.criado_por = self.request.user
        super()._salvar(form, formsets)
        self._processar_anexos_iniciais(form)

    def _processar_anexos_iniciais(self, form):
        """Anexos opcionais enviados no momento da criação. Valida tamanho/mime
        de cada um antes de salvar; se algum falhar, adiciona erro ao form e
        levanta ValidationError pra abortar a transação."""
        arquivos = self.request.FILES.getlist("arquivos")
        if not arquivos:
            return
        erros = []
        for arquivo in arquivos:
            if arquivo.size > Anexo.TAMANHO_MAXIMO_BYTES:
                erros.append(
                    f"'{arquivo.name}': excede o limite de "
                    f"{Anexo.TAMANHO_MAXIMO_BYTES // (1024 * 1024)} MB."
                )
                continue
            # ADR 0056: whitelist removida. Defesa anti-XSS na entrega
            # (AnexoDownloadView força attachment + nosniff).
        if erros:
            for msg in erros:
                form.add_error(None, msg)
            raise ValidationError(erros)
        ct = ContentType.objects.get_for_model(Demanda)
        for arquivo in arquivos:
            Anexo.objects.create(
                content_type=ct,
                object_id=self.object.pk,
                arquivo=arquivo,
                nome_original=arquivo.name,
                tamanho_bytes=arquivo.size,
                mime_type=getattr(arquivo, "content_type", "") or "application/octet-stream",
                enviado_por=self.request.user,
            )

    def _sucesso(self):
        messages.success(self.request, f"Demanda {self.object.numero} cadastrada.")
        return super()._sucesso()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Nova demanda"
        return ctx


class DemandaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, _DemandaFormMixin, UpdateView):
    permission_required = "demandas.change_demanda"
    model = Demanda
    slug_field = "slug_publico"
    slug_url_kwarg = "slug"

    def _sucesso(self):
        messages.success(self.request, "Demanda atualizada.")
        return super()._sucesso()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object.numero}"
        return ctx


class ConcluirDemandaView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Conclui demanda. Bifurca por origem (ADR 0043):
    - Responsiva: cria Interacao(tipo=devolutiva) + classifica resultado + status=concluida.
    - Proativa: só classifica resultado + status=concluida.
    Tudo em transação atômica."""

    permission_required = "demandas.change_demanda"

    def post(self, request, pk):
        demanda = get_object_or_404(Demanda, pk=pk)
        if not demanda.pode_ser_visto_por(request.user):
            raise Http404
        if demanda.status in (Demanda.STATUS_CONCLUIDA, Demanda.STATUS_ARQUIVADO):
            messages.error(request, "Demanda já está fechada.")
            return redirect("demandas:demanda_detalhe", slug=demanda.slug_publico)

        if demanda.origem == Demanda.ORIGEM_RESPONSIVA:
            form = ConcluirDemandaForm(request.POST)
        else:
            form = ConcluirAcaoForm(request.POST, instance=demanda)

        if not form.is_valid():
            flash_form_errors(request, form)
            return redirect("demandas:demanda_detalhe", slug=demanda.slug_publico)

        try:
            with transaction.atomic():
                if demanda.origem == Demanda.ORIGEM_RESPONSIVA:
                    canal_key = form.cleaned_data["devolutiva_canal"]
                    canal_label = dict(Demanda.CANAL_CHOICES).get(canal_key, canal_key)
                    data_dev = form.cleaned_data["devolutiva_data"]
                    # Posição na timeline: se devolutiva é hoje, usa o instante
                    # atual (vai para o fim da timeline). Se é dia anterior,
                    # ancora no fim daquele dia (23:59) para ficar após eventos
                    # do mesmo dia mas antes dos posteriores.
                    hoje = timezone.now().date()
                    if data_dev == hoje:
                        data_ocorr = timezone.now()
                    else:
                        data_ocorr = timezone.make_aware(datetime.combine(data_dev, time(23, 59)))
                    Interacao.objects.create(
                        demanda=demanda,
                        autor=request.user,
                        tipo=Interacao.TIPO_DEVOLUTIVA,
                        conteudo=f"Canal: {canal_label}\n\n{form.cleaned_data['devolutiva_conteudo']}",
                        status=Interacao.STATUS_REALIZADA,
                        data_ocorrencia=data_ocorr,
                        automatica=False,
                    )
                    demanda.resultado = form.cleaned_data["resultado"]
                    demanda.resultado_observacao = form.cleaned_data["resultado_observacao"]
                else:
                    demanda = form.save(commit=False)
                demanda.status = Demanda.STATUS_CONCLUIDA
                demanda.full_clean()
                demanda.save()
        except ValidationError as e:
            for erro in e.messages:
                messages.error(request, erro)
            return redirect("demandas:demanda_detalhe", slug=demanda.slug_publico)
        messages.success(request, f"Demanda {demanda.numero} concluída.")
        return redirect("demandas:demanda_detalhe", slug=demanda.slug_publico)


class ArquivarView(LoginRequiredMixin, View):
    """Arquiva demanda. CO/CG/ADM podem; AS não.

    Vinda de concluida: sem justificativa exigida.
    Vinda de qualquer outro status: exige observacoes_arquivamento E permissão
    pode_arquivar_sem_responder (CG/ADM).
    """

    def post(self, request, pk):
        demanda = get_object_or_404(Demanda, pk=pk)
        if not demanda.pode_ser_visto_por(request.user):
            raise Http404
        if not request.user.has_perm("demandas.pode_arquivar_demanda"):
            raise PermissionDenied("Sem permissão para arquivar demanda.")
        if demanda._original_status != Demanda.STATUS_CONCLUIDA and not request.user.has_perm(
            "demandas.pode_arquivar_sem_responder"
        ):
            raise PermissionDenied("Apenas CG/ADM podem arquivar demanda não concluída.")

        form = ArquivarForm(request.POST, instance=demanda)
        if not form.is_valid():
            flash_form_errors(request, form)
            return redirect("demandas:demanda_detalhe", slug=demanda.slug_publico)
        demanda = form.save(commit=False)
        demanda.status = Demanda.STATUS_ARQUIVADO
        try:
            demanda.full_clean()
        except ValidationError as e:
            for erro in e.messages:
                messages.error(request, erro)
            return redirect("demandas:demanda_detalhe", slug=demanda.slug_publico)
        demanda.save()
        messages.success(request, "Demanda arquivada.")
        return redirect("demandas:demanda_detalhe", slug=demanda.slug_publico)


class ReabrirView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "demandas.pode_reabrir_demanda"

    def post(self, request, pk):
        demanda = get_object_or_404(Demanda, pk=pk)
        if demanda.status != Demanda.STATUS_CONCLUIDA:
            messages.error(request, "Apenas demandas concluídas podem ser reabertas.")
            return redirect("demandas:demanda_detalhe", slug=demanda.slug_publico)
        demanda.status = Demanda.STATUS_EM_ANDAMENTO
        demanda.save()
        messages.success(request, "Demanda reaberta.")
        return redirect("demandas:demanda_detalhe", slug=demanda.slug_publico)
