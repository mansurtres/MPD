# Roteiro de execução — v0.7.2

> Documento de trabalho criado para garantir continuidade entre sessões. Cobre os gaps levantados na revisão de fim-de-Fase-6 (chefe-de-área Anthropic, 2026-05-17). Deve ser **deletado ou movido para `docs/historico/` ao fechar a tag v0.7.2.**

## Estado de partida

- Tag atual: **v0.7.1** (UX polishings em forms de demanda — autocomplete, papel com choices, popup de tema).
- 190/190 testes verdes, ruff/black limpos, makemigrations sincronizado.
- Working tree pode conter alterações em `templates/layouts/app.html` (badges topbar) — verificar com `git status` antes de começar.

## Estado-alvo

- Tag: **v0.7.2**.
- Marco: fechar Fase 6 de fato (segurança, auditoria) + polimentos de robustez levantados pela revisão.
- Esperado: **≥ 200 testes verdes** (190 atuais + ~12 novos).
- ADRs novas: **0048–0052** (numeração contínua a partir de 0047).

## Branch e versão

- Branch: `feature/v0.7.2-seguranca-auditoria`
- `pyproject.toml` → `version = "0.7.2"`

## Princípios de execução

1. **Carta branca em decisões técnicas** — não devolver perguntas em pontos triviais. Se houver bifurcação real, explicar trade-off antes.
2. **Commits incrementais** — uma tarefa = um (ou poucos) commit(s) com Conventional Commits.
3. **Sem push até autorização explícita.**
4. **Verificar pyproject.toml e roadmap.md ao final** — mantê-los sincronizados.

---

# Marco 1 — Segurança e auditoria (4–5h)

Objetivo: fechar os 2 gaps de visibilidade + gap de auditoria. **Bloqueante** para o resto. Tudo que toca dado sensível.

## Tarefa 1.1 — Centralizar checagem de papel

**Por que:** 11 locais com `groups.filter(name__in=["Administrador", "Chefe de Gabinete"])` literais. ADR 0024 ("nunca checar grupo pelo nome") violado. Pré-requisito de 1.2 e 3.3.

**Arquivo novo:**
- [core/permissoes.py](../core/permissoes.py)

**Arquivos tocados:**
- [demandas/models.py](../demandas/models.py) — `Demanda.pode_ser_visto_por`, `Interacao.pode_editar`
- [demandas/views.py](../demandas/views.py) — `_filtrar_visiveis`, `_pode_exportar`, `InteracaoMarcarRealizadaView`, `AnexoDeleteView`
- [pessoas/views.py](../pessoas/views.py) — `PessoaListView.get_context_data`, `PessoaDetailView.get_context_data`, `EntidadeDetailView.get_context_data`, `PessoaCSVExportView.get`
- [core/views.py](../core/views.py) — `AnaliseView.test_func`, `AuditoriaListView.test_func`
- [core/context_processors.py](../core/context_processors.py) — `pendencias_usuario`

**Mudança conceitual:**

```python
# core/permissoes.py
"""Checagens de papel centralizadas. Única fonte de verdade dos nomes
dos grupos — qualquer rename só toca este arquivo.

ADR 0024: nunca checar grupo pelo nome no código de produto. Esta camada
é a exceção controlada: as 4 funções abaixo são o único lugar autorizado
a referenciar os literais. O resto do código chama as funções.
"""

GRUPO_ADM = "Administrador"
GRUPO_CG = "Chefe de Gabinete"
GRUPO_CO = "Coordenador"
GRUPO_AS = "Assessor"


def eh_cg_plus(user):
    """Admin ou Chefe de Gabinete. Visibilidade plena (incluindo restritas),
    acesso à auditoria, edição de interação alheia."""
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=[GRUPO_ADM, GRUPO_CG]).exists()


def eh_co_plus(user):
    """Admin, CG ou Coordenador. Exportação CSV, painel /analise."""
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=[GRUPO_ADM, GRUPO_CG, GRUPO_CO]).exists()
```

Substituir todos os call sites. Os **únicos** lugares que podem manter os literais são:
- `core/permissoes.py` (fonte)
- Data migrations que criam os grupos (precisam dos nomes)

**Critério de aceite:**
- `grep -rn 'name__in=\["Administrador' demandas/ pessoas/ core/ accounts/` retorna **apenas** `core/permissoes.py`.
- Testes existentes continuam verdes (sem regressão de comportamento).

**Teste novo** (em `core/tests.py`):

```python
def test_eh_cg_plus_superuser_sem_grupo(db):
    from core.permissoes import eh_cg_plus, eh_co_plus
    u = Usuario.objects.create_superuser(email="s@t.com", password="senha12345")
    assert eh_cg_plus(u)
    assert eh_co_plus(u)

def test_eh_co_plus_assessor_sem_grupo(db):
    from core.permissoes import eh_co_plus
    u = Usuario.objects.create_user(email="a@t.com", password="senha12345")
    assert not eh_co_plus(u)

def test_eh_cg_plus_anonimo():
    from core.permissoes import eh_cg_plus
    from django.contrib.auth.models import AnonymousUser
    assert not eh_cg_plus(AnonymousUser())
```

