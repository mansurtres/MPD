from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView, View

from .forms import LoginForm, PerfilForm, UsuarioCreateForm, UsuarioUpdateForm
from .models import Usuario


class GerenciarUsuariosMixin(PermissionRequiredMixin):
    """Gating da gestão de equipe pela permissão custom (DT-011).

    Anônimo → redireciona para login; autenticado sem a permissão → 403.
    Promoção a staff/superuser fica reservada ao Django Admin."""

    permission_required = "accounts.gerenciar_usuarios"


class MPDLoginView(DjangoLoginView):
    form_class = LoginForm
    template_name = "accounts/login.html"

    def form_valid(self, form):
        if form.cleaned_data.get("lembrar"):
            self.request.session.set_expiry(2592000)  # 30 dias
        else:
            self.request.session.set_expiry(0)
        return super().form_valid(form)


class PerfilView(LoginRequiredMixin, UpdateView):
    model = Usuario
    form_class = PerfilForm
    template_name = "accounts/perfil.html"
    success_url = reverse_lazy("accounts:perfil")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Perfil atualizado.")
        return super().form_valid(form)


class UsuarioListView(GerenciarUsuariosMixin, ListView):
    model = Usuario
    template_name = "accounts/usuarios/lista.html"
    context_object_name = "usuarios"
    ordering = ["nome_completo", "email"]


class UsuarioCreateView(GerenciarUsuariosMixin, CreateView):
    model = Usuario
    form_class = UsuarioCreateForm
    template_name = "accounts/usuarios/form.html"
    success_url = reverse_lazy("accounts:usuarios_lista")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo usuário"
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Usuário criado com sucesso.")
        return super().form_valid(form)


class UsuarioUpdateView(GerenciarUsuariosMixin, UpdateView):
    model = Usuario
    form_class = UsuarioUpdateForm
    template_name = "accounts/usuarios/form.html"
    success_url = reverse_lazy("accounts:usuarios_lista")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar {self.object}"
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Usuário atualizado.")
        return super().form_valid(form)


class UsuarioToggleAtivoView(GerenciarUsuariosMixin, View):
    def post(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        if usuario == request.user:
            messages.error(request, "Você não pode desativar sua própria conta.")
            return redirect("accounts:usuarios_lista")
        usuario.is_active = not usuario.is_active
        usuario.save(update_fields=["is_active"])
        acao = "ativado" if usuario.is_active else "desativado"
        messages.success(request, f"Usuário {acao}.")
        return redirect("accounts:usuarios_lista")
