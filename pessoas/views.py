"""Views de Pessoa, Entidade, Vínculo, Tag — CRUD da Fase 2."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View

from .deduplicacao import buscar_similares
from .forms import EntidadeForm, PessoaForm, TagForm, VinculoForm
from .models import Entidade, Pessoa, Tag, Vinculo
from .viacep import consultar as consultar_cep

# --- Pessoas ---


class PessoaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "pessoas.view_pessoa"
    model = Pessoa
    template_name = "pessoas/lista.html"
    context_object_name = "pessoas"
    paginate_by = 25

    def get_queryset(self):
        qs = Pessoa.objects.all().prefetch_related("tags")
        if self.request.GET.get("inativos") != "1":
            qs = qs.filter(ativo=True)
        busca = self.request.GET.get("q", "").strip()
        if busca:
            qs = qs.filter(
                Q(nome__icontains=busca)
                | Q(sobrenome__icontains=busca)
                | Q(nome_social__icontains=busca)
                | Q(email__icontains=busca)
                | Q(telefone__icontains=busca)
                | Q(whatsapp__icontains=busca)
                | Q(bairro__icontains=busca)
            )
        bairro = self.request.GET.get("bairro", "").strip()
        if bairro:
            qs = qs.filter(bairro__iexact=bairro)
        tag = self.request.GET.get("tag", "").strip()
        if tag:
            qs = qs.filter(tags__id=tag)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["bairro"] = self.request.GET.get("bairro", "")
        ctx["tag_id"] = self.request.GET.get("tag", "")
        ctx["mostrar_inativos"] = self.request.GET.get("inativos") == "1"
        ctx["tags_disponiveis"] = Tag.objects.filter(ativo=True)
        return ctx


class PessoaDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "pessoas.view_pessoa"
    model = Pessoa
    template_name = "pessoas/detalhe.html"
    context_object_name = "pessoa"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["vinculos"] = self.object.vinculos.select_related("entidade").all()
        ctx["form_vinculo"] = VinculoForm(pessoa=self.object)
        return ctx


class PessoaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "pessoas.add_pessoa"
    model = Pessoa
    form_class = PessoaForm
    template_name = "pessoas/form.html"

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"Pessoa cadastrada: {self.object.nome_exibicao}.")
        return response

    def get_success_url(self):
        return reverse("pessoas:pessoa_detalhe", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Nova pessoa"
        return ctx


class PessoaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "pessoas.change_pessoa"
    model = Pessoa
    form_class = PessoaForm
    template_name = "pessoas/form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Pessoa atualizada.")
        return response

    def get_success_url(self):
        return reverse("pessoas:pessoa_detalhe", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object.nome_exibicao}"
        return ctx


class PessoaToggleAtivoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Desativa ou reativa pessoa. Requer pode_desativar_pessoa ou pode_reativar_pessoa."""

    permission_required = "pessoas.change_pessoa"

    def post(self, request, pk):
        pessoa = get_object_or_404(Pessoa, pk=pk)
        if pessoa.ativo:
            if not request.user.has_perm("pessoas.pode_desativar_pessoa"):
                raise PermissionDenied("Sem permissão para desativar pessoa.")
            pessoa.ativo = False
            pessoa.save()
            messages.success(request, f"{pessoa.nome_exibicao} desativada.")
        else:
            if not request.user.has_perm("pessoas.pode_reativar_pessoa"):
                raise PermissionDenied("Sem permissão para reativar pessoa.")
            pessoa.ativo = True
            pessoa.save()
            messages.success(request, f"{pessoa.nome_exibicao} reativada.")
        return redirect("pessoas:pessoa_detalhe", pk=pk)


# --- Vínculos ---


class VinculoCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "pessoas.add_vinculo"

    def post(self, request, pessoa_pk):
        pessoa = get_object_or_404(Pessoa, pk=pessoa_pk)
        form = VinculoForm(request.POST, pessoa=pessoa)
        if form.is_valid():
            form.save()
            messages.success(request, "Vínculo adicionado.")
        else:
            for err in form.errors.values():
                messages.error(request, "; ".join(err))
        return redirect("pessoas:pessoa_detalhe", pk=pessoa.pk)


class VinculoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "pessoas.delete_vinculo"

    def post(self, request, pk):
        vinculo = get_object_or_404(Vinculo, pk=pk)
        pessoa_pk = vinculo.pessoa_id
        vinculo.delete()
        messages.success(request, "Vínculo removido.")
        return redirect("pessoas:pessoa_detalhe", pk=pessoa_pk)


# --- Entidades ---


class EntidadeListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "pessoas.view_entidade"
    model = Entidade
    template_name = "pessoas/entidades/lista.html"
    context_object_name = "entidades"
    paginate_by = 25

    def get_queryset(self):
        qs = Entidade.objects.all().prefetch_related("tags")
        if self.request.GET.get("inativos") != "1":
            qs = qs.filter(ativo=True)
        busca = self.request.GET.get("q", "").strip()
        if busca:
            qs = qs.filter(
                Q(nome__icontains=busca)
                | Q(nome_fantasia__icontains=busca)
                | Q(cnpj__icontains=busca)
                | Q(email__icontains=busca)
            )
        tipo = self.request.GET.get("tipo", "").strip()
        if tipo:
            qs = qs.filter(tipo=tipo)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["tipo_atual"] = self.request.GET.get("tipo", "")
        ctx["mostrar_inativos"] = self.request.GET.get("inativos") == "1"
        ctx["tipos"] = Entidade.TIPO_CHOICES
        return ctx


class EntidadeDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "pessoas.view_entidade"
    model = Entidade
    template_name = "pessoas/entidades/detalhe.html"
    context_object_name = "entidade"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["vinculos"] = self.object.vinculos.select_related("pessoa").filter(pessoa__ativo=True)
        return ctx


class EntidadeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "pessoas.add_entidade"
    model = Entidade
    form_class = EntidadeForm
    template_name = "pessoas/entidades/form.html"

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"Entidade cadastrada: {self.object.nome}.")
        return response

    def get_success_url(self):
        return reverse("pessoas:entidade_detalhe", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Nova entidade"
        return ctx


class EntidadeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "pessoas.change_entidade"
    model = Entidade
    form_class = EntidadeForm
    template_name = "pessoas/entidades/form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Entidade atualizada.")
        return response

    def get_success_url(self):
        return reverse("pessoas:entidade_detalhe", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object.nome}"
        return ctx


class EntidadeToggleAtivoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "pessoas.change_entidade"

    def post(self, request, pk):
        entidade = get_object_or_404(Entidade, pk=pk)
        if entidade.ativo:
            if not request.user.has_perm("pessoas.pode_desativar_entidade"):
                raise PermissionDenied("Sem permissão para desativar entidade.")
            entidade.ativo = False
            entidade.save()
            messages.success(request, f"{entidade.nome} desativada.")
        else:
            if not request.user.has_perm("pessoas.pode_reativar_entidade"):
                raise PermissionDenied("Sem permissão para reativar entidade.")
            entidade.ativo = True
            entidade.save()
            messages.success(request, f"{entidade.nome} reativada.")
        return redirect("pessoas:entidade_detalhe", pk=pk)


# --- Tags ---


class TagListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "pessoas.view_tag"
    model = Tag
    template_name = "pessoas/tags/lista.html"
    context_object_name = "tags"

    def get_queryset(self):
        return Tag.objects.all().order_by("categoria", "nome")


class TagCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "pessoas.add_tag"
    model = Tag
    form_class = TagForm
    template_name = "pessoas/tags/form.html"
    success_url = reverse_lazy("pessoas:tag_lista")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Tag '{self.object.nome}' criada.")
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Nova tag"
        return ctx


class TagUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "pessoas.change_tag"
    model = Tag
    form_class = TagForm
    template_name = "pessoas/tags/form.html"
    success_url = reverse_lazy("pessoas:tag_lista")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Tag atualizada.")
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object.nome}"
        return ctx


class TagDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "pessoas.delete_tag"
    model = Tag
    success_url = reverse_lazy("pessoas:tag_lista")
    template_name = "pessoas/tags/confirmar_remocao.html"


# --- Endpoints auxiliares ---


class CEPLookupView(LoginRequiredMixin, View):
    """GET /pessoas/cep/<cep>/ — retorna dados do ViaCEP em JSON."""

    def get(self, request, cep):
        dados = consultar_cep(cep)
        if dados is None:
            return JsonResponse({"erro": "CEP não encontrado."}, status=404)
        return JsonResponse(dados)


class DeduplicacaoCheckView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """GET /pessoas/deduplicar/?email=&telefone=&whatsapp=&exclude="""

    permission_required = "pessoas.view_pessoa"

    def get(self, request):
        excluir_pk = request.GET.get("exclude") or None
        similares = buscar_similares(
            email=request.GET.get("email", ""),
            telefone=request.GET.get("telefone", ""),
            whatsapp=request.GET.get("whatsapp", ""),
            excluir_pk=excluir_pk,
        )[:5]
        dados = [
            {
                "id": p.pk,
                "nome": p.nome_exibicao,
                "email": p.email,
                "telefone": p.telefone,
                "whatsapp": p.whatsapp,
                "url": reverse("pessoas:pessoa_detalhe", args=[p.pk]),
            }
            for p in similares
        ]
        return JsonResponse({"resultados": dados})