**Sem dependências. Faça primeiro.**

**Commit sugerido:** `refactor(core): centraliza checagem de papel em core/permissoes.py (ADR 0048)`

---

## Tarefa 1.2 — Filtrar restritas no painel `/analise`

**Por que:** Coordenador (não-ADM/CG) acessando `/analise` vê count de demandas restritas em 6 métricas. `top_pessoas` vaza **nome+sobrenome** de partes de casos sigilosos. Confidencialidade rompida.

**Arquivos tocados:**
- [demandas/models.py](../demandas/models.py) — adicionar custom manager
- [demandas/views.py](../demandas/views.py) — refactor `_filtrar_visiveis` para usar manager
- [core/views.py](../core/views.py) — `AnaliseView.get_context_data` aplica visibilidade

**Mudança conceitual:**

**1. Em `demandas/models.py`, antes da classe `Demanda`:**

```python
class DemandaQuerySet(models.QuerySet):
    def visiveis_para(self, user):
        """Filtra demandas pela regra de visibilidade restrita.
        Restritas só aparecem para: responsável, ADM, CG ou superuser.
        Ver ADR 0049 / permissoes.md §3.3."""
        from core.permissoes import eh_cg_plus
        if eh_cg_plus(user):
            return self
        return self.filter(models.Q(restrito=False) | models.Q(responsavel=user))


class DemandaManager(models.Manager.from_queryset(DemandaQuerySet)):
    pass
```

Na classe `Demanda`, adicionar `objects = DemandaManager()`.

**2. Em `demandas/views.py`:**

```python
def _filtrar_visiveis(qs, user):
    """Compat wrapper — chama o manager. Mantido como função porque várias
    views consomem como callable. Pode ser inlined em todo lugar com
    .visiveis_para(user) depois."""
    return qs.visiveis_para(user)
```

**3. Em `core/views.py:AnaliseView.get_context_data`, refatorar as 6 métricas:**

```python
from django.db.models import Q, Count
from django.db.models.functions import TruncMonth
from django.utils import timezone as tz
from datetime import timedelta
from demandas.models import Demanda, Encaminhamento
from pessoas.models import Pessoa
from accounts.models import Usuario

# Base: queryset de demandas visíveis ao usuário.
demandas_visiveis = Demanda.objects.visiveis_para(self.request.user)

# 1. Por tema — só de demandas visíveis.
ctx["por_tema"] = list(
    demandas_visiveis.values("temas__nome", "temas__cor")
    .annotate(total=Count("id"))
    .exclude(temas__nome__isnull=True)
    .order_by("-total")[:12]
)

# 2. Por mês.
limite_mes = tz.now() - timedelta(days=365)
ctx["por_mes"] = list(
    demandas_visiveis.filter(criado_em__gte=limite_mes)
    .annotate(mes=TruncMonth("criado_em"))
    .values("mes").annotate(total=Count("id")).order_by("mes")
)

# 3. Por coordenação.
ctx["por_coordenacao"] = list(
    demandas_visiveis.values("coordenacao_responsavel")
    .annotate(total=Count("id")).order_by("-total")
)
coord_display = dict(Demanda.COORDENACAO_CHOICES)
for item in ctx["por_coordenacao"]:
    item["display"] = coord_display.get(
        item["coordenacao_responsavel"], item["coordenacao_responsavel"]
    )

# 4. Top pessoas — filtrado por demandas visíveis via Count(filter=).
filtro_visivel = Q(demanda_pessoas__demanda__in=demandas_visiveis)
ctx["top_pessoas"] = list(
    Pessoa.objects.annotate(total=Count("demanda_pessoas", filter=filtro_visivel))
    .filter(total__gt=0).order_by("-total")[:20]
    .values("nome", "sobrenome", "slug_publico", "total")
)

# 5. Enc por órgão — filtrado por demandas visíveis.
ctx["enc_por_orgao"] = list(
    Encaminhamento.objects.filter(
        demanda__in=demandas_visiveis,
        status__in=[Encaminhamento.STATUS_ENVIADO, Encaminhamento.STATUS_PRAZO_VENCIDO],
    ).values("destinatario_orgao")
    .annotate(total=Count("id")).order_by("-total")[:15]
)

# 6. Carga por assessor — DEFER para tarefa 3.3 (transforma em 1 query).
#    Por ora, aplicar filtro de visibilidade no loop atual:
hoje = tz.now().date()
assessores = []
for u in Usuario.objects.filter(is_active=True):
    abertas = demandas_visiveis.filter(
        responsavel=u,
        status__in=[Demanda.STATUS_NOVO, Demanda.STATUS_EM_ANDAMENTO,
                    Demanda.STATUS_AGUARDANDO_TERCEIROS, Demanda.STATUS_AGUARDANDO_PESSOA],
    ).count()
    vencidas = (
        demandas_visiveis.filter(responsavel=u, prazo__lt=hoje)
        .exclude(status__in=[Demanda.STATUS_CONCLUIDA, Demanda.STATUS_ARQUIVADO])
        .count()
    )
    if abertas > 0 or vencidas > 0:
        assessores.append({
            "nome": u.nome_completo or u.email,
            "abertas": abertas, "vencidas": vencidas,
        })
ctx["carga_assessores"] = sorted(assessores, key=lambda x: -x["abertas"])
```

