"""Padroniza slug_publico de Pessoa e Entidade em 8 caracteres (ADR 0038, errata).

Ordem importa: PRIMEIRO regenera todos os slugs existentes para um valor único
de 8 chars (RunPython), DEPOIS o AlterField reduz max_length de 12 para 8 — assim
o ALTER varchar(8) não trunca dados de 12 chars (sem produção; regerar é OK).

Reversão: no-op (não restauramos os slugs de 12 chars originais — não há
produção e os valores são opacos).
"""

import uuid

from django.db import migrations, models


def _regerar_slugs(apps, schema_editor):
    for app_label, model_name in (("pessoas", "Pessoa"), ("pessoas", "Entidade")):
        Modelo = apps.get_model(app_label, model_name)
        usados = set()
        for obj in Modelo.objects.all().iterator():
            while True:
                novo = uuid.uuid4().hex[:8]
                if novo not in usados:
                    break
            usados.add(novo)
            obj.slug_publico = novo
            obj.save(update_fields=["slug_publico"])


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("pessoas", "0004_canais_compartilhados"),
    ]

    operations = [
        migrations.RunPython(_regerar_slugs, _noop),
        migrations.AlterField(
            model_name="pessoa",
            name="slug_publico",
            field=models.CharField(
                blank=True,
                editable=False,
                help_text="Slug curto (8 chars) para URLs públicas. Gerado automaticamente no save().",
                max_length=8,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="entidade",
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
