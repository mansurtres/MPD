# Permissões need-to-know (ADR 0059) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) ou superpowers:executing-plans para implementar tarefa-a-tarefa. Os passos usam checkbox (`- [ ]`).

**Goal:** Inverter o modelo de acesso do MPD de "colaborativo por default" para **privilégio mínimo / need-to-know** (ADR 0059): 3 papéis (Admin / Chefe de Gabinete / Assessor), removendo Coordenação e `restrito`, com visibilidade inteiramente por papel, busca cega e exportação/auditoria/análise/configuração exclusivas do Admin.

**Architecture:** A regra de visibilidade vive num único ponto — `Demanda.objects.visiveis_para(user)` + o predicado Q em `demandas/models.py` — e nos helpers de papel em `core/permissoes.py`. Checagem de papel NUNCA fora desses pontos (ADR 0024/0048). Front esconde por papel em 3 camadas (template/view/manager). Removações de campo espelham o drop de `papel` (ADR 0054): ajustar testes → model → forms → views → templates → migration → suíte verde.

**Tech Stack:** Django 5.2, PostgreSQL (SQLite in-memory nos testes), pytest, ruff, black, `uv`.

## Global Constraints

- **Fonte de verdade:** `docs/decisoes.md` ADR 0059 + `docs/permissoes.md` v2. O código não vai além delas.
- Idioma: código em inglês, domínio/UI em português.
- Comentário Django `{# #}` **só uma linha** (há hook de pre-commit que bloqueia multi-linha).
- Plataforma Windows; atalhos sempre `Ctrl`.
- **Nunca pushar sem confirmação.** Commits incrementais (Conventional Commits; escopo = app).
- **Suíte verde é gate de cada tarefa:** `uv run pytest -q` (linha de base: 228). Também `ruff check .`, `black .`, `manage.py check`, `makemigrations --check`.
- Papéis: `eh_admin` (Admin/superuser), `eh_cg_plus` (Admin **ou** Chefe de Gabinete). **Assessor = qualquer logado que não é nenhum dos dois.** Não criar checagem de "é assessor" por nome de grupo na lógica de visibilidade — usar a negação.
- `STATUS_ATIVOS` = todos os status de `Demanda` **exceto** `concluida` e `arquivado`.

---

## Convenções deste plano

As remoções de campo (Coordenação, `restrito`) seguem o **padrão já provado do `papel`** (commit `849af41`): remover dos testes → model → forms → templates/JS → migration `RemoveField` → rodar a suíte. Onde digo "espelhe o padrão papel", o implementador lê aquele commit como referência. O núcleo novo (visibilidade, busca cega, gating) vem com código/teste completos.

Verificação por tarefa: `uv run pytest -q` verde + `ruff`/`black`/`check`/`makemigrations --check` limpos.

---

## FASE 1 — Remoções de campo (encolhem a superfície)

### Task 1: Drop do flag `restrito`

**Files:**
- Modify: `demandas/models.py` (campo `restrito`, qualquer uso em `clean`/índices), `demandas/forms.py` (`DemandaForm.fields`), `demandas/admin.py`, `demandas/views/*.py` (ramos `restrito` na visibilidade — ver Task 7 reescreve a visibilidade; aqui só remover o campo e o ramo `Q(restrito=False)`), `demandas/tests.py`
- Modify templates: `templates/demandas/lista.html` (ícone cadeado 🔒 + coluna), `templates/demandas/detalhe.html` (badge/uso de restrito), `templates/demandas/form.html` (checkbox "Marcar como restrita")
- Create: `demandas/migrations/00NN_drop_restrito.py` (`RemoveField` + remover a permissão custom `pode_marcar_restrita` se declarada em `Meta.permissions`)

**Interfaces:**
- Produces: `Demanda` sem `restrito`; visibilidade deixa de ter ramo `restrito` (vira responsável-only até a Task 7 reescrever para need-to-know).

