"""Remove o papel 'Coordenador' (ADR 0059 — papéis v1: Admin/CG/Assessor).

Membros do grupo Coordenador são movidos para Assessor antes de o grupo
ser excluído, para não perderem suas permissões de visualização.
"""

from django.db import migrations


def remove_grupo_coordenador(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Usuario = apps.get_model("accounts", "Usuario")
    try:
        coordenador = Group.objects.get(name="Coordenador")
    except Group.DoesNotExist:
        return
    assessor, _ = Group.objects.get_or_create(name="Assessor")
    for usuario in Usuario.objects.filter(groups=coordenador):
        usuario.groups.add(assessor)
    coordenador.delete()


def recriar_grupo_coordenador(apps, schema_editor):
    # Reverso best-effort: recria o grupo vazio (sem permissões nem membros).
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="Coordenador")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_drop_coordenacao"),
    ]

    operations = [
        migrations.RunPython(remove_grupo_coordenador, recriar_grupo_coordenador),
    ]
