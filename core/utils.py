"""Utilidades de formatação e validação compartilhadas entre apps.

Funções formatadoras devolvem string vazia quando o input é vazio ou inválido —
elas não levantam exceção. Validação algorítmica fica em `validate_*` (que
levantam `ValidationError`). A normalização real dos campos dos models é feita
em signals `pre_save` (ver `pessoas/signals.py`).
"""

import json
import logging
import re
import uuid

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

# --- Slug público curto (ADR 0038, padronizado em 8 chars) ---

SLUG_LENGTH = 8
_MAX_TENTATIVAS_SLUG = 10


def gerar_slug_publico():
    """Gera um identificador hex curto para URLs públicas (ADR 0038).

    8 caracteres hex = 16^8 ≈ 4,3 bilhões de combinações — amplo para a escala
    de um mandato municipal. Usado por Pessoa, Entidade e Demanda.
    """
    return uuid.uuid4().hex[:SLUG_LENGTH]


def salvar_com_slug_unico(instance, super_save, *args, **kwargs):
    """Salva `instance` garantindo `slug_publico` único, com retry em colisão.

    Substitui a geração via pre_save signal (que tinha TOCTOU:
    filter().exists() → save). Ver ADR 0051.

    Cada tentativa roda dentro de um savepoint (`transaction.atomic`) — sem
    isso, IntegrityError taints a transação externa e queries subsequentes
    falham com TransactionManagementError.
    """
    if instance.slug_publico:
        return super_save(*args, **kwargs)
    for tentativa in range(_MAX_TENTATIVAS_SLUG):
        instance.slug_publico = gerar_slug_publico()
        try:
            with transaction.atomic():
                return super_save(*args, **kwargs)
        except IntegrityError as exc:
            # Outras constraints (CPF/CNPJ unique) precisam propagar.
            if "slug_publico" not in str(exc).lower():
                raise
            if tentativa == _MAX_TENTATIVAS_SLUG - 1:
                raise
            # Próxima iteração tenta novo uuid.
            continue


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


# --- Helpers de UI ---


def flash_form_errors(request, *forms):
    """Emite uma mensagem de erro por campo, para todos os formulários dados.

    Substitui blocos duplicados que iteravam `form.errors.values()` e
    chamavam `messages.error` em 5+ views de demandas.

    Args:
        request: HttpRequest com acesso ao message framework.
        *forms: um ou mais objetos Form cujos erros serão exibidos.
    """
    from django.contrib import messages

    for form in forms:
        for erros in form.errors.values():
            if hasattr(erros, "__iter__") and not isinstance(erros, str):
                msg = "; ".join(erros)
            else:
                msg = str(erros)
            messages.error(request, msg)


# --- Auditoria de exportações (Fase 6, refinada na v0.7.3 / ADR 0053) ---


_MODELO_PARA_CT = {
    "Demanda": ("demandas", "demanda"),
    "Encaminhamento": ("demandas", "encaminhamento"),
    "Pessoa": ("pessoas", "pessoa"),
}


def registrar_export(user, modelo, filtros, total):
    """Registra um evento de exportação CSV para auditoria.

    Grava em duas camadas (ADR 0053):
    1. `auditlog.LogEntry` com `action=ACCESS` — visível em /auditoria, fecha o
       critério literal do roadmap §4.6.3.
    2. Logger 'mpd.exports' — linha de defesa operacional (se o banco do
       auditlog ficar indisponível, ainda sobra rastro no arquivo de log).

    Args:
        user: usuário que executou.
        modelo: nome legível do modelo exportado (ex.: "Demanda").
        filtros: dict de filtros aplicados (querystring).
        total: número de registros exportados.
    """
    logger = logging.getLogger("mpd.exports")
    logger.info(
        "Exportação CSV — modelo=%s usuario=%s total=%d filtros=%s",
        modelo,
        getattr(user, "email", "anônimo"),
        total,
        filtros,
    )

    try:
        from auditlog.models import LogEntry
        from django.contrib.contenttypes.models import ContentType

        app_label, model_name = _MODELO_PARA_CT.get(modelo, ("demandas", "demanda"))
        ct = ContentType.objects.get(app_label=app_label, model=model_name)
        LogEntry.objects.create(
            content_type=ct,
            object_pk="",
            object_repr=f"Exportação CSV — {modelo} ({total} registros)",
            action=LogEntry.Action.ACCESS,
            changes_text=json.dumps({"filtros": filtros, "total": total}, default=str),
            actor=user if getattr(user, "is_authenticated", False) else None,
        )
    except Exception:
        # Não derruba o export se o auditlog falhar — logger já gravou.
        logger.exception("Falha ao gravar LogEntry de export")