- [ ] **Step 1: Testes** — em `demandas/tests.py`, remover/ajustar todos os testes que criam `Demanda(..., restrito=True)` ou asseguram visibilidade de restrita (ex.: `test_*_restrita*`). Remover asserts sobre o cadeado na lista.
- [ ] **Step 2: Model** — remover `restrito = models.BooleanField(...)`; remover `pode_marcar_restrita` de `Meta.permissions` (se existir); ajustar `_q_demanda_visivel_para` para não referenciar `restrito` (interim: `Q(responsavel=user)` para não-CG+ — será reescrito na Task 7).
- [ ] **Step 3: Form/admin** — remover `restrito` de `DemandaForm.fields` e de `demandas/admin.py` (list_display/fieldsets/filters).
- [ ] **Step 4: Templates** — remover o checkbox "Marcar como restrita" do form; o ícone cadeado e qualquer `{% if d.restrito %}` da lista e do detalhe.
- [ ] **Step 5: Migration** — `uv run python manage.py makemigrations demandas -n drop_restrito` → confirmar `RemoveField` (e remoção da permissão, se aplicável).
- [ ] **Step 6: Verificar** — `migrate` + `pytest -q` verde + `grep -rn "restrit" demandas/ templates/demandas/` só retorna migrations históricas. `makemigrations --check` limpo.
- [ ] **Step 7: Commit** — `refactor(demandas): drop do flag restrito (ADR 0059 supersede 0007)`

**Acceptance:** nenhuma referência viva a `restrito`; suíte verde; cadeado/checkbox sumiram da UI.

### Task 2: Drop do campo Coordenação (time)

**Files:**
- Modify: `accounts/models.py` (`Usuario.coordenacao` + `COORDENACAO_CHOICES`), `accounts/admin.py`, `accounts/forms.py`, `accounts/tests.py`
- Modify: `demandas/models.py` (`Demanda.coordenacao_responsavel` + `COORDENACAO_CHOICES` + índice `(status, coordenacao_responsavel)`), `demandas/forms.py` (`DemandaForm`), `demandas/admin.py`, `demandas/tests.py`
- Modify: `demandas/views/demandas.py` (quick filter `minha_coord`, `coord`/`coord_choices`/`coord_atual`), `demandas/views/_shared.py`, `demandas/views/inbox.py`, `demandas/views/export.py` (coluna coordenação no CSV), `pessoas/views.py`
- Modify: `core/views.py` (métricas "demandas por coordenação" e "carga por coordenação" no `AnaliseView`), `core/tests.py`
- Modify templates: `templates/demandas/{lista,detalhe,form}.html`, `templates/accounts/usuarios/{lista,form}.html`, `templates/core/analise.html`, `templates/layouts/app.html` (se citar)
- Modify: `pessoas/management/commands/criar_dados_teste.py`, `demandas/management/commands/verificar_integridade.py`
- Create: `accounts/migrations/00NN_drop_coordenacao.py`, `demandas/migrations/00NN_drop_coordenacao_responsavel.py`

**Interfaces:**
- Produces: `Usuario` sem `coordenacao`; `Demanda` sem `coordenacao_responsavel`; sem filtro/métrica de coordenação.

