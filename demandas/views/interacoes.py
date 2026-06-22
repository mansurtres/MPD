"""Views de Interação: adicionar, marcar realizada, cancelar."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View

from core.permissoes import eh_cg_plus
from core.utils import flash_form_errors

from ..forms import FollowupForm, InteracaoForm
from ..models import Demanda, Interacao
from ._shared import _anexar_se_houver


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
