"""Comando manage.py verificar_integridade — Fase 6.

Relata inconsistências que regras codificadas no clean() não bloqueiam
(dados que driftaram por importação, edição via shell, ou janela entre
ações coordenadas). Roda em cron diário em produção; sinal de alerta
para operação manual."""

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Relata inconsistências internas (Fase 6)."

    def handle(self, *args, **options):
        from demandas.models import Anexo, Demanda, Encaminhamento, Interacao, ItemInbox

        problemas = []

        # 1. Demandas responsivas em status=concluida sem Interação devolutiva realizada.
        sem_devolutiva = Demanda.objects.filter(
            origem=Demanda.ORIGEM_RESPONSIVA,
            status=Demanda.STATUS_CONCLUIDA,
        ).exclude(
            interacoes__tipo=Interacao.TIPO_DEVOLUTIVA,
            interacoes__status=Interacao.STATUS_REALIZADA,
        )
        for d in sem_devolutiva:
            problemas.append(
                f"Demanda {d.numero} ({d.titulo[:60]}): responsiva concluída sem "
                f"Interação devolutiva realizada."
            )

        # 2. Anexos órfãos: registro existe mas arquivo no disco não.
        for a in Anexo.objects.all():
            try:
                if not a.arquivo or not a.arquivo.storage.exists(a.arquivo.name):
                    problemas.append(
                        f"Anexo {a.pk} ({a.nome_original}): registro existe mas "
                        f"arquivo no disco não encontrado."
                    )
            except Exception as exc:  # storage pode falhar — não derruba a checagem
                problemas.append(f"Anexo {a.pk}: erro ao verificar arquivo — {exc}.")

        # 2b. Anexos com content_type apontando para objeto inexistente.
        for a in Anexo.objects.all():
            try:
                if a.content_object is None:
                    ct = ContentType.objects.get(pk=a.content_type_id)
                    problemas.append(
                        f"Anexo {a.pk} ({a.nome_original}): aponta para "
                        f"{ct.model}#{a.object_id} que não existe (órfão polimórfico)."
                    )
            except Exception:
                # objeto pai pode estar desreferenciado — também é problema
                problemas.append(
                    f"Anexo {a.pk}: não consegue resolver objeto pai (órfão polimórfico)."
                )

        # 3. Encaminhamentos com prazo_resposta < hoje e status=enviado
        #    (cron de atualização de status não rodou).
        hoje = timezone.now().date()
        vencidos_sem_atualizar = Encaminhamento.objects.filter(
            status=Encaminhamento.STATUS_ENVIADO,
            prazo_resposta__lt=hoje,
        )
        for e in vencidos_sem_atualizar:
            problemas.append(
                f"Encaminhamento {e.pk} ({e.destinatario_orgao}): prazo "
                f"{e.prazo_resposta} já passou mas status segue 'enviado'."
            )

        # 4. ItemInbox pendente há mais de 90 dias.
        limite_inbox = timezone.now() - timedelta(days=90)
        inbox_antigos = ItemInbox.objects.filter(
            status=ItemInbox.STATUS_PENDENTE,
            criado_em__lt=limite_inbox,
        )
        for i in inbox_antigos:
            dias = (timezone.now() - i.criado_em).days
            problemas.append(f"ItemInbox {i.pk} ({i.conteudo[:50]}): pendente há {dias} dias.")

        # 5. Interações agendadas há mais de 180 dias sem ação.
        limite_interacao = timezone.now() - timedelta(days=180)
        interacoes_paradas = Interacao.objects.filter(
            status=Interacao.STATUS_AGENDADA,
            data_ocorrencia__lt=limite_interacao,
        )
        for i in interacoes_paradas:
            dias = (timezone.now() - i.data_ocorrencia).days
            problemas.append(
                f"Interação {i.pk} (demanda {i.demanda.numero}): agendada para "
                f"há {dias} dias, status ainda 'agendada'."
            )

        if not problemas:
            self.stdout.write(self.style.SUCCESS("Nenhuma inconsistência detectada."))
            return

        self.stdout.write(self.style.WARNING(f"{len(problemas)} inconsistência(s) detectada(s):"))
        for p in problemas:
            self.stdout.write(f"  - {p}")
        # Exit code 1 para cron monitorado.
        import sys

        sys.exit(1)
