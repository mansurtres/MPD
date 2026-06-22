"""Views de Encaminhamento: adicionar, registrar resposta, listagem transversal."""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import ListView, View

from core.utils import flash_form_errors

from ..forms import EncaminhamentoForm, EncaminhamentoRespostaForm
from ..models import Demanda, Encaminhamento, Interacao
from ._shared import _anexar_se_houver, _pode_exportar


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
