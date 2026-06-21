"""Atribui a permissão custom `gerenciar_usuarios` ao grupo Administrador (DT-011).

Gating da gestão de equipe deixou de ser por `is_staff` e passou a ser pela
permissão `accounts.gerenciar_usuarios`. O grupo Administrador a recebe aqui.
"""

from django.db import migrations


def adicionar_permissao(apps, schema_editor):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    # Garante que a permissão custom exista neste ponto da cadeia de migrations.
    create_permissions(global_apps.get_app_config("accounts"), verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    try:
        grupo = Group.objects.get(name="Administrador")
    except Group.DoesNotExist:
        return
    try:
        perm = Permission.objects.get(
            content_type__app_label="accounts", codename="gerenciar_usuarios"
        )
    except Permission.DoesNotExist:
        return
    grupo.permissions.add(perm)


def remover_permissao(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    try:
        perm = Permission.objects.get(
            content_type__app_label="accounts", codename="gerenciar_usuarios"
        )
    except Permission.DoesNotExist:
        return
    for grupo in Group.objects.filter(name="Administrador"):
        grupo.permissions.remove(perm)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_gerenciar_usuarios_permissao"),
        ("pessoas", "0002_grupos_padrao"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(adicionar_permissao, remover_permissao),
    ]
