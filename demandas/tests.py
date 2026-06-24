"""Testes do app demandas — Fase 3.

Cobre os 22 critérios de aceite do roadmap §4.3.3 com casos diretos.
Para cada bloco, comentário aponta o critério.
"""

import re
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
    )
    g = Group.objects.filter(name="Chefe de Gabinete").first()
    if g:
        u.groups.add(g)
    return u


@pytest.fixture
def assessor(db):
    u = Usuario.objects.create_user(
        email="assessor@test.com",
        password="senha12345",  # pragma: allowlist secret
        nome_completo="Assessor",
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
        criado_por=admin_user,
    )
    DemandaPessoa.objects.create(demanda=d, pessoa=pessoa)
    return d


# --- Geração de número (formato D-AAMM-NNNNN, ADR 0056) ---


def test_gera_numero_no_save(db, admin_user, pessoa):
    d = Demanda.objects.create(
        titulo="X",
        descricao="Y",
        canal_entrada="presencial",
        criado_por=admin_user,
    )
    agora = timezone.now()
    assert d.numero.startswith(f"D-{agora.strftime('%y%m')}-")
    assert re.fullmatch(r"D-\d{4}-\d{5}", d.numero)


def test_numero_aleatorio_e_unico(db, admin_user):
    """Duas demandas no mesmo mês têm sufixos diferentes (retry cobre colisão)."""
    a = Demanda.objects.create(
        titulo="A",
        descricao="X",
        canal_entrada="presencial",
        criado_por=admin_user,
        anonimo=True,
    )
    b = Demanda.objects.create(
        titulo="B",
        descricao="X",
        canal_entrada="presencial",
        criado_por=admin_user,
        anonimo=True,
    )
    assert a.numero != b.numero
    # 5 dígitos: 10000–99999
    assert 10000 <= int(a.numero.rsplit("-", 1)[1]) <= 99999
    assert 10000 <= int(b.numero.rsplit("-", 1)[1]) <= 99999


# --- Critérios 1-3: criar com partes / anônima / só entidade ---


def test_criar_demanda_com_pessoa_funciona(db, demanda):
    assert demanda.demanda_pessoas.count() == 1
    assert demanda.tem_partes()


def test_criar_demanda_com_entidade_funciona(db, admin_user, entidade):
    d = Demanda.objects.create(
        titulo="Só entidade",
        descricao="X",
        canal_entrada="oficio",
        criado_por=admin_user,
    )
    from demandas.models import DemandaEntidade

    DemandaEntidade.objects.create(demanda=d, entidade=entidade)
    assert d.tem_partes()


def test_criar_demanda_anonima_funciona(db, admin_user):
    d = Demanda.objects.create(
        titulo="Anônima",
        descricao="X",
        canal_entrada="presencial",
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
    nova = demanda.interacoes.filter(tipo=Interacao.TIPO_MUDANCA_RESULTADO).first()
    assert nova is not None
    assert nova.automatica


# --- Critério 13: mudança de status gera interação automática ---


def test_mudanca_status_gera_interacao(db, demanda):
    inicial = demanda.interacoes.count()
    demanda.status = Demanda.STATUS_EM_ANDAMENTO
    demanda.save()
    assert demanda.interacoes.count() == inicial + 1
    nova = demanda.interacoes.filter(tipo=Interacao.TIPO_MUDANCA_STATUS).first()
    assert nova is not None
    assert nova.automatica


# --- Critério 14: mudança de responsável gera interação automática ---


def test_mudanca_responsavel_gera_interacao(db, demanda, chefe):
    inicial = demanda.interacoes.count()
    demanda.responsavel = chefe
    demanda.save()
    assert demanda.interacoes.count() == inicial + 1
    nova = demanda.interacoes.filter(tipo=Interacao.TIPO_MUDANCA_RESPONSAVEL).first()
    assert nova is not None


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
    # +2: a manual de tipo encaminhamento + a auto de mudança de status
    # (ADR 0044: criar encaminhamento move novo → aguardando_terceiros).
    assert demanda.interacoes.count() == inicial + 2
    assert demanda.interacoes.filter(tipo=Interacao.TIPO_ENCAMINHAMENTO).exists()


# --- ADR 0044: transições automáticas de status ---


def test_primeira_interacao_manual_move_novo_para_em_andamento(db, demanda, admin_user):
    assert demanda.status == Demanda.STATUS_NOVO
    Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_CONTATO_PESSOA,
        conteudo="Liguei pra Maria.",
        status=Interacao.STATUS_REALIZADA,
        data_ocorrencia=timezone.now(),
    )
    demanda.refresh_from_db()
    assert demanda.status == Demanda.STATUS_EM_ANDAMENTO


def test_interacao_automatica_nao_move_status(db, demanda, admin_user):
    assert demanda.status == Demanda.STATUS_NOVO
    Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_MUDANCA_STATUS,
        conteudo="ruído",
        status=Interacao.STATUS_REALIZADA,
        data_ocorrencia=timezone.now(),
        automatica=True,
    )
    demanda.refresh_from_db()
    assert demanda.status == Demanda.STATUS_NOVO


def test_criar_encaminhamento_move_status_para_aguardando_terceiros(db, demanda, admin_user):
    assert demanda.status == Demanda.STATUS_NOVO
    Encaminhamento.objects.create(
        demanda=demanda,
        destinatario_orgao="Sesa",
        tipo_documento="oficio",
        data_envio=timezone.now().date(),
        criado_por=admin_user,
    )
    demanda.refresh_from_db()
    assert demanda.status == Demanda.STATUS_AGUARDANDO_TERCEIROS


def test_responder_unico_encaminhamento_volta_para_em_andamento(db, demanda, admin_user):
    enc = Encaminhamento.objects.create(
        demanda=demanda,
        destinatario_orgao="Sesa",
        tipo_documento="oficio",
        data_envio=timezone.now().date(),
        criado_por=admin_user,
    )
    demanda.refresh_from_db()
    assert demanda.status == Demanda.STATUS_AGUARDANDO_TERCEIROS
    enc.status = Encaminhamento.STATUS_RESPONDIDO_SAT
    enc.data_resposta = timezone.now().date()
    enc.conteudo_resposta = "Obra autorizada."
    enc.save()
    demanda.refresh_from_db()
    assert demanda.status == Demanda.STATUS_EM_ANDAMENTO


def test_view_encaminhamento_liga_fk_em_interacao(client, demanda, admin_user):
    """ADR 0045: ao criar encaminhamento via view, a Interacao gerada
    aponta para o Encaminhamento (timeline expansível)."""
    client.force_login(admin_user)
    url = reverse("demandas:encaminhamento_novo", args=[demanda.pk])
    resp = client.post(
        url,
        {
            "destinatario_orgao": "Sesa",
            "destinatario_pessoa": "",
            "tipo_documento": "oficio",
            "numero_documento": "001/2026",
            "data_envio": timezone.now().date().isoformat(),
            "prazo_resposta": "",
        },
    )
    assert resp.status_code == 302
    enc = Encaminhamento.objects.get(demanda=demanda)
    interacao = Interacao.objects.get(demanda=demanda, tipo=Interacao.TIPO_ENCAMINHAMENTO)
    assert interacao.encaminhamento_id == enc.pk


