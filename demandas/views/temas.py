"""Views de Tema: CRUD, criação AJAX e toggle arquivar."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View

from ..forms import TemaForm
from ..models import Tema

# Paleta de 11 cores fixas — mesma de pessoas.Tag para consistência visual.
_CORES_TEMA = [
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


class TemaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "demandas.view_tema"
    model = Tema
    template_name = "demandas/temas/lista.html"
    context_object_name = "temas"

    def get_queryset(self):
        return Tema.objects.all().order_by("-ativo", "nome")


class TemaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "demandas.add_tema"
    model = Tema
    form_class = TemaForm
    template_name = "demandas/temas/form.html"

    def get_success_url(self):
        return reverse("demandas:tema_lista")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Novo tema"
        ctx["cores_predefinidas"] = _CORES_TEMA
        return ctx


class TemaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "demandas.change_tema"
    model = Tema
    form_class = TemaForm
    template_name = "demandas/temas/form.html"

    def get_success_url(self):
        return reverse("demandas:tema_lista")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar — {self.object.nome}"
        ctx["cores_predefinidas"] = _CORES_TEMA
        return ctx


class TemaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Hard delete de Tema. Bloqueia se houver demanda vinculada — auditlog
    não registra mudança em M:N quando o tema some, então perderia trilha
    histórica silenciosamente. Caminho seguro: arquivar."""

    permission_required = "demandas.delete_tema"
    model = Tema
    success_url = reverse_lazy("demandas:tema_lista")
    template_name = "demandas/temas/confirmar_remocao.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["em_uso"] = self.object.demandas.count()
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        em_uso = self.object.demandas.count()
        if em_uso:
            messages.error(
                request,
                f"'{self.object.nome}' está em {em_uso} demanda(s). Arquive em vez de remover — mantém a classificação histórica.",
            )
            return redirect("demandas:tema_editar", pk=self.object.pk)
        return super().post(request, *args, **kwargs)


class TemaCreateAjaxView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Cria Tema via AJAX (chamado do popup no form de Demanda). Permissão
    demandas.add_tema. Retorna JSON com id, nome, cor para o JS adicionar
    o checkbox dinâmico já marcado."""

    permission_required = "demandas.add_tema"

    def post(self, request):
        nome = (request.POST.get("nome") or "").strip()
        cor = (request.POST.get("cor") or "").strip()
        if not nome:
            return JsonResponse({"erro": "Nome é obrigatório."}, status=400)
        if Tema.objects.filter(nome__iexact=nome).exists():
            return JsonResponse({"erro": f"Já existe um tema com o nome '{nome}'."}, status=400)
        tema = Tema.objects.create(nome=nome, cor=cor)
        return JsonResponse({"id": tema.pk, "nome": tema.nome, "cor": tema.cor or ""}, status=201)


class TemaToggleArquivarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Arquiva/desarquiva tema. FK para Demanda preserva temas arquivados em
    demandas que já os tinham, mas não aparecem em novos formulários."""

    permission_required = "demandas.change_tema"

    def post(self, request, pk):
        tema = get_object_or_404(Tema, pk=pk)
        tema.ativo = not tema.ativo
        tema.save()
        messages.success(
            request, f"Tema '{tema.nome}' {'reativado' if tema.ativo else 'arquivado'}."
        )
        return redirect("demandas:tema_lista")
