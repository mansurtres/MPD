"""Signals de normalização de campos.

Roda em `pre_save` (todas as portas: ORM direto, Forms, Admin, scripts). Garante
que o que entra no banco está no formato canônico — formatado quando válido,
zerado quando inválido. Validação algorítmica fica nos `validators` dos campos
(disparados pelo `full_clean()` que os ModelForms chamam automaticamente).

`slug_publico` NÃO é mais gerado aqui. Migrou para `Pessoa.save()` /
`Entidade.save()` com retry em IntegrityError (ADR 0051) — a abordagem
TOCTOU `filter().exists() → save()` tinha race em ambientes concorrentes.
"""

from django.db.models.signals import pre_save
from django.dispatch import receiver

from core.utils import formatar_cep, formatar_cnpj, formatar_cpf, somente_digitos

from .models import EmailPessoa, Entidade, Pessoa, RedeSocial, Telefone


@receiver(pre_save, sender=Pessoa)
def normalizar_pessoa(sender, instance, **kwargs):
    instance.cpf = formatar_cpf(instance.cpf)
    instance.cep = formatar_cep(instance.cep)
    if instance.estado:
        instance.estado = instance.estado.upper()


@receiver(pre_save, sender=Entidade)
def normalizar_entidade(sender, instance, **kwargs):
    instance.cnpj = formatar_cnpj(instance.cnpj)
    instance.telefone = somente_digitos(instance.telefone)
    instance.cep = formatar_cep(instance.cep)
    if instance.estado:
        instance.estado = instance.estado.upper()


@receiver(pre_save, sender=Telefone)
def normalizar_telefone(sender, instance, **kwargs):
    instance.numero = somente_digitos(instance.numero)


@receiver(pre_save, sender=EmailPessoa)
def normalizar_email(sender, instance, **kwargs):
    instance.endereco = (instance.endereco or "").strip().lower()


@receiver(pre_save, sender=RedeSocial)
def normalizar_rede_social(sender, instance, **kwargs):
    instance.valor = (instance.valor or "").strip().lstrip("@")
