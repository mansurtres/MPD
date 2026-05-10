"""Mixins abstratos reutilizáveis em modelos do MPD.

Mixins concentram campos e regras compartilhadas entre entidades do domínio
(Pessoa, Entidade e, futuramente, Demanda). Mantém uma única fonte de verdade
para conceitos transversais como endereço e auditoria.
"""

from django.core.validators import RegexValidator
from django.db import models

from core.utils import validate_cep

UF_VALIDATOR = RegexValidator(r"^[A-Za-z]{2}$", "Use a sigla de 2 letras (ex: ES).")


class EnderecavelMixin(models.Model):
    """Endereço brasileiro inline. Todos os campos opcionais por padrão.

    Subclasses que exijam bairro/cidade redeclaram esses campos com `blank=False`.
    Subclasses que tenham UF padrão diferente redeclaram `estado`.
    """

    cep = models.CharField(
        "CEP",
        max_length=9,
        blank=True,
        default="",
        validators=[validate_cep],
    )
    logradouro = models.CharField("logradouro", max_length=200, blank=True, default="")
    numero = models.CharField("número", max_length=20, blank=True, default="")
    complemento = models.CharField("complemento", max_length=100, blank=True, default="")
    bairro = models.CharField("bairro", max_length=100, blank=True, default="")
    cidade = models.CharField("cidade", max_length=100, blank=True, default="")
    estado = models.CharField(
        "estado (UF)",
        max_length=2,
        blank=True,
        default="",
        validators=[UF_VALIDATOR],
    )

    class Meta:
        abstract = True


class AuditavelMixin(models.Model):
    """Timestamps de criação e atualização.

    `criado_por` é declarado por cada subclasse para preservar `related_name`
    específico (ex: `pessoas_criadas`, `entidades_criadas`).
    """

    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        abstract = True
