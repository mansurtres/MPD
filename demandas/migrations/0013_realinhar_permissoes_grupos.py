"""Realinha as permissões dos 3 grupos à matriz da permissoes.md v2 (ADR 0059, DT-018).

As *views* já garantem o acesso need-to-know; isto alinha a **configuração dos
grupos** à doc, que prometia uma matriz que as data migrations da Fase 2/3 não
mais refletiam:

- Tags e Temas (CRUD) e anonimização (LGPD) passam a ser exclusivos do
  Administrador (permissoes.md §3.1, §3.7).
- Chefe de Gabinete perde `add_tag`/`change_tag` e `pode_anonimizar_pessoa`;
  Assessor já não os tinha (remoção defensiva, no-op).
- Administrador ganha o CRUD de Tema (nenhum grupo o tinha — só superusuário
  criava temas).
- Desativar/reativar (Admin + CG) permanece inalterado.
"""

from django.db import migrations

# (app_label, codename) reservados ao grupo Administrador.
PERMS_SO_ADMIN = [
    ("pessoas", "pode_anonimizar_pessoa"),
    ("pessoas", "pode_anonimizar_entidade"),
    ("pessoas", "add_tag"),
    ("pessoas", "change_tag"),
    ("pessoas", "delete_tag"),
    ("demandas", "view_tema"),
    ("demandas", "add_tema"),
    ("demandas", "change_tema"),
    ("demandas", "delete_tema"),
]


def _perms(Permission):
    out = []
    for app_label, codename in PERMS_SO_ADMIN:
        p = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
        if p is not None:
            out.append(p)
    return out


def realinhar(apps, schema_editor):
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    for app_label in ("pessoas", "demandas"):
        create_permissions(global_apps.get_app_config(app_label), verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    perms = _perms(Permission)

    # Administrador detém todas (inclui o CRUD de Tema, que faltava).
    try:
        admin = Group.objects.get(name="Administrador")
        admin.permissions.add(*perms)
    except Group.DoesNotExist:
        pass

    # Chefe de Gabinete e Assessor não detêm nenhuma delas.
    for nome in ("Chefe de Gabinete", "Assessor"):
        try:
            grupo = Group.objects.get(name=nome)
        except Group.DoesNotExist:
            continue
        grupo.permissions.remove(*perms)


def reverter(apps, schema_editor):
    # Reverso best-effort: devolve ao Chefe de Gabinete o que ele tinha antes
    # (anonimizar_pessoa, add_tag, change_tag). Não recria o estado exato.
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    try:
        cg = Group.objects.get(name="Chefe de Gabinete")
    except Group.DoesNotExist:
        return
    for app_label, codename in [
        ("pessoas", "pode_anonimizar_pessoa"),
        ("pessoas", "add_tag"),
        ("pessoas", "change_tag"),
    ]:
        p = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
        if p is not None:
            cg.permissions.add(p)


class Migration(migrations.Migration):
    dependencies = [
        ("demandas", "0012_drop_coordenacao"),
        ("accounts", "0008_remove_grupo_coordenador"),
        ("pessoas", "0002_grupos_padrao"),
    ]

    operations = [
        migrations.RunPython(realinhar, reverter),
    ]
