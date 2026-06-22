"""Models de Pessoas, Entidades, Vínculos e Tags.

Núcleo do sistema. Pessoa é a entidade central; Entidade é qualquer agrupamento
(formal ou informal); Vínculo liga pessoa a entidade com papel; Tag é uma
classificação compartilhada por pessoa, entidade e demanda.

Normalização de campos (CPF/CEP/CNPJ/UF/dígitos) é feita em `pessoas/signals.py`
via `pre_save`. Validação algorítmica usa validators no campo (ver core/utils.py
e core/mixins.py).
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction

from core.mixins import UF_VALIDATOR, AuditavelMixin, EnderecavelMixin
from core.utils import (
    formatar_cpf,
    salvar_com_slug_unico,
    somente_digitos,
    validate_cnpj_tamanho,
    validate_cpf,
)


def _validar_xor_pessoa_entidade(canal):
    """XOR: canal de contato pertence a uma Pessoa OU a uma Entidade, nunca
    ambas (ADR 0057). Usado em clean() de Telefone, EmailContato, RedeSocial
    e Site. Não barra "ambos vazios" — durante validação de inlineformset,
    a FK só é atribuída no save; a CheckConstraint do banco impede que
    registros órfãos sejam efetivamente persistidos."""
    if canal.pessoa_id is not None and canal.entidade_id is not None:
        raise ValidationError(
            "Canal não pode pertencer simultaneamente a uma pessoa e a uma entidade."
        )


_CHECK_DONO_XOR = models.Q(pessoa__isnull=False, entidade__isnull=True) | models.Q(
    pessoa__isnull=True, entidade__isnull=False
)


class Tag(models.Model):
    """Etiqueta livre, compartilhada por pessoa, entidade e demanda. Ver ADR 0039."""

    nome = models.CharField("nome", max_length=50, unique=True)
    cor = models.CharField("cor", max_length=7, blank=True, help_text="Hex #RRGGBB")
    descricao = models.TextField("descrição", blank=True)
    ativo = models.BooleanField("ativa", default=True)
    criado_em = models.DateTimeField("criada em", auto_now_add=True)

    class Meta:
        verbose_name = "tag"
        verbose_name_plural = "tags"
        ordering = ["nome"]
        indexes = [
            models.Index(fields=["ativo"]),
        ]

    def __str__(self):
        return self.nome


class PessoaManager(models.Manager):
    def ativas(self):
        return self.filter(ativo=True)


class Pessoa(EnderecavelMixin, AuditavelMixin, models.Model):
    """Pessoa física que se relaciona com o mandato. Endereço inline."""

    GENERO_MULHER = "mulher"
    GENERO_HOMEM = "homem"
    GENERO_NAO_BINARIO = "nao_binario"
    GENERO_OUTRO = "outro"
    GENERO_PREFERE_NAO_DIZER = "prefere_nao_dizer"
    GENERO_CHOICES = [
        (GENERO_MULHER, "Mulher"),
        (GENERO_HOMEM, "Homem"),
        (GENERO_NAO_BINARIO, "Não-binário"),
        (GENERO_OUTRO, "Outro"),
        (GENERO_PREFERE_NAO_DIZER, "Prefere não dizer"),
    ]

    ORIGEM_MANUAL = "manual"
    ORIGEM_INBOX = "inbox"
    ORIGEM_IMPORTACAO = "importacao"
    ORIGEM_CHOICES = [
        (ORIGEM_MANUAL, "Manual"),
        (ORIGEM_INBOX, "Inbox"),
        (ORIGEM_IMPORTACAO, "Importação"),
    ]

    slug_publico = models.CharField(
        max_length=8,
        unique=True,
        blank=True,
        editable=False,
        help_text="Slug curto (8 chars) para URLs públicas. Gerado automaticamente no save().",
    )

    nome = models.CharField("nome", max_length=100)
    sobrenome = models.CharField("sobrenome", max_length=150)
    nome_social = models.CharField("nome social", max_length=200, blank=True)
    cpf = models.CharField("CPF", max_length=14, blank=True, default="", validators=[validate_cpf])
    data_nascimento = models.DateField("data de nascimento", null=True, blank=True)
    genero = models.CharField(
        "gênero", max_length=30, choices=GENERO_CHOICES, blank=True, default=""
    )

    # Sobrescreve campos do EnderecavelMixin: bairro/cidade obrigatórios; UF default ES.
    bairro = models.CharField("bairro", max_length=100)
    cidade = models.CharField("cidade", max_length=100)
    estado = models.CharField("estado (UF)", max_length=2, default="ES", validators=[UF_VALIDATOR])

    observacoes = models.TextField("observações", blank=True)
    origem_cadastro = models.CharField(
        "origem do cadastro", max_length=20, choices=ORIGEM_CHOICES, default=ORIGEM_MANUAL
    )
    ativo = models.BooleanField("ativo", default=True)
    anonimizado = models.BooleanField("anonimizado", default=False)

    tags = models.ManyToManyField(Tag, related_name="pessoas", blank=True)
    entidades = models.ManyToManyField(
        "Entidade", through="Vinculo", related_name="pessoas", blank=True
    )

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pessoas_criadas",
    )

    objects = PessoaManager()

    class Meta:
        verbose_name = "pessoa"
        verbose_name_plural = "pessoas"
        ordering = ["nome", "sobrenome"]
        permissions = [
            ("pode_desativar_pessoa", "Pode desativar pessoa (soft delete)"),
            ("pode_reativar_pessoa", "Pode reativar pessoa desativada"),
            ("pode_anonimizar_pessoa", "Pode anonimizar pessoa (LGPD)"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["cpf"],
                condition=~models.Q(cpf=""),
                name="pessoa_cpf_unico_quando_preenchido",
            ),
        ]
        indexes = [
            models.Index(fields=["nome", "sobrenome"]),
            models.Index(fields=["bairro"]),
            models.Index(fields=["ativo"]),
        ]

    def __str__(self):
        return self.nome_exibicao

    @property
    def nome_exibicao(self):
        if self.anonimizado:
            return "[Pessoa Removida]"
        if self.nome_social:
            return self.nome_social
        return f"{self.nome} {self.sobrenome}".strip()

    @property
    def cpf_formatado(self):
        return formatar_cpf(self.cpf) if self.cpf else ""

    def tem_meio_de_contato(self):
        """Pelo menos um canal: telefone, email, rede social ou site."""
        if not self.pk:
            return False
        return (
            self.telefones.exists()
            or self.emails.exists()
            or self.redes_sociais.exists()
            or self.sites.exists()
        )

    def save(self, *args, **kwargs):
        return salvar_com_slug_unico(self, super().save, *args, **kwargs)

    @transaction.atomic
    def anonimizar(self):
        """Apaga PII e canais de contato em uma única transação (LGPD)."""
        self.nome = "[Pessoa Removida]"
        self.sobrenome = ""
        self.nome_social = ""
        self.cpf = ""
        self.data_nascimento = None
        self.observacoes = ""
        self.anonimizado = True
        self.ativo = False
        self.save()
        self.telefones.all().delete()
        self.emails.all().delete()
        self.redes_sociais.all().delete()
        self.sites.all().delete()


class EntidadeManager(models.Manager):
    def ativas(self):
        return self.filter(ativo=True)


class Entidade(EnderecavelMixin, AuditavelMixin, models.Model):
    """Pessoa jurídica, coletivo ou agrupamento de qualquer natureza."""

    TIPO_CHOICES = [
        ("associacao_de_moradores", "Associação de moradores"),
        ("sindicato", "Sindicato"),
        ("partido", "Partido"),
        ("escola", "Escola"),
        ("conselho", "Conselho"),
        ("igreja", "Igreja"),
        ("ong", "ONG"),
        ("empresa", "Empresa"),
        ("orgao_publico", "Órgão público"),
        ("coletivo", "Coletivo"),
        ("familia", "Família"),
        ("grupo_informal", "Grupo informal"),
        ("condominio", "Condomínio"),
        ("outros", "Outros"),
    ]

    slug_publico = models.CharField(
        max_length=8,
        unique=True,
        blank=True,
        editable=False,
        help_text="Slug curto (8 chars) para URLs públicas. Gerado automaticamente no save().",
    )

    nome = models.CharField("nome", max_length=200)
    nome_fantasia = models.CharField("nome fantasia", max_length=200, blank=True, default="")
    tipo = models.CharField("tipo", max_length=30, choices=TIPO_CHOICES)
    cnpj = models.CharField(
        "CNPJ", max_length=18, blank=True, default="", validators=[validate_cnpj_tamanho]
    )

    # Canais (telefones, emails, redes_sociais, sites) agora são modelos
    # plurais compartilhados com Pessoa — ver ADR 0057. Os campos simples
    # `email`, `telefone` e `site` foram removidos na migration 0004.

    observacoes = models.TextField("observações", blank=True)
    ativo = models.BooleanField("ativa", default=True)

    tags = models.ManyToManyField(Tag, related_name="entidades", blank=True)

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="entidades_criadas",
    )

    objects = EntidadeManager()

    class Meta:
        verbose_name = "entidade"
        verbose_name_plural = "entidades"
        ordering = ["nome"]
        permissions = [
            ("pode_desativar_entidade", "Pode desativar entidade (soft delete)"),
            ("pode_reativar_entidade", "Pode reativar entidade desativada"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["cnpj"],
                condition=~models.Q(cnpj=""),
                name="entidade_cnpj_unico_quando_preenchido",
            ),
        ]
        indexes = [
            models.Index(fields=["nome"]),
            models.Index(fields=["tipo"]),
            models.Index(fields=["ativo"]),
        ]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        return salvar_com_slug_unico(self, super().save, *args, **kwargs)


class Vinculo(models.Model):
    """Relação Pessoa ↔ Entidade com papel."""

    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name="vinculos")
    entidade = models.ForeignKey(Entidade, on_delete=models.CASCADE, related_name="vinculos")
    papel = models.CharField("papel", max_length=100)
    data_inicio = models.DateField("início", null=True, blank=True)
    data_fim = models.DateField("fim", null=True, blank=True)
    observacao = models.TextField("observação", blank=True)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "vínculo"
        verbose_name_plural = "vínculos"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["pessoa"]),
            models.Index(fields=["entidade"]),
        ]

    def __str__(self):
        return f"{self.pessoa} — {self.papel} em {self.entidade}"

    def clean(self):
        super().clean()
        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({"data_fim": "Fim não pode ser antes do início."})

    @property
    def vigente(self):
        return self.data_fim is None


class Telefone(models.Model):
    """Número de telefone de uma pessoa OU de uma entidade. Tipo distingue
    celular de fixo. Dono dual via FK nullable + XOR no clean (ADR 0057)."""

    TIPO_CELULAR = "celular"
    TIPO_FIXO = "fixo"
    TIPO_CHOICES = [
        (TIPO_CELULAR, "Celular"),
        (TIPO_FIXO, "Fixo"),
    ]

    pessoa = models.ForeignKey(
        Pessoa, on_delete=models.CASCADE, related_name="telefones", null=True, blank=True
    )
    entidade = models.ForeignKey(
        "Entidade", on_delete=models.CASCADE, related_name="telefones", null=True, blank=True
    )
    numero = models.CharField("número", max_length=20)
    tipo = models.CharField("tipo", max_length=10, choices=TIPO_CHOICES, default=TIPO_CELULAR)
    eh_whatsapp = models.BooleanField("é WhatsApp", default=False)
    rotulo = models.CharField(
        "rótulo",
        max_length=50,
        blank=True,
        default="",
        help_text='Opcional. Ex: "trabalho", "recado da mãe".',
    )
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "telefone"
        verbose_name_plural = "telefones"
        ordering = ["-eh_whatsapp", "criado_em"]
        indexes = [
            models.Index(fields=["numero"]),
            models.Index(fields=["pessoa"]),
            models.Index(fields=["entidade"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["pessoa", "numero"],
                name="telefone_unico_por_pessoa",
                condition=models.Q(pessoa__isnull=False),
                violation_error_message="Esta pessoa já tem este número cadastrado.",
            ),
            models.UniqueConstraint(
                fields=["entidade", "numero"],
                name="telefone_unico_por_entidade",
                condition=models.Q(entidade__isnull=False),
                violation_error_message="Esta entidade já tem este número cadastrado.",
            ),
            models.CheckConstraint(
                check=_CHECK_DONO_XOR,
                name="telefone_dono_xor",
                violation_error_message="Telefone precisa pertencer a uma pessoa OU a uma entidade, não ambas.",
            ),
        ]

    def __str__(self):
        return f"{self.numero_formatado} ({self.get_tipo_display()})"

    @property
    def dono(self):
        """Retorna a Pessoa ou Entidade dona do canal — XOR garantido por clean."""
        return self.pessoa or self.entidade

    @property
    def numero_formatado(self):
        n = self.numero or ""
        if len(n) == 11:
            return f"({n[:2]}) {n[2:7]}-{n[7:]}"
        if len(n) == 10:
            return f"({n[:2]}) {n[2:6]}-{n[6:]}"
        return n

    def clean(self):
        super().clean()
        _validar_xor_pessoa_entidade(self)
        digitos = somente_digitos(self.numero)
        if self.tipo == self.TIPO_CELULAR:
            if len(digitos) != 11:
                raise ValidationError(
                    {"numero": "Celular deve ter 11 dígitos: DDD + 9 + 8 dígitos."}
                )
            if digitos[2] != "9":
                raise ValidationError(
                    {"numero": "Celular deve começar com 9 após o DDD (regra Anatel)."}
                )
        elif self.tipo == self.TIPO_FIXO:
            if len(digitos) != 10:
                raise ValidationError(
                    {"numero": "Telefone fixo deve ter 10 dígitos: DDD + 8 dígitos."}
                )
        if self.eh_whatsapp and self.tipo != self.TIPO_CELULAR:
            raise ValidationError(
                {"eh_whatsapp": "WhatsApp só pode ser marcado em telefone celular."}
            )


class EmailContato(models.Model):
    """E-mail de contato — pertence a uma Pessoa OU a uma Entidade (XOR,
    ADR 0057). Renomeado de EmailPessoa para refletir o uso compartilhado."""

    pessoa = models.ForeignKey(
        Pessoa, on_delete=models.CASCADE, related_name="emails", null=True, blank=True
    )
    entidade = models.ForeignKey(
        "Entidade", on_delete=models.CASCADE, related_name="emails", null=True, blank=True
    )
    endereco = models.EmailField("endereço", max_length=254)
    rotulo = models.CharField(
        "rótulo",
        max_length=50,
        blank=True,
        default="",
        help_text='Opcional. Ex: "trabalho", "pessoal".',
    )
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "e-mail"
        verbose_name_plural = "e-mails"
        ordering = ["criado_em"]
        indexes = [
            models.Index(fields=["endereco"]),
            models.Index(fields=["pessoa"]),
            models.Index(fields=["entidade"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["pessoa", "endereco"],
                name="email_unico_por_pessoa",
                condition=models.Q(pessoa__isnull=False),
                violation_error_message="Esta pessoa já tem este e-mail cadastrado.",
            ),
            models.UniqueConstraint(
                fields=["entidade", "endereco"],
                name="email_unico_por_entidade",
                condition=models.Q(entidade__isnull=False),
                violation_error_message="Esta entidade já tem este e-mail cadastrado.",
            ),
            models.CheckConstraint(
                check=_CHECK_DONO_XOR,
                name="email_dono_xor",
                violation_error_message="E-mail precisa pertencer a uma pessoa OU a uma entidade, não ambas.",
            ),
        ]

    def __str__(self):
        return self.endereco

    @property
    def dono(self):
        return self.pessoa or self.entidade

    def clean(self):
        super().clean()
        _validar_xor_pessoa_entidade(self)


class RedeSocial(models.Model):
    """Presença em rede social. Pessoa pode ter várias."""

    PLATAFORMA_INSTAGRAM = "instagram"
    PLATAFORMA_FACEBOOK = "facebook"
    PLATAFORMA_LINKEDIN = "linkedin"
    PLATAFORMA_X_TWITTER = "x_twitter"
    PLATAFORMA_OUTRO = "outro"
    PLATAFORMA_CHOICES = [
        (PLATAFORMA_INSTAGRAM, "Instagram"),
        (PLATAFORMA_FACEBOOK, "Facebook"),
        (PLATAFORMA_LINKEDIN, "LinkedIn"),
        (PLATAFORMA_X_TWITTER, "X (Twitter)"),
        (PLATAFORMA_OUTRO, "Outro"),
    ]

    pessoa = models.ForeignKey(
        Pessoa, on_delete=models.CASCADE, related_name="redes_sociais", null=True, blank=True
    )
    entidade = models.ForeignKey(
        "Entidade", on_delete=models.CASCADE, related_name="redes_sociais", null=True, blank=True
    )
    plataforma = models.CharField("plataforma", max_length=20, choices=PLATAFORMA_CHOICES)
    valor = models.CharField(
        "usuário ou URL",
        max_length=255,
        help_text="@handle ou URL do perfil.",
    )
    rotulo = models.CharField(
        "rótulo",
        max_length=50,
        blank=True,
        default="",
        help_text='Opcional. Especialmente útil quando plataforma="Outro" para indicar qual rede.',
    )
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "rede social"
        verbose_name_plural = "redes sociais"
        ordering = ["plataforma", "criado_em"]
        indexes = [
            models.Index(fields=["plataforma"]),
            models.Index(fields=["pessoa"]),
            models.Index(fields=["entidade"]),
            models.Index(fields=["valor"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["pessoa", "plataforma", "valor"],
                name="rede_social_unica_por_pessoa",
                condition=models.Q(pessoa__isnull=False),
                violation_error_message="Esta pessoa já tem este perfil cadastrado nesta plataforma.",
            ),
            models.UniqueConstraint(
                fields=["entidade", "plataforma", "valor"],
                name="rede_social_unica_por_entidade",
                condition=models.Q(entidade__isnull=False),
                violation_error_message="Esta entidade já tem este perfil cadastrado nesta plataforma.",
            ),
            models.CheckConstraint(
                check=_CHECK_DONO_XOR,
                name="rede_social_dono_xor",
                violation_error_message="Rede social precisa pertencer a uma pessoa OU a uma entidade, não ambas.",
            ),
        ]

    def __str__(self):
        return f"{self.get_plataforma_display()}: {self.valor}"

    @property
    def dono(self):
        return self.pessoa or self.entidade

    def clean(self):
        super().clean()
        _validar_xor_pessoa_entidade(self)
        if self.plataforma == self.PLATAFORMA_OUTRO and not self.rotulo:
            raise ValidationError(
                {"rotulo": 'Quando a plataforma é "Outro", informe o rótulo (qual rede).'}
            )


class Site(models.Model):
    """Site/URL associado a uma pessoa ou a uma entidade (ADR 0057). Entidades
    institucionais costumam ter múltiplos (site principal, página de projeto,
    blog, canal de doação). Pessoa raramente mas pode ter (portfólio, blog)."""

    pessoa = models.ForeignKey(
        Pessoa, on_delete=models.CASCADE, related_name="sites", null=True, blank=True
    )
    entidade = models.ForeignKey(
        "Entidade", on_delete=models.CASCADE, related_name="sites", null=True, blank=True
    )
    url = models.URLField("URL", max_length=500)
    rotulo = models.CharField(
        "rótulo",
        max_length=50,
        blank=True,
        default="",
        help_text='Opcional. Ex: "institucional", "projeto X", "blog".',
    )
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "site"
        verbose_name_plural = "sites"
        ordering = ["criado_em"]
        indexes = [
            models.Index(fields=["pessoa"]),
            models.Index(fields=["entidade"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["pessoa", "url"],
                name="site_unico_por_pessoa",
                condition=models.Q(pessoa__isnull=False),
                violation_error_message="Esta pessoa já tem este site cadastrado.",
            ),
            models.UniqueConstraint(
                fields=["entidade", "url"],
                name="site_unico_por_entidade",
                condition=models.Q(entidade__isnull=False),
                violation_error_message="Esta entidade já tem este site cadastrado.",
            ),
            models.CheckConstraint(
                check=_CHECK_DONO_XOR,
                name="site_dono_xor",
                violation_error_message="Site precisa pertencer a uma pessoa OU a uma entidade, não ambas.",
            ),
        ]

    def __str__(self):
        return f"{self.rotulo + ': ' if self.rotulo else ''}{self.url}"

    @property
    def dono(self):
        return self.pessoa or self.entidade

    def clean(self):
        super().clean()
        _validar_xor_pessoa_entidade(self)