def test_view_resposta_encaminhamento_liga_fk_em_interacao(client, demanda, admin_user):
    """ADR 0045: ao registrar resposta, a Interacao retorno_externo_recebido
    também aponta para o Encaminhamento."""
    client.force_login(admin_user)
    enc = Encaminhamento.objects.create(
        demanda=demanda,
        destinatario_orgao="Sesa",
        tipo_documento="oficio",
        data_envio=timezone.now().date(),
        criado_por=admin_user,
    )
    resp = client.post(
        reverse("demandas:encaminhamento_responder", args=[enc.pk]),
        {
            "status": "respondido_satisfatorio",
            "data_resposta": timezone.now().date().isoformat(),
            "conteudo_resposta": "Obra autorizada.",
        },
    )
    assert resp.status_code == 302
    retorno = Interacao.objects.get(demanda=demanda, tipo=Interacao.TIPO_RETORNO_EXTERNO)
    assert retorno.encaminhamento_id == enc.pk


def test_responder_um_de_dois_encaminhamentos_mantem_aguardando(db, demanda, admin_user):
    enc1 = Encaminhamento.objects.create(
        demanda=demanda,
        destinatario_orgao="Sesa",
        tipo_documento="oficio",
        data_envio=timezone.now().date(),
        criado_por=admin_user,
    )
    Encaminhamento.objects.create(
        demanda=demanda,
        destinatario_orgao="Setran",
        tipo_documento="oficio",
        data_envio=timezone.now().date(),
        criado_por=admin_user,
    )
    demanda.refresh_from_db()
    assert demanda.status == Demanda.STATUS_AGUARDANDO_TERCEIROS
    enc1.status = Encaminhamento.STATUS_RESPONDIDO_SAT
    enc1.data_resposta = timezone.now().date()
    enc1.conteudo_resposta = "Resposta."
    enc1.save()
    demanda.refresh_from_db()
    # 2º encaminhamento ainda aberto — status mantém aguardando_terceiros.
    assert demanda.status == Demanda.STATUS_AGUARDANDO_TERCEIROS


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


# --- Visibilidade need-to-know por papel (ADR 0059) ---


def _mk_demanda(autor, responsavel=None, status=Demanda.STATUS_NOVO, titulo="D"):
    return Demanda.objects.create(
        titulo=titulo,
        descricao="X",
        canal_entrada="email",
        criado_por=autor,
        responsavel=responsavel,
        status=status,
    )


def test_visibilidade_admin_ve_tudo(db, admin_user, assessor):
    ativa = _mk_demanda(assessor, responsavel=assessor)
    concluida = _mk_demanda(assessor, responsavel=assessor, status=Demanda.STATUS_CONCLUIDA)
    vis = set(Demanda.objects.visiveis_para(admin_user))
    assert ativa in vis and concluida in vis
    assert ativa.pode_ser_visto_por(admin_user)
    assert concluida.pode_ser_visto_por(admin_user)


def test_visibilidade_cg_ve_ativas_nao_concluidas(db, admin_user, chefe, assessor):
    ativa = _mk_demanda(assessor, responsavel=assessor)
    concluida = _mk_demanda(assessor, responsavel=assessor, status=Demanda.STATUS_CONCLUIDA)
    vis = set(Demanda.objects.visiveis_para(chefe))
    assert ativa in vis
    assert concluida not in vis
    assert ativa.pode_ser_visto_por(chefe)
    assert not concluida.pode_ser_visto_por(chefe)


def test_visibilidade_assessor_so_as_proprias(db, admin_user, assessor):
    minha_resp = _mk_demanda(admin_user, responsavel=assessor)
    minha_autor = _mk_demanda(assessor, responsavel=admin_user)
    de_outro = _mk_demanda(admin_user, responsavel=admin_user)
    vis = set(Demanda.objects.visiveis_para(assessor))
    assert minha_resp in vis  # responsável
    assert minha_autor in vis  # autor
    assert de_outro not in vis
    assert not de_outro.pode_ser_visto_por(assessor)


def test_visibilidade_assessor_ve_propria_concluida(db, admin_user, assessor):
    minha = _mk_demanda(admin_user, responsavel=assessor, status=Demanda.STATUS_CONCLUIDA)
    assert minha in set(Demanda.objects.visiveis_para(assessor))
    assert minha.pode_ser_visto_por(assessor)


def test_assessor_historico_mascara_ficha_da_parte(client, admin_user, assessor, pessoa):
    """No histórico próprio (concluída), a parte aparece só com nome —
    sem link para a ficha (ADR 0059)."""
    d = _mk_demanda(admin_user, responsavel=assessor, status=Demanda.STATUS_CONCLUIDA)
    DemandaPessoa.objects.create(demanda=d, pessoa=pessoa)
    client.force_login(assessor)
    resp = client.get(reverse("demandas:demanda_detalhe", args=[d.slug_publico]))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert pessoa.nome_exibicao in body  # nome aparece
    assert pessoa.slug_publico not in body  # mas sem link para a ficha


def test_assessor_ativa_mostra_ficha_da_parte(client, admin_user, assessor, pessoa):
    """Na demanda ATIVA do assessor, a parte tem link para a ficha."""
    d = _mk_demanda(admin_user, responsavel=assessor, status=Demanda.STATUS_EM_ANDAMENTO)
    DemandaPessoa.objects.create(demanda=d, pessoa=pessoa)
    client.force_login(assessor)
    resp = client.get(reverse("demandas:demanda_detalhe", args=[d.slug_publico]))
    assert resp.status_code == 200
    assert pessoa.slug_publico in resp.content.decode()  # link presente


def test_assessor_nao_ve_ficha_de_pessoa_sem_demanda_sua(client, assessor, pessoa):
    """Sem demanda visível ligada (e não foi quem cadastrou), o assessor
    não abre a ficha (ADR 0059 — sem navegação pelo acervo)."""
    client.force_login(assessor)
    resp = client.get(reverse("pessoas:pessoa_detalhe", args=[pessoa.slug_publico]))
    assert resp.status_code == 403


def test_assessor_ve_ficha_no_contexto_de_demanda_sua(client, admin_user, assessor, pessoa):
    d = _mk_demanda(admin_user, responsavel=assessor)
    DemandaPessoa.objects.create(demanda=d, pessoa=pessoa)
    client.force_login(assessor)
    resp = client.get(reverse("pessoas:pessoa_detalhe", args=[pessoa.slug_publico]))
    assert resp.status_code == 200


def test_assessor_ve_ficha_de_pessoa_que_cadastrou(client, assessor):
    from pessoas.models import Pessoa

    p = Pessoa.objects.create(nome="Nova", sobrenome="Pessoa", criado_por=assessor)
    client.force_login(assessor)
    resp = client.get(reverse("pessoas:pessoa_detalhe", args=[p.slug_publico]))
    assert resp.status_code == 200


# --- Permissões via grupos ---


def test_assessor_tem_perm_de_criar_demanda(db, assessor):
    assert assessor.has_perm("demandas.add_demanda")


def test_assessor_nao_arquiva_demanda(db, assessor):
    assert not assessor.has_perm("demandas.pode_arquivar_demanda")


def test_chefe_arquiva_sem_responder(db, chefe):
    assert chefe.has_perm("demandas.pode_arquivar_sem_responder")


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
    resp = client.get(reverse("demandas:demanda_detalhe", args=[demanda.slug_publico]))
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


# --- Filtro de tipos da Interacao manual (impede Interações órfãs) ---


