"""Views de Pessoa, Entidade, Vínculo, Tag — CRUD da Fase 2."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View

from core.utils import somente_digitos

from .deduplicacao import buscar_similares
from .forms import (
    EmailPessoaFormSet,
    EntidadeForm,
    PessoaForm,
    RedeSocialFormSet,
    TagForm,
    TelefoneFormSet,
    VinculoForm,
)
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
        qs = Pessoa.objects.all().prefetch_related("tags", "telefones", "emails")
        if self.request.GET.get("inativos") != "1":
            qs = qs.filter(ativo=True)
        busca = self.request.GET.get("q", "").strip()
        if busca:
            digitos = somente_digitos(busca)
            condicoes = (
                Q(nome__icontains=busca)
                | Q(sobrenome__icontains=busca)
                | Q(nome_social__icontains=busca)
                | Q(emails__endereco__icontains=busca)
                | Q(redes_sociais__valor__icontains=busca)
                | Q(bairro__icontains=busca)
            )
            if digitos:
                condicoes |= Q(telefones__numero__contains=digitos)
            qs = qs.filter(condicoes)
        bairro = self.request.GET.get("bairro", "").strip()
        if bairro:
            qs = qs.filter(bairro__iexact=bairro)
        tag = self.request.GET.get("tag", "").strip()
        if tag:
            qs = qs.filter(tags__id=tag)
        # distinct só quando há joins M:N (busca cruza emails/telefones/redes_sociais; tag é M:N).
        if busca or tag:
            qs = qs.distinct()
        return qs

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
    slug_field = "slug_publico"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return super().get_queryset().select_related("criado_por")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["vinculos"] = self.object.vinculos.select_related("entidade").all()
        ctx["form_vinculo"] = VinculoForm(pessoa=self.object)
        u = self.request.user
        ctx["pode_alternar_ativo"] = (
            self.object.ativo and u.has_perm("pessoas.pode_desativar_pessoa")
        ) or (not self.object.ativo and u.has_perm("pessoas.pode_reativar_pessoa"))
        return ctx


class _PessoaFormMixin:
    """Lógica comum a Create e Update: processa 3 formsets (telefones, emails,
    redes sociais) e exige pelo menos um canal preenchido."""

    template_name = "pessoas/form.html"

    FORMSETS = [
        ("telefones", TelefoneFormSet),
        ("emails", EmailPessoaFormSet),
        ("redes_sociais", RedeSocialFormSet),
    ]

    def _build_formsets(self, post_data=None):
        instance = self.object if hasattr(self, "object") else None
        return {
            chave: cls(post_data, instance=instance, prefix=chave) for chave, cls in self.FORMSETS
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if "formsets_contato" not in ctx:
            ctx["formsets_contato"] = self._build_formsets()
        return ctx

    def post(self, request, *args, **kwargs):
        eh_update = bool(self.kwargs.get("slug"))
        self.object = self.get_object() if eh_update else None
        # POST sem management forms = aba aberta antes de um deploy que mudou
        # o template, ou submit duplicado do navegador. Redireciona para GET
        # limpo em vez de exibir o erro interno do Django sobre ManagementForm.
        for chave, _ in self.FORMSETS:
            if f"{chave}-TOTAL_FORMS" not in request.POST:
                messages.warning(
                    request, "A página estava desatualizada. Recarregue e preencha novamente."
                )
                return redirect(request.path)
        form = self.get_form()
        formsets = self._build_formsets(request.POST)
        if not (form.is_valid() and all(fs.is_valid() for fs in formsets.values())):
            return self.form_invalid_with_formsets(form, formsets)

        # Salva tudo numa transação; se a regra cross-formset (pelo menos um
        # canal preenchido) falhar, faz rollback. Regra mora em
        # Pessoa.tem_meio_de_contato() — fonte única, ver DT-008.
        with transaction.atomic():
            self._salvar(form, formsets)
            tem_canal = self.object.tem_meio_de_contato()
            if not tem_canal:
                transaction.set_rollback(True)

        if tem_canal:
            return self._sucesso()
        form.add_error(
            None, "Preencha pelo menos um canal de contato: telefone, e-mail ou rede social."
        )
        return self.form_invalid_with_formsets(form, formsets)

    def _salvar(self, form, formsets):
        """Subclasses sobrescrevem para customizar (ex: criado_por)."""
        self.object = form.save()
        for fs in formsets.values():
            fs.instance = self.object
            fs.save()

    def _sucesso(self):
        return redirect("pessoas:pessoa_detalhe", slug=self.object.slug_publico)

    def form_invalid_with_formsets(self, form, formsets):
        return self.render_to_response(self.get_context_data(form=form, formsets_contato=formsets))


class PessoaCreateView(LoginRequiredMixin, PermissionRequiredMixin, _PessoaFormMixin, CreateView):
    permission_required = "pessoas.add_pessoa"
    model = Pessoa
    form_class = PessoaForm

    def _salvar(self, form, formsets):
        form.instance.criado_por = self.request.user
        super()._salvar(form, formsets)

    def _sucesso(self):
        messages.success(self.request, f"Pessoa cadastrada: {self.object.nome_exibicao}.")
        return super()._sucesso()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Nova pessoa"
        return ctx


class PessoaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, _PessoaFormMixin, UpdateView):
    permission_required = "pessoas.change_pessoa"
    model = Pessoa
    form_class = PessoaForm
    slug_field = "slug_publico"
    slug_url_kwarg = "slug"

    def _sucesso(self):
        messages.success(self.request, "Pessoa atualizada.")
        return super()._sucesso()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object.nome_exibicao}"
        return ctx


class PessoaToggleAtivoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Desativa ou reativa pessoa. Requer pode_desativar_pessoa ou pode_reativar_pessoa."""

    permission_required = "pessoas.change_pessoa"

    def post(self, request, slug):
        pessoa = get_object_or_404(Pessoa, slug_publico=slug)
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
        return redirect("pessoas:pessoa_detalhe", slug=pessoa.slug_publico)