- [ ] **Step 1: Testes** — remover de `demandas/tests.py`, `accounts/tests.py`, `core/tests.py`, `pessoas/tests.py` todo `coordenacao=`/`coordenacao_responsavel=` em fixtures e os testes do filtro "minha coordenação" e da métrica "por coordenação".
- [ ] **Step 2: Models** — remover os dois campos + `COORDENACAO_CHOICES` (accounts e demandas) + o índice `(status, coordenacao_responsavel)`.
- [ ] **Step 3: Forms/admin** — remover de `DemandaForm`, `UsuarioCreateForm`/`UsuarioUpdateForm` (campo coordenação no form de usuário) e dos dois `admin.py`.
- [ ] **Step 4: Views** — remover o quick filter "Da minha coordenação" + lógica `coord`/`coord_choices` em `demandas/views/demandas.py`; a coluna coordenação no CSV (`export.py`); as métricas de coordenação no `AnaliseView` (`core/views.py`); qualquer auto-preenchimento de `coordenacao_responsavel` ao criar demanda.
- [ ] **Step 5: Templates/seed/integridade** — remover coordenação dos templates listados, do `criar_dados_teste` e do `verificar_integridade`.
- [ ] **Step 6: Migrations** — `makemigrations accounts demandas -n drop_coordenacao` → `RemoveField` (×2) + drop do índice.
- [ ] **Step 7: Verificar** — `migrate` + `pytest -q` verde + `grep -rniE "coordenac" accounts/ demandas/ core/ pessoas/ templates/ --include=*.py --include=*.html` só retorna o papel "Coordenador" (grupo) e migrations históricas — **nenhum** uso do campo. `makemigrations --check` limpo.
- [ ] **Step 8: Commit** — `refactor: drop do campo Coordenação/time (ADR 0059, supersede 0041)`

**Acceptance:** campo coordenação ausente de model/form/view/UI/seed; só o papel "Coordenador" (grupo, removido na Fase 2) e migrations históricas mencionam "coordena"; suíte verde.

---

## FASE 2 — Papéis 4→3 e bloqueio de exportação

### Task 3: Exportação, auditoria, análise e config exclusivas do Admin

**Files:**
- Modify: `demandas/views/_shared.py:15` (`_pode_exportar`), `pessoas/views.py:95,758`, `core/views.py:95` (`AnaliseView.test_func`), `demandas/views/anexos.py:150`
- Modify: `core/tests.py`, `demandas/tests.py`, `pessoas/tests.py` (testes de gating de export/análise)

**Interfaces:**
- Consumes: `core.permissoes.eh_admin`, `eh_cg_plus`.
- Produces: export/análise/auditoria/config só ADM; remoção de anexo alheio = CG+.

- [ ] **Step 1: Teste (TDD)** — em `pessoas/tests.py` e `demandas/tests.py`, escrever/ajustar: CG **não** exporta CSV (403/ausência do botão) e **não** acessa `/analise` (403); Admin exporta e acessa. Em `core/tests.py`: `/analise` agora exige `eh_admin` (CG recebe 403).

```python
def test_cg_nao_exporta_csv(client, usuario_chefe):
    client.force_login(usuario_chefe)
    assert client.get(reverse("demandas:demanda_export_csv")).status_code == 403

def test_cg_nao_acessa_analise(client, usuario_chefe):
    client.force_login(usuario_chefe)
    assert client.get(reverse("core:analise")).status_code == 403
```

- [ ] **Step 2: Rodar e ver falhar** — `pytest demandas/tests.py::test_cg_nao_exporta_csv core/tests.py::test_cg_nao_acessa_analise -q` → FAIL (hoje CG exporta/analisa).
- [ ] **Step 3: Implementar** — `_pode_exportar` passa a `return eh_admin(user)`; `pessoas/views.py` idem (`pode_exportar`/gating CSV → `eh_admin`); `core/views.py` `AnaliseView.test_func` → `eh_admin`. Auditoria já é `eh_admin`. Anexo alheio (`anexos.py:150`) `eh_co_plus` → `eh_cg_plus`.
- [ ] **Step 4: Verificar** — `pytest -q` verde.
- [ ] **Step 5: Commit** — `feat(permissoes): export/analise exclusivos do Admin; anexo alheio = CG+ (ADR 0059)`

**Acceptance:** CG/Assessor não exportam nem acessam `/analise`; só Admin. Suíte verde.

### Task 4: Remover o papel "Coordenador" (4→3 grupos)

**Files:**
- Modify: `core/permissoes.py` (remover `GRUPO_CO` e `eh_co_plus` — agora sem uso após Task 3), `core/context_processors.py` (remover `papel_eh_coordenador`, `papel_co_plus`)
- Modify: `core/tests.py` (testes de `eh_co_plus`)
- Create: data migration `accounts/migrations/00NN_remove_grupo_coordenador.py` — move membros do grupo "Coordenador" para "Assessor" e remove o grupo.

