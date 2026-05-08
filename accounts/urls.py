from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("entrar/", views.MPDLoginView.as_view(), name="login"),
    path("sair/", LogoutView.as_view(), name="logout"),
    path("perfil/", views.PerfilView.as_view(), name="perfil"),
    path(
        "configuracoes/usuarios/",
        views.UsuarioListView.as_view(),
        name="usuarios_lista",
    ),
    path(
        "configuracoes/usuarios/novo/",
        views.UsuarioCreateView.as_view(),
        name="usuarios_criar",
    ),
    path(
        "configuracoes/usuarios/<int:pk>/editar/",
        views.UsuarioUpdateView.as_view(),
        name="usuarios_editar",
    ),
    path(
        "configuracoes/usuarios/<int:pk>/toggle-ativo/",
        views.UsuarioToggleAtivoView.as_view(),
        name="usuarios_toggle_ativo",
    ),
]