**Critério de aceite:**
- Coordenador em `/analise` vê counts **sem** demandas restritas de outras coords.
- Admin/CG continua vendo tudo.
- `top_pessoas` não inclui partes de demandas restritas inacessíveis.

**Testes novos** (em `demandas/tests.py`, ao lado dos outros testes de Fase 6):

```python
def test_analise_oculta_demandas_restritas_para_coord(client, coord_juridico, demanda_restrita_juridico, admin_user):
    """Coordenador da Comunicação não vê counts da demanda restrita da Jurídico
    no painel /analise — incluindo no por_mes (count total)."""
    # coord_juridico tem coordenacao='juridico' mas pertence ao grupo Coordenador
    # (não é responsável da demanda restrita). Pela regra, NÃO deve ver.
    # Cria uma demanda pública pra comparar.
    Demanda.objects.create(
        titulo="Pública", anonimo=True, canal_entrada="presencial",
        coordenacao_responsavel="comunicacao", criado_por=admin_user,
    )
    client.force_login(coord_juridico)
    resp = client.get(reverse("core:analise"))
    por_mes = resp.context["por_mes"]
    total_visivel = sum(m["total"] for m in por_mes)
    # Só a pública entra — a restrita fica oculta.
    assert total_visivel == 1

def test_analise_top_pessoas_oculta_partes_de_restrita(client, coord_juridico, demanda_restrita_juridico):
    """top_pessoas não revela nome de quem só aparece em demanda restrita."""
    client.force_login(coord_juridico)
    resp = client.get(reverse("core:analise"))
    nomes_visiveis = {p["nome"] for p in resp.context["top_pessoas"]}
    pessoa_restrita = demanda_restrita_juridico.demanda_pessoas.first().pessoa
    assert pessoa_restrita.nome not in nomes_visiveis

def test_analise_admin_ve_tudo(client, admin_user, demanda_restrita_juridico):
    """Sanity: admin continua vendo demandas restritas no painel."""
    client.force_login(admin_user)
    resp = client.get(reverse("core:analise"))
    por_mes = resp.context["por_mes"]
    total_admin = sum(m["total"] for m in por_mes)
    assert total_admin >= 1  # ao menos a restrita
```

**Depende de:** Tarefa 1.1.

**Commit sugerido:** `feat(analise): filtra demandas restritas por visibilidade (ADR 0049)`

---

## Tarefa 1.3 — Registrar `Interacao` e `ItemInbox` no auditlog

**Por que:** Timeline é o coração do produto e edição não deixa rastro. Devolutiva editada silenciosamente é o vetor que LGPD/Lei de Acesso quer fechar. ItemInbox descartado perde rastro de quem descartou.

**Arquivos tocados:**
- [demandas/apps.py](../demandas/apps.py)

**Mudança conceitual:**

```python
def ready(self):
    from auditlog.registry import auditlog
    from . import signals  # noqa: F401
    from .models import Anexo, Demanda, Encaminhamento, Interacao, ItemInbox, Tema

    auditlog.register(Demanda)
    auditlog.register(Encaminhamento)
    auditlog.register(Anexo)
    auditlog.register(Tema)
    # Fase 6.1 (ADR 0050): timeline e inbox entram na trilha.
    # Interações automáticas geram volume — aceito como custo de auditoria correta.
    # Se ficar barulhento em produção, considerar exclude_fields ou filtro no
    # AuditlogCorrelationMiddleware.
    auditlog.register(Interacao)
    auditlog.register(ItemInbox)
```

**Risco conhecido:** auditlog vai registrar **toda** Interacao automática (mudança_status, mudança_responsavel, etc.). Volume aumenta significativamente. **Aceitar** — são auditoria de fato (quem mudou o quê quando). Documentar em ADR 0050.

**Critério de aceite:**
- Editar uma Interacao gera `LogEntry(action=UPDATE)`.
- Descartar ItemInbox gera `LogEntry`.

**Testes novos** (em `demandas/tests.py`):

```python
def test_auditlog_registra_edicao_de_interacao(db, demanda, admin_user):
    from auditlog.models import LogEntry
    i = Interacao.objects.create(
        demanda=demanda, autor=admin_user,
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
    from demandas.models import ItemInbox
    from auditlog.models import LogEntry
    item = ItemInbox.objects.create(conteudo="Spam qualquer", autor=admin_user)
    item.status = ItemInbox.STATUS_DESCARTADO
    item.motivo_descarte = "Spam"
    item.save()
    logs = LogEntry.objects.get_for_object(item)
    assert logs.filter(action=LogEntry.Action.UPDATE).exists()
```

