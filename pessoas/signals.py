"""Signals de normalização de campos e geração de slug público.

Roda em `pre_save` (todas as portas: ORM direto, Forms, Admin, scripts). Garante
que o que entra no banco está no formato canônico — formatado quando válido,
zerado quando inválido. Validação algorítmica fica nos `validators` dos campos
(disparados pelo `full_clean()` que os ModelForms chamam automaticamente).

`slug_publico` é gerado uma única vez na criação. Usa `uuid4().hex[:12]` com
retry em colisão (probabilidade desprezível na escala do mandato).
"""

import uuid

from django.db.models.signals import pre_save
from django.dispatch import receiver

from core.utils import formatar_cep, formatar_cnpj, formatar_cpf, somente_digitos

from .models import EmailPessoa, Entidade, Pessoa, RedeSocial, Telefone


def _gerar_slug_unico(model, length=12, max_tentativas=10):
    """Gera slug hexadecimal único para o model. Levanta após N tentativas."""
    for _ in range(max_tentativas):
        candidato = uuid.uuid4().hex[:length]
        if not model.objects.filter(slug_publico=candidato).exists():
            return candidato
    raise RuntimeError(
        f"Não foi possível gerar slug_publico único para {model.__name__} "
        f"após {max_tentativas} tentativas."
    )


@receiver(pre_save, sender=Pessoa)
def normalizar_pessoa(sender, instance, **kwargs):
    if not instance.slug_publico:
        instance.slug_publico = _gerar_slug_unico(Pessoa)
    instance.cpf = formatar_cpf(instance.cpf)
    instance.cep = formatar_cep(instance.cep)
    if instance.estado:
        instance.estado = instance.estado.upper()


@receiver(pre_save, sender=Entidade)
def normalizar_entidade(sender, instance, **kwargs):
    if not instance.slug_publico:
        instance.slug_publico = _gerar_slug_unico(Entidade)
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
