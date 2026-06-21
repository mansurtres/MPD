"""Views do app demandas — Fase 3.

Padrões herdados de pessoas/views.py:
- LoginRequiredMixin + PermissionRequiredMixin em CBVs.
- transaction.atomic + cross-objeto rule (ver _DemandaFormMixin).
- aplicar_tailwind via core/forms.py.
- pode_alternar_* calculado em get_context_data.
"""

from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View

from core.permissoes import eh_cg_plus, eh_co_plus
from core.utils import flash_form_errors

from .forms import (
    AnexoForm,
    ArquivarForm,
    ConcluirAcaoForm,
    ConcluirDemandaForm,
    DemandaEntidadeFormSet,
    DemandaForm,
    DemandaPessoaFormSet,
    DescartarInboxForm,
    EncaminhamentoForm,
    EncaminhamentoRespostaForm,
    FollowupForm,
    InboxItemForm,
    InteracaoForm,
    TemaForm,
)
from .models import Anexo, Demanda, Encaminhamento, Interacao, ItemInbox, Tema


def _pode_exportar(user):
    """Coordenador, Chefe de Gabinete, Administrador. Critério de Fase 6."""
    return eh_co_plus(user)


def _anexar_se_houver(request, objeto_pai):
    """Cria Anexo(s) vinculados a `objeto_pai` se o request trouxer arquivos
    no campo `anexo` (múltiplos suportados via <input multiple>). Usado pelas
    views de criar interação/encaminhamento para permitir upload na mesma
    transação. Silencioso: lista vazia é OK (campo opcional). Se algum
    arquivo exceder o limite, levanta ValueError — a transação inteira faz
    rollback (nenhum anexo é salvo, nem o objeto pai)."""
    arquivos = request.FILES.getlist("anexo")
    if not arquivos:
        return
    ct = ContentType.objects.get_for_model(type(objeto_pai))
    for arquivo in arquivos:
        if arquivo.size > Anexo.TAMANHO_MAXIMO_BYTES:
            messages.error(
                request,
                f"Arquivo '{arquivo.name}' excede o limite de "
                f"{Anexo.TAMANHO_MAXIMO_BYTES // (1024*1024)} MB.",
            )
            raise ValueError("anexo excede limite")
        Anexo.objects.create(
            content_type=ct,
            object_id=objeto_pai.pk,
            arquivo=arquivo,
            nome_original=arquivo.name,
            tamanho_bytes=arquivo.size,
            mime_type=getattr(arquivo, "content_type", "") or "application/octet-stream",
            enviado_por=request.user,
        )


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
        coord = params.get("coord", "").strip()
        if coord:
            qs = qs.filter(coordenacao_responsavel=coord)
        tema_id = params.get("tema", "").strip()
        if tema_id:
            qs = qs.filter(temas__id=tema_id)

        quick = params.get("filtro", "").strip()
        if quick == "minhas":
            qs = qs.filter(responsavel=self.request.user)
        elif quick == "minha_coord" and self.request.user.coordenacao:
            qs = qs.filter(coordenacao_responsavel=self.request.user.coordenacao)
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
        ctx["coord_atual"] = self.request.GET.get("coord", "")
        ctx["tema_atual"] = self.request.GET.get("tema", "")
        ctx["status_choices"] = Demanda.STATUS_CHOICES
        ctx["resultado_choices"] = Demanda.RESULTADO_CHOICES
        ctx["coord_choices"] = Demanda.COORDENACAO_CHOICES
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


