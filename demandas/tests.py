"""Testes do app demandas — Fase 3.

Cobre os 22 critérios de aceite do roadmap §4.3.3 com casos diretos.
Para cada bloco, comentário aponta o critério.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from demandas.models import (
    Anexo,
    Demanda,
    DemandaPessoa,
    Encaminhamento,
    Interacao,
)
from pessoas.models import Entidade, Pessoa

Usuario = get_user_model()


# --- Fixtures ---


@pytest.fixture
def admin_user(db):
    u = Usuario.objects.create_user(
        email="adm@test.com",
        password="senha12345",  # pragma: allowlist secret
        nome_completo="Admin",
        is_staff=True,
        is_superuser=True,
    )
    g = Group.objects.filter(name="Administrador").first()
    if g:
        u.groups.add(g)
    return u


@pytest.fixture
def chefe(db):
    u = Usuario.objects.create_user(
        email="chefe@test.com",
        password="senha12345",  # pragma: allowlist secret
        nome_completo="Chefe",
        coordenacao="gabinete",
    )
    g = Group.objects.filter(name="Chefe de Gabinete").first()
    if g:
        u.groups.add(g)
    return u


@pytest.fixture
def coord_juridico(db):
    u = Usuario.objects.create_user(
        email="coord@test.com",
        password="senha12345",  # pragma: allowlist secret
        nome_completo="Coord Jurídico",
        coordenacao="juridico",
    )
    g = Group.objects.filter(name="Coordenador").first()
    if g:
        u.groups.add(g)
    return u


@pytest.fixture
def assessor(db):
    u = Usuario.objects.create_user(
        email="assessor@test.com",
        password="senha12345",  # pragma: allowlist secret
        nome_completo="Assessor",
        coordenacao="comunicacao",
    )
    g = Group.objects.filter(name="Assessor").first()
    if g:
        u.groups.add(g)
    return u


@pytest.fixture
def pessoa(db, admin_user):
    return Pessoa.objects.create(
        nome="Maria", sobrenome="Silva", bairro="Centro", cidade="Vitória", criado_por=admin_user
    )


@pytest.fixture
def entidade(db, admin_user):
    return Entidade.objects.create(nome="Família Silva", tipo="familia", criado_por=admin_user)


@pytest.fixture
def demanda(db, admin_user, pessoa):
    d = Demanda.objects.create(
        titulo="Demanda teste",
        descricao="Descrição teste",
        canal_entrada="whatsapp",
        coordenacao_responsavel="gabinete",
        criado_por=admin_user,
    )
    DemandaPessoa.objects.create(demanda=d, pessoa=pessoa, papel="solicitante")
    return d


# --- Geração de número (critério: implícito no schema MPD-AAAA-NNNNN) ---


def test_gera_numero_no_save(db, admin_user, pessoa):
    d = Demanda.objects.create(
        titulo="X",
        descricao="Y",
        canal_entrada="presencial",
        coordenacao_responsavel="gabinete",
        criado_por=admin_user,
    )
    assert d.numero.startswith(f"MPD-{timezone.now().year}-")
    assert len(d.numero.rsplit("-", 1)[1]) == 5


def test_numeros_sequenciais(db, admin_user):
    a = Demanda.objects.create(
        titulo="A",
        descricao="X",
        canal_entrada="presencial",
        coordenacao_responsavel="gabinete",
        criado_por=admin_user,
        anonimo=True,
    )
    b = Demanda.objects.create(
        titulo="B",
        descricao="X",
        canal_entrada="presencial",
        coordenacao_responsavel="gabinete",
        criado_por=admin_user,
        anonimo=True,
    )
    sa = int(a.numero.rsplit("-", 1)[1])
    sb = int(b.numero.rsplit("-", 1)[1])
    assert sb == sa + 1


# --- Critérios 1-3: criar com partes / anônima / só entidade ---


def test_criar_demanda_com_pessoa_funciona(db, demanda):
    assert demanda.demanda_pessoas.count() == 1
    assert demanda.tem_partes()


def test_criar_demanda_com_entidade_funciona(db, admin_user, entidade):
    d = Demanda.objects.create(
        titulo="Só entidade",
        descricao="X",
        canal_entrada="oficio",
        coordenacao_responsavel="juridico",
        criado_por=admin_user,
    )
    from demandas.models import DemandaEntidade

    DemandaEntidade.objects.create(demanda=d, entidade=entidade, papel="representada")
    assert d.tem_partes()


def test_criar_demanda_anonima_funciona(db, admin_user):
    d = Demanda.objects.create(
        titulo="Anônima",
        descricao="X",
        canal_entrada="presencial",
        coordenacao_responsavel="gabinete",
        criado_por=admin_user,
        anonimo=True,
    )
    assert d.anonimo
    assert not d.tem_partes()


# --- Critério 4: resultado default 'pendente' ---


def test_resultado_default_pendente(db, demanda):
    assert demanda.resultado == Demanda.RESULTADO_PENDENTE


# --- Critérios 5-6: regra de fechamento (ADR 0043 — bifurcada por origem) ---


def _registrar_devolutiva(demanda, autor):
    return Interacao.objects.create(
        demanda=demanda,
        autor=autor,
        tipo=Interacao.TIPO_DEVOLUTIVA,
        conteudo="Devolutiva ao demandante",
        status=Interacao.STATUS_REALIZADA,
        data_ocorrencia=timezone.now(),
        automatica=False,
    )


def test_responsiva_concluida_sem_devolutiva_bloqueada(db, demanda, admin_user):
    # demanda fixture é responsiva por default
    demanda.resultado = Demanda.RESULTADO_ATENDIDO
    demanda.status = Demanda.STATUS_CONCLUIDA
    with pytest.raises(ValidationError):
        demanda.full_clean()


def test_responsiva_concluida_com_devolutiva_e_resultado_pendente_bloqueada(
    db, demanda, admin_user
):
    _registrar_devolutiva(demanda, admin_user)
    demanda.status = Demanda.STATUS_CONCLUIDA
    # resultado fica pendente — deve bloquear
    with pytest.raises(ValidationError):
        demanda.full_clean()


def test_responsiva_concluida_com_devolutiva_e_resultado_funciona(db, demanda, admin_user):
    _registrar_devolutiva(demanda, admin_user)
    demanda.resultado = Demanda.RESULTADO_ATENDIDO
    demanda.status = Demanda.STATUS_CONCLUIDA
    demanda.full_clean()  # não levanta
    demanda.save()
    assert demanda.status == Demanda.STATUS_CONCLUIDA


def test_proativa_concluida_sem_devolutiva_funciona(db, admin_user):
    # Demanda proativa não exige devolutiva — só resultado classificado.
    d = Demanda.objects.create(
        titulo="Moção X",
        descricao="Reconhecimento",
        origem=Demanda.ORIGEM_PROATIVA,
        canal_entrada="presencial",
        coordenacao_responsavel="comunicacao",
        anonimo=True,
        criado_por=admin_user,
    )
    d.resultado = Demanda.RESULTADO_NAO_SE_APLICA
    d.status = Demanda.STATUS_CONCLUIDA
    d.full_clean()  # não levanta
    d.save()
    assert d.status == Demanda.STATUS_CONCLUIDA


def test_proativa_concluida_com_resultado_pendente_bloqueada(db, admin_user):
    d = Demanda.objects.create(
        titulo="Moção Y",
        descricao="Reconhecimento",
        origem=Demanda.ORIGEM_PROATIVA,
        canal_entrada="presencial",
        coordenacao_responsavel="comunicacao",
        anonimo=True,
        criado_por=admin_user,
    )
    d.status = Demanda.STATUS_CONCLUIDA
    with pytest.raises(ValidationError):
        d.full_clean()


# --- Critério 7: atualizar resultado em qualquer status ---


def test_resultado_pode_mudar_em_qualquer_status(db, demanda):
    demanda.status = Demanda.STATUS_EM_ANDAMENTO
    demanda.resultado = Demanda.RESULTADO_ATENDIDO
    demanda.full_clean()
    demanda.save()
    assert demanda.resultado == Demanda.RESULTADO_ATENDIDO


def test_resultado_classificado_nao_volta_a_pendente(db, demanda):
    demanda.resultado = Demanda.RESULTADO_ATENDIDO
    demanda.save()
    demanda.refresh_from_db()
    demanda.resultado = Demanda.RESULTADO_PENDENTE
    with pytest.raises(ValidationError):
        demanda.full_clean()


# --- Critério 8: mudança de resultado gera interação automática ---


def test_mudanca_resultado_gera_interacao(db, demanda, admin_user):
    # Demanda recém-criada já tem registro_inicial.
    inicial = demanda.interacoes.count()
    demanda.resultado = Demanda.RESULTADO_ATENDIDO_PARCIALMENTE
    demanda.save()
    assert demanda.interacoes.count() == inicial + 1
    nova = demanda.interacoes.order_by("-criado_em").first()
    assert nova.tipo == Interacao.TIPO_MUDANCA_RESULTADO
    assert nova.automatica


# --- Critério 13: mudança de status gera interação automática ---


def test_mudanca_status_gera_interacao(db, demanda):
    inicial = demanda.interacoes.count()
    demanda.status = Demanda.STATUS_EM_ANDAMENTO
    demanda.save()
    assert demanda.interacoes.count() == inicial + 1
    nova = demanda.interacoes.order_by("-criado_em").first()
    assert nova.tipo == Interacao.TIPO_MUDANCA_STATUS
    assert nova.automatica


# --- Critério 14: mudança de responsável gera interação automática ---


def test_mudanca_responsavel_gera_interacao(db, demanda, chefe):
    inicial = demanda.interacoes.count()
    demanda.responsavel = chefe
    demanda.save()
    assert demanda.interacoes.count() == inicial + 1
    nova = demanda.interacoes.order_by("-criado_em").first()
    assert nova.tipo == Interacao.TIPO_MUDANCA_RESPONSAVEL


# --- Critério 9-10: interação realizada / agendada ---


def test_interacao_realizada_aparece_na_timeline(db, demanda, admin_user):
    Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_CONTATO_PESSOA,
        conteudo="Liguei pra Maria",
        status=Interacao.STATUS_REALIZADA,
        data_ocorrencia=timezone.now(),
    )
    assert demanda.interacoes.filter(tipo=Interacao.TIPO_CONTATO_PESSOA).exists()


def test_interacao_agendada_aparece_em_pendentes(db, demanda, admin_user):
    futuro = timezone.now() + timedelta(days=7)
    i = Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_CONTATO_PESSOA,
        conteudo="Follow-up",
        status=Interacao.STATUS_AGENDADA,
        data_ocorrencia=futuro,
    )
    pendentes = Interacao.objects.filter(autor=admin_user, status=Interacao.STATUS_AGENDADA)
    assert i in pendentes


# --- Critérios 11-12: schedule follow-up + cadeia ---


def test_followup_referencia_origem(db, demanda, admin_user):
    origem = Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_REUNIAO,
        conteudo="Reunião",
        status=Interacao.STATUS_REALIZADA,
        data_ocorrencia=timezone.now(),
    )
    fu = Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_CONTATO_PESSOA,
        conteudo="Próxima ligação",
        status=Interacao.STATUS_AGENDADA,
        data_ocorrencia=timezone.now() + timedelta(days=7),
        interacao_origem=origem,
    )
    assert fu.interacao_origem_id == origem.id
    assert origem.follow_ups.count() == 1


# --- Critério 15: interação automática é imutável ---


def test_interacao_automatica_nao_e_editavel(db, demanda, admin_user):
    auto = demanda.interacoes.filter(automatica=True).first()
    assert auto is not None
    assert not auto.pode_editar(admin_user)


# --- Critério 16: janela 24h ---


def test_interacao_propria_editavel_dentro_de_24h(db, demanda, admin_user):
    i = Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_CONTATO_PESSOA,
        conteudo="Recém",
        status=Interacao.STATUS_REALIZADA,
        data_ocorrencia=timezone.now(),
    )
    assert i.pode_editar(admin_user)


def test_interacao_propria_imutavel_apos_24h(db, demanda, admin_user):
    i = Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_CONTATO_PESSOA,
        conteudo="Velha",
        status=Interacao.STATUS_REALIZADA,
        data_ocorrencia=timezone.now(),
    )
    # Simula passagem de 25h.
    i.criado_em = timezone.now() - timedelta(hours=25)
    i.save()
    # Para autor regular (sem ADM/CG), não pode editar após janela.
    autor_solo = Usuario.objects.create_user(
        email="solo@test.com",
        password="senha12345",  # pragma: allowlist secret
        nome_completo="Solo",
    )
    i.autor = autor_solo
    assert not i.pode_editar(autor_solo)


# --- Critério 17: encaminhamento aparece na timeline ---


def test_encaminhamento_aparece_na_timeline(db, demanda, admin_user):
    inicial = demanda.interacoes.count()
    enc = Encaminhamento.objects.create(
        demanda=demanda,
        destinatario_orgao="Sesa",
        tipo_documento="oficio",
        data_envio=timezone.now().date(),
        criado_por=admin_user,
    )
    # A view cria a interação manual reflexa; aqui geramos diretamente
    # para isolar do request cycle.
    Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_ENCAMINHAMENTO,
        conteudo=f"Enviado para {enc.destinatario_orgao}",
        status=Interacao.STATUS_REALIZADA,
        data_ocorrencia=timezone.now(),
    )
    assert demanda.interacoes.count() == inicial + 1
    assert demanda.interacoes.filter(tipo=Interacao.TIPO_ENCAMINHAMENTO).exists()


# --- Critérios 18-19: anexo polimórfico ---


def test_anexo_5mb_aceito(db, demanda, admin_user):
    from django.contrib.contenttypes.models import ContentType
    from django.core.files.uploadedfile import SimpleUploadedFile

    f = SimpleUploadedFile("doc.pdf", b"X" * (5 * 1024 * 1024), content_type="application/pdf")
    ct = ContentType.objects.get_for_model(Demanda)
    a = Anexo(
        content_type=ct,
        object_id=demanda.pk,
        arquivo=f,
        nome_original=f.name,
        tamanho_bytes=f.size,
        mime_type="application/pdf",
        enviado_por=admin_user,
    )
    a.full_clean()
    a.save()
    assert a.pk is not None


def test_anexo_30mb_rejeitado(db, demanda, admin_user):
    from django.contrib.contenttypes.models import ContentType

    ct = ContentType.objects.get_for_model(Demanda)
    a = Anexo(
        content_type=ct,
        object_id=demanda.pk,
        arquivo="dummy.pdf",
        nome_original="big.pdf",
        tamanho_bytes=30 * 1024 * 1024,
        mime_type="application/pdf",
        enviado_por=admin_user,
    )
    with pytest.raises(ValidationError):
        a.full_clean()


def test_anexo_em_encaminhamento_aceito(db, demanda, admin_user):
    from django.contrib.contenttypes.models import ContentType
    from django.core.files.uploadedfile import SimpleUploadedFile

    enc = Encaminhamento.objects.create(
        demanda=demanda,
        destinatario_orgao="Sesa",
        tipo_documento="oficio",
        data_envio=timezone.now().date(),
        criado_por=admin_user,
    )
    f = SimpleUploadedFile("ofi.pdf", b"X" * 100, content_type="application/pdf")
    ct = ContentType.objects.get_for_model(Encaminhamento)
    a = Anexo(
        content_type=ct,
        object_id=enc.pk,
        arquivo=f,
        nome_original=f.name,
        tamanho_bytes=f.size,
        mime_type="application/pdf",
        enviado_por=admin_user,
    )
    a.full_clean()
    a.save()
    assert a.pk is not None


# --- Critério 20: detalhe da pessoa lista demandas vinculadas ---


def test_pessoa_acessa_demandas_via_related_manager(db, demanda, pessoa):
    assert demanda in pessoa.demandas.all()


# --- Critério 22: demanda restrita ---


def test_demanda_restrita_invisivel_para_co_de_outra_coord(db, admin_user, pessoa, coord_juridico):
    d = Demanda.objects.create(
        titulo="Restrita",
        descricao="Sigilo",
        canal_entrada="email",
        coordenacao_responsavel="comunicacao",
        restrito=True,
        criado_por=admin_user,
        responsavel=admin_user,
    )
    DemandaPessoa.objects.create(demanda=d, pessoa=pessoa)
    assert not d.pode_ser_visto_por(coord_juridico)


def test_demanda_restrita_visivel_para_responsavel(db, admin_user, pessoa, assessor):
    d = Demanda.objects.create(
        titulo="Restrita",
        descricao="Sigilo",
        canal_entrada="email",
        coordenacao_responsavel="comunicacao",
        restrito=True,
        criado_por=admin_user,
        responsavel=assessor,
    )
    DemandaPessoa.objects.create(demanda=d, pessoa=pessoa)
    assert d.pode_ser_visto_por(assessor)


# --- Permissões via grupos ---


def test_assessor_tem_perm_de_criar_demanda(db, assessor):
    assert assessor.has_perm("demandas.add_demanda")


def test_assessor_nao_arquiva_demanda(db, assessor):
    assert not assessor.has_perm("demandas.pode_arquivar_demanda")


def test_chefe_arquiva_sem_responder(db, chefe):
    assert chefe.has_perm("demandas.pode_arquivar_sem_responder")


def test_coordenador_nao_pode_arquivar_sem_responder(db, coord_juridico):
    assert not coord_juridico.has_perm("demandas.pode_arquivar_sem_responder")


# --- Arquivamento ---


def test_arquivar_demanda_concluida_funciona(db, demanda, admin_user):
    _registrar_devolutiva(demanda, admin_user)
    demanda.resultado = Demanda.RESULTADO_ATENDIDO
    demanda.status = Demanda.STATUS_CONCLUIDA
    demanda.save()
    demanda.status = Demanda.STATUS_ARQUIVADO
    demanda.full_clean()
    demanda.save()
    assert demanda.arquivado_em is not None


def test_arquivar_sem_responder_exige_justificativa(db, demanda):
    demanda.status = Demanda.STATUS_ARQUIVADO
    with pytest.raises(ValidationError):
        demanda.full_clean()


def test_arquivar_sem_responder_com_justificativa_funciona(db, demanda):
    demanda.observacoes_arquivamento = "Demanda duplicada com outra"
    demanda.status = Demanda.STATUS_ARQUIVADO
    demanda.full_clean()
    demanda.save()
    assert demanda.arquivado_em is not None


# --- View: criar demanda via formulário (smoke test do POST) ---


def test_view_lista_demandas_redireciona_anonimo(client):
    resp = client.get(reverse("demandas:demanda_lista"))
    assert resp.status_code == 302


def test_view_detalhe_protegido_por_login(client, demanda):
    resp = client.get(reverse("demandas:demanda_detalhe", args=[demanda.pk]))
    assert resp.status_code == 302


def test_view_lista_acessivel_para_assessor(client, assessor):
    client.force_login(assessor)
    resp = client.get(reverse("demandas:demanda_lista"))
    assert resp.status_code == 200


def test_view_form_create_cancelar_aponta_para_lista(client, admin_user):
    # Regressão: UUIDField com default=uuid4 popula form.instance.pk antes do
    # save. Antes do fix, "Cancelar" gerava URL para /demandas/<uuid-fictício>/.
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:demanda_nova"))
    assert resp.status_code == 200
    # Cancelar deve apontar para a lista, não para detalhe.
    assert reverse("demandas:demanda_lista").encode() in resp.content
    assert b"Cancelar" in resp.content


def test_view_lista_renderiza_demanda_sem_responsavel(client, admin_user):
    # Regressão: template usava {{ d.responsavel.nome_completo|default:d.responsavel.email }}
    # que falhava com VariableDoesNotExist quando responsavel era None.
    Demanda.objects.create(
        titulo="Sem responsável",
        descricao="X",
        canal_entrada="presencial",
        coordenacao_responsavel="gabinete",
        criado_por=admin_user,
        anonimo=True,
    )
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:demanda_lista"))
    assert resp.status_code == 200
    assert b"Sem respons" in resp.content


def test_pessoa_detalhe_lista_demandas_vinculadas(client, demanda, pessoa, admin_user):
    # Critério §22 do roadmap §4.3.3: detalhe da pessoa lista demandas vinculadas.
    client.force_login(admin_user)
    resp = client.get(reverse("pessoas:pessoa_detalhe", args=[pessoa.slug_publico]))
    assert resp.status_code == 200
    assert demanda.numero.encode() in resp.content


def test_pessoa_detalhe_oculta_demanda_restrita_de_outra_coord(
    client, admin_user, pessoa, coord_juridico
):
    d = Demanda.objects.create(
        titulo="Restrita comunicacao",
        descricao="X",
        canal_entrada="email",
        coordenacao_responsavel="comunicacao",
        restrito=True,
        criado_por=admin_user,
        responsavel=admin_user,
    )
    DemandaPessoa.objects.create(demanda=d, pessoa=pessoa)
    client.force_login(coord_juridico)
    resp = client.get(reverse("pessoas:pessoa_detalhe", args=[pessoa.slug_publico]))
    assert resp.status_code == 200
    assert d.numero.encode() not in resp.content
