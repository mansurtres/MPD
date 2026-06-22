"""Adiciona slug_publico (8 chars) à Demanda para URLs públicas (ADR 0038, errata).

Padrão para campo unique em tabela populada:
1. AddField nullable e não-unique (não quebra linhas existentes).
2. RunPython backfill com slug único de 8 chars por linha.
3. AlterField para o estado final (unique=True, blank=True, editable=False, NOT NULL).

Reversão: RemoveField.
"""

import uuid

from django.db import migrations, models


def _backfill_slugs(apps, schema_editor):
    Demanda = apps.get_model("demandas", "Demanda")
    usados = set()
    for demanda in Demanda.objects.all().iterator():
        if demanda.slug_publico:
            usados.add(demanda.slug_publico)
            continue
        while True:
            novo = uuid.uuid4().hex[:8]
            if novo not in usados:
                break
        usados.add(novo)
        demanda.slug_publico = novo
        demanda.save(update_fields=["slug_publico"])


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("demandas", "0009_drop_papel"),
    ]

    operations = [
        migrations.AddField(
            model_name="demanda",
            name="slug_publico",
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=8,
                null=True,
            ),
        ),
        migrations.RunPython(_backfill_slugs, _noop),
        migrations.AlterField(
            model_name="demanda",
            name="slug_publico",
            field=models.CharField(
                blank=True,
                editable=False,
                help_text="Slug curto (8 chars) para URLs públicas. Gerado automaticamente no save().",
                max_length=8,
                unique=True,
            ),
        ),
    ]
