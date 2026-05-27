"""Renumera demandas existentes do formato MPD-AAAA-NNNNN para D-AAMM-NNNNN.

Ver ADR 0056 em docs/decisoes.md.

- Idempotente: se o `numero` já começa com 'D-', pula.
- Ano e mês derivados de `criado_em` da demanda (preserva a janela cronológica).
- Sufixo aleatório uniforme em [10000, 99999], com retry em colisão por savepoint.
"""

import random

from django.db import IntegrityError, migrations, transaction


def _renumerar(apps, schema_editor):
    Demanda = apps.get_model("demandas", "Demanda")
    qs = Demanda.objects.exclude(numero__startswith="D-").order_by("criado_em")
    for demanda in qs:
        prefixo = f"D-{demanda.criado_em.strftime('%y%m')}-"
        ultima_excecao = None
        for _ in range(20):  # margem extra na migration (volume desconhecido por mês)
            novo = f"{prefixo}{random.randint(10000, 99999)}"
            try:
                with transaction.atomic():
                    demanda.numero = novo
                    demanda.save(update_fields=["numero"])
                break
            except IntegrityError as exc:
                ultima_excecao = exc
                continue
        else:
            raise ultima_excecao


def _reverter(apps, schema_editor):
    """Reversão não suportada — o número original (sequencial) foi perdido.

    A renumeração é destrutiva por design: não armazenamos o número antigo em
    lugar nenhum, então não há como reconstruí-lo. Se for necessário reverter,
    restaurar a partir de backup.
    """
    raise NotImplementedError(
        "Renumeração D-AAMM-NNNNN é irreversível (sequencial original perdido). "
        "Restaurar do backup se necessário."
    )


class Migration(migrations.Migration):
    dependencies = [
        ("demandas", "0007_papel_choices_drop_observacao"),
    ]

    operations = [
        migrations.RunPython(_renumerar, _reverter),
    ]
