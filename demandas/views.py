"""Views do app demandas — Fase 3.

Padrões herdados de pessoas/views.py:
- LoginRequiredMixin + PermissionRequiredMixin em CBVs.
- transaction.atomic + cross-objeto rule (ver _DemandaFormMixin).
- aplicar_tailwind via core/forms.py.
- pode_alternar_* calculado em get_context_data.
"""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from .forms import (
    AnexoForm,
    ArquivarForm,
    DemandaEntidadeFormSet,
    DemandaForm,
    DemandaPessoaFormSet,
    EncaminhamentoForm,
    EncaminhamentoRespostaForm,
    FollowupForm,
    InteracaoForm,
    MarcarRespondidaForm,
    TemaForm,
)
from .models import Anexo, Demanda, Encaminhamento, Interacao, Tema


def _filtrar_visiveis(qs, user):
    """Restritas só são visíveis para responsável, ADM, CG e superuser."""
    if (
        user.is_superuser
        or user.groups.filter(name__in=["Administrador", "Chefe de Gabinete"]).exists()
    ):
        return qs
    return qs.filter(Q(restrito=False) | Q(responsavel=user))


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
        qs = _filtrar_visiveis(qs, self.request.user)

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
                status__in=[Demanda.STATUS_RESPONDIDO, Demanda.STATUS_ARQUIVADO]
            )
        elif quick == "sem_retorno_30d":
            limite = timezone.now() - timedelta(days=30)
            qs = qs.filter(criado_em__lte=limite, retorno_data__isnull=True).exclude(
                status__in=[Demanda.STATUS_RESPONDIDO, Demanda.STATUS_ARQUIVADO]
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

        return qs.distinct() if (busca or tema_id) else qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["filtro"] = self.request.GET.get("filtro", "")
        ctx["status_atual"] = self.request.GET.get("status", "")
        ctx["resultado_atual"] = self.request.GET.get("resultado", "")
        ctx["coord_atual"] = self.request.GET.get("coord", "")
        ctx["tag_id"] = self.request.GET.get("tag", "")
        ctx["status_choices"] = Demanda.STATUS_CHOICES
        ctx["resultado_choices"] = Demanda.RESULTADO_CHOICES
        ctx["coord_choices"] = Demanda.COORDENACAO_CHOICES
        ctx["temas_disponiveis"] = Tema.objects.filter(ativo=True)
        return ctx


class DemandaDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "demandas.view_demanda"
    model = Demanda
    template_name = "demandas/detalhe.html"
    context_object_name = "demanda"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.pode_ser_visto_por(self.request.user):
            raise Http404("Demanda restrita.")
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        d = self.object
        u = self.request.user
        ctx["interacoes"] = d.interacoes.select_related("autor").order_by(
            "-data_ocorrencia", "-criado_em"
        )
        ctx["partes_pessoas"] = d.demanda_pessoas.select_related("pessoa")
        ctx["partes_entidades"] = d.demanda_entidades.select_related("entidade")
        ctx["encaminhamentos"] = d.encaminhamentos.select_related("criado_por")
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
        ctx["form_followup"] = FollowupForm()
        ctx["form_encaminhamento"] = EncaminhamentoForm()
        ctx["form_anexo"] = AnexoForm()
        ctx["form_arquivar"] = ArquivarForm(instance=d)
        ctx["form_responder"] = MarcarRespondidaForm(instance=d)
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

        with transaction.atomic():
            self._salvar(form, formsets)
            if not self.object.anonimo and not self.object.tem_partes():
                form.add_error(
                    None,
                    "Demanda não-anônima exige ao menos uma parte (pessoa ou entidade).",
                )
                transaction.set_rollback(True)
                return self.form_invalid(form, formsets)

        return self._sucesso()

    def _salvar(self, form, formsets):
        self.object = form.save()
        for fs in formsets.values():
            fs.instance = self.object
            fs.save()

    def _sucesso(self):
        return redirect("demandas:demanda_detalhe", pk=self.object.pk)

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

    def _sucesso(self):
        messages.success(self.request, "Demanda atualizada.")
        return super()._sucesso()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object.numero}"
        return ctx


class AtualizarResultadoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """POST do bloco de Resultado no detalhe — atualiza resultado + observação."""

    permission_required = "demandas.change_demanda"

    def post(self, request, pk):
        demanda = get_object_or_404(Demanda, pk=pk)
        if not demanda.pode_ser_visto_por(request.user):
            raise Http404
        novo = request.POST.get("resultado", "").strip()
        obs = request.POST.get("resultado_observacao", "").strip()
        if novo not in dict(Demanda.RESULTADO_CHOICES):
            messages.error(request, "Resultado inválido.")
            return redirect("demandas:demanda_detalhe", pk=pk)
        demanda.resultado = novo
        demanda.resultado_observacao = obs
        try:
            demanda.full_clean()
        except ValidationError as e:
            for erro in e.messages:
                messages.error(request, erro)
            return redirect("demandas:demanda_detalhe", pk=pk)
        demanda.save()
        messages.success(request, "Resultado atualizado.")
        return redirect("demandas:demanda_detalhe", pk=pk)