**Sem dependências.** Paralelo com 1.1 e 1.2.

**Commit sugerido:** `feat(demandas): auditlog cobre Interacao e ItemInbox (ADR 0050)`

---

## Tarefa 1.4 — Teste de regressão CSV (não vaza restritas)

**Por que:** `_filtrar_visiveis` já roda em `DemandaListView.get_queryset` e o CSV reusa. Mas **não há teste** confirmando.

**Arquivos tocados:** apenas testes.

**Teste novo** (em `demandas/tests.py`, perto dos outros testes de Fase 6):

```python
def test_export_csv_oculta_demanda_restrita_de_coord(client, coord_juridico, admin_user):
    """Coordenador não consegue exportar demanda restrita de outra coord
    mesmo via CSV. Confirma que _filtrar_visiveis aplicado no get_queryset
    cobre o fluxo de export."""
    publica = Demanda.objects.create(
        titulo="Publica", anonimo=True, canal_entrada="presencial",
        coordenacao_responsavel="comunicacao", criado_por=admin_user,
    )
    restrita = Demanda.objects.create(
        titulo="SegredoMaximo", anonimo=True, canal_entrada="presencial",
        coordenacao_responsavel="juridico", criado_por=admin_user, restrito=True,
    )
    client.force_login(coord_juridico)
    resp = client.get(reverse("demandas:demanda_export_csv"))
    assert resp.status_code == 200
    assert publica.numero.encode() in resp.content
    assert restrita.numero.encode() not in resp.content
    assert b"SegredoMaximo" not in resp.content
```

**Sem dependências.** Independente.

**Commit sugerido:** `test(demandas): regressão de visibilidade no export CSV`

---

# Marco 2 — Robustez de signals e fluxo (4–6h)

## Tarefa 2.1 — Excluir `TIPO_DEVOLUTIVA` do gatilho de avanço de status

**Por que:** `ConcluirDemandaView` em demanda `status=novo` cria 3 eventos na timeline (devolutiva manual + auto `novo→em_andamento` + auto `em_andamento→concluida`). Deveria criar 2 (devolutiva + transição direta).

**Arquivos tocados:**
- [demandas/signals.py](../demandas/signals.py)

**Mudança conceitual:**

```python
_TIPOS_INTERACAO_NAO_OPERACIONAIS = frozenset({
    Interacao.TIPO_REGISTRO_INICIAL,
    Interacao.TIPO_MUDANCA_STATUS,
    Interacao.TIPO_MUDANCA_RESPONSAVEL,
    Interacao.TIPO_MUDANCA_RESULTADO,
    Interacao.TIPO_ARQUIVAMENTO,
    # ADR 0048 / revisão fim-Fase-6: devolutiva é parte do fluxo de fechamento
    # (ConcluirDemandaView). Não deve avançar status — a view já vai setar concluida.
    Interacao.TIPO_DEVOLUTIVA,
})
```

**Critério de aceite:**
- Demanda em `novo` concluída por `ConcluirDemandaView` (responsiva) gera **exatamente 2 Interacoes** (devolutiva + mudança_status: novo→concluida).

**Teste novo:**

```python
def test_conclusao_de_demanda_nova_responsiva_gera_2_interacoes(client, admin_user, demanda):
    """Demanda em status=novo, ConcluirDemandaView cria devolutiva + 1 transição
    direta para concluida (sem passar por em_andamento intermediário fake)."""
    assert demanda.status == Demanda.STATUS_NOVO
    inicial = demanda.interacoes.count()
    client.force_login(admin_user)
    resp = client.post(reverse("demandas:demanda_concluir", args=[demanda.pk]), {
        "devolutiva_data": timezone.now().date(),
        "devolutiva_canal": "whatsapp",
        "devolutiva_conteudo": "Comunicado",
        "resultado": Demanda.RESULTADO_ATENDIDO,
        "resultado_observacao": "",
    })
    demanda.refresh_from_db()
    assert demanda.status == Demanda.STATUS_CONCLUIDA
    # +2: devolutiva manual + auto mudanca_status(novo→concluida).
    # Sem o fix: seriam +3 (também passaria por em_andamento intermediário).
    assert demanda.interacoes.count() == inicial + 2
    transicoes = demanda.interacoes.filter(tipo=Interacao.TIPO_MUDANCA_STATUS)
    assert transicoes.count() == 1
```

**Sem dependências.**

**Commit sugerido:** `fix(signals): devolutiva não dispara avanço de status (timeline limpa)`

---

## Tarefa 2.2 — `slug_publico` com retry em `IntegrityError`

**Por que:** TOCTOU em pre_save. Probabilidade microscópica de colisão (16¹²) mas falha vira 500 ininteligível.

**Arquivos tocados:**
- [pessoas/models.py](../pessoas/models.py) — override de `save()` em Pessoa e Entidade
- [pessoas/signals.py](../pessoas/signals.py) — remover geração de slug do pre_save

