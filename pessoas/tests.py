import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.urls import reverse

from pessoas.deduplicacao import buscar_similares
from pessoas.models import Entidade, Pessoa, Tag, Vinculo, validate_cpf

Usuario = get_user_model()


# --- Fixtures ---


@pytest.fixture
def usuario_admin(db):
    u = Usuario.objects.create_user(
        email="admin@test.com",
        password="senha12345",  # pragma: allowlist secret
        nome_completo="Admin",
        is_staff=True,
        is_superuser=True,
    )
    grupo = Group.objects.filter(name="Administrador").first()
    if grupo:
        u.groups.add(grupo)
    return u


@pytest.fixture
def usuario_assessor(db):
    u = Usuario.objects.create_user(
        email="assessor@test.com",
        password="senha12345",  # pragma: allowlist secret
        nome_completo="Assessor",
    )
    grupo = Group.objects.filter(name="Assessor").first()
    if grupo:
        u.groups.add(grupo)
    return u


@pytest.fixture
def usuario_coordenador(db):
    u = Usuario.objects.create_user(
        email="coord@test.com",
        password="senha12345",  # pragma: allowlist secret
        nome_completo="Coordenador",
    )
    grupo = Group.objects.filter(name="Coordenador").first()
    if grupo:
        u.groups.add(grupo)
    return u


@pytest.fixture
def pessoa_basica(db, usuario_admin):
    return Pessoa.objects.create(
        nome="Maria",
        sobrenome="Silva",
        email="maria@example.com",
        bairro="Centro",
        cidade="Vitória",
        estado="ES",
        criado_por=usuario_admin,
    )


# --- Validações de CPF ---


def test_cpf_valido():
    validate_cpf("529.982.247-25")


def test_cpf_invalido_digito():
    with pytest.raises(ValidationError):
        validate_cpf("529.982.247-99")


def test_cpf_repetido_invalido():
    with pytest.raises(ValidationError):
        validate_cpf("111.111.111-11")


def test_cpf_curto_invalido():
    with pytest.raises(ValidationError):
        validate_cpf("123")


# --- Pessoa: model ---


def test_pessoa_str_usa_nome_e_sobrenome(db, usuario_admin):
    p = Pessoa.objects.create(
        nome="João",
        sobrenome="Pereira",
        telefone="27999990000",
        bairro="Praia",
        cidade="Vitória",
        criado_por=usuario_admin,
    )
    assert str(p) == "João Pereira"


def test_pessoa_str_prioriza_nome_social(db, usuario_admin):
    p = Pessoa.objects.create(
        nome="João",
        sobrenome="Pereira",
        nome_social="Joana",
        telefone="27999990000",
        bairro="Praia",
        cidade="Vitória",
        criado_por=usuario_admin,
    )
    assert str(p) == "Joana"


def test_pessoa_anonimizada_oculta_nome(db, usuario_admin):
    p = Pessoa.objects.create(
        nome="Maria",
        sobrenome="Silva",
        email="x@y.com",
        bairro="X",
        cidade="Y",
        criado_por=usuario_admin,
    )
    p.anonimizar()
    assert str(p) == "[Pessoa Removida]"
    assert p.email == ""
    assert not p.ativo


def test_pessoa_exige_um_meio_de_contato(db, usuario_admin):
    p = Pessoa(nome="Sem", sobrenome="Contato", bairro="X", cidade="Y", criado_por=usuario_admin)
    with pytest.raises(ValidationError):
        p.full_clean()


def test_pessoa_aceita_apenas_whatsapp(db, usuario_admin):
    p = Pessoa(
        nome="Ana",
        sobrenome="Souza",
        whatsapp="(27) 99999-0000",
        bairro="X",
        cidade="Y",
        criado_por=usuario_admin,
    )
    p.full_clean()
    p.save()
    assert p.whatsapp == "27999990000"


def test_pessoa_cpf_invalido_falha_clean(db, usuario_admin):
    p = Pessoa(
        nome="X",
        sobrenome="Y",
        email="x@y.com",
        cpf="111.111.111-11",
        bairro="X",
        cidade="Y",
        criado_por=usuario_admin,
    )
    with pytest.raises(ValidationError):
        p.full_clean()