def test_interacao_form_nao_oferece_tipos_geridos_pelo_sistema(db):
    """InteracaoForm não deve oferecer tipos que vivem em fluxos dedicados:
    devolutiva (criada pelo CTA Concluir), encaminhamento_externo e
    retorno_externo_recebido (criados pelo fluxo de Encaminhamento).
    Oferecer manualmente criaria Interações órfãs sem objeto associado.
    """
    from demandas.forms import InteracaoForm

    form = InteracaoForm()
    tipos_disponiveis = dict(form.fields["tipo"].choices)
    for tipo_proibido in (
        Interacao.TIPO_DEVOLUTIVA,
        Interacao.TIPO_ENCAMINHAMENTO,
        Interacao.TIPO_RETORNO_EXTERNO,
        Interacao.TIPO_MUDANCA_STATUS,
        Interacao.TIPO_MUDANCA_RESPONSAVEL,
        Interacao.TIPO_MUDANCA_RESULTADO,
        Interacao.TIPO_ARQUIVAMENTO,
        Interacao.TIPO_REGISTRO_INICIAL,
    ):
        assert (
            tipo_proibido not in tipos_disponiveis
        ), f"Tipo '{tipo_proibido}' não pode aparecer no seletor manual."
    # Tipos manuais legítimos devem estar lá.
    for tipo_esperado in (
        Interacao.TIPO_CONTATO_PESSOA,
        Interacao.TIPO_CONTATO_INTERNO,
        Interacao.TIPO_REUNIAO,
        Interacao.TIPO_ANOTACAO,
    ):
        assert tipo_esperado in tipos_disponiveis


# --- Anexos opcionais na criação da demanda ---


def test_criar_demanda_com_anexo_inicial(client, admin_user, pessoa):
    """POST /demandas/nova/ aceita arquivos opcionais e cria Anexos
    polimórficos apontando para a Demanda recém-criada."""
    from django.contrib.contenttypes.models import ContentType
    from django.core.files.uploadedfile import SimpleUploadedFile

    client.force_login(admin_user)
    pdf = SimpleUploadedFile("contrato.pdf", b"%PDF-1.4 test", content_type="application/pdf")
    resp = client.post(
        reverse("demandas:demanda_nova"),
        {
            "titulo": "Com anexo inicial",
            "descricao": "Teste anexo",
            "origem": Demanda.ORIGEM_RESPONSIVA,
            "canal_entrada": "presencial",
            "prioridade": "normal",
            # Inline formsets vazios (mas com management form):
            "dp-TOTAL_FORMS": "1",
            "dp-INITIAL_FORMS": "0",
            "dp-MIN_NUM_FORMS": "0",
            "dp-MAX_NUM_FORMS": "1000",
            "dp-0-pessoa": pessoa.pk,
            "dp-0-observacao": "",
            "de-TOTAL_FORMS": "0",
            "de-INITIAL_FORMS": "0",
            "de-MIN_NUM_FORMS": "0",
            "de-MAX_NUM_FORMS": "1000",
            "arquivos": pdf,
        },
        follow=False,
    )
    assert resp.status_code == 302, f"Esperado redirect; veio {resp.status_code}"
    d = Demanda.objects.get(titulo="Com anexo inicial")
    ct = ContentType.objects.get_for_model(Demanda)
    anexos = Anexo.objects.filter(content_type=ct, object_id=d.pk)
    assert anexos.count() == 1
    assert anexos.first().nome_original == "contrato.pdf"