**Interfaces:**
- Produces: 3 grupos (Administrador, Chefe de Gabinete, Assessor); `eh_co_plus` deixa de existir.

- [ ] **Step 1: Confirmar zero uso de `eh_co_plus`** — `grep -rn "eh_co_plus\|papel_co_plus\|GRUPO_CO\b\|papel_eh_coordenador" --include=*.py --include=*.html` (fora de core/permissoes/context_processors/tests). Deve estar vazio após Task 3. Se restar, redirecionar para `eh_cg_plus`/`eh_admin` conforme a regra.
- [ ] **Step 2: Data migration** — RunPython: `Group.objects.get(name="Coordenador")` → para cada user, `user.groups.add(grupo_assessor)`, depois `grupo_coordenador.delete()`. Guard `DoesNotExist`. Reverso: recria o grupo vazio (no-op aceitável).
- [ ] **Step 3: Remover helpers** — apagar `eh_co_plus` e `GRUPO_CO` de `core/permissoes.py`; `papel_eh_coordenador`/`papel_co_plus` de `core/context_processors.py`; ajustar/remover os testes de `eh_co_plus` em `core/tests.py`.
- [ ] **Step 4: Verificar** — `migrate` + `pytest -q` verde; `grep -rn "Coordenador\|eh_co_plus" --include=*.py` só em migrations históricas.
- [ ] **Step 5: Commit** — `feat(permissoes): remove o papel Coordenador — papéis v1 = Admin/CG/Assessor (ADR 0059)`

**Acceptance:** 3 grupos; `eh_co_plus`/`GRUPO_CO` removidos; membros antigos viram Assessor; suíte verde.

---

## FASE 3 — Visibilidade need-to-know (o núcleo)

### Task 5: Predicado de visibilidade por papel

**Files:**
- Modify: `demandas/models.py` (`_q_demanda_visivel_para`, `DemandaQuerySet.visiveis_para`, `Demanda.q_visivel_para`, `Demanda.pode_ser_visto_por`; adicionar constante `STATUS_ATIVOS`)
- Modify: `demandas/tests.py`

**Interfaces:**
- Consumes: `eh_admin`, `eh_cg_plus`, `Demanda.STATUS_ATIVOS`, `Demanda.responsavel`, `Demanda.criado_por`.
- Produces: `Demanda.objects.visiveis_para(user)` com a regra dos 3 papéis; usado por todas as listas/detalhes.

- [ ] **Step 1: Teste (TDD)** — em `demandas/tests.py`:

```python
def test_visibilidade_admin_ve_tudo(db, admin_user, demanda, demanda_concluida_de_outro):
    vis = set(Demanda.objects.visiveis_para(admin_user))
    assert demanda in vis and demanda_concluida_de_outro in vis

def test_visibilidade_cg_ve_ativas_nao_concluidas(db, usuario_chefe, demanda, demanda_concluida_de_outro):
    vis = set(Demanda.objects.visiveis_para(usuario_chefe))
    assert demanda in vis                       # ativa
    assert demanda_concluida_de_outro not in vis  # concluída de outro → CG não vê

def test_visibilidade_assessor_so_as_proprias(db, usuario_comum, demanda_de_outro, demanda_do_assessor):
    vis = set(Demanda.objects.visiveis_para(usuario_comum))
    assert demanda_do_assessor in vis           # responsável ou autor
    assert demanda_de_outro not in vis

def test_visibilidade_assessor_ve_propria_concluida(db, usuario_comum, demanda_concluida_do_assessor):
    assert demanda_concluida_do_assessor in set(Demanda.objects.visiveis_para(usuario_comum))
```

(Fixtures necessárias: `usuario_chefe` no grupo "Chefe de Gabinete"; `demanda_do_assessor` com `responsavel=usuario_comum`; `demanda_concluida_do_assessor` idem com status concluída; `demanda_de_outro`/`demanda_concluida_de_outro` de terceiros. Criar no `demandas/tests.py`.)