def test_pessoa_normaliza_telefone(db, usuario_admin):
    p = Pessoa.objects.create(
        nome="X",
        sobrenome="Y",
        telefone="(27) 99999-1234",
        bairro="A",
        cidade="B",
        criado_por=usuario_admin,
    )
    assert p.telefone == "27999991234"


def test_pessoa_formata_cep(db, usuario_admin):
    p = Pessoa.objects.create(
        nome="X",
        sobrenome="Y",
        email="x@y.com",
        cep="29010100",
        bairro="A",
        cidade="B",
        criado_por=usuario_admin,
    )
    assert p.cep == "29010-100"


def test_pessoa_cpf_unico_quando_preenchido(db, usuario_admin):
    Pessoa.objects.create(
        nome="A",
        sobrenome="B",
        email="a@b.com",
        cpf="529.982.247-25",
        bairro="X",
        cidade="Y",
        criado_por=usuario_admin,
    )
    from django.db import IntegrityError

    with pytest.raises(IntegrityError):
        Pessoa.objects.create(
            nome="C",
            sobrenome="D",
            email="c@d.com",
            cpf="529.982.247-25",
            bairro="X",
            cidade="Y",
            criado_por=usuario_admin,
        )


def test_pessoa_cpf_vazio_nao_conflita(db, usuario_admin):
    Pessoa.objects.create(
        nome="A",
        sobrenome="B",
        email="a@b.com",
        bairro="X",
        cidade="Y",
        criado_por=usuario_admin,
    )
    Pessoa.objects.create(
        nome="C",
        sobrenome="D",
        email="c@d.com",
        bairro="X",
        cidade="Y",
        criado_por=usuario_admin,
    )


# --- Entidade ---


def test_entidade_familia_aceita_apenas_nome_e_tipo(db, usuario_admin):
    e = Entidade.objects.create(nome="Família Silva", tipo="familia", criado_por=usuario_admin)
    e.full_clean()
    assert str(e) == "Família Silva"


def test_entidade_cnpj_invalido_falha(db, usuario_admin):
    e = Entidade(nome="X", tipo="empresa", cnpj="123", criado_por=usuario_admin)
    with pytest.raises(ValidationError):
        e.full_clean()


def test_entidade_formata_cnpj_no_save(db, usuario_admin):
    e = Entidade.objects.create(
        nome="X", tipo="empresa", cnpj="11222333000181", criado_por=usuario_admin
    )
    assert e.cnpj == "11.222.333/0001-81"


# --- Vínculo ---


def test_vinculo_data_fim_antes_inicio_falha(db, usuario_admin, pessoa_basica):
    e = Entidade.objects.create(nome="ONG X", tipo="ong", criado_por=usuario_admin)
    from datetime import date

    v = Vinculo(
        pessoa=pessoa_basica,
        entidade=e,
        papel="associado",
        data_inicio=date(2025, 6, 1),
        data_fim=date(2025, 1, 1),
    )
    with pytest.raises(ValidationError):
        v.full_clean()


# --- Tag ---


def test_tag_nome_unico(db):
    Tag.objects.create(nome="Saúde", categoria="tema")
    from django.db import IntegrityError

    with pytest.raises(IntegrityError):
        Tag.objects.create(nome="Saúde", categoria="tema")


# --- Deduplicação ---


def test_dedup_acha_pessoa_por_email(db, pessoa_basica):
    similares = buscar_similares(email="maria@example.com")
    assert pessoa_basica in similares


def test_dedup_ignora_pessoa_excluida(db, pessoa_basica):
    similares = buscar_similares(email="maria@example.com", excluir_pk=pessoa_basica.pk)
    assert pessoa_basica not in similares


def test_dedup_ignora_inativos(db, pessoa_basica):
    pessoa_basica.ativo = False
    pessoa_basica.save()
    assert buscar_similares(email="maria@example.com").count() == 0