# --- Vínculos ---


class VinculoCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "pessoas.add_vinculo"

    def post(self, request, slug):
        pessoa = get_object_or_404(Pessoa, slug_publico=slug)
        form = VinculoForm(request.POST, pessoa=pessoa)
        if form.is_valid():
            form.save()
            messages.success(request, "Vínculo adicionado.")
        else:
            for err in form.errors.values():
                messages.error(request, "; ".join(err))
        return redirect("pessoas:pessoa_detalhe", slug=pessoa.slug_publico)


class VinculoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "pessoas.delete_vinculo"

    def post(self, request, pk):
        vinculo = get_object_or_404(Vinculo, pk=pk)
        slug = vinculo.pessoa.slug_publico
        vinculo.delete()
        messages.success(request, "Vínculo removido.")
        return redirect("pessoas:pessoa_detalhe", slug=slug)


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
        return qs

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
    slug_field = "slug_publico"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return super().get_queryset().select_related("criado_por")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["vinculos"] = self.object.vinculos.select_related("pessoa").filter(pessoa__ativo=True)
        u = self.request.user
        ctx["pode_alternar_ativo"] = (
            self.object.ativo and u.has_perm("pessoas.pode_desativar_entidade")
        ) or (not self.object.ativo and u.has_perm("pessoas.pode_reativar_entidade"))
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
        return reverse("pessoas:entidade_detalhe", kwargs={"slug": self.object.slug_publico})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Nova entidade"
        return ctx


class EntidadeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "pessoas.change_entidade"
    model = Entidade
    form_class = EntidadeForm
    template_name = "pessoas/entidades/form.html"
    slug_field = "slug_publico"
    slug_url_kwarg = "slug"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Entidade atualizada.")
        return response

    def get_success_url(self):
        return reverse("pessoas:entidade_detalhe", kwargs={"slug": self.object.slug_publico})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object.nome}"
        return ctx


class EntidadeToggleAtivoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "pessoas.change_entidade"

    def post(self, request, slug):
        entidade = get_object_or_404(Entidade, slug_publico=slug)
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
        return redirect("pessoas:entidade_detalhe", slug=slug)


# --- Tags ---


class TagListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "pessoas.view_tag"
    model = Tag
    template_name = "pessoas/tags/lista.html"
    context_object_name = "tags"

    def get_queryset(self):
        return Tag.objects.all().order_by("-ativo", "nome")


# Paleta de cores nomeadas (referência: Google Calendar) — usada nos forms de Tag.
CORES_PREDEFINIDAS = [
    ("#d50000", "Tomate"),
    ("#e67c73", "Flamingo"),
    ("#f4511e", "Tangerina"),
    ("#f6bf26", "Banana"),
    ("#33b679", "Sálvia"),
    ("#0b8043", "Manjericão"),
    ("#039be5", "Pavão"),
    ("#3f51b5", "Mirtilo"),
    ("#7986cb", "Lavanda"),
    ("#8e24aa", "Uva"),
    ("#616161", "Grafite"),
]


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
        ctx["cores_predefinidas"] = CORES_PREDEFINIDAS
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
        ctx["cores_predefinidas"] = CORES_PREDEFINIDAS
        return ctx


class TagDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "pessoas.delete_tag"
    model = Tag
    success_url = reverse_lazy("pessoas:tag_lista")
    template_name = "pessoas/tags/confirmar_remocao.html"


class TagToggleArquivarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Alterna `ativo` da tag. Tag arquivada some das telas de atribuição/filtro
    mas continua nas pessoas/entidades que já a tinham."""

    permission_required = "pessoas.change_tag"

    def post(self, request, pk):
        tag = get_object_or_404(Tag, pk=pk)
        tag.ativo = not tag.ativo
        tag.save()
        if tag.ativo:
            messages.success(request, f"Tag '{tag.nome}' desarquivada.")
        else:
            messages.success(request, f"Tag '{tag.nome}' arquivada.")
        return redirect("pessoas:tag_lista")


# --- Endpoints auxiliares ---


class CEPLookupView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """GET /pessoas/cep/<cep>/ — retorna dados do ViaCEP em JSON.

    Gated em `view_pessoa` para coerência com o resto do app: quem está
    consultando CEP está dentro do fluxo de cadastro/edição de pessoa.
    """

    permission_required = "pessoas.view_pessoa"

    def get(self, request, cep):
        dados = consultar_cep(cep)
        if dados is None:
            return JsonResponse({"erro": "CEP não encontrado."}, status=404)
        return JsonResponse(dados)


class DeduplicacaoCheckView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """GET /pessoas/deduplicar/?email=&telefone=&rede_social=&exclude=

    Busca match em qualquer um dos 3 canais. Retorna até 5 pessoas similares.
    """

    permission_required = "pessoas.view_pessoa"

    def get(self, request):
        excluir_pk = request.GET.get("exclude") or None
        similares = buscar_similares(
            email=request.GET.get("email", ""),
            telefone=request.GET.get("telefone", ""),
            rede_social=request.GET.get("rede_social", ""),
            excluir_pk=excluir_pk,
        ).prefetch_related("telefones", "emails")[:5]
        dados = []
        for p in similares:
            telefones = list(p.telefones.all())
            emails = list(p.emails.all())
            dados.append(
                {
                    "slug": p.slug_publico,
                    "nome": p.nome_exibicao,
                    "email": emails[0].endereco if emails else "",
                    "telefone": telefones[0].numero_formatado if telefones else "",
                    "url": reverse("pessoas:pessoa_detalhe", kwargs={"slug": p.slug_publico}),
                }
            )
        return JsonResponse({"resultados": dados})