- [ ] **Step 2: Rodar e ver falhar** — `pytest demandas/tests.py -k visibilidade -q` → FAIL.
- [ ] **Step 3: Implementar** — em `demandas/models.py`:

```python
# Constante (na classe Demanda)
STATUS_ATIVOS = [STATUS_NOVO, STATUS_EM_ANDAMENTO, STATUS_AGUARDANDO_PESSOA, STATUS_AGUARDANDO_TERCEIROS]

def _q_demanda_visivel_para(user):
    """Predicado Q de visibilidade need-to-know (ADR 0059).
    Admin → None (tudo). CG → todas as ATIVAS. Assessor → as próprias
    (responsável ou autor), ativas + histórico próprio."""
    from core.permissoes import eh_admin, eh_cg_plus
    if eh_admin(user):
        return None
    if eh_cg_plus(user):
        return Q(status__in=Demanda.STATUS_ATIVOS)
    return Q(responsavel=user) | Q(criado_por=user)
```

`visiveis_para`/`q_visivel_para`/`pode_ser_visto_por` passam a usar esse predicado (pode_ser_visto_por: Admin True; CG `status in ATIVOS`; senão `responsavel==user or criado_por==user`).

- [ ] **Step 4: Verificar** — `pytest -q` verde (incluindo os testes existentes de lista que agora refletem a nova regra — ajustar os que assumiam "todos veem tudo").
- [ ] **Step 5: Commit** — `feat(demandas): visibilidade need-to-know por papel (ADR 0059)`

**Acceptance:** Admin vê tudo; CG só ativas; Assessor só as próprias (incl. próprias concluídas); suíte verde.

### Task 6: Mascarar dados das partes no histórico do Assessor

**Files:**
- Modify: `demandas/views/demandas.py` (`DemandaDetailView.get_context_data` — flag `mascarar_partes`), `templates/demandas/detalhe.html` (aside de partes), `demandas/tests.py`

**Interfaces:**
- Consumes: `eh_admin`, `eh_cg_plus`, `Demanda.STATUS_ATIVOS`.
- Produces: contexto `mascarar_partes` (bool) consumido pelo template.

- [ ] **Step 1: Teste (TDD)** — Assessor abrindo a **própria demanda concluída**: a resposta contém o **nome** da parte mas **não** o link para a ficha (`pessoa_detalhe`) nem dados de contato.

```python
def test_assessor_historico_mascara_ficha_da_parte(client, usuario_comum, demanda_concluida_do_assessor_com_pessoa):
    client.force_login(usuario_comum)
    resp = client.get(reverse("demandas:demanda_detalhe", args=[demanda_concluida_do_assessor_com_pessoa.slug_publico]))
    body = resp.content.decode()
    assert "Maria" in body                       # nome aparece
    assert "pessoa_detalhe" not in body or "/pessoas/" not in body  # sem link p/ ficha
```

- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar** — em `DemandaDetailView.get_context_data`: `ctx["mascarar_partes"] = (not eh_admin(u) and not eh_cg_plus(u) and self.object.status not in Demanda.STATUS_ATIVOS)`. No `detalhe.html`, no aside de partes: `{% if mascarar_partes %}` mostra só `{{ dp.pessoa.nome_exibicao }}` (texto, sem `<a>` e sem contato); `{% else %}` o atual (com link).
- [ ] **Step 4: Verificar** — `pytest -q` verde.
- [ ] **Step 5: Commit** — `feat(demandas): mascara ficha das partes no histórico do Assessor (ADR 0059)`

**Acceptance:** no histórico próprio do Assessor, nome da parte aparece sem link/contato; nas ativas, contexto completo. Suíte verde.

---

## FASE 4 — Acervo de pessoas/entidades: esconder e busca cega

### Task 7: Listas de Pessoas/Entidades exclusivas do Admin