def test_dedup_vazio_sem_criterios(db, pessoa_basica):
    assert buscar_similares().count() == 0


# --- Views: autenticação e permissão ---


def test_lista_pessoas_redireciona_anonimo(client, db):
    response = client.get(reverse("pessoas:pessoa_lista"))
    assert response.status_code == 302
    assert "/entrar/" in response["Location"]


def test_assessor_acessa_lista_pessoas(client, usuario_assessor):
    client.force_login(usuario_assessor)
    response = client.get(reverse("pessoas:pessoa_lista"))
    assert response.status_code == 200


def test_assessor_cria_pessoa(client, usuario_assessor):
    client.force_login(usuario_assessor)
    response = client.post(
        reverse("pessoas:pessoa_nova"),
        {
            "nome": "Pedro",
            "sobrenome": "Tester",
            "email": "pedro@example.com",
            "bairro": "Centro",
            "cidade": "Vitória",
            "estado": "ES",
        },
    )
    assert response.status_code == 302
    assert Pessoa.objects.filter(email="pedro@example.com").exists()


def test_assessor_nao_desativa_pessoa(client, usuario_assessor, pessoa_basica):
    client.force_login(usuario_assessor)
    client.post(reverse("pessoas:pessoa_toggle_ativo", args=[pessoa_basica.pk]))
    pessoa_basica.refresh_from_db()
    assert pessoa_basica.ativo  # continuou ativa


def test_coord_desativa_pessoa(client, usuario_coordenador, pessoa_basica):
    client.force_login(usuario_coordenador)
    client.post(reverse("pessoas:pessoa_toggle_ativo", args=[pessoa_basica.pk]))
    pessoa_basica.refresh_from_db()
    assert not pessoa_basica.ativo


def test_coord_nao_reativa_pessoa(client, usuario_coordenador, pessoa_basica):
    pessoa_basica.ativo = False
    pessoa_basica.save()
    client.force_login(usuario_coordenador)
    client.post(reverse("pessoas:pessoa_toggle_ativo", args=[pessoa_basica.pk]))
    pessoa_basica.refresh_from_db()
    assert not pessoa_basica.ativo  # CO não pode reativar


def test_admin_reativa_pessoa(client, usuario_admin, pessoa_basica):
    pessoa_basica.ativo = False
    pessoa_basica.save()
    client.force_login(usuario_admin)
    client.post(reverse("pessoas:pessoa_toggle_ativo", args=[pessoa_basica.pk]))
    pessoa_basica.refresh_from_db()
    assert pessoa_basica.ativo


def test_assessor_nao_cria_tag(client, usuario_assessor):
    client.force_login(usuario_assessor)
    response = client.post(reverse("pessoas:tag_nova"), {"nome": "Saúde", "categoria": "tema"})
    assert response.status_code == 403


def test_coord_cria_tag(client, usuario_coordenador):
    client.force_login(usuario_coordenador)
    response = client.post(
        reverse("pessoas:tag_nova"), {"nome": "Saúde", "categoria": "tema", "ativo": "on"}
    )
    assert response.status_code == 302
    assert Tag.objects.filter(nome="Saúde").exists()


# --- Lista: filtros e soft delete ---


def test_lista_padrao_oculta_inativos(client, usuario_assessor, pessoa_basica):
    pessoa_basica.ativo = False
    pessoa_basica.save()
    client.force_login(usuario_assessor)
    response = client.get(reverse("pessoas:pessoa_lista"))
    assert pessoa_basica not in response.context["pessoas"]


def test_lista_inativos_mostra_tudo(client, usuario_assessor, pessoa_basica):
    pessoa_basica.ativo = False
    pessoa_basica.save()
    client.force_login(usuario_assessor)
    response = client.get(reverse("pessoas:pessoa_lista") + "?inativos=1")
    assert pessoa_basica in response.context["pessoas"]


def test_lista_busca_por_nome(client, usuario_assessor, pessoa_basica):
    client.force_login(usuario_assessor)
    response = client.get(reverse("pessoas:pessoa_lista") + "?q=Maria")
    assert pessoa_basica in response.context["pessoas"]


