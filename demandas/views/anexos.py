"""Views de Anexo polimórfico: upload, download, remoção."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View

from core.permissoes import eh_co_plus

from ..forms import AnexoForm
from ..models import Anexo, Demanda, Encaminhamento, Interacao

# Mapeamento tipo-URL → (app_label, model_name) para lookup de ContentType.
_TIPO_PARA_MODEL = {
    "demanda": ("demandas", "demanda"),
    "pessoa": ("pessoas", "pessoa"),
    "entidade": ("pessoas", "entidade"),
    "encaminhamento": ("demandas", "encaminhamento"),
    "interacao": ("demandas", "interacao"),
}


class AnexoUploadView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Upload polimórfico — recebe (tipo, object_id) e cria Anexo."""

    permission_required = "demandas.add_anexo"

    def get(self, request, tipo, object_id):
        # GET nessa URL não tem semântica útil — acontece quando o usuário
        # recarrega a aba após o POST. Em vez de devolver 405, manda de volta
        # pra página do objeto pai. Demanda e Encaminhamento são os casos
        # primários (UI atual); outros tipos caem no referer ou na raiz.
        if tipo == "demanda":
            slug = get_object_or_404(
                Demanda.objects.values_list("slug_publico", flat=True), pk=object_id
            )
            return redirect("demandas:demanda_detalhe", slug=slug)
        if tipo == "encaminhamento":
            enc = get_object_or_404(Encaminhamento, pk=object_id)
            return redirect("demandas:demanda_detalhe", slug=enc.demanda.slug_publico)
        if tipo == "interacao":
            interacao = get_object_or_404(Interacao, pk=object_id)
            return redirect("demandas:demanda_detalhe", slug=interacao.demanda.slug_publico)
        return redirect(request.META.get("HTTP_REFERER", "/"))

    def post(self, request, tipo, object_id):
        if tipo not in _TIPO_PARA_MODEL:
            raise Http404("Tipo de objeto pai inválido.")
        app_label, model_name = _TIPO_PARA_MODEL[tipo]
        try:
            ct = ContentType.objects.get(app_label=app_label, model=model_name)
        except ContentType.DoesNotExist as exc:
            raise Http404("Tipo desconhecido.") from exc
        objeto_pai = get_object_or_404(ct.model_class(), pk=object_id)
        if isinstance(objeto_pai, Demanda) and not objeto_pai.pode_ser_visto_por(request.user):
            raise Http404
        if isinstance(objeto_pai, Encaminhamento) and not objeto_pai.demanda.pode_ser_visto_por(
            request.user
        ):
            raise Http404
        form = AnexoForm(request.POST, request.FILES)
        if not form.is_valid():
            for erros in form.errors.values():
                messages.error(request, "; ".join(erros))
            return redirect(request.META.get("HTTP_REFERER", "/"))
        arquivo = form.cleaned_data["arquivo"]
        anexo = Anexo(
            content_type=ct,
            object_id=objeto_pai.pk,
            arquivo=arquivo,
            nome_original=arquivo.name,
            tamanho_bytes=arquivo.size,
            mime_type=getattr(arquivo, "content_type", "") or "application/octet-stream",
            descricao=form.cleaned_data.get("descricao", ""),
            enviado_por=request.user,
        )
        try:
            anexo.full_clean()
        except ValidationError as e:
            for erro in e.messages:
                messages.error(request, erro)
            return redirect(request.META.get("HTTP_REFERER", "/"))
        anexo.save()
        messages.success(request, f"Anexo '{anexo.nome_original}' adicionado.")
        return redirect(request.META.get("HTTP_REFERER", "/"))


class AnexoDownloadView(LoginRequiredMixin, View):
    """Serve o arquivo de um Anexo com defesas anti-XSS (ADR 0056).

    Defesas:
    - `Content-Disposition: attachment` — força o browser a BAIXAR em vez
      de tentar executar/exibir inline. Um .html malicioso vira download
      de arquivo, não código rodando na origem do MPD.
    - `X-Content-Type-Options: nosniff` — impede o browser de "adivinhar"
      um content-type executável diferente do declarado.
    - `Content-Security-Policy: default-src 'none'` — caso o browser
      ignore os outros headers, ainda bloqueia execução de scripts/iframes
      a partir do arquivo servido.

    Permissão: precisa poder ver o objeto pai (Demanda respeita
    visibilidade restrita; Encaminhamento herda da demanda; Pessoa/Entidade
    exigem `view_pessoa`/`view_entidade`).
    """

    def get(self, request, pk):
        anexo = get_object_or_404(Anexo, pk=pk)
        objeto_pai = anexo.objeto_pai
        if objeto_pai is None:
            raise Http404

        if isinstance(objeto_pai, Demanda):
            if not objeto_pai.pode_ser_visto_por(request.user):
                raise Http404
        elif isinstance(objeto_pai, Encaminhamento):
            if not objeto_pai.demanda.pode_ser_visto_por(request.user):
                raise Http404
        elif isinstance(objeto_pai, Interacao):
            if not objeto_pai.demanda.pode_ser_visto_por(request.user):
                raise Http404
        else:
            # Pessoa, Entidade — basta a permissão de view do app
            from pessoas.models import Entidade as _Ent
            from pessoas.models import Pessoa as _Pes

            if isinstance(objeto_pai, _Pes) and not request.user.has_perm("pessoas.view_pessoa"):
                raise PermissionDenied
            if isinstance(objeto_pai, _Ent) and not request.user.has_perm("pessoas.view_entidade"):
                raise PermissionDenied

        resp = FileResponse(
            anexo.arquivo.open("rb"),
            as_attachment=True,
            filename=anexo.nome_original,
        )
        # Headers de segurança (defesa em profundidade).
        resp["X-Content-Type-Options"] = "nosniff"
        resp["Content-Security-Policy"] = "default-src 'none'"
        return resp


class AnexoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "demandas.delete_anexo"

    def post(self, request, pk):
        anexo = get_object_or_404(Anexo, pk=pk)
        if anexo.enviado_por_id != request.user.id and not eh_co_plus(request.user):
            raise PermissionDenied("Sem permissão para excluir este anexo.")
        referer = request.META.get("HTTP_REFERER", "/")
        anexo.arquivo.delete(save=False)
        anexo.delete()
        messages.success(request, "Anexo removido.")
        return redirect(referer)
