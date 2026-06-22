"""Testes do app core: views institucionais e helpers compartilhados."""

from django import forms
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.forms import aplicar_tailwind

Usuario = get_user_model()


# --- Views ---


def test_healthz_responde_ok(client, db):
    # /healthz verifica o banco; precisa da fixture db para ter conexão.
    response = client.get(reverse("core:healthz"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_inicio_anonimo_renderiza_publico(client):
    response = client.get(reverse("core:inicio"))
    assert response.status_code == 200
    templates = [t.name for t in response.templates if t.name]
    assert "core/inicio.html" in templates


def test_inicio_autenticado_renderiza_dashboard(client, db):
    user = Usuario.objects.create_user(
        email="dashboard@test.com",
        password="senha12345",  # pragma: allowlist secret
    )
    client.force_login(user)
    response = client.get(reverse("core:inicio"))
    assert response.status_code == 200
    templates = [t.name for t in response.templates if t.name]
    assert "core/inicio_autenticado.html" in templates


def test_configuracoes_exclusiva_do_admin(client, db):
    """Configurações (tags/temas/usuários) é só do Admin (ADR 0059)."""
    from django.contrib.auth.models import Group

    admin = Usuario.objects.create_user(
        email="adm3@t.com",
        password="senha12345",  # pragma: allowlist secret
        is_superuser=True,
        is_staff=True,
    )
    assessor = Usuario.objects.create_user(
        email="as3@t.com",
        password="senha12345",  # pragma: allowlist secret
    )
    g = Group.objects.filter(name="Assessor").first()
    if g:
        assessor.groups.add(g)
    client.force_login(assessor)
    assert client.get(reverse("core:configuracoes")).status_code == 403
    client.force_login(admin)
    assert client.get(reverse("core:configuracoes")).status_code == 200


# --- aplicar_tailwind ---


class _FormDeTeste(forms.Form):
    texto = forms.CharField()
    flag = forms.BooleanField(required=False)


def test_aplicar_tailwind_injeta_classes_em_input_e_checkbox():
    f = _FormDeTeste()
    aplicar_tailwind(f)
    assert "rounded-lg" in f.fields["texto"].widget.attrs["class"]
    assert "rounded border-slate-300" in f.fields["flag"].widget.attrs["class"]


def test_aplicar_tailwind_idempotente():
    f = _FormDeTeste()
    aplicar_tailwind(f)
    aplicar_tailwind(f)
    classes = f.fields["texto"].widget.attrs["class"]
    assert classes.count("rounded-lg") == 1


# --- core.permissoes (ADR 0048) ---


def test_eh_cg_plus_superuser_sem_grupo(db):
    from core.permissoes import eh_admin, eh_cg_plus

    u = Usuario.objects.create_superuser(
        email="super@t.com",
        password="senha12345",  # pragma: allowlist secret
    )
    assert eh_admin(u)
    assert eh_cg_plus(u)


def test_assessor_sem_grupo_nao_e_admin_nem_cg(db):
    from core.permissoes import eh_admin, eh_cg_plus

    u = Usuario.objects.create_user(
        email="assessor_solo@t.com",
        password="senha12345",  # pragma: allowlist secret
    )
    assert not eh_admin(u)
    assert not eh_cg_plus(u)


def test_eh_admin_chefe_nao_e_admin(db):
    """ADR 0054: Chefe de Gabinete deixou de ser admin. eh_admin
    distingue ADM dos demais grupos (acesso à auditoria)."""
    from django.contrib.auth.models import Group

    from core.permissoes import eh_admin, eh_cg_plus

    u = Usuario.objects.create_user(
        email="chefe_solo@t.com",
        password="senha12345",  # pragma: allowlist secret
    )
    g = Group.objects.filter(name="Chefe de Gabinete").first()
    if g:
        u.groups.add(g)
    assert eh_cg_plus(u)
    assert not eh_admin(u)


def test_eh_cg_plus_anonimo():
    from django.contrib.auth.models import AnonymousUser

    from core.permissoes import eh_admin, eh_cg_plus

    anon = AnonymousUser()
    assert not eh_admin(anon)
    assert not eh_cg_plus(anon)


# --- Busca global do topbar ---


def test_buscar_global_exige_login(client, db):
    """Endpoint protegido por @login_required."""
    resp = client.get(reverse("core:buscar_global"), {"q": "maria"})
    # @login_required redireciona para login
    assert resp.status_code == 302


def test_buscar_global_termo_curto_retorna_vazio(client, db):
    """Termos com menos de 2 caracteres não fazem busca (economiza queries)."""
    from django.contrib.auth.models import Group

    u = Usuario.objects.create_user(
        email="u@t.com", password="senha12345"  # pragma: allowlist secret
    )
    g = Group.objects.filter(name="Administrador").first()
    if g:
        u.groups.add(g)
    client.force_login(u)
    resp = client.get(reverse("core:buscar_global"), {"q": "a"})
    assert resp.status_code == 200
    assert resp.json() == {"resultados": []}


def test_buscar_global_acha_pessoa_demanda_entidade(client, db):
    """Termo bate em pessoa (nome), demanda (titulo) e entidade (nome) —
    cada categoria aparece no resultado com label, sublabel e url."""
    from django.contrib.auth.models import Group

    from demandas.models import Demanda
    from pessoas.models import Entidade, Pessoa

    admin = Usuario.objects.create_user(
        email="adm@t.com",
        password="senha12345",  # pragma: allowlist secret
        is_superuser=True,
        is_staff=True,
    )
    g = Group.objects.filter(name="Administrador").first()
    if g:
        admin.groups.add(g)

    Pessoa.objects.create(
        nome="Maria",
        sobrenome="Silva",
        bairro="Centro",
        cidade="Vitória",
        criado_por=admin,
    )
    Entidade.objects.create(
        nome="Maria Mãe Associação",
        tipo="associacao",
        criado_por=admin,
    )
    Demanda.objects.create(
        titulo="Reforma da praça da Maria",
        descricao="X",
        canal_entrada="presencial",
        criado_por=admin,
        anonimo=True,
    )

    client.force_login(admin)
    resp = client.get(reverse("core:buscar_global"), {"q": "maria"})
    assert resp.status_code == 200
    data = resp.json()
    categorias = {r["categoria"] for r in data["resultados"]}
    assert "Pessoa" in categorias
    assert "Entidade" in categorias
    assert "Demanda" in categorias
    # Cada resultado tem url e label
    for r in data["resultados"]:
        assert r["url"].startswith("/")
        assert r["label"]


def test_buscar_global_respeita_visibilidade(client, db):
    """Demanda que o usuário não criou nem é responsável NÃO aparece na
    busca global (ADR 0059 — visiveis_para)."""
    from django.contrib.auth.models import Group

    from demandas.models import Demanda

    admin = Usuario.objects.create_user(
        email="adm2@t.com",
        password="senha12345",  # pragma: allowlist secret
        is_superuser=True,
        is_staff=True,
    )
    assessor = Usuario.objects.create_user(
        email="assessor2@t.com",
        password="senha12345",  # pragma: allowlist secret
    )
    g = Group.objects.filter(name="Assessor").first()
    if g:
        assessor.groups.add(g)

    Demanda.objects.create(
        titulo="SegredoMaximo Z",
        descricao="X",
        canal_entrada="presencial",
        criado_por=admin,
        responsavel=admin,
        anonimo=True,
    )
    client.force_login(assessor)
    resp = client.get(reverse("core:buscar_global"), {"q": "SegredoMaximo"})
    assert resp.status_code == 200
    labels = [r["label"] for r in resp.json()["resultados"]]
    assert not any("SegredoMaximo" in lbl for lbl in labels)
