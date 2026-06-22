"""Helpers e mixins compartilhados entre os módulos de views do app demandas."""

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect

from core.permissoes import eh_admin

from ..forms import DemandaEntidadeFormSet, DemandaForm, DemandaPessoaFormSet
from ..models import Anexo


def _pode_exportar(user):
    """Exportação é exclusiva do Administrador (need-to-know, ADR 0059)."""
    return eh_admin(user)


def _anexar_se_houver(request, objeto_pai):
    """Cria Anexo(s) vinculados a `objeto_pai` se o request trouxer arquivos
    no campo `anexo` (múltiplos suportados via <input multiple>). Usado pelas
    views de criar interação/encaminhamento para permitir upload na mesma
    transação. Silencioso: lista vazia é OK (campo opcional). Se algum
    arquivo exceder o limite, levanta ValueError — a transação inteira faz
    rollback (nenhum anexo é salvo, nem o objeto pai)."""
    arquivos = request.FILES.getlist("anexo")
    if not arquivos:
        return
    ct = ContentType.objects.get_for_model(type(objeto_pai))
    for arquivo in arquivos:
        if arquivo.size > Anexo.TAMANHO_MAXIMO_BYTES:
            messages.error(
                request,
                f"Arquivo '{arquivo.name}' excede o limite de "
                f"{Anexo.TAMANHO_MAXIMO_BYTES // (1024*1024)} MB.",
            )
            raise ValueError("anexo excede limite")
        Anexo.objects.create(
            content_type=ct,
            object_id=objeto_pai.pk,
            arquivo=arquivo,
            nome_original=arquivo.name,
            tamanho_bytes=arquivo.size,
            mime_type=getattr(arquivo, "content_type", "") or "application/octet-stream",
            enviado_por=request.user,
        )


class _DemandaFormMixin:
    """Coordena DemandaForm + dois formsets (pessoas, entidades) com a regra
    'demanda não-anônima exige ao menos uma parte'."""

    template_name = "demandas/form.html"
    form_class = DemandaForm

    def _build_formsets(self, post_data=None):
        instance = self.object if hasattr(self, "object") else None
        return {
            "pessoas": DemandaPessoaFormSet(post_data, instance=instance, prefix="dp"),
            "entidades": DemandaEntidadeFormSet(post_data, instance=instance, prefix="de"),
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if "formsets" not in ctx:
            ctx["formsets"] = self._build_formsets()
        return ctx

    def post(self, request, *args, **kwargs):
        eh_update = bool(self.kwargs.get("pk"))
        self.object = self.get_object() if eh_update else None
        for prefix in ("dp", "de"):
            if f"{prefix}-TOTAL_FORMS" not in request.POST:
                messages.warning(
                    request, "A página estava desatualizada. Recarregue e preencha novamente."
                )
                return redirect(request.path)
        form = self.get_form()
        formsets = self._build_formsets(request.POST)
        if not (form.is_valid() and all(fs.is_valid() for fs in formsets.values())):
            return self.form_invalid(form, formsets)

        try:
            with transaction.atomic():
                self._salvar(form, formsets)
                if not self.object.anonimo and not self.object.tem_partes():
                    form.add_error(
                        None,
                        "Demanda não-anônima exige ao menos uma parte (pessoa ou entidade).",
                    )
                    transaction.set_rollback(True)
                    return self.form_invalid(form, formsets)
        except ValidationError:
            # Erros já estão em form.errors (adicionados em _salvar). Atomic
            # fez rollback ao propagar a exceção; agora renderizamos o form
            # de volta com as mensagens.
            return self.form_invalid(form, formsets)

        return self._sucesso()

    def _salvar(self, form, formsets):
        self.object = form.save()
        for fs in formsets.values():
            fs.instance = self.object
            fs.save()

    def _sucesso(self):
        return redirect("demandas:demanda_detalhe", slug=self.object.slug_publico)

    def form_invalid(self, form, formsets):
        return self.render_to_response(self.get_context_data(form=form, formsets=formsets))
