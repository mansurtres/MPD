from django.contrib import admin

from .models import EmailContato, Entidade, Pessoa, RedeSocial, Site, Tag, Telefone, Vinculo


class VinculoInline(admin.TabularInline):
    model = Vinculo
    extra = 0
    autocomplete_fields = ["entidade"]


class TelefonePessoaInline(admin.TabularInline):
    model = Telefone
    fk_name = "pessoa"
    extra = 0
    fields = ("numero", "tipo", "eh_whatsapp", "rotulo")


class EmailPessoaInline(admin.TabularInline):
    model = EmailContato
    fk_name = "pessoa"
    extra = 0
    fields = ("endereco", "rotulo")


class RedeSocialPessoaInline(admin.TabularInline):
    model = RedeSocial
    fk_name = "pessoa"
    extra = 0
    fields = ("plataforma", "valor", "rotulo")


class SitePessoaInline(admin.TabularInline):
    model = Site
    fk_name = "pessoa"
    extra = 0
    fields = ("url", "rotulo")


class TelefoneEntidadeInline(admin.TabularInline):
    model = Telefone
    fk_name = "entidade"
    extra = 0
    fields = ("numero", "tipo", "eh_whatsapp", "rotulo")


class EmailEntidadeInline(admin.TabularInline):
    model = EmailContato
    fk_name = "entidade"
    extra = 0
    fields = ("endereco", "rotulo")


class RedeSocialEntidadeInline(admin.TabularInline):
    model = RedeSocial
    fk_name = "entidade"
    extra = 0
    fields = ("plataforma", "valor", "rotulo")


class SiteEntidadeInline(admin.TabularInline):
    model = Site
    fk_name = "entidade"
    extra = 0
    fields = ("url", "rotulo")


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
    inlines = [
        TelefonePessoaInline,
        EmailPessoaInline,
        RedeSocialPessoaInline,
        SitePessoaInline,
        VinculoInline,
    ]
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
    search_fields = ("nome", "nome_fantasia", "cnpj", "emails__endereco", "telefones__numero")
    readonly_fields = ("criado_em", "atualizado_em", "criado_por")
    filter_horizontal = ("tags",)
    inlines = [
        TelefoneEntidadeInline,
        EmailEntidadeInline,
        RedeSocialEntidadeInline,
        SiteEntidadeInline,
    ]
    fieldsets = (
        ("Identificação", {"fields": ("nome", "nome_fantasia", "tipo", "cnpj")}),
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
    list_display = ("numero_formatado", "tipo", "eh_whatsapp", "dono", "rotulo")
    list_filter = ("tipo", "eh_whatsapp")
    search_fields = ("numero", "pessoa__nome", "pessoa__sobrenome", "entidade__nome")
    autocomplete_fields = ("pessoa", "entidade")
    readonly_fields = ("criado_em",)


@admin.register(EmailContato)
class EmailContatoAdmin(admin.ModelAdmin):
    list_display = ("endereco", "dono", "rotulo")
    search_fields = ("endereco", "pessoa__nome", "pessoa__sobrenome", "entidade__nome")
    autocomplete_fields = ("pessoa", "entidade")
    readonly_fields = ("criado_em",)


@admin.register(RedeSocial)
class RedeSocialAdmin(admin.ModelAdmin):
    list_display = ("plataforma", "valor", "dono", "rotulo")
    list_filter = ("plataforma",)
    search_fields = ("valor", "rotulo", "pessoa__nome", "pessoa__sobrenome", "entidade__nome")
    autocomplete_fields = ("pessoa", "entidade")
    readonly_fields = ("criado_em",)


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("url", "dono", "rotulo")
    search_fields = ("url", "rotulo", "pessoa__nome", "pessoa__sobrenome", "entidade__nome")
    autocomplete_fields = ("pessoa", "entidade")
    readonly_fields = ("criado_em",)