def test_anexo_download_forca_attachment_e_nosniff(db, demanda, admin_user, client):
    """Defesa anti-XSS (ADR 0056): anexos aceitam qualquer tipo, mas a entrega
    via AnexoDownloadView força Content-Disposition: attachment +
    X-Content-Type-Options: nosniff + CSP. Um .html malicioso vira download,
    não código executando na origem do MPD."""
    from django.contrib.contenttypes.models import ContentType
    from django.core.files.uploadedfile import SimpleUploadedFile

    ct = ContentType.objects.get_for_model(Demanda)
    html_malicioso = SimpleUploadedFile(
        "ataque.html",
        b"<script>alert('XSS')</script>",
        content_type="text/html",
    )
    anexo = Anexo.objects.create(
        content_type=ct,
        object_id=demanda.pk,
        arquivo=html_malicioso,
        nome_original="ataque.html",
        tamanho_bytes=html_malicioso.size,
        mime_type="text/html",
        enviado_por=admin_user,
    )
    anexo.full_clean()  # sem whitelist, agora passa

    client.force_login(admin_user)
    resp = client.get(reverse("demandas:anexo_baixar", args=[anexo.pk]))
    assert resp.status_code == 200
    cd = resp["Content-Disposition"]
    assert cd.startswith("attachment"), f"esperado attachment, veio: {cd}"
    assert "ataque.html" in cd
    assert resp["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'none'" in resp["Content-Security-Policy"]


# --- Fase 4 — Visões Transversais (ADR 0046) ---


@pytest.fixture
def demanda_de_terceiro(db, admin_user, pessoa):
    """Demanda que o assessor não criou nem é responsável — invisível a ele
    no modelo need-to-know (ADR 0059)."""
    d = Demanda.objects.create(
        titulo="De terceiro",
        descricao="X",
        canal_entrada="oficio",
        criado_por=admin_user,
        responsavel=admin_user,
    )
    DemandaPessoa.objects.create(demanda=d, pessoa=pessoa)
    return d


def test_encaminhamento_lista_acessivel_a_admin(client, admin_user, demanda):
    enc = Encaminhamento.objects.create(
        demanda=demanda,
        destinatario_orgao="Sesa",
        tipo_documento="oficio",
        data_envio=timezone.now().date(),
        criado_por=admin_user,
    )
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:encaminhamento_lista"))
    assert resp.status_code == 200
    assert b"Sesa" in resp.content
    assert enc.demanda.numero.encode() in resp.content


def test_encaminhamento_lista_respeita_visibilidade_da_demanda(
    client, admin_user, assessor, demanda_de_terceiro
):
    """Assessor não vê encaminhamentos de demanda que não é dele (ADR 0059)."""
    Encaminhamento.objects.create(
        demanda=demanda_de_terceiro,
        destinatario_orgao="Procuradoria-Geral",
        tipo_documento="oficio",
        data_envio=timezone.now().date(),
        criado_por=admin_user,
    )
    client.force_login(assessor)
    resp = client.get(reverse("demandas:encaminhamento_lista"))
    assert resp.status_code == 200
    assert b"Procuradoria-Geral" not in resp.content


def test_encaminhamento_lista_quick_filter_vencidos(client, admin_user, demanda):
    """O filtro 'vencidos' inclui status=enviado com prazo no passado."""
    from datetime import date
    from datetime import timedelta as td

    atrasada = Encaminhamento.objects.create(
        demanda=demanda,
        destinatario_orgao="Atrasada",
        tipo_documento="oficio",
        data_envio=date.today() - td(days=60),
        prazo_resposta=date.today() - td(days=30),
        criado_por=admin_user,
        status=Encaminhamento.STATUS_ENVIADO,
    )
    no_prazo = Encaminhamento.objects.create(
        demanda=demanda,
        destinatario_orgao="OutroOrg",
        tipo_documento="oficio",
        data_envio=date.today(),
        prazo_resposta=date.today() + td(days=15),
        criado_por=admin_user,
        status=Encaminhamento.STATUS_ENVIADO,
    )
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:encaminhamento_lista") + "?filtro=vencidos")
    assert resp.status_code == 200
    # Verifica via contexto — o datalist de órgãos no template lista todos
    # os distintos visíveis (independente do quick filter), então comparar
    # bytes do HTML pode dar falso negativo.
    encaminhamentos = list(resp.context["encaminhamentos"])
    assert atrasada in encaminhamentos
    assert no_prazo not in encaminhamentos


def test_demandas_quick_filter_com_encaminhamento_aberto(client, admin_user, demanda):
    """Quick filter de demandas mostra só as com encaminhamento em status
    enviado/prazo_vencido."""
    Encaminhamento.objects.create(
        demanda=demanda,
        destinatario_orgao="Aberto",
        tipo_documento="oficio",
        data_envio=timezone.now().date(),
        criado_por=admin_user,
        status=Encaminhamento.STATUS_ENVIADO,
    )
    sem_enc = Demanda.objects.create(
        titulo="Sem encaminhamento",
        descricao="X",
        canal_entrada="presencial",
        criado_por=admin_user,
        anonimo=True,
    )
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:demanda_lista") + "?filtro=com_encaminhamento_aberto")
    assert resp.status_code == 200
    assert demanda.numero.encode() in resp.content
    assert sem_enc.numero.encode() not in resp.content


def test_pessoas_quick_filter_com_demanda_aberta(client, admin_user, pessoa, demanda):
    """Pessoa com demanda em aberto aparece; pessoa sem, não."""
    from pessoas.models import Pessoa

    outra = Pessoa.objects.create(
        nome="Sem", sobrenome="Demanda", bairro="X", cidade="Y", criado_por=admin_user
    )
    client.force_login(admin_user)
    resp = client.get(reverse("pessoas:pessoa_lista") + "?filtro=com_demanda_aberta")
    assert resp.status_code == 200
    assert pessoa.nome.encode() in resp.content
    assert outra.nome.encode() not in resp.content


# --- Fase 5 — Inbox GTD e Minhas Pendências ---


def test_capturar_inbox_cria_item_com_autor(client, admin_user):
    from demandas.models import ItemInbox

    client.force_login(admin_user)
    resp = client.post(
        reverse("demandas:inbox_capturar"),
        {"conteudo": "Lembrete: ligar para Maria sobre vaga de creche."},
        follow=False,
    )
    assert resp.status_code == 302
    item = ItemInbox.objects.get(conteudo__startswith="Lembrete")
    assert item.autor == admin_user
    assert item.status == ItemInbox.STATUS_PENDENTE


def test_capturar_inbox_ajax_retorna_json(client, admin_user):
    client.force_login(admin_user)
    resp = client.post(
        reverse("demandas:inbox_capturar") + "?ajax=1",
        {"conteudo": "Captura AJAX"},
    )
    assert resp.status_code == 201
    assert resp.json()["ok"] is True


def test_processar_inbox_cria_demanda_e_marca_processado(client, admin_user, pessoa):
    from demandas.models import ItemInbox

    item = ItemInbox.objects.create(conteudo="Buraco na rua X", autor=admin_user)
    client.force_login(admin_user)
    resp = client.post(
        reverse("demandas:inbox_processar", args=[item.pk]),
        {
            "titulo": "Buraco na rua X",
            "descricao": "Buraco grande na esquina.",
            "origem": Demanda.ORIGEM_RESPONSIVA,
            "canal_entrada": "presencial",
            "prioridade": "normal",
            "dp-TOTAL_FORMS": "1",
            "dp-INITIAL_FORMS": "0",
            "dp-MIN_NUM_FORMS": "0",
            "dp-MAX_NUM_FORMS": "1000",
            "dp-0-pessoa": pessoa.pk,
            "dp-0-observacao": "",
            "de-TOTAL_FORMS": "0",
            "de-INITIAL_FORMS": "0",
            "de-MIN_NUM_FORMS": "0",
            "de-MAX_NUM_FORMS": "1000",
        },
        follow=False,
    )
    assert resp.status_code == 302
    item.refresh_from_db()
    assert item.status == ItemInbox.STATUS_PROCESSADO
    assert item.demanda_gerada is not None
    assert item.processado_por == admin_user
    assert item.demanda_gerada.descricao == "Buraco grande na esquina."


def test_descartar_inbox_exige_motivo(client, admin_user):
    from demandas.models import ItemInbox

    item = ItemInbox.objects.create(conteudo="Item inutil", autor=admin_user)
    client.force_login(admin_user)
    # Sem motivo: rejeita
    resp = client.post(reverse("demandas:inbox_descartar", args=[item.pk]), {"motivo_descarte": ""})
    item.refresh_from_db()
    assert item.status == ItemInbox.STATUS_PENDENTE  # não mudou
    # Com motivo: aceita
    resp = client.post(
        reverse("demandas:inbox_descartar", args=[item.pk]),
        {"motivo_descarte": "Duplicado com #42"},
    )
    assert resp.status_code == 302
    item.refresh_from_db()
    assert item.status == ItemInbox.STATUS_DESCARTADO
    assert item.motivo_descarte == "Duplicado com #42"


def test_minhas_pendencias_lista_agendadas_do_usuario(client, admin_user, demanda):
    Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_REUNIAO,
        conteudo="Reunião na quinta",
        status=Interacao.STATUS_AGENDADA,
        data_ocorrencia=timezone.now() + timedelta(days=3),
        automatica=False,
    )
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:minhas_pendencias"))
    assert resp.status_code == 200
    grupos = resp.context["grupos"]
    rotulos = [g["label"] for g in grupos]
    assert "Esta semana" in rotulos
    assert b"Reuni\xc3\xa3o na quinta" in resp.content


def test_minhas_pendencias_vencidas_no_topo(client, admin_user, demanda):
    Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_REUNIAO,
        conteudo="Vencida",
        status=Interacao.STATUS_AGENDADA,
        data_ocorrencia=timezone.now() - timedelta(days=2),
        automatica=False,
    )
    Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_REUNIAO,
        conteudo="Futura",
        status=Interacao.STATUS_AGENDADA,
        data_ocorrencia=timezone.now() + timedelta(days=5),
        automatica=False,
    )
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:minhas_pendencias"))
    grupos = resp.context["grupos"]
    primeiro = grupos[0]["label"]
    assert primeiro == "Vencidas"


def test_minhas_reunioes_filtra_tipo_reuniao(client, admin_user, demanda):
    Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_REUNIAO,
        conteudo="Reunião",
        status=Interacao.STATUS_AGENDADA,
        data_ocorrencia=timezone.now() + timedelta(days=3),
        automatica=False,
    )
    Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_CONTATO_PESSOA,
        conteudo="Contato",
        status=Interacao.STATUS_AGENDADA,
        data_ocorrencia=timezone.now() + timedelta(days=4),
        automatica=False,
    )
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:minhas_reunioes"))
    pendencias = list(resp.context["pendencias"])
    assert len(pendencias) == 1
    assert pendencias[0].tipo == Interacao.TIPO_REUNIAO


def test_context_processor_conta_pendencias_vencidas(client, admin_user, demanda):
    Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_REUNIAO,
        conteudo="Vencida 1",
        status=Interacao.STATUS_AGENDADA,
        data_ocorrencia=timezone.now() - timedelta(days=1),
        automatica=False,
    )
    Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_REUNIAO,
        conteudo="No futuro",
        status=Interacao.STATUS_AGENDADA,
        data_ocorrencia=timezone.now() + timedelta(days=5),
        automatica=False,
    )
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:demanda_lista"))
    assert resp.context["topbar_pendencias_vencidas"] == 1


