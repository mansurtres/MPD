import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.urls import reverse

from core.utils import validate_cpf
from pessoas.deduplicacao import buscar_similares
from pessoas.models import (
    EmailPessoa,
    Entidade,
    Pessoa,
    RedeSocial,
    Tag,
    Telefone,
    Vinculo,
)

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
    p = Pessoa.objects.create(
        nome="Maria",
        sobrenome="Silva",
        bairro="Centro",
        cidade="Vitória",
        estado="ES",
        criado_por=usuario_admin,
    )
    EmailPessoa.objects.create(pessoa=p, endereco="maria@example.com")
    return p


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
        bairro="Praia",
        cidade="Vitória",
        criado_por=usuario_admin,
    )
    assert str(p) == "Joana"


def test_pessoa_anonimizada_apaga_canais(db, usuario_admin):
    p = Pessoa.objects.create(
        nome="Maria",
        sobrenome="Silva",
        bairro="X",
        cidade="Y",
        criado_por=usuario_admin,
    )
    Telefone.objects.create(pessoa=p, numero="27999990000", tipo="celular")
    EmailPessoa.objects.create(pessoa=p, endereco="x@y.com")
    RedeSocial.objects.create(pessoa=p, plataforma="instagram", valor="maria")
    p.anonimizar()
    assert str(p) == "[Pessoa Removida]"
    assert not p.ativo
    assert p.telefones.count() == 0
    assert p.emails.count() == 0
    assert p.redes_sociais.count() == 0


def test_pessoa_tem_meio_de_contato_so_email(db, usuario_admin):
    p = Pessoa.objects.create(
        nome="Sem",
        sobrenome="Telefone",
        bairro="X",
        cidade="Y",
        criado_por=usuario_admin,
    )
    assert not p.tem_meio_de_contato()
    EmailPessoa.objects.create(pessoa=p, endereco="sem@tel.com")
    assert p.tem_meio_de_contato()


def test_pessoa_tem_meio_de_contato_so_telefone(db, usuario_admin):
    p = Pessoa.objects.create(
        nome="Sem",
        sobrenome="Email",
        bairro="X",
        cidade="Y",
        criado_por=usuario_admin,
    )
    assert not p.tem_meio_de_contato()
    Telefone.objects.create(pessoa=p, numero="27999990000", tipo="celular")
    assert p.tem_meio_de_contato()


def test_pessoa_tem_meio_de_contato_so_rede_social(db, usuario_admin):
    p = Pessoa.objects.create(
        nome="Sem",
        sobrenome="Tudo",
        bairro="X",
        cidade="Y",
        criado_por=usuario_admin,
    )
    assert not p.tem_meio_de_contato()
    RedeSocial.objects.create(pessoa=p, plataforma="instagram", valor="usuario")
    assert p.tem_meio_de_contato()


def test_pessoa_cpf_invalido_falha_clean(db, usuario_admin):
    p = Pessoa(
        nome="X",
        sobrenome="Y",
        cpf="111.111.111-11",
        bairro="X",
        cidade="Y",
        criado_por=usuario_admin,
    )
    with pytest.raises(ValidationError):
        p.full_clean()


def test_pessoa_form_renderiza_data_nascimento_em_iso(db, usuario_admin):
    # Regressão: <input type="date"> só aceita YYYY-MM-DD; sem format= explícito,
    # widget renderizava DD/MM/YYYY (locale pt-br) e browser zerava o campo,
    # fazendo edições inocentes apagarem a data.
    from datetime import date

    from pessoas.forms import PessoaForm

    p = Pessoa.objects.create(
        nome="A",
        sobrenome="B",
        bairro="X",
        cidade="Y",
        data_nascimento=date(1994, 4, 30),
        criado_por=usuario_admin,
    )
    html = PessoaForm(instance=p).as_p()
    assert 'value="1994-04-30"' in html


def test_pessoa_formata_cep(db, usuario_admin):
    p = Pessoa.objects.create(
        nome="X",
        sobrenome="Y",
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
            cpf="529.982.247-25",
            bairro="X",
            cidade="Y",
            criado_por=usuario_admin,
        )


