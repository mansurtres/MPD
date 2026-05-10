from django.contrib import admin

from .models import EmailPessoa, Entidade, Pessoa, RedeSocial, Tag, Telefone, Vinculo


class VinculoInline(admin.TabularInline):
    model = Vinculo
    extra = 0
    autocomplete_fields = ["entidade"]


class TelefoneInline(admin.TabularInline):
    model = Telefone
    extra = 0
    fields = ("numero", "tipo", "eh_whatsapp", "rotulo")


class EmailInline(admin.TabularInline):
    model = EmailPessoa
    extra = 0
    fields = ("endereco", "rotulo")


class RedeSocialInline(admin.TabularInline):
    model = RedeSocial
    extra = 0
    fields = ("plataforma", "valor", "rotulo")


@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    list_display = (
        "nome_exibicao",
        "principal_email_admin",
        "principal_telefone_admin",
        "bairro",
        "cidade",
        "ativo",
    )
    list_filter = ("ativo", "anonimizado", "estado", "cidade", "bairro", "genero")
    search_fields = (
        "nome",
        "sobrenome",
        "nome_social",
        "cpf",
        "telefones__numero",
        "emails__endereco",
        "redes_sociais__valor",
    )
    readonly_fields = ("criado_em", "atualizado_em", "criado_por")
    filter_horizontal = ("tags",)
    inlines = [TelefoneInline, EmailInline, RedeSocialInline, VinculoInline]
    fieldsets = (
        (
            "Identificação",
            {"fields": ("nome", "sobrenome", "nome_social", "cpf", "data_nascimento", "genero")},
        ),
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

    @admin.display(description="e-mail")
    def principal_email_admin(self, obj):
        e = obj.emails.first()
        return e.endereco if e else "—"

    @admin.display(description="telefone")
    def principal_telefone_admin(self, obj):
        tel = obj.telefones.first()
        return tel.numero_formatado if tel else "—"

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
    list_display = ("nome", "cor", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome", "descricao")
    readonly_fields = ("criado_em",)


@admin.register(Vinculo)
class VinculoAdmin(admin.ModelAdmin):
    list_display = ("pessoa", "entidade", "papel", "data_inicio", "data_fim")
    list_filter = ("entidade__tipo",)
    search_fields = ("pessoa__nome", "pessoa__sobrenome", "entidade__nome", "papel")
    autocomplete_fields = ("pessoa", "entidade")
    readonly_fields = ("criado_em",)


@admin.register(Telefone)
class TelefoneAdmin(admin.ModelAdmin):
    list_display = ("numero_formatado", "tipo", "eh_whatsapp", "pessoa", "rotulo")
    list_filter = ("tipo", "eh_whatsapp")
    search_fields = ("numero", "pessoa__nome", "pessoa__sobrenome")
    autocomplete_fields = ("pessoa",)
    readonly_fields = ("criado_em",)


@admin.register(EmailPessoa)
class EmailPessoaAdmin(admin.ModelAdmin):
    list_display = ("endereco", "pessoa", "rotulo")
    search_fields = ("endereco", "pessoa__nome", "pessoa__sobrenome")
    autocomplete_fields = ("pessoa",)
    readonly_fields = ("criado_em",)


@admin.register(RedeSocial)
class RedeSocialAdmin(admin.ModelAdmin):
    list_display = ("plataforma", "valor", "pessoa", "rotulo")
    list_filter = ("plataforma",)
    search_fields = ("valor", "rotulo", "pessoa__nome", "pessoa__sobrenome")
    autocomplete_fields = ("pessoa",)
    readonly_fields = ("criado_em",)
