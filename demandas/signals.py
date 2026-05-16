"""Signals do app demandas.

Mudanças de estado de Demanda geram interações automáticas (timeline).
Padrão herdado de pessoas/signals.py: pre_save normaliza/snapshot, post_save
emite efeitos. Detalhes em docs/fluxos-de-estado.md §1.4 e §1.5.

Transições automáticas de status da Demanda (ADR 0044):
- 1ª Interacao manual criada: novo → em_andamento
- Encaminhamento criado (novo/em_andamento): → aguardando_terceiros
- Encaminhamento respondido sem outros abertos: aguardando_terceiros → em_andamento

Anexos polimórficos são órfãos por padrão (GenericForeignKey não cascateia
no banco). pre_delete dos models pais limpa antes da exclusão.
"""

from threading import local

from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import Anexo, Demanda, Encaminhamento, Interacao

# Thread-local para passar o usuário atual ao signal — setado pelo middleware
# do auditlog (que já carrega request.user via ContextVar). Reaproveitamos
# uma instância local simples para evitar acoplar ao auditlog internamente.
_request_local = local()


def set_usuario_atual(user):
    """Setado pelo middleware (ver demandas/middleware.py)."""
    _request_local.user = user


def get_usuario_atual():
    return getattr(_request_local, "user", None)


@receiver(post_save, sender=Demanda)
def registrar_eventos_automaticos(sender, instance, created, **kwargs):
    """Cria interações automáticas para criação e mudanças de estado da demanda.

    Comparação contra _original_status / _original_resultado / _original_responsavel_id
    capturados em Demanda.__init__ — ver fluxos-de-estado.md §1.4.
    """
    if created:
        Interacao.objects.create(
            demanda=instance,
            autor=instance.criado_por,
            tipo=Interacao.TIPO_REGISTRO_INICIAL,
            conteudo=f"Demanda aberta: {instance.titulo}",
            status=Interacao.STATUS_REALIZADA,
            data_ocorrencia=instance.criado_em,
            automatica=True,
        )
        instance._original_status = instance.status
        instance._original_resultado = instance.resultado
        instance._original_responsavel_id = instance.responsavel_id
        return

    autor = get_usuario_atual() or instance.criado_por

    if instance._original_status != instance.status:
        de = dict(Demanda.STATUS_CHOICES).get(instance._original_status, instance._original_status)
        para = dict(Demanda.STATUS_CHOICES).get(instance.status, instance.status)
        Interacao.objects.create(
            demanda=instance,
            autor=autor,
            tipo=Interacao.TIPO_MUDANCA_STATUS,
            conteudo=f"Status: {de} → {para}",
            status=Interacao.STATUS_REALIZADA,
            data_ocorrencia=timezone.now(),
            automatica=True,
        )

    if instance._original_responsavel_id != instance.responsavel_id:
        de = _nome_usuario(instance._original_responsavel_id)
        para = _nome_usuario(instance.responsavel_id)
        Interacao.objects.create(
            demanda=instance,
            autor=autor,
            tipo=Interacao.TIPO_MUDANCA_RESPONSAVEL,
            conteudo=f"Responsável: {de} → {para}",
            status=Interacao.STATUS_REALIZADA,
            data_ocorrencia=timezone.now(),
            automatica=True,
        )

    if instance._original_resultado != instance.resultado:
        de = dict(Demanda.RESULTADO_CHOICES).get(
            instance._original_resultado, instance._original_resultado
        )
        para = dict(Demanda.RESULTADO_CHOICES).get(instance.resultado, instance.resultado)
        Interacao.objects.create(
            demanda=instance,
            autor=autor,
            tipo=Interacao.TIPO_MUDANCA_RESULTADO,
            conteudo=f"Resultado: {de} → {para}",
            status=Interacao.STATUS_REALIZADA,
            data_ocorrencia=timezone.now(),
            automatica=True,
        )

    # Resync snapshots para futuras mudanças no mesmo objeto em memória.
    instance._original_status = instance.status
    instance._original_resultado = instance.resultado
    instance._original_responsavel_id = instance.responsavel_id


def _nome_usuario(uid):
    if not uid:
        return "[não atribuído]"
    from django.contrib.auth import get_user_model

    user_model = get_user_model()
    try:
        u = user_model.objects.get(pk=uid)
        return u.nome_completo or u.email
    except user_model.DoesNotExist:
        return "[usuário removido]"


# Anexos polimórficos: GenericForeignKey não cascateia no banco. Antes de
# deletar Pessoa/Entidade/Demanda/Encaminhamento, removemos os anexos órfãos.
# --- Transições automáticas de status da Demanda (ADR 0044) ---

# Tipos de Interacao que NÃO devem disparar avanço de status (são geradas
# pelo próprio sistema ou são acessórias, não evidência de trabalho operacional).
_TIPOS_INTERACAO_NAO_OPERACIONAIS = frozenset(
    {
        Interacao.TIPO_REGISTRO_INICIAL,
        Interacao.TIPO_MUDANCA_STATUS,
        Interacao.TIPO_MUDANCA_RESPONSAVEL,
        Interacao.TIPO_MUDANCA_RESULTADO,
        Interacao.TIPO_ARQUIVAMENTO,
    }
)


@receiver(post_save, sender=Interacao)
def avancar_status_na_primeira_interacao(sender, instance, created, **kwargs):
    """1ª Interacao manual de trabalho: demanda sai de 'novo' para 'em_andamento'."""
    if not created or instance.automatica:
        return
    if instance.tipo in _TIPOS_INTERACAO_NAO_OPERACIONAIS:
        return
    demanda = instance.demanda
    if demanda.status == Demanda.STATUS_NOVO:
        demanda.status = Demanda.STATUS_EM_ANDAMENTO
        demanda.save()  # dispara post_save de Demanda → cria Interacao mudanca_status


@receiver(post_save, sender=Encaminhamento)
def avancar_status_por_encaminhamento(sender, instance, created, **kwargs):
    """Criar encaminhamento → aguardando_terceiros.
    Responder o último encaminhamento aberto → em_andamento."""
    demanda = instance.demanda
    abertos = ("enviado", "prazo_vencido")
    if created:
        if demanda.status in (Demanda.STATUS_NOVO, Demanda.STATUS_EM_ANDAMENTO):
            demanda.status = Demanda.STATUS_AGUARDANDO_TERCEIROS
            demanda.save()
        return
    # Update: a resposta acabou de fechar o encaminhamento?
    if instance.status not in abertos and demanda.status == Demanda.STATUS_AGUARDANDO_TERCEIROS:
        ainda_abertos = (
            demanda.encaminhamentos.filter(status__in=abertos).exclude(pk=instance.pk).exists()
        )
        if not ainda_abertos:
            demanda.status = Demanda.STATUS_EM_ANDAMENTO
            demanda.save()


def _registrar_limpeza_anexos(model):
    @receiver(pre_delete, sender=model, weak=False)
    def _limpar_anexos(sender, instance, **kwargs):
        ct = ContentType.objects.get_for_model(model)
        Anexo.objects.filter(content_type=ct, object_id=instance.pk).delete()


def _setup_anexos_orfaos():
    from pessoas.models import Entidade, Pessoa

    for model in (Demanda, Pessoa, Entidade):
        _registrar_limpeza_anexos(model)
    # Encaminhamento já cascateia via FK pra Demanda; mas se for deletado
    # isolado, anexos próprios também devem sumir.
    _registrar_limpeza_anexos(Encaminhamento)


_setup_anexos_orfaos()
