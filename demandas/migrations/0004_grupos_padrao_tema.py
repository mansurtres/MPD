"""Adiciona permissões de Tema aos grupos existentes (ADR 0042)."""

from django.db import migrations


def codenames_para_grupo(grupo):
    if grupo == "Administrador":
        return [
            "demandas.view_tema",
            "demandas.add_tema",
            "demandas.change_tema",
            "demandas.delete_tema",
        ]
    if grupo == "Chefe de Gabinete":
        return [
            "demandas.view_tema",
            "demandas.add_tema",
            "demandas.change_tema",
        ]
    if grupo == "Coordenador":
        return [
            "demandas.view_tema",
            "demandas.add_tema",
            "demandas.change_tema",
        ]
    if grupo == "Assessor":
        return [
            "demandas.view_tema",
        ]
    return []


def adicionar_permissoes(apps, schema_editor):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    create_permissions(global_apps.get_app_config("demandas"), verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    for nome in ["Administrador", "Chefe de Gabinete", "Coordenador", "Assessor"]:
        try:
            grupo = Group.objects.get(name=nome)
        except Group.DoesNotExist:
            continue
        codenames = [cn.split(".", 1)[1] for cn in codenames_para_grupo(nome)]
        perms = Permission.objects.filter(
            content_type__app_label="demandas",
            codename__in=codenames,
        )
        grupo.permissions.add(*perms)


def remover_permissoes(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perms = Permission.objects.filter(
        content_type__app_label="demandas",
        codename__in=["view_tema", "add_tema", "change_tema", "delete_tema"],
    )
    for grupo in Group.objects.filter(
        name__in=["Administrador", "Chefe de Gabinete", "Coordenador", "Assessor"]
    ):
        grupo.permissions.remove(*perms)


class Migration(migrations.Migration):
    dependencies = [
        ("demandas", "0003_separar_tema_de_tag"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(adicionar_permissoes, remover_permissoes),
    ]
