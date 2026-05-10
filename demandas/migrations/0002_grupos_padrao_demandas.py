"""Adiciona permissões dos models de demandas aos grupos existentes
(Administrador, Chefe de Gabinete, Coordenador, Assessor) — conforme
docs/permissoes.md §3.3-3.8.
"""

from django.db import migrations


def codenames_para_grupo(grupo):
    if grupo == "Administrador":
        return [
            # Demanda
            "demandas.view_demanda",
            "demandas.add_demanda",
            "demandas.change_demanda",
            "demandas.delete_demanda",
            "demandas.pode_arquivar_demanda",
            "demandas.pode_arquivar_sem_responder",
            "demandas.pode_marcar_restrita",
            "demandas.pode_atribuir_responsavel",
            "demandas.pode_reabrir_demanda",
            "demandas.pode_excluir_demanda",
            # DemandaPessoa, DemandaEntidade
            "demandas.view_demandapessoa",
            "demandas.add_demandapessoa",
            "demandas.change_demandapessoa",
            "demandas.delete_demandapessoa",
            "demandas.view_demandaentidade",
            "demandas.add_demandaentidade",
            "demandas.change_demandaentidade",
            "demandas.delete_demandaentidade",
            # Interacao
            "demandas.view_interacao",
            "demandas.add_interacao",
            "demandas.change_interacao",
            "demandas.delete_interacao",
            "demandas.pode_editar_interacao_alheia",
            # Encaminhamento
            "demandas.view_encaminhamento",
            "demandas.add_encaminhamento",
            "demandas.change_encaminhamento",
            "demandas.delete_encaminhamento",
            "demandas.pode_excluir_encaminhamento",
            # Anexo
            "demandas.view_anexo",
            "demandas.add_anexo",
            "demandas.change_anexo",
            "demandas.delete_anexo",
            # ItemInbox
            "demandas.view_iteminbox",
            "demandas.add_iteminbox",
            "demandas.change_iteminbox",
            "demandas.delete_iteminbox",
        ]
    if grupo == "Chefe de Gabinete":
        return [
            "demandas.view_demanda",
            "demandas.add_demanda",
            "demandas.change_demanda",
            "demandas.pode_arquivar_demanda",
            "demandas.pode_arquivar_sem_responder",
            "demandas.pode_marcar_restrita",
            "demandas.pode_atribuir_responsavel",
            "demandas.pode_reabrir_demanda",
            "demandas.view_demandapessoa",
            "demandas.add_demandapessoa",
            "demandas.change_demandapessoa",
            "demandas.delete_demandapessoa",
            "demandas.view_demandaentidade",
            "demandas.add_demandaentidade",
            "demandas.change_demandaentidade",
            "demandas.delete_demandaentidade",
            "demandas.view_interacao",
            "demandas.add_interacao",
            "demandas.change_interacao",
            "demandas.pode_editar_interacao_alheia",
            "demandas.view_encaminhamento",
            "demandas.add_encaminhamento",
            "demandas.change_encaminhamento",
            "demandas.delete_encaminhamento",
            "demandas.pode_excluir_encaminhamento",
            "demandas.view_anexo",
            "demandas.add_anexo",
            "demandas.change_anexo",
            "demandas.delete_anexo",
            "demandas.view_iteminbox",
            "demandas.add_iteminbox",
            "demandas.change_iteminbox",
        ]
    if grupo == "Coordenador":
        return [
            "demandas.view_demanda",
            "demandas.add_demanda",
            "demandas.change_demanda",
            "demandas.pode_arquivar_demanda",
            "demandas.pode_atribuir_responsavel",
            "demandas.view_demandapessoa",
            "demandas.add_demandapessoa",
            "demandas.change_demandapessoa",
            "demandas.delete_demandapessoa",
            "demandas.view_demandaentidade",
            "demandas.add_demandaentidade",
            "demandas.change_demandaentidade",
            "demandas.delete_demandaentidade",
            "demandas.view_interacao",
            "demandas.add_interacao",
            "demandas.change_interacao",
            "demandas.view_encaminhamento",
            "demandas.add_encaminhamento",
            "demandas.change_encaminhamento",
            "demandas.view_anexo",
            "demandas.add_anexo",
            "demandas.change_anexo",
            "demandas.delete_anexo",
            "demandas.view_iteminbox",
            "demandas.add_iteminbox",
            "demandas.change_iteminbox",
        ]
    if grupo == "Assessor":
        return [
            "demandas.view_demanda",
            "demandas.add_demanda",
            "demandas.change_demanda",
            "demandas.view_demandapessoa",
            "demandas.add_demandapessoa",
            "demandas.change_demandapessoa",
            "demandas.view_demandaentidade",
            "demandas.add_demandaentidade",
            "demandas.change_demandaentidade",
            "demandas.view_interacao",
            "demandas.add_interacao",
            "demandas.change_interacao",
            "demandas.view_encaminhamento",
            "demandas.add_encaminhamento",
            "demandas.change_encaminhamento",
            "demandas.view_anexo",
            "demandas.add_anexo",
            "demandas.view_iteminbox",
            "demandas.add_iteminbox",
            "demandas.change_iteminbox",
        ]
    return []


def adicionar_permissoes(apps, schema_editor):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    demandas_app = global_apps.get_app_config("demandas")
    create_permissions(demandas_app, verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    for nome in ["Administrador", "Chefe de Gabinete", "Coordenador", "Assessor"]:
        try:
            grupo = Group.objects.get(name=nome)
        except Group.DoesNotExist:
            continue
        codenames_alvo = [cn.split(".", 1)[1] for cn in codenames_para_grupo(nome)]
        perms = Permission.objects.filter(
            content_type__app_label="demandas",
            codename__in=codenames_alvo,
        )
        grupo.permissions.add(*perms)


def remover_permissoes(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perms = Permission.objects.filter(content_type__app_label="demandas")
    for grupo in Group.objects.filter(
        name__in=["Administrador", "Chefe de Gabinete", "Coordenador", "Assessor"]
    ):
        grupo.permissions.remove(*perms)


class Migration(migrations.Migration):
    dependencies = [
        ("demandas", "0001_criar_models_demandas"),
        ("pessoas", "0002_grupos_padrao"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(adicionar_permissoes, remover_permissoes),
    ]