class MarcarRespondidaView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "demandas.change_demanda"

    def post(self, request, pk):
        demanda = get_object_or_404(Demanda, pk=pk)
        if not demanda.pode_ser_visto_por(request.user):
            raise Http404
        form = MarcarRespondidaForm(request.POST, instance=demanda)
        if not form.is_valid():
            for erros in form.errors.values():
                messages.error(request, "; ".join(erros))
            return redirect("demandas:demanda_detalhe", pk=pk)
        demanda = form.save(commit=False)
        demanda.status = Demanda.STATUS_RESPONDIDO
        try:
            demanda.full_clean()
        except ValidationError as e:
            for erro in e.messages:
                messages.error(request, erro)
            return redirect("demandas:demanda_detalhe", pk=pk)
        demanda.save()
        messages.success(request, f"Demanda {demanda.numero} marcada como respondida.")
        return redirect("demandas:demanda_detalhe", pk=pk)


class ArquivarView(LoginRequiredMixin, View):
    """Arquiva demanda. CO/CG/ADM podem; AS não.

    Vinda de respondido: sem justificativa exigida.
    Vinda de qualquer outro status: exige observacoes_arquivamento E permissão
    pode_arquivar_sem_responder (CG/ADM).
    """

    def post(self, request, pk):
        demanda = get_object_or_404(Demanda, pk=pk)
        if not demanda.pode_ser_visto_por(request.user):
            raise Http404
        if not request.user.has_perm("demandas.pode_arquivar_demanda"):
            raise PermissionDenied("Sem permissão para arquivar demanda.")
        if demanda._original_status != Demanda.STATUS_RESPONDIDO and not request.user.has_perm(
            "demandas.pode_arquivar_sem_responder"
        ):
            raise PermissionDenied("Apenas CG/ADM podem arquivar demanda não respondida.")

        form = ArquivarForm(request.POST, instance=demanda)
        if not form.is_valid():
            for erros in form.errors.values():
                messages.error(request, "; ".join(erros))
            return redirect("demandas:demanda_detalhe", pk=pk)
        demanda = form.save(commit=False)
        demanda.status = Demanda.STATUS_ARQUIVADO
        try:
            demanda.full_clean()
        except ValidationError as e:
            for erro in e.messages:
                messages.error(request, erro)
            return redirect("demandas:demanda_detalhe", pk=pk)
        demanda.save()
        messages.success(request, "Demanda arquivada.")
        return redirect("demandas:demanda_detalhe", pk=pk)


class ReabrirView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "demandas.pode_reabrir_demanda"

    def post(self, request, pk):
        demanda = get_object_or_404(Demanda, pk=pk)
        if demanda.status != Demanda.STATUS_RESPONDIDO:
            messages.error(request, "Apenas demandas respondidas podem ser reabertas.")
            return redirect("demandas:demanda_detalhe", pk=pk)
        demanda.status = Demanda.STATUS_EM_ANDAMENTO
        demanda.save()
        messages.success(request, "Demanda reaberta.")
        return redirect("demandas:demanda_detalhe", pk=pk)


# --- Interações ---


class AdicionarInteracaoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "demandas.add_interacao"

    def post(self, request, pk):
        demanda = get_object_or_404(Demanda, pk=pk)
        if not demanda.pode_ser_visto_por(request.user):
            raise Http404
        form = InteracaoForm(request.POST)
        followup = FollowupForm(request.POST)
        if not form.is_valid() or not followup.is_valid():
            erros_lista = list(form.errors.values()) + list(followup.errors.values())
            for grupo in erros_lista:
                if hasattr(grupo, "__iter__") and not isinstance(grupo, str):
                    messages.error(request, "; ".join(grupo))
                else:
                    messages.error(request, str(grupo))
            return redirect("demandas:demanda_detalhe", pk=pk)
        with transaction.atomic():
            interacao = form.save(commit=False)
            interacao.demanda = demanda
            interacao.autor = request.user
            interacao.save()
            if (
                followup.cleaned_data.get("criar")
                and interacao.status == Interacao.STATUS_REALIZADA
            ):
                Interacao.objects.create(
                    demanda=demanda,
                    autor=request.user,
                    tipo=followup.cleaned_data["tipo"],
                    conteudo=followup.cleaned_data["conteudo"],
                    status=Interacao.STATUS_AGENDADA,
                    data_ocorrencia=followup.cleaned_data["data_ocorrencia"],
                    interacao_origem=interacao,
                )
        messages.success(request, "Interação registrada.")
        return redirect("demandas:demanda_detalhe", pk=pk)