**Files:**
- Modify: `pessoas/views.py` (`PessoaListView`, `EntidadeListView` → exigir `eh_admin`; idem export, já feito), `templates/layouts/app.html` (links "Pessoas"/"Entidades" só p/ Admin via `papel_eh_admin`), `pessoas/tests.py`

- [ ] **Step 1: Teste (TDD)** — Assessor/CG GET `/pessoas/` e `/entidades/` → 403; Admin → 200.

```python
def test_assessor_nao_lista_pessoas(client, usuario_comum):
    client.force_login(usuario_comum)
    assert client.get(reverse("pessoas:pessoa_lista")).status_code == 403
```

- [ ] **Step 2: Rodar e ver falhar** (hoje todos listam).
- [ ] **Step 3: Implementar** — `PessoaListView`/`EntidadeListView` ganham `UserPassesTestMixin` com `test_func = lambda: eh_admin(self.request.user)` (ou mixin dedicado). Detalhe de pessoa/entidade (`PessoaDetailView`/`EntidadeDetailView`): manter acessível **apenas** quando a pessoa é parte de uma demanda visível ao usuário (Admin sempre; CG/Assessor só se houver demanda visível ligada) — senão 403. No `app.html`, envolver os links "Pessoas"/"Entidades" em `{% if papel_eh_admin %}`.
- [ ] **Step 4: Verificar** — `pytest -q` verde.
- [ ] **Step 5: Commit** — `feat(pessoas): lista/detalhe de pessoas e entidades por need-to-know (ADR 0059)`

**Acceptance:** só Admin navega o acervo; links somem para CG/Assessor; detalhe só no contexto de demanda visível.

### Task 8: Busca cega para vincular partes

**Files:**
- Modify: os endpoints de autocomplete em `pessoas/views.py` (ex.: `pessoa_buscar_json`, `entidade_buscar_json`), `static/js/autocomplete.js`, `templates/_drawer_criar_parte.html` (ou onde o autocomplete vincula partes), `pessoas/tests.py`

**Interfaces:**
- Produces: resposta "cega" para não-Admin (confirma existência + permite vincular por id/slug; sem ficha/contato).

- [ ] **Step 1: Teste (TDD)** — Assessor consultando o autocomplete com um termo que casa: a resposta **não** inclui contato/endereço; inclui o mínimo para vincular (id/slug + nome). Admin recebe o resultado completo de hoje.

```python
def test_busca_cega_nao_vaza_contato_para_assessor(client, usuario_comum, pessoa_com_telefone):
    client.force_login(usuario_comum)
    data = client.get(reverse("pessoas:pessoa_buscar_json"), {"q": "Maria"}).json()
    blob = json.dumps(data)
    assert "Maria" in blob
    assert pessoa_com_telefone.telefones.first().numero not in blob  # sem contato
```

- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar** — nos endpoints `*_buscar_json`: se `eh_admin(user)`, retorna o payload atual; senão, retorna **somente** `{id/slug, rótulo mínimo: nome}` — sem telefone/email/endereço — e a quantidade ("N registros compatíveis"). O `autocomplete.js`/drawer, para não-Admin, mostra "já existe — vincular?" sem expor ficha. A criação de pessoa nova segue permitida (cadastro mínimo).
- [ ] **Step 4: Verificar** — `pytest -q` verde; conferir manualmente o fluxo de nova demanda (vincular existente / criar nova) como Assessor.
- [ ] **Step 5: Commit** — `feat(pessoas): busca cega de partes para não-Admin (ADR 0059)`

**Acceptance:** Assessor vincula/cria sem ver a base; nenhum dado de contato vaza no autocomplete para não-Admin.

---

## FASE 5 — Gating de front + verificação final

### Task 9: Esconder export/análise/auditoria/config no front + encaminhamentos por papel

**Files:**
- Modify: `templates/layouts/app.html` (topbar: "Análise" e "Auditoria" já gated por `papel_*` — ajustar para `papel_eh_admin`; "Configurações" idem), todos os templates de lista com botão **Exportar CSV** (`demandas/lista.html`, `pessoas/lista.html`, `encaminhamentos/lista.html`) — botão dentro de `{% if pode_exportar %}` (já existe; `pode_exportar` agora é só Admin via Task 3), `core/templates/core/configuracoes.html` (cards só Admin)

