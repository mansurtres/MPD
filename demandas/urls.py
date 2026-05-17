"""URLs do app demandas. Caminhos absolutos para permitir que temas vivam
em /configuracoes/temas/ (administração) enquanto demandas vivem em
/demandas/. Padrão herdado de pessoas/urls.py (tags em /configuracoes/tags/).
"""

from django.urls import path

from . import views

app_name = "demandas"

urlpatterns = [
    # --- Demandas (CRUD) ---
    path("demandas/", views.DemandaListView.as_view(), name="demanda_lista"),
    path("demandas/nova/", views.DemandaCreateView.as_view(), name="demanda_nova"),
    path("demandas/<uuid:pk>/", views.DemandaDetailView.as_view(), name="demanda_detalhe"),
    path(
        "demandas/<uuid:pk>/editar/",
        views.DemandaUpdateView.as_view(),
        name="demanda_editar",
    ),
    path(
        "demandas/<uuid:pk>/estado/",
        views.AtualizarEstadoView.as_view(),
        name="demanda_estado",
    ),
    path(
        "demandas/<uuid:pk>/concluir/",
        views.ConcluirDemandaView.as_view(),
        name="demanda_concluir",
    ),
    path(
        "demandas/<uuid:pk>/arquivar/",
        views.ArquivarView.as_view(),
        name="demanda_arquivar",
    ),
    path(
        "demandas/<uuid:pk>/reabrir/",
        views.ReabrirView.as_view(),
        name="demanda_reabrir",
    ),
    # --- Interações ---
    path(
        "demandas/<uuid:pk>/interacoes/nova/",
        views.AdicionarInteracaoView.as_view(),
        name="interacao_nova",
    ),
    path(
        "demandas/interacoes/<uuid:pk>/realizada/",
        views.InteracaoMarcarRealizadaView.as_view(),
        name="interacao_realizada",
    ),
    path(
        "demandas/interacoes/<uuid:pk>/cancelar/",
        views.InteracaoCancelarView.as_view(),
        name="interacao_cancelar",
    ),
    # --- Encaminhamentos ---
    path(
        "demandas/<uuid:pk>/encaminhamentos/novo/",
        views.AdicionarEncaminhamentoView.as_view(),
        name="encaminhamento_novo",
    ),
    path(
        "demandas/encaminhamentos/<uuid:pk>/responder/",
        views.EncaminhamentoRespostaView.as_view(),
        name="encaminhamento_responder",
    ),
    # --- Visão transversal de Encaminhamentos (ADR 0046, Fase 4) ---
    path(
        "encaminhamentos/",
        views.EncaminhamentoListView.as_view(),
        name="encaminhamento_lista",
    ),
    # --- Anexos polimórficos ---
    path(
        "demandas/anexos/<str:tipo>/<uuid:object_id>/",
        views.AnexoUploadView.as_view(),
        name="anexo_upload",
    ),
    path(
        "demandas/anexos/<uuid:pk>/remover/",
        views.AnexoDeleteView.as_view(),
        name="anexo_remover",
    ),
    # --- Temas (administração) ---
    path("configuracoes/temas/", views.TemaListView.as_view(), name="tema_lista"),
    path("configuracoes/temas/novo/", views.TemaCreateView.as_view(), name="tema_novo"),
    path(
        "configuracoes/temas/<int:pk>/editar/",
        views.TemaUpdateView.as_view(),
        name="tema_editar",
    ),
    path(
        "configuracoes/temas/<int:pk>/remover/",
        views.TemaDeleteView.as_view(),
        name="tema_remover",
    ),
    path(
        "configuracoes/temas/<int:pk>/arquivar/",
        views.TemaToggleArquivarView.as_view(),
        name="tema_arquivar",
    ),
]