**Mudança conceitual:**

**1. Em `pessoas/models.py`, classe `Pessoa`:**

```python
import uuid

def save(self, *args, **kwargs):
    from django.db import IntegrityError
    if self.slug_publico:
        return super().save(*args, **kwargs)
    # Gera slug com retry em colisão (ADR 0051).
    for tentativa in range(10):
        self.slug_publico = uuid.uuid4().hex[:12]
        try:
            return super().save(*args, **kwargs)
        except IntegrityError as exc:
            if "slug_publico" not in str(exc).lower():
                raise
            if tentativa == 9:
                raise
            continue
```

Idem para `Entidade` (mesma lógica).

**2. Em `pessoas/signals.py`, remover a geração de slug do pre_save:**

```python
@receiver(pre_save, sender=Pessoa)
def normalizar_pessoa(sender, instance, **kwargs):
    # slug_publico agora é gerado em Pessoa.save() com retry (ADR 0051).
    instance.cpf = formatar_cpf(instance.cpf)
    instance.cep = formatar_cep(instance.cep)
    if instance.estado:
        instance.estado = instance.estado.upper()

# Idem para Entidade — remover `if not instance.slug_publico: ...`.
```

Função `_gerar_slug_unico` fica obsoleta — **remover**.

**Critério de aceite:**
- Comportamento normal idêntico.
- Colisão forçada não levanta IntegrityError para o caller.

**Teste novo:**

```python
def test_slug_publico_retenta_em_colisao(db, admin_user, monkeypatch):
    """Simula 1 colisão; segundo uuid deve passar."""
    from pessoas import models as pessoas_models
    slugs_forjados = iter([
        "aaaaaaaaaaaa00000000",  # primeira pessoa salva com este slug
        "aaaaaaaaaaaa00000000",  # segunda tenta o mesmo (colisão)
        "bbbbbbbbbbbb00000000",  # retry, sucesso
    ])
    class FakeUUID:
        def __init__(self, hex_str):
            self.hex = hex_str
    monkeypatch.setattr(
        pessoas_models.uuid, "uuid4",
        lambda: FakeUUID(next(slugs_forjados))
    )
    p1 = Pessoa.objects.create(nome="A", sobrenome="B", bairro="X", cidade="Y", criado_por=admin_user)
    p2 = Pessoa.objects.create(nome="C", sobrenome="D", bairro="X", cidade="Y", criado_por=admin_user)
    assert p1.slug_publico == "aaaaaaaaaaaa"
    assert p2.slug_publico == "bbbbbbbbbbbb"  # retry funcionou
```

**Atenção:** o teste depende do nome do módulo importado (`pessoas.models.uuid`). Pode precisar ajuste pequeno se o monkeypatch não pegar — alternativa é mockar `uuid.uuid4` no módulo `uuid` direto.

**Sem dependências.**

**Commit sugerido:** `fix(pessoas): slug_publico com retry em IntegrityError (ADR 0051)`

---

## Tarefa 2.3 — `_setup_anexos_orfaos` inline

**Por que:** Closure escondida + 4 receivers com mesmo nome dificulta debug.

**Arquivos tocados:**
- [demandas/signals.py](../demandas/signals.py)

**Mudança conceitual:**

```python
def _limpar_anexos_de(modelo):
    """Factory: retorna handler que limpa anexos polimórficos do modelo."""
    def handler(sender, instance, **kwargs):
        ct = ContentType.objects.get_for_model(modelo)
        Anexo.objects.filter(content_type=ct, object_id=instance.pk).delete()
    handler.__name__ = f"limpar_anexos_de_{modelo.__name__.lower()}"
    return handler


def _setup_anexos_orfaos():
    """Liga pre_delete dos modelos pais para limpar anexos polimórficos.
    GenericForeignKey não cascateia no banco — precisamos fazer manualmente."""
    from pessoas.models import Entidade, Pessoa
    for modelo in (Demanda, Pessoa, Entidade, Encaminhamento):
        pre_delete.connect(
            _limpar_anexos_de(modelo),
            sender=modelo,
            weak=False,
        )


_setup_anexos_orfaos()
```

Remover a função antiga `_registrar_limpeza_anexos`.

**Critério de aceite:**
- Comportamento idêntico (testes existentes verdes).
- Receivers ganham nomes distintos (`limpar_anexos_de_demanda`, etc.).

**Sem teste novo necessário** — coberto pelos testes existentes de cascata de anexo.

**Sem dependências.**

**Commit sugerido:** `refactor(signals): inline _setup_anexos_orfaos com nomes distintos`

---

## Tarefa 2.4 — `AnexoUploadView`: `get_object_or_404`

**Por que:** `.get()` cru estoura 500 se `object_id` inexistente.

**Arquivos tocados:**
- [demandas/views.py](../demandas/views.py) — `AnexoUploadView.post`

**Mudança conceitual:**