- [ ] **Step 1** — Topbar: `/analise` e `/auditoria` em `{% if papel_eh_admin %}` (antes `papel_cg_plus`/admin). Configurações idem.
- [ ] **Step 2** — Confirmar que todo botão "Exportar CSV" está sob `{% if pode_exportar %}` e que `pode_exportar` vem como `eh_admin` (Task 3). A lista de encaminhamentos já usa `visiveis_para` indiretamente (Task 5) — confirmar que filtra por papel.
- [ ] **Step 3: Verificar** — abrir como Assessor/CG/Admin (smoke): os links/botões certos aparecem/somem. `pytest -q` verde.
- [ ] **Step 4: Commit** — `feat(ui): topbar e botões de export/admin por papel (ADR 0059)`

**Acceptance:** CG/Assessor não veem links/botões de export/análise/auditoria/config; demandas/encaminhamentos/pendências filtram por papel.

### Task 10: Docs, seed e verificação completa

**Files:** `CLAUDE.md` (§5), `roadmap.md` (glossário/§ permissões se citar coordenação), `pessoas/management/commands/criar_dados_teste.py` (criar 1 Admin + 1 CG + 1 Assessor + demandas de cada para exercitar a visibilidade)

- [ ] **Step 1** — `criar_dados_teste`: garantir usuários nos 3 grupos + demandas atribuídas para demonstrar a cascata (Assessor vê só as dele; CG as ativas; Admin tudo).
- [ ] **Step 2** — Atualizar CLAUDE.md §5 (modelo need-to-know, 3 papéis, coordenação/restrito removidos) e o glossário do roadmap (sem coordenação/restrito).
- [ ] **Step 3: Bateria** — `uv run pytest -q` (verde) · `ruff check .` · `black --check .` · `manage.py check` · `makemigrations --check` (sincronizado).
- [ ] **Step 4: Smoke 3 papéis** — logar como Admin, CG e Assessor (do seed) e percorrer demandas/pessoas/export/análise; entregar a Pedro uma checklist enxuta.
- [ ] **Step 5: Commit** — `docs: fecha modelo need-to-know (ADR 0059) — CLAUDE.md, roadmap, seed`

**Acceptance:** suíte/lint/migrations verdes; docs refletem o modelo; seed exercita os 3 papéis; checklist entregue.

---

## Self-Review (cobertura vs. ADR 0059 + permissoes.md v2)

- **Inversão need-to-know:** Task 5 (predicado) + Task 7/8 (acervo/busca cega) + Task 9 (front). ✔
- **3 papéis (remove Coordenador):** Task 4. ✔
- **Remove Coordenação (campo):** Task 2. ✔
- **Remove `restrito`:** Task 1. ✔
- **Export/auditoria/análise/config só Admin:** Task 3 + Task 9. ✔
- **Assessor = responsável/autor; ativas completas + histórico próprio mascarado:** Task 5 + Task 6. ✔
- **CG = todas as ativas, sem histórico/listas/auditoria/análise/export:** Task 3, 5, 7, 9. ✔
- **Busca cega:** Task 8. ✔
- **Continuidade (backup/recuperação):** fora deste plano — é Fase 7 (deploy); anotado na ADR. ✔ (registrado, não implementado aqui)
- **Ordem/dependências:** Fase 1 (remoções) antes da Fase 3 (visibilidade limpa); Task 3 antes da Task 4 (zera uso de `eh_co_plus`); Task 5 antes de 6/7/9 (visibilidade é base).
- **Anti-placeholder:** as remoções referenciam o padrão `papel` (commit real `849af41`); o núcleo tem código/teste completos. Nomes de status (`STATUS_ATIVOS`) e helpers (`eh_admin`/`eh_cg_plus`) consistentes entre tarefas.