class _DemandaFormMixin:
    """Coordena DemandaForm + dois formsets (pessoas, entidades) com a regra
    'demanda não-anônima exige ao menos uma parte'."""

    template_name = "demandas/form.html"
    form_class = DemandaForm

    def _build_formsets(self, post_data=None):
        instance = self.object if hasattr(self, "object") else None
        return {
            "pessoas": DemandaPessoaFormSet(post_data, instance=instance, prefix="dp"),
            "entidades": DemandaEntidadeFormSet(post_data, instance=instance, prefix="de"),
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if "formsets" not in ctx:
            ctx["formsets"] = self._build_formsets()
        return ctx

    def post(self, request, *args, **kwargs):
        eh_update = bool(self.kwargs.get("pk"))
        self.object = self.get_object() if eh_update else None
        for prefix in ("dp", "de"):
            if f"{prefix}-TOTAL_FORMS" not in request.POST:
                messages.warning(
                    request, "A página estava desatualizada. Recarregue e preencha novamente."
                )
                return redirect(request.path)
        form = self.get_form()
        formsets = self._build_formsets(request.POST)
        if not (form.is_valid() and all(fs.is_valid() for fs in formsets.values())):
            return self.form_invalid(form, formsets)

        try:
            with transaction.atomic():
                self._salvar(form, formsets)
                if not self.object.anonimo and not self.object.tem_partes():
                    form.add_error(
                        None,
                        "Demanda não-anônima exige ao menos uma parte (pessoa ou entidade).",
                    )
                    transaction.set_rollback(True)
                    return self.form_invalid(form, formsets)
        except ValidationError:
            # Erros já estão em form.errors (adicionados em _salvar). Atomic
            # fez rollback ao propagar a exceção; agora renderizamos o form
            # de volta com as mensagens.
            return self.form_invalid(form, formsets)

        return self._sucesso()

    def _salvar(self, form, formsets):
        self.object = form.save()
        for fs in formsets.values():
            fs.instance = self.object
            fs.save()

    def _sucesso(self):
        return redirect("demandas:demanda_detalhe", slug=self.object.slug_publico)

    def form_invalid(self, form, formsets):
        return self.render_to_response(self.get_context_data(form=form, formsets=formsets))


class DemandaCreateView(LoginRequiredMixin, PermissionRequiredMixin, _DemandaFormMixin, CreateView):
    permission_required = "demandas.add_demanda"
    model = Demanda

    def _salvar(self, form, formsets):
        form.instance.criado_por = self.request.user
        if not form.instance.coordenacao_responsavel and self.request.user.coordenacao:
            form.instance.coordenacao_responsavel = self.request.user.coordenacao
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


# --- Interações ---


class AdicionarInteracaoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "demandas.add_interacao"

    def post(self, request, pk):
        demanda = get_object_or_404(Demanda, pk=pk)
        if not demanda.pode_ser_visto_por(request.user):
            raise Http404
        form = InteracaoForm(request.POST)
        followup = FollowupForm(request.POST, prefix="fu")
        if not form.is_valid() or not followup.is_valid():
            flash_form_errors(request, form, followup)
            return redirect("demandas:demanda_detalhe", slug=demanda.slug_publico)
        try:
            with transaction.atomic():
                interacao = form.save(commit=False)
                interacao.demanda = demanda
                interacao.autor = request.user
                interacao.save()
                # Detecta intenção de follow-up pelo preenchimento (não mais por
                # checkbox separado, que era pegadinha de UX). Só cria a interação
                # agendada se a principal é realizada e se os campos essenciais
                # do follow-up estão preenchidos (data + conteúdo).
                fu_data = followup.cleaned_data.get("data_ocorrencia")
                fu_conteudo = (followup.cleaned_data.get("conteudo") or "").strip()
                quer_followup = (
                    bool(fu_data)
                    and bool(fu_conteudo)
                    and interacao.status == Interacao.STATUS_REALIZADA
                )
                if quer_followup:
                    Interacao.objects.create(
                        demanda=demanda,
                        autor=request.user,
                        tipo=followup.cleaned_data.get("tipo") or Interacao.TIPO_CONTATO_PESSOA,
                        conteudo=fu_conteudo,
                        status=Interacao.STATUS_AGENDADA,
                        data_ocorrencia=fu_data,
                        interacao_origem=interacao,
                    )
                _anexar_se_houver(request, interacao)
        except ValueError:
            return redirect("demandas:demanda_detalhe", slug=demanda.slug_publico)
        messages.success(request, "Interação registrada.")
        return redirect("demandas:demanda_detalhe", slug=demanda.slug_publico)


class InteracaoMarcarRealizadaView(LoginRequiredMixin, View):
    """Converte interação agendada em realizada — autor ou ADM/CG."""

    def post(self, request, pk):
        interacao = get_object_or_404(Interacao, pk=pk)
        if not interacao.demanda.pode_ser_visto_por(request.user):
            raise Http404
        if interacao.autor_id != request.user.id and not eh_cg_plus(request.user):
            raise PermissionDenied("Apenas o autor pode marcar como realizada.")
        if interacao.status != Interacao.STATUS_AGENDADA:
            messages.error(request, "Interação não está agendada.")
            return redirect("demandas:demanda_detalhe", slug=interacao.demanda.slug_publico)
        interacao.status = Interacao.STATUS_REALIZADA
        interacao.save()
        messages.success(request, "Interação marcada como realizada.")
        return redirect("demandas:demanda_detalhe", slug=interacao.demanda.slug_publico)


class InteracaoCancelarView(LoginRequiredMixin, View):
    """Cancela interação agendada própria ou de outros (com permissão)."""

    def post(self, request, pk):
        interacao = get_object_or_404(Interacao, pk=pk)
        if not interacao.demanda.pode_ser_visto_por(request.user):
            raise Http404
        eh_propria = interacao.autor_id == request.user.id
        if not eh_propria and not request.user.has_perm("demandas.pode_editar_interacao_alheia"):
            raise PermissionDenied("Sem permissão para cancelar interação alheia.")
        if interacao.status != Interacao.STATUS_AGENDADA:
            messages.error(request, "Apenas interações agendadas podem ser canceladas.")
            return redirect("demandas:demanda_detalhe", slug=interacao.demanda.slug_publico)
        interacao.status = Interacao.STATUS_CANCELADA
        interacao.save()
        messages.success(request, "Interação cancelada.")
        return redirect("demandas:demanda_detalhe", slug=interacao.demanda.slug_publico)


# --- Encaminhamentos ---


class AdicionarEncaminhamentoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "demandas.add_encaminhamento"

    def post(self, request, pk):
        demanda = get_object_or_404(Demanda, pk=pk)
        if not demanda.pode_ser_visto_por(request.user):
            raise Http404
        form = EncaminhamentoForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            return redirect("demandas:demanda_detalhe", slug=demanda.slug_publico)
        try:
            with transaction.atomic():
                enc = form.save(commit=False)
                enc.demanda = demanda
                enc.criado_por = request.user
                enc.save()
                Interacao.objects.create(
                    demanda=demanda,
                    autor=request.user,
                    tipo=Interacao.TIPO_ENCAMINHAMENTO,
                    conteudo=f"{enc.get_tipo_documento_display()} → {enc.destinatario_orgao}",
                    status=Interacao.STATUS_REALIZADA,
                    data_ocorrencia=timezone.now(),
                    automatica=False,
                    encaminhamento=enc,
                )
                _anexar_se_houver(request, enc)
        except ValueError:
            return redirect("demandas:demanda_detalhe", slug=demanda.slug_publico)
        messages.success(request, "Encaminhamento adicionado.")
        return redirect("demandas:demanda_detalhe", slug=demanda.slug_publico)


class EncaminhamentoRespostaView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "demandas.change_encaminhamento"

    def post(self, request, pk):
        enc = get_object_or_404(Encaminhamento, pk=pk)
        if not enc.demanda.pode_ser_visto_por(request.user):
            raise Http404
        form = EncaminhamentoRespostaForm(request.POST, instance=enc)
        if not form.is_valid():
            flash_form_errors(request, form)
            return redirect("demandas:demanda_detalhe", slug=enc.demanda.slug_publico)
        enc = form.save()
        Interacao.objects.create(
            demanda=enc.demanda,
            autor=request.user,
            tipo=Interacao.TIPO_RETORNO_EXTERNO,
            conteudo=(
                f"{enc.destinatario_orgao} respondeu — {enc.get_status_display()}.\n\n"
                f"{enc.conteudo_resposta}"
            ),
            status=Interacao.STATUS_REALIZADA,
            data_ocorrencia=timezone.now(),
            automatica=False,
            encaminhamento=enc,
        )
        messages.success(request, "Resposta registrada.")
        return redirect("demandas:demanda_detalhe", slug=enc.demanda.slug_publico)


# --- Visão transversal: lista de Encaminhamentos (ADR 0046) ---


class EncaminhamentoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lente de leitura agregada sobre Encaminhamentos. Cada linha é
    deep-link para a Demanda associada. Sem CRUD próprio — toda mutação
    acontece no detalhe da Demanda (princípio de ADR 0046)."""

    permission_required = "demandas.view_encaminhamento"
    model = Encaminhamento
    template_name = "demandas/encaminhamentos/lista.html"
    context_object_name = "encaminhamentos"
    paginate_by = 25

    def get_queryset(self):
        # Visibilidade segue a da Demanda associada (encaminhamento de
        # demanda restrita só aparece para quem pode ver a demanda).
        demandas_visiveis = Demanda.objects.visiveis_para(self.request.user)
        qs = (
            Encaminhamento.objects.filter(demanda__in=demandas_visiveis)
            .select_related("demanda", "criado_por")
            .order_by("-data_envio", "-criado_em")
        )
        params = self.request.GET
        status = params.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        orgao = params.get("orgao", "").strip()
        if orgao:
            qs = qs.filter(destinatario_orgao__icontains=orgao)
        tipo_doc = params.get("tipo", "").strip()
        if tipo_doc:
            qs = qs.filter(tipo_documento=tipo_doc)
        busca = (params.get("q") or "").strip()
        if busca:
            qs = qs.filter(
                Q(destinatario_orgao__icontains=busca)
                | Q(numero_documento__icontains=busca)
                | Q(demanda__numero__icontains=busca)
                | Q(demanda__titulo__icontains=busca)
            )

        quick = params.get("filtro", "").strip()
        hoje = timezone.now().date()
        if quick == "aguardando":
            qs = qs.filter(
                status__in=[Encaminhamento.STATUS_ENVIADO, Encaminhamento.STATUS_PRAZO_VENCIDO]
            )
        elif quick == "vencidos":
            # Inclui status='prazo_vencido' E status='enviado' com prazo no passado
            # (cobre cron que pode não estar rodando).
            qs = qs.filter(
                Q(status=Encaminhamento.STATUS_PRAZO_VENCIDO)
                | Q(status=Encaminhamento.STATUS_ENVIADO, prazo_resposta__lt=hoje)
            )
        elif quick == "respondidos_semana":
            limite = hoje - timedelta(days=7)
            qs = qs.filter(
                status__in=[
                    Encaminhamento.STATUS_RESPONDIDO_SAT,
                    Encaminhamento.STATUS_RESPONDIDO_INSAT,
                ],
                data_resposta__gte=limite,
            )

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["filtro"] = self.request.GET.get("filtro", "")
        ctx["status_atual"] = self.request.GET.get("status", "")
        ctx["orgao_atual"] = self.request.GET.get("orgao", "")
        ctx["tipo_atual"] = self.request.GET.get("tipo", "")
        ctx["status_choices"] = Encaminhamento.STATUS_CHOICES
        ctx["tipo_choices"] = Encaminhamento.TIPO_DOCUMENTO_CHOICES
        # Lista de órgãos distintos para o filtro de autocomplete simples.
        demandas_visiveis = Demanda.objects.visiveis_para(self.request.user)
        ctx["orgaos_distintos"] = (
            Encaminhamento.objects.filter(demanda__in=demandas_visiveis)
            .values_list("destinatario_orgao", flat=True)
            .distinct()
            .order_by("destinatario_orgao")
        )
        ctx["hoje"] = timezone.now().date()
        ctx["pode_exportar"] = _pode_exportar(self.request.user)
        return ctx


# --- Temas (categorização de Demanda) ---


class TemaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "demandas.view_tema"
    model = Tema
    template_name = "demandas/temas/lista.html"
    context_object_name = "temas"

    def get_queryset(self):
        return Tema.objects.all().order_by("-ativo", "nome")


class TemaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "demandas.add_tema"
    model = Tema
    form_class = TemaForm
    template_name = "demandas/temas/form.html"

    def get_success_url(self):
        return reverse("demandas:tema_lista")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo tema"
        ctx["cores_predefinidas"] = _CORES_TEMA
        return ctx


class TemaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "demandas.change_tema"
    model = Tema
    form_class = TemaForm
    template_name = "demandas/temas/form.html"

    def get_success_url(self):
        return reverse("demandas:tema_lista")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object.nome}"
        ctx["cores_predefinidas"] = _CORES_TEMA
        return ctx


class TemaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Hard delete de Tema. Bloqueia se houver demanda vinculada — auditlog
    não registra mudança em M:N quando o tema some, então perderia trilha
    histórica silenciosamente. Caminho seguro: arquivar."""

    permission_required = "demandas.delete_tema"
    model = Tema
    success_url = reverse_lazy("demandas:tema_lista")
    template_name = "demandas/temas/confirmar_remocao.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["em_uso"] = self.object.demandas.count()
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        em_uso = self.object.demandas.count()
        if em_uso:
            messages.error(
                request,
                f"'{self.object.nome}' está em {em_uso} demanda(s). Arquive em vez de remover — mantém a classificação histórica.",
            )
            return redirect("demandas:tema_editar", pk=self.object.pk)
        return super().post(request, *args, **kwargs)


class TemaCreateAjaxView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Cria Tema via AJAX (chamado do popup no form de Demanda). Permissão
    demandas.add_tema. Retorna JSON com id, nome, cor para o JS adicionar
    o checkbox dinâmico já marcado."""

    permission_required = "demandas.add_tema"

    def post(self, request):
        nome = (request.POST.get("nome") or "").strip()
        cor = (request.POST.get("cor") or "").strip()
        if not nome:
            return JsonResponse({"erro": "Nome é obrigatório."}, status=400)
        if Tema.objects.filter(nome__iexact=nome).exists():
            return JsonResponse({"erro": f"Já existe um tema com o nome '{nome}'."}, status=400)
        tema = Tema.objects.create(nome=nome, cor=cor)
        return JsonResponse({"id": tema.pk, "nome": tema.nome, "cor": tema.cor or ""}, status=201)


class TemaToggleArquivarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Arquiva/desarquiva tema. FK para Demanda preserva temas arquivados em
    demandas que já os tinham, mas não aparecem em novos formulários."""

    permission_required = "demandas.change_tema"

    def post(self, request, pk):
        tema = get_object_or_404(Tema, pk=pk)
        tema.ativo = not tema.ativo
        tema.save()
        messages.success(
            request, f"Tema '{tema.nome}' {'reativado' if tema.ativo else 'arquivado'}."
        )
        return redirect("demandas:tema_lista")


# Paleta de 11 cores fixas — mesma de pessoas.Tag para consistência visual.
_CORES_TEMA = [
    ("#d50000", "Tomate"),
    ("#e67c73", "Flamingo"),
    ("#f4511e", "Tangerina"),
    ("#f6bf26", "Banana"),
    ("#33b679", "Sálvia"),
    ("#0b8043", "Manjericão"),
    ("#039be5", "Pavão"),
    ("#3f51b5", "Mirtilo"),
    ("#7986cb", "Lavanda"),
    ("#8e24aa", "Uva"),
    ("#616161", "Grafite"),
]


# --- Anexos polimórficos ---


_TIPO_PARA_MODEL = {
    "demanda": ("demandas", "demanda"),
    "pessoa": ("pessoas", "pessoa"),
    "entidade": ("pessoas", "entidade"),
    "encaminhamento": ("demandas", "encaminhamento"),
    "interacao": ("demandas", "interacao"),
}


class AnexoUploadView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Upload polimórfico — recebe (tipo, object_id) e cria Anexo."""

    permission_required = "demandas.add_anexo"

    def get(self, request, tipo, object_id):
        # GET nessa URL não tem semântica útil — acontece quando o usuário
        # recarrega a aba após o POST. Em vez de devolver 405, manda de volta
        # pra página do objeto pai. Demanda e Encaminhamento são os casos
        # primários (UI atual); outros tipos caem no referer ou na raiz.
        if tipo == "demanda":
            slug = get_object_or_404(
                Demanda.objects.values_list("slug_publico", flat=True), pk=object_id
            )
            return redirect("demandas:demanda_detalhe", slug=slug)
        if tipo == "encaminhamento":
            enc = get_object_or_404(Encaminhamento, pk=object_id)
            return redirect("demandas:demanda_detalhe", slug=enc.demanda.slug_publico)
        if tipo == "interacao":
            interacao = get_object_or_404(Interacao, pk=object_id)
            return redirect("demandas:demanda_detalhe", slug=interacao.demanda.slug_publico)
        return redirect(request.META.get("HTTP_REFERER", "/"))

    def post(self, request, tipo, object_id):
        if tipo not in _TIPO_PARA_MODEL:
            raise Http404("Tipo de objeto pai inválido.")
        app_label, model_name = _TIPO_PARA_MODEL[tipo]
        try:
            ct = ContentType.objects.get(app_label=app_label, model=model_name)
        except ContentType.DoesNotExist as exc:
            raise Http404("Tipo desconhecido.") from exc
        objeto_pai = get_object_or_404(ct.model_class(), pk=object_id)
        if isinstance(objeto_pai, Demanda) and not objeto_pai.pode_ser_visto_por(request.user):
            raise Http404
        if isinstance(objeto_pai, Encaminhamento) and not objeto_pai.demanda.pode_ser_visto_por(
            request.user
        ):
            raise Http404
        form = AnexoForm(request.POST, request.FILES)
        if not form.is_valid():
            for erros in form.errors.values():
                messages.error(request, "; ".join(erros))
            return redirect(request.META.get("HTTP_REFERER", "/"))
        arquivo = form.cleaned_data["arquivo"]
        anexo = Anexo(
            content_type=ct,
            object_id=objeto_pai.pk,
            arquivo=arquivo,
            nome_original=arquivo.name,
            tamanho_bytes=arquivo.size,
            mime_type=getattr(arquivo, "content_type", "") or "application/octet-stream",
            descricao=form.cleaned_data.get("descricao", ""),
            enviado_por=request.user,
        )
        try:
            anexo.full_clean()
        except ValidationError as e:
            for erro in e.messages:
                messages.error(request, erro)
            return redirect(request.META.get("HTTP_REFERER", "/"))
        anexo.save()
        messages.success(request, f"Anexo '{anexo.nome_original}' adicionado.")
        return redirect(request.META.get("HTTP_REFERER", "/"))


class AnexoDownloadView(LoginRequiredMixin, View):
    """Serve o arquivo de um Anexo com defesas anti-XSS (ADR 0056).

    Defesas:
    - `Content-Disposition: attachment` — força o browser a BAIXAR em vez
      de tentar executar/exibir inline. Um .html malicioso vira download
      de arquivo, não código rodando na origem do MPD.
    - `X-Content-Type-Options: nosniff` — impede o browser de "adivinhar"
      um content-type executável diferente do declarado.
    - `Content-Security-Policy: default-src 'none'` — caso o browser
      ignore os outros headers, ainda bloqueia execução de scripts/iframes
      a partir do arquivo servido.

    Permissão: precisa poder ver o objeto pai (Demanda respeita
    visibilidade restrita; Encaminhamento herda da demanda; Pessoa/Entidade
    exigem `view_pessoa`/`view_entidade`).
    """

    def get(self, request, pk):
        anexo = get_object_or_404(Anexo, pk=pk)
        objeto_pai = anexo.objeto_pai
        if objeto_pai is None:
            raise Http404

        if isinstance(objeto_pai, Demanda):
            if not objeto_pai.pode_ser_visto_por(request.user):
                raise Http404
        elif isinstance(objeto_pai, Encaminhamento):
            if not objeto_pai.demanda.pode_ser_visto_por(request.user):
                raise Http404
        elif isinstance(objeto_pai, Interacao):
            if not objeto_pai.demanda.pode_ser_visto_por(request.user):
                raise Http404
        else:
            # Pessoa, Entidade — basta a permissão de view do app
            from pessoas.models import Entidade as _Ent
            from pessoas.models import Pessoa as _Pes

            if isinstance(objeto_pai, _Pes) and not request.user.has_perm("pessoas.view_pessoa"):
                raise PermissionDenied
            if isinstance(objeto_pai, _Ent) and not request.user.has_perm("pessoas.view_entidade"):
                raise PermissionDenied

        resp = FileResponse(
            anexo.arquivo.open("rb"),
            as_attachment=True,
            filename=anexo.nome_original,
        )
        # Headers de segurança (defesa em profundidade).
        resp["X-Content-Type-Options"] = "nosniff"
        resp["Content-Security-Policy"] = "default-src 'none'"
        return resp


class AnexoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "demandas.delete_anexo"

    def post(self, request, pk):
        anexo = get_object_or_404(Anexo, pk=pk)
        if anexo.enviado_por_id != request.user.id and not eh_co_plus(request.user):
            raise PermissionDenied("Sem permissão para excluir este anexo.")
        referer = request.META.get("HTTP_REFERER", "/")
        anexo.arquivo.delete(save=False)
        anexo.delete()
        messages.success(request, "Anexo removido.")
        return redirect(referer)


# --- Fase 5: Inbox GTD ---


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


# --- Fase 6: Exportação CSV ---


class DemandaCSVExportView(LoginRequiredMixin, View):
    """Exporta a lista de demandas filtrada pelo querystring para CSV BR
    (UTF-8 BOM + separador ;). Limite 10k. CO+. Registra log."""

    def get(self, request):
        if not _pode_exportar(request.user):
            raise PermissionDenied("Exportação restrita a Coordenadores e acima.")
        from core.csv_export import exportar_csv

        def row_fn(d):
            temas = ", ".join(t.nome for t in d.temas.all())
            return [
                d.numero,
                d.titulo,
                d.get_origem_display(),
                d.get_canal_entrada_display(),
                d.get_status_display(),
                d.get_resultado_display(),
                d.get_coordenacao_responsavel_display(),
                (d.responsavel.nome_completo or d.responsavel.email) if d.responsavel else "",
                "Sim" if d.restrito else "Não",
                "Sim" if d.anonimo else "Não",
                d.criado_em.strftime("%d/%m/%Y %H:%M"),
                d.prazo.strftime("%d/%m/%Y") if d.prazo else "",
                temas,
            ]

        return exportar_csv(
            request,
            list_view_cls=DemandaListView,
            modelo="Demanda",
            filename="demandas.csv",
            header=[
                "Número",
                "Título",
                "Origem",
                "Canal",
                "Status",
                "Resultado",
                "Coordenação",
                "Responsável",
                "Restrita",
                "Anônima",
                "Criada em",
                "Prazo",
                "Temas",
            ],
            row_fn=row_fn,
        )


class EncaminhamentoCSVExportView(LoginRequiredMixin, View):
    def get(self, request):
        if not _pode_exportar(request.user):
            raise PermissionDenied("Exportação restrita a Coordenadores e acima.")
        from core.csv_export import exportar_csv

        def row_fn(e):
            return [
                e.demanda.numero,
                e.demanda.titulo,
                e.destinatario_orgao,
                e.destinatario_pessoa or "",
                e.get_tipo_documento_display(),
                e.numero_documento or "",
                e.data_envio.strftime("%d/%m/%Y") if e.data_envio else "",
                e.prazo_resposta.strftime("%d/%m/%Y") if e.prazo_resposta else "",
                e.get_status_display(),
                e.data_resposta.strftime("%d/%m/%Y") if e.data_resposta else "",
            ]

        return exportar_csv(
            request,
            list_view_cls=EncaminhamentoListView,
            modelo="Encaminhamento",
            filename="encaminhamentos.csv",
            header=[
                "Demanda",
                "Título da demanda",
                "Órgão",
                "Pessoa contato",
                "Tipo documento",
                "Nº documento",
                "Data envio",
                "Prazo resposta",
                "Status",
                "Data resposta",
            ],
            row_fn=row_fn,
        )
