from django.urls import path

from . import views

app_name = "demandas"

urlpatterns = [
    path("", views.DemandaListView.as_view(), name="demanda_lista"),
    path("nova/", views.DemandaCreateView.as_view(), name="demanda_nova"),
    path("<uuid:pk>/", views.DemandaDetailView.as_view(), name="demanda_detalhe"),
    path("<uuid:pk>/editar/", views.DemandaUpdateView.as_view(), name="demanda_editar"),
    path(
        "<uuid:pk>/resultado/",
        views.AtualizarResultadoView.as_view(),
        name="demanda_resultado",
    ),
    path(
        "<uuid:pk>/responder/",
        views.MarcarRespondidaView.as_view(),
        name="demanda_responder",
    ),
    path("<uuid:pk>/arquivar/", views.ArquivarView.as_view(), name="demanda_arquivar"),
    path("<uuid:pk>/reabrir/", views.ReabrirView.as_view(), name="demanda_reabrir"),
    # Interações
    path(
        "<uuid:pk>/interacoes/nova/",
        views.AdicionarInteracaoView.as_view(),
        name="interacao_nova",
    ),
    path(
        "interacoes/<uuid:pk>/realizada/",
        views.InteracaoMarcarRealizadaView.as_view(),
        name="interacao_realizada",
    ),
    path(
        "interacoes/<uuid:pk>/cancelar/",
        views.InteracaoCancelarView.as_view(),
        name="interacao_cancelar",
    ),
    # Encaminhamentos
    path(
        "<uuid:pk>/encaminhamentos/novo/",
        views.AdicionarEncaminhamentoView.as_view(),
        name="encaminhamento_novo",
    ),
    path(
        "encaminhamentos/<uuid:pk>/responder/",
        views.EncaminhamentoRespostaView.as_view(),
        name="encaminhamento_responder",
    ),
    # Anexos polimórficos
    path(
        "anexos/<str:tipo>/<uuid:object_id>/",
        views.AnexoUploadView.as_view(),
        name="anexo_upload",
    ),
    path(
        "anexos/<uuid:pk>/remover/",
        views.AnexoDeleteView.as_view(),
        name="anexo_remover",
    ),
    # Temas (administração de categorias de demanda)
    path("temas/", views.TemaListView.as_view(), name="tema_lista"),
    path("temas/novo/", views.TemaCreateView.as_view(), name="tema_novo"),
    path("temas/<int:pk>/editar/", views.TemaUpdateView.as_view(), name="tema_editar"),
    path(
        "temas/<int:pk>/arquivar/",
        views.TemaToggleArquivarView.as_view(),
        name="tema_arquivar",
    ),
]
