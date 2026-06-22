from django.contrib import admin

from .models import (
    Anexo,
    Demanda,
    DemandaEntidade,
    DemandaPessoa,
    Encaminhamento,
    Interacao,
    ItemInbox,
    Tema,
)


class DemandaPessoaInline(admin.TabularInline):
    model = DemandaPessoa
    extra = 0
    autocomplete_fields = ["pessoa"]


class DemandaEntidadeInline(admin.TabularInline):
    model = DemandaEntidade
    extra = 0
    autocomplete_fields = ["entidade"]


@admin.register(Demanda)
class DemandaAdmin(admin.ModelAdmin):
    list_display = [
        "numero",
        "titulo",
        "status",
        "resultado",
        "responsavel",
        "criado_em",
    ]
    list_filter = ["status", "resultado", "origem"]
    search_fields = ["numero", "titulo", "descricao"]
    readonly_fields = ["numero", "criado_em", "atualizado_em", "arquivado_em"]
    autocomplete_fields = ["responsavel", "criado_por"]
    filter_horizontal = ["temas"]
    inlines = [DemandaPessoaInline, DemandaEntidadeInline]

    fieldsets = (
        ("Identificação", {"fields": ("numero", "titulo", "descricao")}),
        ("Origem", {"fields": ("origem", "canal_entrada", "anonimo")}),
        ("Estado", {"fields": ("status", "resultado", "resultado_observacao", "prioridade")}),
        (
            "Atribuição",
            {"fields": ("responsavel", "prazo")},
        ),
        (
            "Arquivamento",
            {"fields": ("observacoes_arquivamento", "arquivado_em"), "classes": ("collapse",)},
        ),
        ("Metadados", {"fields": ("criado_por", "criado_em", "atualizado_em", "temas")}),
    )


@admin.register(Interacao)
class InteracaoAdmin(admin.ModelAdmin):
    list_display = ["data_ocorrencia", "tipo", "status", "demanda", "autor", "automatica"]
    list_filter = ["tipo", "status", "automatica"]
    search_fields = ["conteudo", "demanda__numero", "demanda__titulo"]
    autocomplete_fields = ["demanda", "autor", "interacao_origem"]
    readonly_fields = ["criado_em", "atualizado_em"]


@admin.register(Encaminhamento)
class EncaminhamentoAdmin(admin.ModelAdmin):
    list_display = [
        "destinatario_orgao",
        "tipo_documento",
        "data_envio",
        "prazo_resposta",
        "status",
        "demanda",
    ]
    list_filter = ["tipo_documento", "status"]
    search_fields = ["destinatario_orgao", "destinatario_pessoa", "numero_documento"]
    autocomplete_fields = ["demanda", "criado_por"]
    readonly_fields = ["criado_em"]


@admin.register(Anexo)
class AnexoAdmin(admin.ModelAdmin):
    list_display = ["nome_original", "content_type", "tamanho_bytes", "enviado_por", "enviado_em"]
    list_filter = ["content_type", "mime_type"]
    search_fields = ["nome_original", "descricao"]
    readonly_fields = ["enviado_em", "tamanho_bytes", "mime_type"]


@admin.register(Tema)
class TemaAdmin(admin.ModelAdmin):
    list_display = ["nome", "cor", "ativo", "criado_em"]
    list_filter = ["ativo"]
    search_fields = ["nome", "descricao"]
    readonly_fields = ["criado_em"]


@admin.register(ItemInbox)
class ItemInboxAdmin(admin.ModelAdmin):
    list_display = ["conteudo", "autor", "status", "criado_em"]
    list_filter = ["status"]
    search_fields = ["conteudo"]
    autocomplete_fields = ["autor", "demanda_gerada", "processado_por"]
    readonly_fields = ["criado_em", "processado_em"]
