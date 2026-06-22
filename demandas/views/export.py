"""Views de exportação CSV (Fase 6). Apenas Admin (ADR 0059). Registra log via auditlog."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import View

from ._shared import _pode_exportar


class DemandaCSVExportView(LoginRequiredMixin, View):
    """Exporta a lista de demandas filtrada pelo querystring para CSV BR
    (UTF-8 BOM + separador ;). Limite 10k. Apenas Admin. Registra log."""

    def get(self, request):
        if not _pode_exportar(request.user):
            raise PermissionDenied("Exportação restrita ao Administrador.")
        from core.csv_export import exportar_csv

        from .demandas import DemandaListView

        def row_fn(d):
            temas = ", ".join(t.nome for t in d.temas.all())
            return [
                d.numero,
                d.titulo,
                d.get_origem_display(),
                d.get_canal_entrada_display(),
                d.get_status_display(),
                d.get_resultado_display(),
                (d.responsavel.nome_completo or d.responsavel.email) if d.responsavel else "",
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
                "Responsável",
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
            raise PermissionDenied("Exportação restrita ao Administrador.")
        from core.csv_export import exportar_csv

        from .encaminhamentos import EncaminhamentoListView

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