# --- Fase 6 — Segurança, Visualização, Exportação (ADR 0047) ---


def test_export_csv_demandas_acessivel_a_admin(client, admin_user, demanda):
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:demanda_export_csv"))
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    assert b"\xef\xbb\xbf" in resp.content[:5]  # BOM (Excel BR)
    assert b";" in resp.content  # separador BR
    assert demanda.numero.encode() in resp.content


def test_export_csv_bloqueia_assessor(client, assessor, demanda):
    client.force_login(assessor)
    resp = client.get(reverse("demandas:demanda_export_csv"))
    assert resp.status_code == 403


def test_export_csv_bloqueia_chefe(client, chefe, demanda):
    """Export é exclusivo do Admin (ADR 0059) — CG não exporta."""
    client.force_login(chefe)
    resp = client.get(reverse("demandas:demanda_export_csv"))
    assert resp.status_code == 403


def test_export_csv_respeita_filtros_da_querystring(client, admin_user, pessoa):
    """CSV exportado respeita filtros da querystring — filtra por status."""
    Demanda.objects.create(
        titulo="Demanda nova",
        descricao="X",
        canal_entrada="presencial",
        criado_por=admin_user,
        anonimo=True,
        status=Demanda.STATUS_NOVO,
    )
    Demanda.objects.create(
        titulo="Demanda em andamento",
        descricao="Y",
        canal_entrada="oficio",
        criado_por=admin_user,
        anonimo=True,
        status=Demanda.STATUS_EM_ANDAMENTO,
    )
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:demanda_export_csv") + "?status=em_andamento")
    assert resp.status_code == 200
    assert b"Demanda em andamento" in resp.content
    assert b"Demanda nova" not in resp.content


def test_auditoria_acessivel_a_admin(client, admin_user, demanda):
    # Demanda criada gera LogEntry via auditlog.
    client.force_login(admin_user)
    resp = client.get(reverse("core:auditoria"))
    assert resp.status_code == 200


def test_auditoria_bloqueia_chefe(client, chefe):
    client.force_login(chefe)
    resp = client.get(reverse("core:auditoria"))
    assert resp.status_code == 403


def test_analise_acessivel_a_admin_com_metricas(client, admin_user, demanda):
    client.force_login(admin_user)
    resp = client.get(reverse("core:analise"))
    assert resp.status_code == 200
    # Métricas no contexto
    assert "por_tema" in resp.context
    assert "por_mes" in resp.context
    assert "top_pessoas" in resp.context
    assert "carga_assessores" in resp.context


def test_analise_bloqueia_chefe(client, chefe):
    """Análise é exclusiva do Admin (ADR 0059) — CG não acessa."""
    client.force_login(chefe)
    resp = client.get(reverse("core:analise"))
    assert resp.status_code == 403


def test_analise_bloqueia_assessor(client, assessor):
    client.force_login(assessor)
    resp = client.get(reverse("core:analise"))
    assert resp.status_code == 403


def test_verificar_integridade_detecta_devolutiva_faltando(db, admin_user, pessoa):
    """Demanda responsiva concluída sem Interação devolutiva é detectada
    pelo comando (cria via bypass do clean — simula dado corrompido)."""
    from io import StringIO

    from django.core.management import call_command

    d = Demanda(
        titulo="Sem devolutiva",
        descricao="X",
        canal_entrada="presencial",
        origem=Demanda.ORIGEM_RESPONSIVA,
        resultado=Demanda.RESULTADO_ATENDIDO,
        criado_por=admin_user,
        anonimo=True,
    )
    # Bypass clean() pra simular drift de dados:
    d.save()
    DemandaPessoa.objects.create(demanda=d, pessoa=pessoa)
    Demanda.objects.filter(pk=d.pk).update(status=Demanda.STATUS_CONCLUIDA)

    out = StringIO()
    try:
        call_command("verificar_integridade", stdout=out)
    except SystemExit as e:
        # sys.exit(1) é esperado quando há inconsistências
        assert e.code == 1
    saida = out.getvalue()
    assert "Sem devolutiva" in saida or "responsiva concluída" in saida


# --- Endpoints de busca (autocomplete) ---


def test_pessoa_buscar_json_retorna_resultados(client, admin_user):
    from pessoas.models import Pessoa

    Pessoa.objects.create(nome="Maria", sobrenome="Silva", bairro="Centro", criado_por=admin_user)
    Pessoa.objects.create(nome="Joao", sobrenome="Souza", bairro="Centro", criado_por=admin_user)
    client.force_login(admin_user)
    resp = client.get(reverse("pessoas:pessoa_buscar_json") + "?q=Maria")
    assert resp.status_code == 200
    data = resp.json()
    nomes = [r["label"] for r in data["resultados"]]
    assert any("Maria" in n for n in nomes)
    assert not any("Joao" in n for n in nomes)


def test_pessoa_buscar_json_exige_login(client):
    resp = client.get(reverse("pessoas:pessoa_buscar_json") + "?q=x")
    assert resp.status_code == 302  # redirect para login


def test_pessoa_buscar_json_limite_20(client, admin_user):
    from pessoas.models import Pessoa

    for i in range(30):
        Pessoa.objects.create(
            nome=f"Pessoa{i:02d}", sobrenome="Sobrenome", bairro="X", criado_por=admin_user
        )
    client.force_login(admin_user)
    resp = client.get(reverse("pessoas:pessoa_buscar_json") + "?q=Pessoa")
    assert resp.status_code == 200
    assert len(resp.json()["resultados"]) == 20


def test_entidade_buscar_json_retorna_resultados(client, admin_user):
    from pessoas.models import Entidade

    Entidade.objects.create(nome="Associacao X", tipo="associacao", criado_por=admin_user)
    Entidade.objects.create(nome="Sindicato Y", tipo="sindicato", criado_por=admin_user)
    client.force_login(admin_user)
    resp = client.get(reverse("pessoas:entidade_buscar_json") + "?q=Associ")
    assert resp.status_code == 200
    data = resp.json()
    nomes = [r["label"] for r in data["resultados"]]
    assert any("Associacao" in n for n in nomes)
    assert not any("Sindicato" in n for n in nomes)


# --- Papel com choices + Outro (Fase 6.1) ---


# --- Criar Tema via AJAX (popup no form de Demanda) ---