```python
def post(self, request, tipo, object_id):
    if tipo not in _TIPO_PARA_MODEL:
        raise Http404("Tipo de objeto pai inválido.")
    app_label, model_name = _TIPO_PARA_MODEL[tipo]
    try:
        ct = ContentType.objects.get(app_label=app_label, model=model_name)
    except ContentType.DoesNotExist:
        raise Http404("Tipo desconhecido.")
    objeto_pai = get_object_or_404(ct.model_class(), pk=object_id)
    # resto igual
```

**Critério de aceite:**
- POST a `/demandas/anexos/demanda/<uuid-inexistente>/` retorna **404**, não 500.

**Teste novo:**

```python
def test_anexo_upload_objeto_inexistente_404(client, admin_user):
    import uuid
    client.force_login(admin_user)
    resp = client.post(
        reverse("demandas:anexo_upload", args=["demanda", uuid.uuid4()]),
        {"descricao": "x"},
    )
    assert resp.status_code == 404
```

**Sem dependências.**

**Commit sugerido:** `fix(anexo): 404 em vez de 500 para objeto pai inexistente`

---

## Tarefa 2.5 — `ProcessarInboxView`: mensagem clara em conflito

**Por que:** Dois assessores processam o mesmo item; segundo recebe 404 sem entender.

**Arquivos tocados:**
- [demandas/views.py](../demandas/views.py) — `ProcessarInboxView.get` e `.post`

**Mudança conceitual:**

```python
def _redirecionar_se_ja_processado(self, request, item):
    """Helper compartilhado por GET e POST."""
    if item.status == ItemInbox.STATUS_PENDENTE:
        return None
    nome = "outro usuário"
    if item.processado_por:
        nome = item.processado_por.nome_completo or item.processado_por.email
    messages.info(request, f"Este item já foi processado por {nome}.")
    if item.demanda_gerada_id:
        return redirect("demandas:demanda_detalhe", pk=item.demanda_gerada_id)
    return redirect("demandas:inbox_lista")

def get(self, request, pk):
    item = get_object_or_404(ItemInbox, pk=pk)
    redirecionar = self._redirecionar_se_ja_processado(request, item)
    if redirecionar:
        return redirecionar
    # ... resto igual ao código atual com `item` já buscado

def post(self, request, pk):
    item = get_object_or_404(ItemInbox, pk=pk)
    redirecionar = self._redirecionar_se_ja_processado(request, item)
    if redirecionar:
        return redirecionar
    # ... resto igual
```

(Remover o `status=ItemInbox.STATUS_PENDENTE` do `get_object_or_404` atual.)

**Critério de aceite:**
- Re-abrir item já processado redireciona para a demanda gerada (não 404).

**Teste novo:**

```python
def test_processar_inbox_ja_processado_redireciona_para_demanda(client, admin_user, pessoa):
    from demandas.models import ItemInbox
    item = ItemInbox.objects.create(conteudo="Item teste", autor=admin_user)
    # Simula processamento prévio:
    demanda = Demanda.objects.create(
        titulo="Já criada", anonimo=True, canal_entrada="presencial",
        coordenacao_responsavel="gabinete", criado_por=admin_user,
    )
    item.status = ItemInbox.STATUS_PROCESSADO
    item.demanda_gerada = demanda
    item.processado_por = admin_user
    item.processado_em = timezone.now()
    item.save()
    client.force_login(admin_user)
    resp = client.get(reverse("demandas:inbox_processar", args=[item.pk]))
    assert resp.status_code == 302
    assert reverse("demandas:demanda_detalhe", args=[demanda.pk]) in resp.url
```

**Sem dependências.**

**Commit sugerido:** `feat(inbox): mensagem clara em conflito de processamento`

---

# Marco 3 — Limpeza e performance (3–4h)

## Tarefa 3.1 — Bumpar versão

**Arquivos tocados:**
- [pyproject.toml](../pyproject.toml)

```toml
version = "0.7.2"
```

Sem teste. Sem dependência.

**Commit sugerido:** `chore: bump versão para 0.7.2`

---

## Tarefa 3.2 — Auditar dependências mortas

**Decisão de produto:**
- **Remover `factory-boy`** — zero uso, sem plano de uso.
- **Manter `django-htmx`** — middleware útil para evolução incremental do front-end (boring stack). Documentar em ADR 0052.

**Arquivos tocados:**
- [pyproject.toml](../pyproject.toml) — remover `factory-boy>=3.3` de `[project.optional-dependencies].dev`
- Rodar `uv lock` para regenerar `uv.lock`

**Critério de aceite:**
- `uv sync --extra dev` instala sem factory-boy.
- Testes verdes.

**Sem teste novo.**

**Commit sugerido:** `chore: remove factory-boy (não usado) — mantém django-htmx (ADR 0052)`

---

## Tarefa 3.3 — `AnaliseView.carga_assessores` em uma query

**Por que:** N+1 (2 queries por usuário ativo). Trivial corrigir agora.

**Arquivos tocados:**
- [core/views.py](../core/views.py) — `AnaliseView.get_context_data`, bloco 6 (`carga_assessores`)

**Mudança conceitual:**

