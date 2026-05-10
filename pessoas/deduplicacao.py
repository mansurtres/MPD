"""Detecção de duplicatas em Pessoa. Match por email, telefone ou rede social."""

from django.db.models import Q

from core.utils import somente_digitos

from .models import Pessoa


def _normalizar_texto(value):
    return (value or "").strip().lower()


def buscar_similares(*, email="", telefone="", rede_social="", excluir_pk=None):
    """Retorna queryset de Pessoas com email, telefone ou rede social coincidentes.

    `telefone` é qualquer número (celular ou fixo) — busca em `Pessoa.telefones`.
    `email` busca em `Pessoa.emails.endereco`.
    `rede_social` busca em `Pessoa.redes_sociais.valor` (qualquer plataforma).
    OR entre os critérios. Exclui a pessoa indicada em `excluir_pk`.
    """
    email_n = _normalizar_texto(email)
    telefone_n = somente_digitos(telefone)
    rede_n = _normalizar_texto(rede_social).lstrip("@")

    q = Q()
    if email_n:
        q |= Q(emails__endereco__iexact=email_n)
    if telefone_n:
        q |= Q(telefones__numero=telefone_n)
    if rede_n:
        q |= Q(redes_sociais__valor__iexact=rede_n)

    if not q:
        return Pessoa.objects.none()

    qs = Pessoa.objects.filter(q).filter(ativo=True).distinct()
    if excluir_pk:
        qs = qs.exclude(pk=excluir_pk)
    return qs.order_by("nome", "sobrenome")
