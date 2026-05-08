import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

Usuario = get_user_model()


@pytest.fixture
def usuario_staff(db):
    return Usuario.objects.create_user(
        email="staff@test.com",
        password="senha12345",  # pragma: allowlist secret
        nome_completo="Staff User",
        is_staff=True,
    )


@pytest.fixture
def usuario_comum(db):
    return Usuario.objects.create_user(
        email="comum@test.com",
        password="senha12345",  # pragma: allowlist secret
        nome_completo="Usuário Comum",
        is_staff=False,
    )


# --- Model ---


def test_usuario_str_usa_nome_completo(db):
    u = Usuario.objects.create_user(email="x@test.com", password="p", nome_completo="Pedro")
    assert str(u) == "Pedro"


def test_usuario_str_usa_email_quando_sem_nome(db):
    u = Usuario.objects.create_user(email="x@test.com", password="p")
    assert str(u) == "x@test.com"


def test_usuario_username_preenchido_automaticamente(db):
    u = Usuario.objects.create_user(email="auto@test.com", password="p")
    assert u.username == "auto@test.com"


def test_email_unico(db):
    from django.db import IntegrityError

    Usuario.objects.create_user(email="dup@test.com", password="p")
    with pytest.raises(IntegrityError):
        Usuario.objects.create_user(email="dup@test.com", password="p2")  # pragma: allowlist secret


# --- Autenticação ---


def test_url_nao_publica_redireciona_para_login(client):
    response = client.get(reverse("accounts:perfil"))
    assert response.status_code == 302
    assert "/entrar/" in response["Location"]


def test_url_usuarios_redireciona_para_login(client):
    response = client.get(reverse("accounts:usuarios_lista"))
    assert response.status_code == 302
    assert "/entrar/" in response["Location"]


def test_login_com_email_e_senha_corretos(client, usuario_comum):
    response = client.post(
        reverse("accounts:login"),
        {"username": "comum@test.com", "password": "senha12345"},  # pragma: allowlist secret
    )
    assert response.status_code == 302


def test_login_com_senha_errada_nega_acesso(client, usuario_comum):
    response = client.post(
        reverse("accounts:login"),
        {"username": "comum@test.com", "password": "errada"},  # pragma: allowlist secret
    )
    assert response.status_code == 200
    assert "non_field_errors" in response.context["form"].errors or response.context["form"].errors


def test_logout_invalida_sessao(client, usuario_comum):
    client.force_login(usuario_comum)
    client.post(reverse("accounts:logout"))
    response = client.get(reverse("accounts:perfil"))
    assert response.status_code == 302


# --- Permissões ---


def test_usuario_comum_nao_acessa_lista_usuarios(client, usuario_comum):
    client.force_login(usuario_comum)
    response = client.get(reverse("accounts:usuarios_lista"))
    assert response.status_code == 403


def test_usuario_staff_acessa_lista_usuarios(client, usuario_staff):
    client.force_login(usuario_staff)
    response = client.get(reverse("accounts:usuarios_lista"))
    assert response.status_code == 200


def test_usuario_staff_cria_usuario(client, usuario_staff):
    client.force_login(usuario_staff)
    response = client.post(
        reverse("accounts:usuarios_criar"),
        {
            "email": "novo@test.com",
            "nome_completo": "Novo Usuário",
            "cargo": "Assessor",
            "is_staff": False,
            "password1": "novasenha123",  # pragma: allowlist secret
            "password2": "novasenha123",  # pragma: allowlist secret
        },
    )
    assert response.status_code == 302
    assert Usuario.objects.filter(email="novo@test.com").exists()


def test_usuario_comum_nao_cria_usuario(client, usuario_comum):
    client.force_login(usuario_comum)
    response = client.post(reverse("accounts:usuarios_criar"), {})
    assert response.status_code == 403


def test_usuario_staff_desativa_outro_usuario(client, usuario_staff, usuario_comum):
    client.force_login(usuario_staff)
    response = client.post(reverse("accounts:usuarios_toggle_ativo", args=[usuario_comum.pk]))
    assert response.status_code == 302
    usuario_comum.refresh_from_db()
    assert not usuario_comum.is_active


def test_usuario_staff_nao_desativa_si_mesmo(client, usuario_staff):
    client.force_login(usuario_staff)
    client.post(reverse("accounts:usuarios_toggle_ativo", args=[usuario_staff.pk]))
    usuario_staff.refresh_from_db()
    assert usuario_staff.is_active


# --- Senha ---


def test_senha_curta_rejeitada(client, usuario_staff):
    client.force_login(usuario_staff)
    response = client.post(
        reverse("accounts:usuarios_criar"),
        {
            "email": "fraca@test.com",
            "nome_completo": "Teste",
            "cargo": "",
            "is_staff": False,
            "password1": "123",
            "password2": "123",
        },
    )
    assert response.status_code == 200
    assert not Usuario.objects.filter(email="fraca@test.com").exists()


def test_senha_comum_rejeitada(client, usuario_staff):
    client.force_login(usuario_staff)
    response = client.post(
        reverse("accounts:usuarios_criar"),
        {
            "email": "comum2@test.com",
            "nome_completo": "Teste",
            "cargo": "",
            "is_staff": False,
            "password1": "password",  # pragma: allowlist secret
            "password2": "password",  # pragma: allowlist secret
        },
    )
    assert response.status_code == 200
    assert not Usuario.objects.filter(email="comum2@test.com").exists()


# --- Perfil ---


def test_perfil_atualiza_dados(client, usuario_comum):
    client.force_login(usuario_comum)
    client.post(
        reverse("accounts:perfil"),
        {"nome_completo": "Nome Novo", "cargo": "Cargo Novo"},
    )
    usuario_comum.refresh_from_db()
    assert usuario_comum.nome_completo == "Nome Novo"
    assert usuario_comum.cargo == "Cargo Novo"


# --- Management command ---


def test_criar_usuarios_iniciais(db, settings):
    settings.DEBUG = True
    call_command("criar_usuarios_iniciais")
    assert Usuario.objects.filter(email="admin@mpd.local").exists()
    assert Usuario.objects.filter(email="usuario@mpd.local").exists()
    admin = Usuario.objects.get(email="admin@mpd.local")
    assert admin.is_staff


def test_criar_usuarios_iniciais_idempotente(db, settings):
    settings.DEBUG = True
    call_command("criar_usuarios_iniciais")
    call_command("criar_usuarios_iniciais")
    assert Usuario.objects.filter(email="admin@mpd.local").count() == 1


def test_criar_usuarios_iniciais_aborta_em_producao(db, settings):
    """Comando recusa rodar com DEBUG=False — protege contra backdoor em prod."""
    from django.core.management.base import CommandError

    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("criar_usuarios_iniciais")
    assert not Usuario.objects.filter(email="admin@mpd.local").exists()


# --- Rate limiting (django-axes) ---


def test_axes_bloqueia_apos_5_falhas(client, usuario_comum, settings):
    """Axes bloqueia (IP+username) após 5 tentativas falhas — 6ª retorna 429."""
    settings.AXES_ENABLED = True

    for _ in range(5):
        client.post(
            reverse("accounts:login"),
            {"username": "comum@test.com", "password": "errada"},  # pragma: allowlist secret
        )

    response = client.post(
        reverse("accounts:login"),
        {"username": "comum@test.com", "password": "errada"},  # pragma: allowlist secret
    )
    # Ao locked, axes responde 429 (Too Many Requests) antes de validar a senha.
    assert response.status_code in (403, 429)