def test_tema_criar_ajax_sucesso(client, admin_user):
    from demandas.models import Tema

    client.force_login(admin_user)
    resp = client.post(
        reverse("demandas:tema_criar_ajax"),
        {"nome": "Saúde Mental", "cor": "#039be5"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["nome"] == "Saúde Mental"
    assert data["cor"] == "#039be5"
    assert Tema.objects.filter(nome="Saúde Mental").exists()


def test_tema_criar_ajax_sem_nome_falha(client, admin_user):
    client.force_login(admin_user)
    resp = client.post(reverse("demandas:tema_criar_ajax"), {"nome": ""})
    assert resp.status_code == 400
    assert "obrigatório" in resp.json()["erro"]


def test_tema_criar_ajax_duplicado_falha(client, admin_user):
    from demandas.models import Tema

    Tema.objects.create(nome="Educação", cor="#3f51b5")
    client.force_login(admin_user)
    resp = client.post(reverse("demandas:tema_criar_ajax"), {"nome": "Educação"})
    assert resp.status_code == 400
    assert "já existe" in resp.json()["erro"].lower()


def test_tema_criar_ajax_bloqueia_assessor(client, assessor):
    # Criar tema é exclusivo do Admin (add_tema; permissoes.md §3.7, ADR 0059).
    client.force_login(assessor)
    resp = client.post(reverse("demandas:tema_criar_ajax"), {"nome": "X"})
    assert resp.status_code == 403


# --- Auditlog estendido: Interacao e ItemInbox (ADR 0050) ---


def test_auditlog_registra_edicao_de_interacao(db, demanda, admin_user):
    """Edição manual de Interacao deve gerar LogEntry(UPDATE).
    Fecha o gap da revisão de fim-Fase-6: devolutiva editada silenciosamente."""
    from auditlog.models import LogEntry

    i = Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_CONTATO_PESSOA,
        conteudo="Original",
        status=Interacao.STATUS_REALIZADA,
        data_ocorrencia=timezone.now(),
    )
    i.conteudo = "Editada"
    i.save()
    logs = LogEntry.objects.get_for_object(i)
    assert logs.filter(action=LogEntry.Action.UPDATE).exists()


def test_auditlog_registra_descarte_de_inbox(db, admin_user):
    """Mudança de status de ItemInbox (pendente → descartado) gera LogEntry."""
    from auditlog.models import LogEntry

    from demandas.models import ItemInbox

    item = ItemInbox.objects.create(conteudo="Spam qualquer", autor=admin_user)
    item.status = ItemInbox.STATUS_DESCARTADO
    item.motivo_descarte = "Spam"
    item.save()
    logs = LogEntry.objects.get_for_object(item)
    assert logs.filter(action=LogEntry.Action.UPDATE).exists()


# --- /analise reflete a visibilidade do viewer (ADR 0049/0059) ---


def test_analise_admin_ve_todas_as_demandas(client, admin_user, demanda_de_terceiro):
    """Sanity: admin vê as demandas no painel (visibilidade total)."""
    client.force_login(admin_user)
    resp = client.get(reverse("core:analise"))
    por_mes = resp.context["por_mes"]
    total_admin = sum(m["total"] for m in por_mes)
    assert total_admin >= 1


# --- Conclusão limpa: devolutiva não dispara avanço de status (Tarefa 2.1) ---


def test_conclusao_de_demanda_nova_responsiva_gera_transicao_unica(client, admin_user, demanda):
    """Demanda em status=novo, ConcluirDemandaView cria devolutiva + UMA
    transição direta para concluida (sem passar por em_andamento
    intermediário fake). Sem o fix da Tarefa 2.1, devolutiva disparava
    avanço para em_andamento, gerando 2 transições de status."""
    assert demanda.status == Demanda.STATUS_NOVO
    client.force_login(admin_user)
    resp = client.post(
        reverse("demandas:demanda_concluir", args=[demanda.pk]),
        {
            "devolutiva_data": timezone.now().date().isoformat(),
            "devolutiva_canal": "whatsapp",
            "devolutiva_conteudo": "Comunicado à Maria.",
            "resultado": Demanda.RESULTADO_ATENDIDO,
            "resultado_observacao": "",
        },
    )
    assert resp.status_code == 302
    demanda.refresh_from_db()
    assert demanda.status == Demanda.STATUS_CONCLUIDA
    # Critério principal: UMA transição de status (novo→concluida).
    # Sem o fix: 2 transições (novo→em_andamento + em_andamento→concluida).
    transicoes = demanda.interacoes.filter(tipo=Interacao.TIPO_MUDANCA_STATUS)
    assert transicoes.count() == 1
    transicao = transicoes.first()
    assert "Novo" in transicao.conteudo
    assert "Concluída" in transicao.conteudo


# --- AnexoUpload: objeto pai inexistente → 404 (Tarefa 2.4) ---


def test_anexo_upload_objeto_inexistente_retorna_404(client, admin_user):
    """POST com UUID que não existe deve retornar 404 (não 500).
    Antes do fix, ct.model_class().objects.get(pk=...) estourava
    DoesNotExist como exceção não tratada."""
    import uuid as _uuid

    client.force_login(admin_user)
    resp = client.post(
        reverse("demandas:anexo_upload", args=["demanda", _uuid.uuid4()]),
        {"descricao": "irrelevante"},
    )
    assert resp.status_code == 404


# --- ProcessarInboxView: conflito UX (Tarefa 2.5) ---


def test_processar_inbox_ja_processado_redireciona_para_demanda(client, admin_user, pessoa):
    """Reabrir item já processado redireciona para a demanda gerada com
    mensagem informativa (não 404 vazio)."""
    from demandas.models import ItemInbox

    item = ItemInbox.objects.create(conteudo="Item teste", autor=admin_user)
    demanda = Demanda.objects.create(
        titulo="Já criada",
        descricao="X",
        canal_entrada="presencial",
        criado_por=admin_user,
        anonimo=True,
    )
    item.status = ItemInbox.STATUS_PROCESSADO
    item.demanda_gerada = demanda
    item.processado_por = admin_user
    item.processado_em = timezone.now()
    item.save()
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:inbox_processar", args=[item.pk]))
    assert resp.status_code == 302
    assert reverse("demandas:demanda_detalhe", args=[demanda.slug_publico]) in resp.url


def test_analise_carga_assessores_nao_tem_n_mais_1(client, admin_user):
    """Query count constante independente do nº de usuários ativos
    (Tarefa 3.3: carga_assessores migrou de loop com 2 queries por
    usuário para uma annotate única)."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    for i in range(20):
        Usuario.objects.create_user(
            email=f"u{i}@t.com",
            password="senha12345",  # pragma: allowlist secret
        )
    client.force_login(admin_user)
    with CaptureQueriesContext(connection) as captured:
        client.get(reverse("core:analise"))
    # Limite generoso pra cobrir as 6 métricas + auth + middlewares.
    # Antes do fix: 40+ queries só nesta métrica.
    assert (
        len(captured.captured_queries) < 30
    ), f"Esperado <30 queries, obtive {len(captured.captured_queries)}"


def test_processar_inbox_descartado_redireciona_para_lista(client, admin_user):
    """Item descartado também faz fall-through para a lista com mensagem."""
    from demandas.models import ItemInbox

    item = ItemInbox.objects.create(conteudo="Spam", autor=admin_user)
    item.status = ItemInbox.STATUS_DESCARTADO
    item.motivo_descarte = "Spam óbvio"
    item.processado_por = admin_user
    item.save()
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:inbox_processar", args=[item.pk]))
    assert resp.status_code == 302
    assert reverse("demandas:inbox_lista") in resp.url


# --- Export CSV grava LogEntry (ADR 0053, Tarefa 1.1 v0.7.3) ---


def test_export_csv_demandas_grava_log_entry(client, admin_user, demanda):
    """roadmap §4.6.3: exportação grava LogEntry visível em /auditoria.
    ADR 0053 migrou registrar_export do logger Python para LogEntry(ACCESS)."""
    from auditlog.models import LogEntry

    antes = LogEntry.objects.filter(object_repr__startswith="Exportação CSV").count()
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:demanda_export_csv"))
    assert resp.status_code == 200
    depois = LogEntry.objects.filter(object_repr__startswith="Exportação CSV").count()
    assert depois == antes + 1
    entry = LogEntry.objects.filter(object_repr__startswith="Exportação CSV").latest("timestamp")
    assert entry.actor == admin_user
    assert entry.action == LogEntry.Action.ACCESS
    assert "Demanda" in entry.object_repr


def test_export_csv_pessoas_grava_log_entry(client, admin_user, pessoa):
    """Mesmo mecanismo no export de pessoas — content_type aponta para Pessoa."""
    from auditlog.models import LogEntry

    client.force_login(admin_user)
    resp = client.get(reverse("pessoas:pessoa_export_csv"))
    assert resp.status_code == 200
    assert LogEntry.objects.filter(
        object_repr__startswith="Exportação CSV",
        object_repr__icontains="Pessoa",
        action=LogEntry.Action.ACCESS,
    ).exists()


def test_export_csv_encaminhamentos_grava_log_entry(client, admin_user, demanda):
    """Export de encaminhamentos também passa pelo registrar_export."""
    from auditlog.models import LogEntry

    Encaminhamento.objects.create(
        demanda=demanda,
        tipo_documento="oficio",
        destinatario_orgao="Semus",
        data_envio=timezone.now().date(),
        criado_por=admin_user,
    )
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:encaminhamento_export_csv"))
    assert resp.status_code == 200
    assert LogEntry.objects.filter(
        object_repr__startswith="Exportação CSV",
        object_repr__icontains="Encaminhamento",
        action=LogEntry.Action.ACCESS,
    ).exists()


# --- verificar_integridade: 5 ramos restantes (Tarefa 1.2 v0.7.3) ---


def _rodar_verificar_integridade():
    """Helper: roda o comando e devolve (exit_code, stdout)."""
    from io import StringIO

    from django.core.management import call_command

    out = StringIO()
    try:
        call_command("verificar_integridade", stdout=out)
        return 0, out.getvalue()
    except SystemExit as e:
        return e.code, out.getvalue()


def test_verificar_integridade_detecta_anexo_com_arquivo_ausente(db, demanda, admin_user):
    """Ramo 2: registro de Anexo existe mas arquivo no storage não."""
    from django.contrib.contenttypes.models import ContentType
    from django.core.files.uploadedfile import SimpleUploadedFile

    ct = ContentType.objects.get_for_model(Demanda)
    f = SimpleUploadedFile("teste.pdf", b"X" * 100, content_type="application/pdf")
    anexo = Anexo.objects.create(
        content_type=ct,
        object_id=demanda.pk,
        arquivo=f,
        nome_original="teste.pdf",
        tamanho_bytes=100,
        mime_type="application/pdf",
        enviado_por=admin_user,
    )
    # Deleta o arquivo do storage mantendo o registro
    anexo.arquivo.storage.delete(anexo.arquivo.name)

    code, saida = _rodar_verificar_integridade()
    assert code == 1
    assert "arquivo no disco não encontrado" in saida


def test_verificar_integridade_detecta_anexo_orfao_polimorfico(db, demanda, admin_user):
    """Ramo 2b: content_type + object_id apontam para registro inexistente."""
    import uuid as _uuid

    from django.contrib.contenttypes.models import ContentType
    from django.core.files.uploadedfile import SimpleUploadedFile

    ct = ContentType.objects.get_for_model(Demanda)
    f = SimpleUploadedFile("teste.pdf", b"X" * 100, content_type="application/pdf")
    anexo = Anexo.objects.create(
        content_type=ct,
        object_id=demanda.pk,
        arquivo=f,
        nome_original="teste.pdf",
        tamanho_bytes=100,
        mime_type="application/pdf",
        enviado_por=admin_user,
    )
    # Sobrescreve object_id para um UUID que não existe — órfão polimórfico
    Anexo.objects.filter(pk=anexo.pk).update(object_id=_uuid.uuid4())

    code, saida = _rodar_verificar_integridade()
    assert code == 1
    assert "órfão polimórfico" in saida


def test_verificar_integridade_detecta_encaminhamento_vencido_status_enviado(
    db, demanda, admin_user
):
    """Ramo 3: prazo passou, status segue 'enviado' (cron de atualização não rodou)."""
    Encaminhamento.objects.create(
        demanda=demanda,
        tipo_documento="oficio",
        destinatario_orgao="Semus",
        data_envio=timezone.now().date() - timedelta(days=60),
        prazo_resposta=timezone.now().date() - timedelta(days=10),
        status=Encaminhamento.STATUS_ENVIADO,
        criado_por=admin_user,
    )
    code, saida = _rodar_verificar_integridade()
    assert code == 1
    assert "Semus" in saida
    assert "enviado" in saida.lower()


def test_verificar_integridade_detecta_inbox_pendente_mais_de_90d(db, admin_user):
    """Ramo 4: ItemInbox pendente há +90 dias."""
    from demandas.models import ItemInbox

    item = ItemInbox.objects.create(conteudo="Esquecido", autor=admin_user)
    # Burlar auto_now_add para datar antigo
    ItemInbox.objects.filter(pk=item.pk).update(criado_em=timezone.now() - timedelta(days=120))

    code, saida = _rodar_verificar_integridade()
    assert code == 1
    assert "pendente há 120 dias" in saida


def test_verificar_integridade_detecta_interacao_agendada_mais_de_180d(db, demanda, admin_user):
    """Ramo 5: Interação agendada há +180 dias sem ação."""
    Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_CONTATO_PESSOA,
        conteudo="Parou no tempo",
        status=Interacao.STATUS_AGENDADA,
        data_ocorrencia=timezone.now() - timedelta(days=200),
    )
    code, saida = _rodar_verificar_integridade()
    assert code == 1
    assert "agendada" in saida.lower()
    assert "200 dias" in saida


def test_verificar_integridade_sem_problemas_retorna_zero(db):
    """Sanity: base limpa, exit code 0."""
    code, saida = _rodar_verificar_integridade()
    assert code == 0
    assert "Nenhuma inconsistência" in saida


# --- Filtros em /auditoria (Tarefa 1.3 v0.7.3) ---


def _criar_log(modelo, actor, action, pk):
    """Helper: cria LogEntry diretamente para testar os filtros da view."""
    from auditlog.models import LogEntry
    from django.contrib.contenttypes.models import ContentType

    ct = ContentType.objects.get_for_model(modelo)
    return LogEntry.objects.create(
        content_type=ct,
        object_pk=str(pk),
        object_repr=f"{modelo.__name__}#{pk}",
        action=action,
        actor=actor,
    )


def test_auditoria_filtra_por_usuario(client, admin_user, chefe, pessoa):
    """Filtro ?usuario=<email_parcial> deixa só LogEntries em que actor.email
    contém o parcial. View usa actor__email__icontains."""
    from auditlog.models import LogEntry

    _criar_log(Pessoa, admin_user, LogEntry.Action.UPDATE, pessoa.pk)
    _criar_log(Pessoa, chefe, LogEntry.Action.UPDATE, pessoa.pk)

    client.force_login(admin_user)
    resp = client.get(reverse("core:auditoria"), {"usuario": "chefe@"})
    assert resp.status_code == 200
    logs = list(resp.context["logs"])
    assert len(logs) >= 1
    assert all(log.actor_id == chefe.pk for log in logs)


def test_auditoria_filtra_por_modelo(client, admin_user, pessoa, demanda):
    """Filtro ?modelo=<content_type_id> deixa só LogEntries do CT escolhido."""
    from auditlog.models import LogEntry
    from django.contrib.contenttypes.models import ContentType

    _criar_log(Pessoa, admin_user, LogEntry.Action.UPDATE, pessoa.pk)
    _criar_log(Demanda, admin_user, LogEntry.Action.UPDATE, demanda.pk)

    ct_pessoa = ContentType.objects.get_for_model(Pessoa)
    client.force_login(admin_user)
    resp = client.get(reverse("core:auditoria"), {"modelo": ct_pessoa.pk})
    assert resp.status_code == 200
    logs = list(resp.context["logs"])
    assert len(logs) >= 1
    assert all(log.content_type_id == ct_pessoa.pk for log in logs)


def test_auditoria_filtra_por_acao(client, admin_user, pessoa):
    """Filtro ?acao=<int> deixa só LogEntries da ação escolhida (1=UPDATE)."""
    from auditlog.models import LogEntry

    _criar_log(Pessoa, admin_user, LogEntry.Action.CREATE, pessoa.pk)
    _criar_log(Pessoa, admin_user, LogEntry.Action.UPDATE, pessoa.pk)

    client.force_login(admin_user)
    resp = client.get(reverse("core:auditoria"), {"acao": LogEntry.Action.UPDATE})
    assert resp.status_code == 200
    logs = list(resp.context["logs"])
    assert len(logs) >= 1
    assert all(log.action == LogEntry.Action.UPDATE for log in logs)


def test_auditoria_filtra_por_periodo_desde(client, admin_user, pessoa):
    """Filtro ?desde=AAAA-MM-DD respeitado — desde=amanhã esvazia resultado."""
    from datetime import date
    from datetime import timedelta as td

    from auditlog.models import LogEntry

    _criar_log(Pessoa, admin_user, LogEntry.Action.UPDATE, pessoa.pk)

    amanha = (date.today() + td(days=1)).isoformat()
    client.force_login(admin_user)
    resp = client.get(reverse("core:auditoria"), {"desde": amanha})
    assert resp.status_code == 200
    logs = list(resp.context["logs"])
    assert len(logs) == 0


# --- /entidades/ quick filter "com demanda em aberto" (Tarefa 2.1 v0.7.3) ---


def test_entidades_quick_filter_com_demanda_aberta(client, admin_user, entidade, demanda):
    """Espelho do test_pessoas_quick_filter_com_demanda_aberta: entidade
    vinculada a demanda aberta aparece; entidade sem demanda não."""
    from demandas.models import DemandaEntidade

    DemandaEntidade.objects.create(demanda=demanda, entidade=entidade)
    outra = Entidade.objects.create(nome="Sem demanda", tipo="associacao", criado_por=admin_user)
    client.force_login(admin_user)
    resp = client.get(reverse("pessoas:entidade_lista") + "?filtro=com_demanda_aberta")
    assert resp.status_code == 200
    assert entidade.nome.encode() in resp.content
    assert outra.nome.encode() not in resp.content


# --- /inbox/ listagem: filtros e badges (Tarefa 2.2 v0.7.3) ---


def test_inbox_lista_default_mostra_so_pendentes(client, admin_user):
    """Sem querystring, /inbox/ filtra status=pendente. Descartados/processados ficam fora."""
    from demandas.models import ItemInbox

    ItemInbox.objects.create(conteudo="Pendente visível", autor=admin_user)
    ItemInbox.objects.create(
        conteudo="Descartado invisível",
        autor=admin_user,
        status=ItemInbox.STATUS_DESCARTADO,
        motivo_descarte="spam",
    )
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:inbox_lista"))
    assert resp.status_code == 200
    conteudos = {i.conteudo for i in resp.context["itens"]}
    assert "Pendente visível" in conteudos
    assert "Descartado invisível" not in conteudos


def test_inbox_lista_filtro_todos_inclui_descartados(client, admin_user):
    """?status=todos não aplica filtro de status — descartados aparecem."""
    from demandas.models import ItemInbox

    ItemInbox.objects.create(
        conteudo="Descartado",
        autor=admin_user,
        status=ItemInbox.STATUS_DESCARTADO,
        motivo_descarte="spam",
    )
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:inbox_lista") + "?status=todos")
    assert resp.status_code == 200
    conteudos = {i.conteudo for i in resp.context["itens"]}
    assert "Descartado" in conteudos


def test_inbox_lista_marca_envelhecimento_amber_e_red(client, admin_user):
    """Item +7 dias ganha badge âmbar; +30 dias ganha vermelho.
    Confirma que limite_7d/limite_30d do context chegam no template."""
    from demandas.models import ItemInbox

    velho = ItemInbox.objects.create(conteudo="Há 10 dias", autor=admin_user)
    antigo = ItemInbox.objects.create(conteudo="Há 35 dias", autor=admin_user)
    ItemInbox.objects.filter(pk=velho.pk).update(criado_em=timezone.now() - timedelta(days=10))
    ItemInbox.objects.filter(pk=antigo.pk).update(criado_em=timezone.now() - timedelta(days=35))

    client.force_login(admin_user)
    resp = client.get(reverse("demandas:inbox_lista"))
    assert resp.status_code == 200
    body = resp.content
    # Badges de idade · classes `.age amber` (+7d) e `.age red` (+30d).
    # Template foi refeito para o design system v2; a regressão antiga
    # checava classes Tailwind, que não existem mais aqui.
    assert b'class="age amber"' in body
    assert b"+7 dias" in body
    assert b'class="age red"' in body
    assert b"+30 dias" in body


# --- /minhas-pendencias/: marcar realizada (Tarefa 2.3 v0.7.3) ---


def test_minhas_pendencias_oferece_form_de_marcar_realizada(client, admin_user, demanda):
    """View renderiza form apontando para interacao_realizada para cada pendência."""
    pendencia = Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_CONTATO_PESSOA,
        conteudo="Ligar amanhã",
        status=Interacao.STATUS_AGENDADA,
        data_ocorrencia=timezone.now() + timedelta(days=1),
    )
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:minhas_pendencias"))
    assert resp.status_code == 200
    url_esperada = reverse("demandas:interacao_realizada", args=[pendencia.pk])
    assert url_esperada.encode() in resp.content


def test_marcar_realizada_remove_pendencia_de_minhas_pendencias(client, admin_user, demanda):
    """POST em interacao_realizada muda status para REALIZADA e a interação
    sai da queryset de /minhas-pendencias/ (que filtra status=AGENDADA)."""
    pendencia = Interacao.objects.create(
        demanda=demanda,
        autor=admin_user,
        tipo=Interacao.TIPO_CONTATO_PESSOA,
        conteudo="Ligar amanhã",
        status=Interacao.STATUS_AGENDADA,
        data_ocorrencia=timezone.now() + timedelta(days=1),
    )
    client.force_login(admin_user)
    resp_post = client.post(reverse("demandas:interacao_realizada", args=[pendencia.pk]))
    assert resp_post.status_code == 302
    pendencia.refresh_from_db()
    assert pendencia.status == Interacao.STATUS_REALIZADA
    # E sai da lista
    resp_lista = client.get(reverse("demandas:minhas_pendencias"))
    pks_visiveis = [p.pk for p in resp_lista.context["pendencias"]]
    assert pendencia.pk not in pks_visiveis