class InteracaoMarcarRealizadaView(LoginRequiredMixin, View):
    """Converte interação agendada em realizada — autor ou ADM/CG."""

    def post(self, request, pk):
        interacao = get_object_or_404(Interacao, pk=pk)
        if not interacao.demanda.pode_ser_visto_por(request.user):
            raise Http404
        if (
            interacao.autor_id != request.user.id
            and not request.user.groups.filter(
                name__in=["Administrador", "Chefe de Gabinete"]
            ).exists()
        ):
            raise PermissionDenied("Apenas o autor pode marcar como realizada.")
        if interacao.status != Interacao.STATUS_AGENDADA:
            messages.error(request, "Interação não está agendada.")
            return redirect("demandas:demanda_detalhe", pk=interacao.demanda_id)
        interacao.status = Interacao.STATUS_REALIZADA
        interacao.save()
        messages.success(request, "Interação marcada como realizada.")
        return redirect("demandas:demanda_detalhe", pk=interacao.demanda_id)


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
            return redirect("demandas:demanda_detalhe", pk=interacao.demanda_id)
        interacao.status = Interacao.STATUS_CANCELADA
        interacao.save()
        messages.success(request, "Interação cancelada.")
        return redirect("demandas:demanda_detalhe", pk=interacao.demanda_id)


# --- Encaminhamentos ---


class AdicionarEncaminhamentoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "demandas.add_encaminhamento"

    def post(self, request, pk):
        demanda = get_object_or_404(Demanda, pk=pk)
        if not demanda.pode_ser_visto_por(request.user):
            raise Http404
        form = EncaminhamentoForm(request.POST)
        if not form.is_valid():
            for erros in form.errors.values():
                messages.error(request, "; ".join(erros))
            return redirect("demandas:demanda_detalhe", pk=pk)
        with transaction.atomic():
            enc = form.save(commit=False)
            enc.demanda = demanda
            enc.criado_por = request.user
            enc.save()
            Interacao.objects.create(
                demanda=demanda,
                autor=request.user,
                tipo=Interacao.TIPO_ENCAMINHAMENTO,
                conteudo=f"Encaminhamento {enc.get_tipo_documento_display()} → {enc.destinatario_orgao}.",
                status=Interacao.STATUS_REALIZADA,
                data_ocorrencia=timezone.now(),
                automatica=False,
            )
        messages.success(request, "Encaminhamento adicionado.")
        return redirect("demandas:demanda_detalhe", pk=pk)


class EncaminhamentoRespostaView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "demandas.change_encaminhamento"

    def post(self, request, pk):
        enc = get_object_or_404(Encaminhamento, pk=pk)
        if not enc.demanda.pode_ser_visto_por(request.user):
            raise Http404
        form = EncaminhamentoRespostaForm(request.POST, instance=enc)
        if not form.is_valid():
            for erros in form.errors.values():
                messages.error(request, "; ".join(erros))
            return redirect("demandas:demanda_detalhe", pk=enc.demanda_id)
        enc = form.save()
        Interacao.objects.create(
            demanda=enc.demanda,
            autor=request.user,
            tipo=Interacao.TIPO_RETORNO_EXTERNO,
            conteudo=f"Resposta de {enc.destinatario_orgao} ({enc.get_status_display()}).",
            status=Interacao.STATUS_REALIZADA,
            data_ocorrencia=timezone.now(),
            automatica=False,
        )
        messages.success(request, "Resposta registrada.")
        return redirect("demandas:demanda_detalhe", pk=enc.demanda_id)


# --- Temas (categorização de Demanda) ---


class TemaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "demandas.view_tema"
    model = Tema
    template_name = "demandas/temas/lista.html"
    context_object_name = "temas"

    def get_queryset(self):
        qs = Tema.objects.all()
        if self.request.GET.get("inativos") != "1":
            qs = qs.filter(ativo=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mostrar_inativos"] = self.request.GET.get("inativos") == "1"
        return ctx


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
}


class AnexoUploadView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Upload polimórfico — recebe (tipo, object_id) e cria Anexo."""

    permission_required = "demandas.add_anexo"

    def post(self, request, tipo, object_id):
        if tipo not in _TIPO_PARA_MODEL:
            raise Http404("Tipo de objeto pai inválido.")
        app_label, model_name = _TIPO_PARA_MODEL[tipo]
        ct = ContentType.objects.get(app_label=app_label, model=model_name)
        objeto_pai = ct.model_class().objects.get(pk=object_id)
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


class AnexoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "demandas.delete_anexo"

    def post(self, request, pk):
        anexo = get_object_or_404(Anexo, pk=pk)
        if (
            anexo.enviado_por_id != request.user.id
            and not request.user.groups.filter(
                name__in=["Administrador", "Chefe de Gabinete", "Coordenador"]
            ).exists()
        ):
            raise PermissionDenied("Sem permissão para excluir este anexo.")
        referer = request.META.get("HTTP_REFERER", "/")
        anexo.arquivo.delete(save=False)
        anexo.delete()
        messages.success(request, "Anexo removido.")
        return redirect(referer)
