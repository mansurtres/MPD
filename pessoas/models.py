"""Models de Pessoas, Entidades, Vínculos e Tags.

Núcleo do sistema. Pessoa é a entidade central; Entidade é qualquer agrupamento
(formal ou informal); Vínculo liga pessoa a entidade com papel; Tag é uma
classificação compartilhada por pessoa, entidade e demanda.
"""

import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def normalize_phone(value):
    """Mantém apenas dígitos. Retorna string vazia se vazio/None."""
    if not value:
        return ""
    return re.sub(r"\D", "", value)


def validate_cpf(value):
    """Valida CPF pelo algoritmo. Aceita com ou sem pontuação."""
    if not value:
        return
    digits = re.sub(r"\D", "", value)
    if len(digits) != 11 or digits == digits[0] * 11:
        raise ValidationError("CPF inválido.")
    for i in (9, 10):
        s = sum(int(digits[j]) * ((i + 1) - j) for j in range(i))
        d = (s * 10) % 11
        if d == 10:
            d = 0
        if d != int(digits[i]):
            raise ValidationError("CPF inválido.")


def format_cpf(value):
    """Formata CPF: 11 dígitos -> XXX.XXX.XXX-XX. Retorna como veio se inválido."""
    digits = re.sub(r"\D", "", value or "")
    if len(digits) != 11:
        return value or ""
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


class Tag(models.Model):
    """Classificação compartilhada por pessoa, entidade e demanda."""

    CATEGORIA_TEMA = "tema"
    CATEGORIA_PERFIL = "perfil"
    CATEGORIA_TERRITORIO = "territorio"
    CATEGORIA_LIVRE = "livre"
    CATEGORIA_CHOICES = [
        (CATEGORIA_TEMA, "Tema"),
        (CATEGORIA_PERFIL, "Perfil"),
        (CATEGORIA_TERRITORIO, "Território"),
        (CATEGORIA_LIVRE, "Livre"),
    ]

    nome = models.CharField("nome", max_length=50, unique=True)
    categoria = models.CharField(
        "categoria", max_length=15, choices=CATEGORIA_CHOICES, default=CATEGORIA_LIVRE
    )
    cor = models.CharField("cor", max_length=7, blank=True, help_text="Hex #RRGGBB")
    descricao = models.TextField("descrição", blank=True)
    ativo = models.BooleanField("ativa", default=True)
    criado_em = models.DateTimeField("criada em", auto_now_add=True)

    class Meta:
        verbose_name = "tag"
        verbose_name_plural = "tags"
        ordering = ["categoria", "nome"]
        indexes = [
            models.Index(fields=["categoria"]),
            models.Index(fields=["ativo"]),
        ]

    def __str__(self):
        return self.nome


class PessoaManager(models.Manager):
    def ativas(self):
        return self.filter(ativo=True)