# --- Endpoints auxiliares ---


def test_dedup_endpoint_anonimo_redireciona(client, db):
    response = client.get(reverse("pessoas:api_deduplicar") + "?email=x@y.com")
    assert response.status_code == 302


def test_dedup_endpoint_logado_responde_json(client, usuario_assessor, pessoa_basica):
    client.force_login(usuario_assessor)
    response = client.get(reverse("pessoas:api_deduplicar") + "?email=maria@example.com")
    assert response.status_code == 200
    data = response.json()
    assert any(r["email"] == "maria@example.com" for r in data["resultados"])


def test_dedup_endpoint_sem_permissao_403(client, db, pessoa_basica):
    """Usuário logado sem `view_pessoa` não pode usar o endpoint (vazaria PII)."""
    sem_grupo = Usuario.objects.create_user(
        email="semgrupo@test.com",
        password="senha12345",  # pragma: allowlist secret
        nome_completo="Sem Grupo",
    )
    client.force_login(sem_grupo)
    response = client.get(reverse("pessoas:api_deduplicar") + "?email=maria@example.com")
    assert response.status_code == 403


def test_cep_endpoint_invalido_404(client, usuario_assessor):
    client.force_login(usuario_assessor)
    response = client.get(reverse("pessoas:api_cep", args=["00000000"]))
    # ViaCEP responde com erro = retornamos 404; ou pode ser timeout (404 também)
    assert response.status_code == 404


# --- Grupos padrão da data migration ---


def test_grupos_padrao_existem(db):
    nomes = set(Group.objects.values_list("name", flat=True))
    assert {"Administrador", "Chefe de Gabinete", "Coordenador", "Assessor"} <= nomes


def test_grupo_assessor_tem_view_pessoa(db):
    grupo = Group.objects.get(name="Assessor")
    assert grupo.permissions.filter(codename="view_pessoa").exists()


def test_grupo_assessor_nao_tem_add_tag(db):
    grupo = Group.objects.get(name="Assessor")
    assert not grupo.permissions.filter(codename="add_tag").exists()


def test_grupo_coordenador_tem_pode_desativar_pessoa(db):
    grupo = Group.objects.get(name="Coordenador")
    assert grupo.permissions.filter(codename="pode_desativar_pessoa").exists()


def test_grupo_coordenador_nao_tem_pode_reativar_pessoa(db):
    grupo = Group.objects.get(name="Coordenador")
    assert not grupo.permissions.filter(codename="pode_reativar_pessoa").exists()


def test_grupo_administrador_tem_delete_pessoa(db):
    grupo = Group.objects.get(name="Administrador")
    assert grupo.permissions.filter(codename="delete_pessoa").exists()


def test_grupo_chefe_de_gabinete_nao_tem_delete_pessoa(db):
    grupo = Group.objects.get(name="Chefe de Gabinete")
    assert not grupo.permissions.filter(codename="delete_pessoa").exists()


# --- Auditlog (LGPD) ---


def test_auditlog_registra_criacao_de_pessoa(db, usuario_admin):
    """Confirma que auditlog cria LogEntry ao criar Pessoa.

    Garante a trilha LGPD ('quem criou, quando, o quê'). Os models Entidade,
    Vínculo e Tag são registrados no mesmo apps.ready(); um teste cobre o setup.
    """
    from auditlog.models import LogEntry

    pessoa = Pessoa.objects.create(
        nome="Auditoria",
        sobrenome="Teste",
        email="audit@example.com",
        bairro="X",
        cidade="Y",
        criado_por=usuario_admin,
    )
    entries = LogEntry.objects.get_for_object(pessoa)
    assert entries.filter(action=LogEntry.Action.CREATE).exists()


def test_auditlog_registra_alteracao_de_pessoa(db, pessoa_basica):
    from auditlog.models import LogEntry

    pessoa_basica.bairro = "Bairro Novo"
    pessoa_basica.save()
    entries = LogEntry.objects.get_for_object(pessoa_basica)
    assert entries.filter(action=LogEntry.Action.UPDATE).exists()
