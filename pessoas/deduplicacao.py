"""Detecção de duplicatas em Pessoa. Match por email/telefone/whatsapp normalizados."""

import re

from django.db.models import Q

from .models import Pessoa


def _digitos(value):
    return re.sub(r"\D", "", value or "")


def _email_normalizado(value):
    return (value or "").strip().lower()


def buscar_similares(*, email="", telefone="", whatsapp="", excluir_pk=None):
    """Retorna queryset de Pessoas com email/telefone/whatsapp coincidentes.

    Usa OR entre os critérios. Ignora valores vazios. Exclui a pessoa indicada
    em `excluir_pk` (útil ao editar — não retorna ela mesma).
    """
    email_n = _email_normalizado(email)
    telefone_n = _digitos(telefone)
    whatsapp_n = _digitos(whatsapp)

    q = Q()
    matched = False
    if email_n:
        q |= Q(email__iexact=email_n)
        matched = True
    if telefone_n:
        q |= Q(telefone=telefone_n)
        matched = True
    if whatsapp_n:
        q |= Q(whatsapp=whatsapp_n)
        matched = True

    if not matched:
        return Pessoa.objects.none()

    qs = Pessoa.objects.filter(q).filter(ativo=True)
    if excluir_pk:
        qs = qs.exclude(pk=excluir_pk)
    return qs.order_by("nome", "sobrenome")