def test_pessoa_cpf_vazio_nao_conflita(db, usuario_admin):
    Pessoa.objects.create(
        nome="A",
        sobrenome="B",
        bairro="X",
        cidade="Y",
        criado_por=usuario_admin,
    )
    Pessoa.objects.create(
        nome="C",
        sobrenome="D",
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
    Tag.objects.create(nome="Saúde")
    from django.db import IntegrityError

    with pytest.raises(IntegrityError):
        Tag.objects.create(nome="Saúde")


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


def _management_forms_vazios():
    """Retorna dict com os management forms de telefones/emails/redes vazios."""
    out = {}
    for prefix in ("telefones", "emails", "redes_sociais"):
        out[f"{prefix}-TOTAL_FORMS"] = "0"
        out[f"{prefix}-INITIAL_FORMS"] = "0"
        out[f"{prefix}-MIN_NUM_FORMS"] = "0"
        out[f"{prefix}-MAX_NUM_FORMS"] = "1000"
    return out


def test_assessor_cria_pessoa_com_email(client, usuario_assessor):
    client.force_login(usuario_assessor)
    payload = {
        "nome": "Pedro",
        "sobrenome": "Tester",
        "bairro": "Centro",
        "cidade": "Vitória",
        "estado": "ES",
        **_management_forms_vazios(),
        "emails-TOTAL_FORMS": "1",
        "emails-0-endereco": "pedro@example.com",
        "emails-0-rotulo": "",
    }
    response = client.post(reverse("pessoas:pessoa_nova"), payload)
    assert response.status_code == 302, response.content[:500]
    p = Pessoa.objects.get(nome="Pedro", sobrenome="Tester")
    assert p.emails.count() == 1
    assert p.emails.first().endereco == "pedro@example.com"


def test_pessoa_view_exige_pelo_menos_um_canal(client, usuario_assessor):
    client.force_login(usuario_assessor)
    payload = {
        "nome": "Sem",
        "sobrenome": "Contato",
        "bairro": "X",
        "cidade": "Y",
        "estado": "ES",
        **_management_forms_vazios(),
    }
    response = client.post(reverse("pessoas:pessoa_nova"), payload)
    assert response.status_code == 200
    assert "canal de contato" in response.content.decode()
    assert not Pessoa.objects.filter(nome="Sem").exists()


def test_pessoa_view_aceita_apenas_telefone(client, usuario_assessor):
    client.force_login(usuario_assessor)
    payload = {
        "nome": "Ana",
        "sobrenome": "Souza",
        "bairro": "X",
        "cidade": "Y",
        "estado": "ES",
        **_management_forms_vazios(),
        "telefones-TOTAL_FORMS": "1",
        "telefones-0-numero": "(27) 99999-0000",
        "telefones-0-tipo": "celular",
        "telefones-0-eh_whatsapp": "on",
        "telefones-0-rotulo": "",
    }
    response = client.post(reverse("pessoas:pessoa_nova"), payload)
    assert response.status_code == 302, response.content[:500]
    p = Pessoa.objects.get(nome="Ana")
    assert p.telefones.count() == 1
    tel = p.telefones.first()
    assert tel.numero == "27999990000"
    assert tel.eh_whatsapp


def test_pessoa_view_aceita_apenas_rede_social(client, usuario_assessor):
    client.force_login(usuario_assessor)
    payload = {
        "nome": "Beto",
        "sobrenome": "Silva",
        "bairro": "X",
        "cidade": "Y",
        "estado": "ES",
        **_management_forms_vazios(),
        "redes_sociais-TOTAL_FORMS": "1",
        "redes_sociais-0-plataforma": "instagram",
        "redes_sociais-0-valor": "@beto",
        "redes_sociais-0-rotulo": "",
    }
    response = client.post(reverse("pessoas:pessoa_nova"), payload)
    assert response.status_code == 302, response.content[:500]
    p = Pessoa.objects.get(nome="Beto")
    assert p.redes_sociais.count() == 1
    rs = p.redes_sociais.first()
    assert rs.plataforma == "instagram"
    assert rs.valor == "beto"  # @ removido no save


def test_pessoa_view_post_sem_management_forms_redireciona(client, usuario_assessor):
    """POST malformado (sem TOTAL_FORMS) → flash + redirect ao GET."""
    client.force_login(usuario_assessor)
    response = client.post(
        reverse("pessoas:pessoa_nova"),
        {"nome": "X", "sobrenome": "Y", "bairro": "X", "cidade": "Y"},
    )
    assert response.status_code == 302


# --- Telefone: model ---


def test_telefone_celular_11_digitos_aceita(db, pessoa_basica):
    t = Telefone(pessoa=pessoa_basica, numero="(27) 99999-0000", tipo="celular")
    t.full_clean()
    t.save()
    assert t.numero == "27999990000"


def test_telefone_celular_sem_9_apos_ddd_rejeita(db, pessoa_basica):
    t = Telefone(pessoa=pessoa_basica, numero="(27) 33333-4444", tipo="celular")
    with pytest.raises(ValidationError):
        t.full_clean()


def test_telefone_celular_sem_ddd_rejeita(db, pessoa_basica):
    t = Telefone(pessoa=pessoa_basica, numero="999990000", tipo="celular")
    with pytest.raises(ValidationError):
        t.full_clean()


def test_telefone_fixo_10_digitos_aceita(db, pessoa_basica):
    t = Telefone(pessoa=pessoa_basica, numero="(27) 3333-4444", tipo="fixo")
    t.full_clean()
    t.save()
    assert t.numero == "2733334444"


def test_telefone_fixo_11_digitos_rejeita(db, pessoa_basica):
    t = Telefone(pessoa=pessoa_basica, numero="(27) 99999-0000", tipo="fixo")
    with pytest.raises(ValidationError):
        t.full_clean()


def test_telefone_eh_whatsapp_so_em_celular(db, pessoa_basica):
    t = Telefone(pessoa=pessoa_basica, numero="(27) 3333-4444", tipo="fixo", eh_whatsapp=True)
    with pytest.raises(ValidationError):
        t.full_clean()


def test_telefone_numero_formatado_celular(db, pessoa_basica):
    t = Telefone.objects.create(pessoa=pessoa_basica, numero="27999990000", tipo="celular")
    assert t.numero_formatado == "(27) 99999-0000"


def test_telefone_numero_formatado_fixo(db, pessoa_basica):
    t = Telefone.objects.create(pessoa=pessoa_basica, numero="2733334444", tipo="fixo")
    assert t.numero_formatado == "(27) 3333-4444"


# --- EmailPessoa ---


def test_email_normaliza_lowercase_no_save(db, pessoa_basica):
    e = EmailPessoa.objects.create(pessoa=pessoa_basica, endereco="  Maria@Example.COM  ")
    assert e.endereco == "maria@example.com"


# --- RedeSocial ---


def test_rede_social_outro_exige_rotulo(db, pessoa_basica):
    r = RedeSocial(pessoa=pessoa_basica, plataforma="outro", valor="@x")
    with pytest.raises(ValidationError):
        r.full_clean()


def test_rede_social_outro_com_rotulo_aceita(db, pessoa_basica):
    r = RedeSocial(pessoa=pessoa_basica, plataforma="outro", valor="@x", rotulo="Threads")
    r.full_clean()


def test_rede_social_remove_arroba_no_save(db, pessoa_basica):
    r = RedeSocial.objects.create(pessoa=pessoa_basica, plataforma="instagram", valor="@maria")
    assert r.valor == "maria"


def test_rede_social_str(db, pessoa_basica):
    r = RedeSocial.objects.create(pessoa=pessoa_basica, plataforma="linkedin", valor="maria")
    assert "LinkedIn" in str(r)


def test_assessor_nao_desativa_pessoa(client, usuario_assessor, pessoa_basica):
    client.force_login(usuario_assessor)
    response = client.post(
        reverse("pessoas:pessoa_toggle_ativo", kwargs={"slug": pessoa_basica.slug_publico})
    )
    assert response.status_code == 403
    pessoa_basica.refresh_from_db()
    assert pessoa_basica.ativo  # continuou ativa


def test_coord_desativa_pessoa(client, usuario_coordenador, pessoa_basica):
    client.force_login(usuario_coordenador)
    client.post(reverse("pessoas:pessoa_toggle_ativo", kwargs={"slug": pessoa_basica.slug_publico}))
    pessoa_basica.refresh_from_db()
    assert not pessoa_basica.ativo


def test_coord_nao_reativa_pessoa(client, usuario_coordenador, pessoa_basica):
    pessoa_basica.ativo = False
    pessoa_basica.save()
    client.force_login(usuario_coordenador)
    response = client.post(
        reverse("pessoas:pessoa_toggle_ativo", kwargs={"slug": pessoa_basica.slug_publico})
    )
    assert response.status_code == 403
    pessoa_basica.refresh_from_db()
    assert not pessoa_basica.ativo  # CO não pode reativar


def test_admin_reativa_pessoa(client, usuario_admin, pessoa_basica):
    pessoa_basica.ativo = False
    pessoa_basica.save()
    client.force_login(usuario_admin)
    client.post(reverse("pessoas:pessoa_toggle_ativo", kwargs={"slug": pessoa_basica.slug_publico}))
    pessoa_basica.refresh_from_db()
    assert pessoa_basica.ativo


def test_assessor_nao_cria_tag(client, usuario_assessor):
    client.force_login(usuario_assessor)
    response = client.post(reverse("pessoas:tag_nova"), {"nome": "Saúde"})
    assert response.status_code == 403


def test_coord_cria_tag(client, usuario_coordenador):
    client.force_login(usuario_coordenador)
    response = client.post(reverse("pessoas:tag_nova"), {"nome": "Saúde", "ativo": "on"})
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


def test_cep_endpoint_sem_permissao_403(client, db):
    """Usuário sem view_pessoa não pode consultar CEP via app."""
    sem_grupo = Usuario.objects.create_user(
        email="semgrupo_cep@test.com",
        password="senha12345",  # pragma: allowlist secret
        nome_completo="Sem Grupo",
    )
    client.force_login(sem_grupo)
    response = client.get(reverse("pessoas:api_cep", args=["29010100"]))
    assert response.status_code == 403


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
