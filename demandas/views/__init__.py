"""Package demandas/views — re-exporta todos os nomes públicos referenciados
em demandas/urls.py (via ``from . import views``) e quaisquer outros
importadores externos, mantendo compatibilidade total com o módulo plano
que este pacote substitui."""

from .anexos import AnexoDeleteView, AnexoDownloadView, AnexoUploadView
from .demandas import (
    ArquivarView,
    ConcluirDemandaView,
    DemandaCreateView,
    DemandaDetailView,
    DemandaListView,
    DemandaUpdateView,
    ReabrirView,
)
from .encaminhamentos import (
    AdicionarEncaminhamentoView,
    EncaminhamentoListView,
    EncaminhamentoRespostaView,
)
from .export import DemandaCSVExportView, EncaminhamentoCSVExportView
from .inbox import (
    CapturarInboxView,
    DescartarInboxView,
    InboxListView,
    MinhasPendenciasView,
    MinhasReunioesView,
    ProcessarInboxView,
)
from .interacoes import (
    AdicionarInteracaoView,
    InteracaoCancelarView,
    InteracaoMarcarRealizadaView,
)
from .temas import (
    TemaCreateAjaxView,
    TemaCreateView,
    TemaDeleteView,
    TemaListView,
    TemaToggleArquivarView,
    TemaUpdateView,
)

__all__ = [
    # demandas
    "DemandaListView",
    "DemandaDetailView",
    "DemandaCreateView",
    "DemandaUpdateView",
    "ConcluirDemandaView",
    "ArquivarView",
    "ReabrirView",
    # interacoes
    "AdicionarInteracaoView",
    "InteracaoMarcarRealizadaView",
    "InteracaoCancelarView",
    # encaminhamentos
    "AdicionarEncaminhamentoView",
    "EncaminhamentoRespostaView",
    "EncaminhamentoListView",
    # temas
    "TemaListView",
    "TemaCreateView",
    "TemaUpdateView",
    "TemaDeleteView",
    "TemaCreateAjaxView",
    "TemaToggleArquivarView",
    # anexos
    "AnexoUploadView",
    "AnexoDownloadView",
    "AnexoDeleteView",
    # inbox + pendencias
    "CapturarInboxView",
    "InboxListView",
    "ProcessarInboxView",
    "DescartarInboxView",
    "MinhasPendenciasView",
    "MinhasReunioesView",
    # export
    "DemandaCSVExportView",
    "EncaminhamentoCSVExportView",
]