```python
from django.db.models import Q, Count

status_abertos = [
    Demanda.STATUS_NOVO, Demanda.STATUS_EM_ANDAMENTO,
    Demanda.STATUS_AGUARDANDO_TERCEIROS, Demanda.STATUS_AGUARDANDO_PESSOA,
]
status_fechados = [Demanda.STATUS_CONCLUIDA, Demanda.STATUS_ARQUIVADO]
hoje = tz.now().date()

# Visibilidade aplicada via subquery (vem da Tarefa 1.2).
ids_visiveis = list(demandas_visiveis.values_list("id", flat=True))

filtro_abertas = Q(
    demandas_responsavel__in=ids_visiveis,
    demandas_responsavel__status__in=status_abertos,
)
filtro_vencidas = (
    Q(demandas_responsavel__in=ids_visiveis)
    & Q(demandas_responsavel__prazo__lt=hoje)
    & ~Q(demandas_responsavel__status__in=status_fechados)
)
assessores_qs = (
    Usuario.objects.filter(is_active=True)
    .annotate(
        abertas=Count("demandas_responsavel", filter=filtro_abertas, distinct=True),
        vencidas=Count("demandas_responsavel", filter=filtro_vencidas, distinct=True),
    )
    .filter(Q(abertas__gt=0) | Q(vencidas__gt=0))
    .order_by("-abertas")
)
ctx["carga_assessores"] = [
    {"nome": u.nome_completo or u.email, "abertas": u.abertas, "vencidas": u.vencidas}
    for u in assessores_qs
]
```

**Atenção:** `values_list("id", flat=True)` força avaliação do subquery — em PG isso vira uma query, depois outra com `IN`. Aceitável e legível. Alternativa mais sofisticada: usar `Subquery` do Django, mas vale a pena só se virar gargalo.

**Critério de aceite:**
- Mesmo resultado final.
- `connection.queries` mostra ≤ 3 queries para esta métrica (era N+1).

**Teste novo:**

```python
def test_analise_carga_assessores_nao_tem_n_mais_1(client, admin_user):
    """Sanity: query count constante independente do nº de usuários ativos."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext
    Usuario = get_user_model()
    for i in range(20):
        Usuario.objects.create_user(email=f"u{i}@t.com", password="senha12345")  # pragma: allowlist secret
    client.force_login(admin_user)
    with CaptureQueriesContext(connection) as ctx:
        client.get(reverse("core:analise"))
    # Antes do fix: ~40 queries só nesta métrica (2 por usuário).
    # Limite generoso pra cobrir as outras 5 métricas + auth.
    assert len(ctx.captured_queries) < 30, f"{len(ctx.captured_queries)} queries"
```

**Depende de:** Tarefa 1.2 (`demandas_visiveis`).

**Commit sugerido:** `perf(analise): carga_assessores em uma annotate (elimina N+1)`

---

## Tarefa 3.4 — `PessoaCSVExportView`: cache de prefetch

**Por que:** `.first()` em prefetch não usa cache. Para 10k pessoas = 20k queries.

**Arquivos tocados:**
- [pessoas/views.py](../pessoas/views.py) — `PessoaCSVExportView.get`

**Mudança conceitual:**

```python
for p in qs:
    telefones = list(p.telefones.all())  # usa cache do prefetch
    emails = list(p.emails.all())
    tel = telefones[0] if telefones else None
    email = emails[0] if emails else None
    tags = ", ".join(t.nome for t in p.tags.all())
    writer.writerow([
        # ...
        tel.numero if tel else "",
        email.endereco if email else "",
        # ...
    ])
```

**Critério de aceite:**
- Query count constante independente de N.

**Teste novo:**

```python
def test_export_csv_pessoas_nao_tem_n_mais_1(client, admin_user):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext
    from pessoas.models import Telefone
    for i in range(30):
        p = Pessoa.objects.create(
            nome=f"P{i}", sobrenome="X", bairro="Y", cidade="Z", criado_por=admin_user
        )
        Telefone.objects.create(pessoa=p, numero="27999999999", tipo="celular")
    client.force_login(admin_user)
    with CaptureQueriesContext(connection) as captured:
        client.get(reverse("pessoas:pessoa_export_csv"))
    # Sem N+1: ~5-7 queries totais (qs principal + prefetches + auth).
    assert len(captured.captured_queries) < 15
```

**Sem dependências.**

**Commit sugerido:** `perf(pessoas): export CSV usa cache de prefetch`

---

# Sequenciamento e paralelização

```
Bloqueante (ordem rígida):
  1.1 papel centralizado
       └─→ 1.2 /analise filtra restritas
              └─→ 3.3 carga_assessores em 1 query

Independentes (podem ser feitas em qualquer ordem entre si):
  1.3 auditlog interacao/inbox
  1.4 teste regressão CSV
  2.1 devolutiva fora do gatilho
  2.2 retry em slug_publico
  2.3 inline anexos órfãos
  2.4 anexo upload 404
  2.5 processar inbox conflito
  3.1 bump versão (trivial, deixar pro final)
  3.2 deps
  3.4 export pessoas N+1
```

