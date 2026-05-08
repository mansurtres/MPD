from django.contrib import admin

from .models import Entidade, Pessoa, Tag, Vinculo


class VinculoInline(admin.TabularInline):
    model = Vinculo
    extra = 0
    autocomplete_fields = ["entidade"]


@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    list_display = (
        "nome_exibicao",
        "email",
        "telefone",
        "whatsapp",
        "bairro",
        "cidade",
        "ativo",
    )
    list_filter = ("ativo", "anonimizado", "estado", "cidade", "bairro", "genero")
    search_fields = ("nome", "sobrenome", "nome_social", "email", "cpf", "telefone", "whatsapp")
    readonly_fields = ("criado_em", "atualizado_em", "criado_por")
    filter_horizontal = ("tags",)
    inlines = [VinculoInline]
    fieldsets = (
        (
            "Identificação",
            {"fields": ("nome", "sobrenome", "nome_social", "cpf", "data_nascimento", "genero")},
        ),
        ("Contato", {"fields": ("email", "telefone", "whatsapp", "instagram")}),
        (
            "Endereço",
            {
                "fields": (
                    "cep",
                    "logradouro",
                    "numero",
                    "complemento",
                    "bairro",
                    "cidade",
                    "estado",
                )
            },
        ),
        (
            "Preferências de comunicação (LGPD)",
            {
                "fields": (
                    "nao_telefonar",
                    "nao_enviar_email",
                    "nao_enviar_sms",
                    "nao_compartilhar_dados",
                )
            },
        ),
        ("Classificação", {"fields": ("tags", "observacoes")}),
        (
            "Status e auditoria",
            {
                "fields": (
                    "origem_cadastro",
                    "ativo",
                    "anonimizado",
                    "criado_por",
                    "criado_em",
                    "atualizado_em",
                )
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Entidade)
class EntidadeAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "cnpj", "cidade", "ativo")
    list_filter = ("ativo", "tipo", "estado", "cidade")
    search_fields = ("nome", "nome_fantasia", "cnpj", "email", "telefone")
    readonly_fields = ("criado_em", "atualizado_em", "criado_por")
    filter_horizontal = ("tags",)
    fieldsets = (
        ("Identificação", {"fields": ("nome", "nome_fantasia", "tipo", "cnpj")}),
        ("Contato", {"fields": ("email", "telefone", "site")}),
        (
            "Endereço",
            {
                "fields": (
                    "cep",
                    "logradouro",
                    "numero",
                    "complemento",
                    "bairro",
                    "cidade",
                    "estado",
                )
            },
        ),
        ("Classificação", {"fields": ("tags", "observacoes")}),
        (
            "Status e auditoria",
            {"fields": ("ativo", "criado_por", "criado_em", "atualizado_em")},
        ),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "cor", "ativo")
    list_filter = ("categoria", "ativo")
    search_fields = ("nome", "descricao")
    readonly_fields = ("criado_em",)


@admin.register(Vinculo)
class VinculoAdmin(admin.ModelAdmin):
    list_display = ("pessoa", "entidade", "papel", "data_inicio", "data_fim")
    list_filter = ("entidade__tipo",)
    search_fields = ("pessoa__nome", "pessoa__sobrenome", "entidade__nome", "papel")
    autocomplete_fields = ("pessoa", "entidade")
    readonly_fields = ("criado_em",)
