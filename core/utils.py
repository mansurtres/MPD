"""Utilidades de formatação e validação compartilhadas entre apps.

Funções formatadoras devolvem string vazia quando o input é vazio ou inválido —
elas não levantam exceção. Validação algorítmica fica em `validate_*` (que
levantam `ValidationError`). A normalização real dos campos dos models é feita
em signals `pre_save` (ver `pessoas/signals.py`).
"""

import re

from django.core.exceptions import ValidationError


def somente_digitos(value):
    """Mantém apenas dígitos. None/vazio devolve ''."""
    if not value:
        return ""
    return re.sub(r"\D", "", value)


def formatar_cep(value):
    """8 dígitos -> 'XXXXX-XXX'. Vazio -> ''. Tamanho diferente -> dígitos crus."""
    if not value:
        return ""
    digitos = somente_digitos(value)
    if len(digitos) == 8:
        return f"{digitos[:5]}-{digitos[5:]}"
    return digitos


def formatar_cpf(value):
    """11 dígitos -> 'XXX.XXX.XXX-XX'. Vazio ou tamanho diferente -> ''.

    Não valida algoritmicamente — só formata. Validação fica em `validate_cpf`.
    """
    if not value:
        return ""
    digitos = somente_digitos(value)
    if len(digitos) != 11:
        return ""
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


def formatar_cnpj(value):
    """14 dígitos -> 'XX.XXX.XXX/XXXX-XX'. Vazio ou tamanho diferente -> ''."""
    if not value:
        return ""
    digitos = somente_digitos(value)
    if len(digitos) != 14:
        return ""
    return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"


def validate_cpf(value):
    """Valida CPF pelo algoritmo. Aceita com ou sem pontuação. Vazio passa."""
    if not value:
        return
    digitos = somente_digitos(value)
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        raise ValidationError("CPF inválido.")
    for i in (9, 10):
        s = sum(int(digitos[j]) * ((i + 1) - j) for j in range(i))
        d = (s * 10) % 11
        if d == 10:
            d = 0
        if d != int(digitos[i]):
            raise ValidationError("CPF inválido.")


def validate_cnpj_tamanho(value):
    """Valida que CNPJ tem 14 dígitos. Vazio passa. Não checa dígito verificador.

    Assimetria deliberada com `validate_cpf`: CPF é digitado em campo livre por
    usuários (cidadãos), CNPJ tipicamente vem de cadastros formais ou colado de
    documento. Risco de erro de digitação é menor — DV não compensa o atrito.
    """
    if not value:
        return
    if len(somente_digitos(value)) != 14:
        raise ValidationError("CNPJ deve ter 14 dígitos.")


def validate_cep(value):
    """Valida que CEP tem 8 dígitos. Vazio passa."""
    if not value:
        return
    if len(somente_digitos(value)) != 8:
        raise ValidationError("CEP deve ter 8 dígitos.")