**Ordem recomendada em execução linear:** 1.1 → 1.3 → 1.2 → 1.4 → 2.1 → 2.2 → 2.4 → 2.5 → 2.3 → 3.3 → 3.4 → 3.2 → 3.1 → ADRs → CLAUDE.md → roadmap.md → tag.

---

# ADRs a criar (em `docs/decisoes.md`)

Numeração continua de 0047 (último). Adicionar ao final do arquivo, em ordem:

- **ADR 0048 — Centralização de checagem de papel em `core/permissoes.py`.**
  Contexto: 11 lugares com strings de grupo literais; ADR 0024 violada. Decisão: única função por papel composto (`eh_cg_plus`, `eh_co_plus`). Consequência: rename de grupo = 1 arquivo.

- **ADR 0049 — Manager `Demanda.objects.visiveis_para(user)` e extensão ao painel `/analise`.**
  Contexto: AnaliseView vazava contagens de restritas para coordenadores (não-ADM/CG). Decisão: regra de visibilidade migra para custom manager; `/analise` aplica nas 6 métricas. Consequência: top_pessoas e demais counts respeitam restrição.

- **ADR 0050 — Auditlog estendido para `Interacao` e `ItemInbox`** (revisita ADR 0029).
  Contexto: timeline e inbox eram os únicos models de domínio sem trilha. Edição de devolutiva era invisível. Decisão: registrar ambos. Consequência: volume de LogEntry aumenta (interações automáticas geram registros); aceito como custo correto de auditoria.

- **ADR 0051 — `slug_publico` com retry em `IntegrityError`** (revisita ADR 0038).
  Contexto: TOCTOU em pre_save. Decisão: gerar slug em `save()` com loop de retry; remover do pre_save. Consequência: race condition tratada; código mais explícito.

- **ADR 0052 — Manutenção de `django-htmx`; remoção de `factory-boy`.**
  Contexto: revisão de fim-de-Fase-6 identificou deps possivelmente mortas. Decisão: factory-boy fora (zero uso, sem plano); django-htmx mantido (middleware útil quando incrementarmos UI). Consequência: dependency tree mais limpa, frame para evolução incremental do front com HTMX.

Cada ADR segue o padrão estabelecido em `docs/decisoes.md` (cabeçalho `## ADR NNNN — título` + corpo curto com Contexto, Decisão, Consequência).

---

# Critério de fechamento de v0.7.2

Para considerar pronto e gerar a tag:

1. **`uv run pytest -q`:** todos verdes (esperado ≥ 200).
2. **`uv run ruff check . && uv run black --check .`:** limpo.
3. **`uv run python manage.py check`:** sem issues novas (deploy warnings em dev são esperados).
4. **`uv run python manage.py makemigrations --check`:** sincronizado.
5. **Grep de saneamento:** `Grep "name__in=\\[.Administrador" demandas/ pessoas/ core/ accounts/` retorna apenas `core/permissoes.py` e migrations.
6. **Smoke manual** (5 min):
   - Login como `coord@test.com` (fixture `coord_juridico`): abrir `/analise` e confirmar que conta não inclui demandas restritas de outras coords.
   - Editar uma `Interacao` e confirmar em `/auditoria` que aparece o update.
   - Concluir demanda em `STATUS_NOVO` (responsiva) e verificar timeline com 2 eventos (devolutiva + transição direta).
   - Tentar processar item de inbox já processado: deve redirecionar para a demanda gerada com mensagem.
   - Subir arquivo via `/demandas/anexos/demanda/<uuid-fake>/`: deve dar 404 (não 500).
7. **ADRs 0048–0052 criadas em `docs/decisoes.md`.**
8. **`CLAUDE.md` atualizado** — bloco "Estado atual" com v0.7.2 fechado.
9. **`roadmap.md` atualizado** — Fase 6 marcada como fechada de verdade; Fase 7 com data de início.
10. **`pyproject.toml` em `0.7.2`.**
11. **Tag git `v0.7.2`** (anotada). **Não pushar sem confirmação explícita do Pedro** (feedback `feedback_nao_pushar_sem_confirmacao`).
12. **Deletar este arquivo** ou movê-lo para `docs/historico/roteiro-v0.7.2.md` se valor de retrospectiva.

---

# Fora de escopo (deliberado)

Pontos da revisão **adiados** para fases futuras:

- **`EstadoForm` modal de confirmação ao classificar resultado** → Fase 7 (consolidar com outras melhorias UX).
- **`pg_trgm` para autocomplete em 10k+ pessoas** → fase posterior, quando o mandato escalar.
- **`pg_dump -Fc` + rotação + encriptação no backup** → Fase 7 (produção).
- **DT-011 (gestão de usuários arquitetural)** → antes de produção, já registrado em `docs/debito-tecnico.md`.

---

*Documento gerado em 2026-05-17 a partir da revisão técnica de fim-de-Fase-6.*