class Pessoa(models.Model):
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

    nome = models.CharField("nome", max_length=100)
    sobrenome = models.CharField("sobrenome", max_length=150)
    nome_social = models.CharField("nome social", max_length=200, blank=True)
    cpf = models.CharField("CPF", max_length=14, blank=True, default="")
    data_nascimento = models.DateField("data de nascimento", null=True, blank=True)
    genero = models.CharField(
        "gênero", max_length=30, choices=GENERO_CHOICES, blank=True, default=""
    )

    email = models.EmailField("e-mail", max_length=254, blank=True, default="")
    telefone = models.CharField("telefone", max_length=20, blank=True, default="")
    whatsapp = models.CharField("WhatsApp", max_length=20, blank=True, default="")
    instagram = models.CharField(
        "Instagram", max_length=50, blank=True, default="", help_text="Sem o @"
    )

    cep = models.CharField("CEP", max_length=9, blank=True, default="")
    logradouro = models.CharField("logradouro", max_length=200, blank=True, default="")
    numero = models.CharField("número", max_length=20, blank=True, default="")
    complemento = models.CharField("complemento", max_length=100, blank=True, default="")
    bairro = models.CharField("bairro", max_length=100)
    cidade = models.CharField("cidade", max_length=100)
    estado = models.CharField("estado (UF)", max_length=2, default="ES")

    nao_telefonar = models.BooleanField("não telefonar", default=False)
    nao_enviar_email = models.BooleanField("não enviar e-mail em massa", default=False)
    nao_enviar_sms = models.BooleanField("não enviar SMS/WhatsApp em massa", default=False)
    nao_compartilhar_dados = models.BooleanField(
        "não compartilhar dados com terceiros", default=False
    )

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
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

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
            models.Index(fields=["email"]),
            models.Index(fields=["telefone"]),
            models.Index(fields=["whatsapp"]),
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
        return format_cpf(self.cpf) if self.cpf else ""

    def clean(self):
        super().clean()
        if not (self.email or self.telefone or self.whatsapp):
            raise ValidationError(
                "Preencha pelo menos um meio de contato: e-mail, telefone ou WhatsApp."
            )
        if self.cpf:
            validate_cpf(self.cpf)
        if self.cep:
            cep = re.sub(r"\D", "", self.cep)
            if len(cep) != 8:
                raise ValidationError({"cep": "CEP deve ter 8 dígitos."})
        if self.estado and len(self.estado) != 2:
            raise ValidationError({"estado": "Use a sigla de 2 letras (ex: ES)."})

    def save(self, *args, **kwargs):
        self.telefone = normalize_phone(self.telefone)
        self.whatsapp = normalize_phone(self.whatsapp)
        if self.cpf:
            self.cpf = format_cpf(self.cpf)
        if self.cep:
            cep = re.sub(r"\D", "", self.cep)
            if len(cep) == 8:
                self.cep = f"{cep[:5]}-{cep[5:]}"
        if self.estado:
            self.estado = self.estado.upper()
        if self.instagram:
            self.instagram = self.instagram.lstrip("@").strip()
        super().save(*args, **kwargs)

    def anonimizar(self):
        self.nome = "[Pessoa Removida]"
        self.sobrenome = ""
        self.nome_social = ""
        self.email = ""
        self.telefone = ""
        self.whatsapp = ""
        self.instagram = ""
        self.cpf = ""
        self.data_nascimento = None
        self.observacoes = ""
        self.anonimizado = True
        self.ativo = False
        self.save()


class EntidadeManager(models.Manager):
    def ativas(self):
        return self.filter(ativo=True)


class Entidade(models.Model):
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

    nome = models.CharField("nome", max_length=200)
    nome_fantasia = models.CharField("nome fantasia", max_length=200, blank=True, default="")
    tipo = models.CharField("tipo", max_length=30, choices=TIPO_CHOICES)
    cnpj = models.CharField("CNPJ", max_length=18, blank=True, default="")

    email = models.EmailField("e-mail", max_length=254, blank=True, default="")
    telefone = models.CharField("telefone", max_length=20, blank=True, default="")
    site = models.URLField("site", max_length=255, blank=True, default="")

    cep = models.CharField("CEP", max_length=9, blank=True, default="")
    logradouro = models.CharField("logradouro", max_length=200, blank=True, default="")
    numero = models.CharField("número", max_length=20, blank=True, default="")
    complemento = models.CharField("complemento", max_length=100, blank=True, default="")
    bairro = models.CharField("bairro", max_length=100, blank=True, default="")
    cidade = models.CharField("cidade", max_length=100, blank=True, default="")
    estado = models.CharField("estado (UF)", max_length=2, blank=True, default="")

    observacoes = models.TextField("observações", blank=True)
    ativo = models.BooleanField("ativa", default=True)

    tags = models.ManyToManyField(Tag, related_name="entidades", blank=True)

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="entidades_criadas",
    )
    criado_em = models.DateTimeField("criada em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizada em", auto_now=True)

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

    def clean(self):
        super().clean()
        if self.cnpj:
            digits = re.sub(r"\D", "", self.cnpj)
            if len(digits) != 14:
                raise ValidationError({"cnpj": "CNPJ deve ter 14 dígitos."})
        if self.cep:
            cep = re.sub(r"\D", "", self.cep)
            if len(cep) != 8:
                raise ValidationError({"cep": "CEP deve ter 8 dígitos."})

    def save(self, *args, **kwargs):
        self.telefone = normalize_phone(self.telefone)
        if self.cnpj:
            digits = re.sub(r"\D", "", self.cnpj)
            if len(digits) == 14:
                self.cnpj = f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
        if self.cep:
            cep = re.sub(r"\D", "", self.cep)
            if len(cep) == 8:
                self.cep = f"{cep[:5]}-{cep[5:]}"
        if self.estado:
            self.estado = self.estado.upper()
        super().save(*args, **kwargs)


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
