from django.urls import path

from . import views

app_name = "pessoas"

urlpatterns = [
    # Pessoas (slug curto na URL pública)
    path("pessoas/", views.PessoaListView.as_view(), name="pessoa_lista"),
    path("pessoas/export.csv", views.PessoaCSVExportView.as_view(), name="pessoa_export_csv"),
    path("pessoas/buscar.json", views.PessoaBuscarJSONView.as_view(), name="pessoa_buscar_json"),
    path("pessoas/criar.json", views.PessoaCriarAjaxView.as_view(), name="pessoa_criar_ajax"),
    path(
        "entidades/buscar.json",
        views.EntidadeBuscarJSONView.as_view(),
        name="entidade_buscar_json",
    ),
    path(
        "entidades/criar.json",
        views.EntidadeCriarAjaxView.as_view(),
        name="entidade_criar_ajax",
    ),
    path("pessoas/nova/", views.PessoaCreateView.as_view(), name="pessoa_nova"),
    path("pessoas/<str:slug>/", views.PessoaDetailView.as_view(), name="pessoa_detalhe"),
    path("pessoas/<str:slug>/editar/", views.PessoaUpdateView.as_view(), name="pessoa_editar"),
    path(
        "pessoas/<str:slug>/toggle-ativo/",
        views.PessoaToggleAtivoView.as_view(),
        name="pessoa_toggle_ativo",
    ),
    # Vínculos
    path(
        "pessoas/<str:slug>/vinculos/novo/",
        views.VinculoCreateView.as_view(),
        name="vinculo_novo",
    ),
    path(
        "vinculos/<int:pk>/remover/",
        views.VinculoDeleteView.as_view(),
        name="vinculo_remover",
    ),
    # Entidades (slug curto na URL pública)
    path("entidades/", views.EntidadeListView.as_view(), name="entidade_lista"),
    path("entidades/nova/", views.EntidadeCreateView.as_view(), name="entidade_nova"),
    path("entidades/<str:slug>/", views.EntidadeDetailView.as_view(), name="entidade_detalhe"),
    path(
        "entidades/<str:slug>/editar/",
        views.EntidadeUpdateView.as_view(),
        name="entidade_editar",
    ),
    path(
        "entidades/<str:slug>/toggle-ativo/",
        views.EntidadeToggleAtivoView.as_view(),
        name="entidade_toggle_ativo",
    ),
    # Tags (UUID — área administrativa, não exposta a cidadãos)
    path("configuracoes/tags/", views.TagListView.as_view(), name="tag_lista"),
    path("configuracoes/tags/nova/", views.TagCreateView.as_view(), name="tag_nova"),
    path(
        "configuracoes/tags/<int:pk>/editar/",
        views.TagUpdateView.as_view(),
        name="tag_editar",
    ),
    path(
        "configuracoes/tags/<int:pk>/remover/",
        views.TagDeleteView.as_view(),
        name="tag_remover",
    ),
    path(
        "configuracoes/tags/<int:pk>/arquivar/",
        views.TagToggleArquivarView.as_view(),
        name="tag_arquivar",
    ),
    # Endpoints auxiliares
    path("api/cep/<str:cep>/", views.CEPLookupView.as_view(), name="api_cep"),
    path("api/deduplicar/", views.DeduplicacaoCheckView.as_view(), name="api_deduplicar"),
]
