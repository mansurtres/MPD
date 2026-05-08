from django.urls import path

from . import views

app_name = "pessoas"

urlpatterns = [
    # Pessoas
    path("pessoas/", views.PessoaListView.as_view(), name="pessoa_lista"),
    path("pessoas/nova/", views.PessoaCreateView.as_view(), name="pessoa_nova"),
    path("pessoas/<int:pk>/", views.PessoaDetailView.as_view(), name="pessoa_detalhe"),
    path("pessoas/<int:pk>/editar/", views.PessoaUpdateView.as_view(), name="pessoa_editar"),
    path(
        "pessoas/<int:pk>/toggle-ativo/",
        views.PessoaToggleAtivoView.as_view(),
        name="pessoa_toggle_ativo",
    ),
    # Vínculos
    path(
        "pessoas/<int:pessoa_pk>/vinculos/novo/",
        views.VinculoCreateView.as_view(),
        name="vinculo_novo",
    ),
    path(
        "vinculos/<int:pk>/remover/",
        views.VinculoDeleteView.as_view(),
        name="vinculo_remover",
    ),
    # Entidades
    path("entidades/", views.EntidadeListView.as_view(), name="entidade_lista"),
    path("entidades/nova/", views.EntidadeCreateView.as_view(), name="entidade_nova"),
    path("entidades/<int:pk>/", views.EntidadeDetailView.as_view(), name="entidade_detalhe"),
    path(
        "entidades/<int:pk>/editar/",
        views.EntidadeUpdateView.as_view(),
        name="entidade_editar",
    ),
    path(
        "entidades/<int:pk>/toggle-ativo/",
        views.EntidadeToggleAtivoView.as_view(),
        name="entidade_toggle_ativo",
    ),
    # Tags
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
    # Endpoints auxiliares
    path("api/cep/<str:cep>/", views.CEPLookupView.as_view(), name="api_cep"),
    path("api/deduplicar/", views.DeduplicacaoCheckView.as_view(), name="api_deduplicar"),
]
