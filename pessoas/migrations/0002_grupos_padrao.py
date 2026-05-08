"""Cria os 4 grupos padrão (Administrador, Chefe de Gabinete, Coordenador, Assessor)
com as permissões dos models de pessoas — Fase 2.

Permissões de demandas serão adicionadas em data migration própria na Fase 3.
A configuração é o ponto de partida; ADM pode ajustar via Django Admin sem deploy.
"""

from django.db import migrations


def codenames_para_grupo(grupo):
    if grupo == "Administrador":
        return [
            "pessoas.view_pessoa",
            "pessoas.add_pessoa",
            "pessoas.change_pessoa",
            "pessoas.delete_pessoa",
            "pessoas.pode_desativar_pessoa",
            "pessoas.pode_reativar_pessoa",
            "pessoas.pode_anonimizar_pessoa",
            "pessoas.view_entidade",
            "pessoas.add_entidade",
            "pessoas.change_entidade",
            "pessoas.delete_entidade",
            "pessoas.pode_desativar_entidade",
            "pessoas.pode_reativar_entidade",
            "pessoas.view_vinculo",
            "pessoas.add_vinculo",
            "pessoas.change_vinculo",
            "pessoas.delete_vinculo",
            "pessoas.view_tag",
            "pessoas.add_tag",
            "pessoas.change_tag",
            "pessoas.delete_tag",
        ]
    if grupo == "Chefe de Gabinete":
        return [
            "pessoas.view_pessoa",
            "pessoas.add_pessoa",
            "pessoas.change_pessoa",
            "pessoas.pode_desativar_pessoa",
            "pessoas.pode_reativar_pessoa",
            "pessoas.pode_anonimizar_pessoa",
            "pessoas.view_entidade",
            "pessoas.add_entidade",
            "pessoas.change_entidade",
            "pessoas.pode_desativar_entidade",
            "pessoas.pode_reativar_entidade",
            "pessoas.view_vinculo",
            "pessoas.add_vinculo",
            "pessoas.change_vinculo",
            "pessoas.delete_vinculo",
            "pessoas.view_tag",
            "pessoas.add_tag",
            "pessoas.change_tag",
        ]
    if grupo == "Coordenador":
        return [
            "pessoas.view_pessoa",
            "pessoas.add_pessoa",
            "pessoas.change_pessoa",
            "pessoas.pode_desativar_pessoa",
            "pessoas.pode_anonimizar_pessoa",
            "pessoas.view_entidade",
            "pessoas.add_entidade",
            "pessoas.change_entidade",
            "pessoas.pode_desativar_entidade",
            "pessoas.view_vinculo",
            "pessoas.add_vinculo",
            "pessoas.change_vinculo",
            "pessoas.view_tag",
            "pessoas.add_tag",
            "pessoas.change_tag",
        ]
    if grupo == "Assessor":
        return [
            "pessoas.view_pessoa",
            "pessoas.add_pessoa",
            "pessoas.change_pessoa",
            "pessoas.view_entidade",
            "pessoas.add_entidade",
            "pessoas.change_entidade",
            "pessoas.view_vinculo",
            "pessoas.add_vinculo",
            "pessoas.change_vinculo",
            "pessoas.view_tag",
        ]
    return []


def criar_grupos(apps, schema_editor):
    # Garante que as permissions dos models de pessoas já existam: o sinal
    # post_migrate só roda ao final da rodada. Sem isso, em DBs limpas (testes,
    # primeira migrate) a busca por Permission viria vazia.
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    pessoas_app = global_apps.get_app_config("pessoas")
    create_permissions(pessoas_app, verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    grupos = ["Administrador", "Chefe de Gabinete", "Coordenador", "Assessor"]
    for nome in grupos:
        grupo, _ = Group.objects.get_or_create(name=nome)
        codenames_alvo = [cn.split(".", 1)[1] for cn in codenames_para_grupo(nome)]
        perms = Permission.objects.filter(
            content_type__app_label="pessoas",
            codename__in=codenames_alvo,
        )
        grupo.permissions.add(*perms)


def remover_grupos(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(
        name__in=["Administrador", "Chefe de Gabinete", "Coordenador", "Assessor"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pessoas", "0001_criar_models_pessoa_entidade_vinculo_tag"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(criar_grupos, remover_grupos),
    ]
