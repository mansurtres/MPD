# Fechamento do Front-end + Fase 7 (template-touching) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Levar todas as telas restantes do MPD para a nova identidade visual e fechar os itens da Fase 7 que tocam template (drop do campo `papel`, permissões de usuários, modal de confirmação do `resultado`, responsividade e acessibilidade), deixando o branch `feature/teste-claude-design` pronto para merge no `main`.

**Architecture:** Replicação de um sistema de design já estabelecido e aprovado. As telas-âncora já existem como código concreto no repositório (`templates/demandas/lista.html` = padrão *ledger*; `templates/demandas/detalhe.html` = padrão detalhe; `templates/pessoas/form.html` = padrão form) e os protótipos de referência ficam em `prototipo/project/v1/`. Cada tarefa visual **porta** uma referência para o template Django alvo, preservando 100% do contrato funcional (URLs, context vars, checagens de permissão) e trocando o markup Tailwind cru pelos componentes próprios (`.page-head`, `.ledger`, `.btn`, `.badge`, `.empty-state`). As tarefas funcionais (B/C1) seguem TDD clássico com a suíte `pytest`.

**Tech Stack:** Django 5.2, PostgreSQL 16 (SQLite in-memory nos testes), Tailwind v4 standalone (bridge em `static/css/components.css`), tokens em `static/css/tokens.css`, pytest, ruff, black, `uv` para tudo.

## Global Constraints

- **Idioma:** código em inglês, domínio/UI em português (CLAUDE.md §4).
- **Comentários Django em template:** `{# ... #}` **só em uma linha**. Multi-linha vaza como texto cru. Para comentário multi-linha usar `{% comment %}…{% endcomment %}` ou simplesmente não comentar. (Erro recorrente — 5x neste branch.)
- **Plataforma prioritária Windows:** atalhos sempre `Ctrl` (nunca `⌘`); fallback de fonte mono inclui Consolas.
- **Nunca pushar sem confirmação explícita.** Commit local é livre.
- **Commits incrementais** (Conventional Commits, escopo = app afetado): `feat(pessoas):`, `refactor(demandas):`, etc. Um commit por tarefa concluída.
- **Documentação é fonte de verdade** (CLAUDE.md §2): todo item funcional aqui já está no `roadmap.md` §4.6.2 / `docs/decisoes.md` (ADR 0054). Marcar DTs como resolvidos no fim.
- **Suíte verde é gate de cada tarefa:** `uv run pytest -q` deve passar (linha de base atual: **230 testes**). Nenhuma tarefa fecha com teste vermelho.
- **Sem cantos arredondados** (tokens: `--radius-sm/md = 0`); sem cor sólida sem glifo/forma em badges (acessibilidade).

---

## Convenções deste plano

**Convenção de porte (tarefas visuais A* e C2/C3):** o "código completo" da nova tela vive em duas fontes já no repo — (1) o **protótipo de referência** indicado na tarefa e (2) a **tela-âncora canônica** do mesmo tipo. O implementador lê as duas, lê o template atual (para extrair o contrato funcional), e escreve o template novo. Não há código HTML inline neste plano para essas tarefas **por desenho** — duplicá-lo seria menos confiável que apontar para a fonte-verdade versionada.

**Contrato funcional a preservar em todo porte:** todos os `{% url %}`, nomes de context vars, `{% if perms.* %}`, `{% if pode_* %}`, formsets, `csrf_token`, paginação (`page_obj`/`is_paginated`/`paginator`), filtros (`request.GET`), e o `{% include "_form_erros_resumo.html" %}` nos forms. Antes de reescrever, listar esses símbolos do template atual; depois de reescrever, conferir que nenhum sumiu.

**Verificação visual padrão (sem teste unitário de CSS):** cada tarefa visual termina com (a) `uv run pytest -q` verde, (b) a página renderiza sem erro de template (checar via `manage.py check` + abrir a rota no runserver ou subagente de smoke), (c) checklist de aceite da tarefa batido, (d) zero `{# %}` multi-linha.

**Estrutura visual canônica de cada tipo:**
- *Lista:* `.page-head` (breadcrumb + h1 + `.count` + `.head-actions` com Exportar/Novo) → `.quick-filters` (chips sticky, filete navy 6px) → `.active-filters` (chips removíveis, se houver filtro ativo) → `.filtros-adv` (colapsável) → `.ledger` (tabela) com `.ledger-foot` (paginação) **ou** `.empty-state`.
- *Detalhe:* `.page-head` com breadcrumb → grid de conteúdo + aside (metadados/ações). Espelhar `templates/demandas/detalhe.html`.
- *Form:* seções numeradas (§01, §02…) com `.btn`, `{% include "_form_erros_resumo.html" with form=form formsets=... %}` no topo, botões Cancelar (volta ao detalhe quando editando) + Salvar. Espelhar `templates/pessoas/form.html`.
- *Confirmar remoção:* card centrado `.msg.warning` + nome do objeto + botões `.btn.danger` (confirmar) e `.btn.secondary` (cancelar).

---

## Frente A — Redesign visual das telas restantes

### Task A1: Lista de Pessoas

**Files:**
- Modify: `templates/pessoas/lista.html`
- Reference: `prototipo/project/v1/pessoas.html` (design) + `templates/demandas/lista.html` (padrão ledger canônico)

**Interfaces:**
- Consumes: contrato funcional atual de `pessoas/lista.html` — context vars de busca (`q`, `bairro`, `tag`, `inativos`), quick filter "Com demanda em aberto", colunas Nome/Email/Telefone/Bairro/Tags/Status, paginação, `{% url 'pessoas:pessoa_detalhe' p.slug_publico %}`, `{% url 'pessoas:pessoa_nova' %}`, `perms.pessoas.add_pessoa`, export CSV se houver (`pode_exportar`).
- Produces: nada que outras tarefas consomem (tela folha).

- [ ] **Step 1: Extrair o contrato funcional** — ler `templates/pessoas/lista.html` atual e anotar todos os `{% url %}`, context vars, perms e filtros. Ler `prototipo/project/v1/pessoas.html` (design) e `templates/demandas/lista.html` (padrão ledger).
- [ ] **Step 2: Reescrever** o template com `.lista-page` → `.page-head` (breadcrumb Início / Pessoas, h1 "Pessoas" + `.count`) → `.quick-filters` (Todas / Com demanda em aberto / inativos) → `.filtros-adv` colapsável (busca, bairro, tag) → `.ledger` (Nome com avatar, Contato, Bairro, Tags como chips coloridos, Status badge) → `.ledger-foot` ou `.empty-state`. Linha clicável para o detalhe (padrão `onclick` + `event.stopPropagation()` nos links internos).
- [ ] **Step 3: Verificar render** — `uv run python manage.py check` sem erros; abrir `/pessoas/` no runserver (ou subagente de smoke) e confirmar lista, filtros e paginação.
- [ ] **Step 4: Rodar a suíte** — `uv run pytest demandas/tests.py pessoas/tests.py -q` (ou suíte completa) verde.
- [ ] **Step 5: Commit** — `git add templates/pessoas/lista.html && git commit -m "feat(pessoas): lista refeita na nova identidade visual (ledger)"`

**Acceptance:** sem classes `slate-*`/`rounded-*` cruas; usa `.page-head`/`.ledger`/`.empty-state`; todos os filtros e a paginação preservados; chips de tag usam as cores do token (`--tag-*`); responsivo (tabela colapsa/scroll em <768px).

---

### Task A2: Lista de Entidades

**Files:**
- Modify: `templates/pessoas/entidades/lista.html`
- Reference: `prototipo/project/v1/entidades.html` + `templates/demandas/lista.html`

- [ ] **Step 1: Extrair contrato** — `q`, `tipo`, `inativos`, quick filter "Com demanda em aberto", colunas Nome/Tipo/CNPJ/Cidade/Status; `{% url 'pessoas:entidade_detalhe' e.slug_publico %}`, `{% url 'pessoas:entidade_nova' %}`, `perms.pessoas.add_entidade`.
- [ ] **Step 2: Reescrever** seguindo o mesmo gabarito da A1 (ledger), com filtro de `tipo` (14 tipos) no `.filtros-adv` e badge de tipo na coluna.
- [ ] **Step 3: Verificar render** — `/entidades/` no runserver.
- [ ] **Step 4: Rodar a suíte** — `uv run pytest -q` verde.
- [ ] **Step 5: Commit** — `git commit -m "feat(pessoas): lista de entidades refeita (ledger)"`

**Acceptance:** idêntico padrão A1; filtro de tipo e quick filter "com demanda em aberto" funcionando.

---

### Task A3: Lista de Encaminhamentos

**Files:**
- Modify: `templates/demandas/encaminhamentos/lista.html`
- Reference: `prototipo/project/v1/encaminhamentos.html` + `templates/demandas/lista.html`

**Interfaces:**
- Consumes: é **lente de leitura** (ADR 0046 / memória "demanda é o núcleo") — cada linha é deep-link para a Demanda associada, **sem CRUD próprio**. Quick filters: Aguardando resposta / Prazo vencido / Respondidos esta semana. Filtros: `q`, `status`, `orgao` (datalist), `tipo`. Colunas Demanda/Encaminhamento/Enviado/Prazo/Status.

- [ ] **Step 1: Extrair contrato** — listar urls (`demandas:demanda_detalhe`), context vars, quick filters e o `<datalist>` de órgão.
- [ ] **Step 2: Reescrever** no padrão ledger; coluna "Prazo" com classes `.col-when.late`/`.warn` (vencido em vermelho); linha → detalhe da demanda. **Não** introduzir botão de criar/editar encaminhamento.
- [ ] **Step 3: Verificar render** — `/encaminhamentos/`.
- [ ] **Step 4: Rodar a suíte** — `uv run pytest -q` verde.
- [ ] **Step 5: Commit** — `git commit -m "feat(demandas): lista de encaminhamentos refeita (ledger, lente de leitura)"`

**Acceptance:** sem CRUD próprio; prazo vencido destacado; deep-link para demanda preservado.

---

### Task A4: Detalhe de Pessoa

**Files:**
- Modify: `templates/pessoas/detalhe.html`
- Reference: `prototipo/project/v1/pessoa.html` + `templates/demandas/detalhe.html` (padrão detalhe)

**Interfaces:**
- Consumes: seções Identificação, Contatos (telefones/emails/redes/sites plurais — ADR 0057), Endereço, Demandas vinculadas, Vínculos (form inline de adicionar vínculo), Tags; ações Editar / Alternar ativo (`pode_alternar_ativo`); aside com metadados (criado/atualizado, slug). Preservar o form inline de vínculo e os `{% url %}` de toggle/anonimizar.

- [ ] **Step 1: Extrair contrato** — anotar TODAS as seções, o form inline de vínculo, perms (`pode_alternar_ativo`, anonimizar) e urls.
- [ ] **Step 2: Reescrever** espelhando `templates/demandas/detalhe.html`: `.page-head` com breadcrumb (Início / Pessoas / Nome) + ações; corpo em grid com seções tipográficas (serif nos rótulos de seção) + aside com metadados. Contatos plurais agrupados. Demandas vinculadas como mini-ledger ou cards.
- [ ] **Step 3: Verificar render** — abrir o detalhe de uma pessoa de teste; testar o form de vínculo inline.
- [ ] **Step 4: Rodar a suíte** — `uv run pytest -q` verde.
- [ ] **Step 5: Commit** — `git commit -m "feat(pessoas): detalhe de pessoa refeito na nova identidade"`

**Acceptance:** todas as seções presentes; form inline de vínculo funciona; canais plurais (ADR 0057) exibidos; aside de metadados; responsivo (grid colapsa em 1 coluna <768px).

---

### Task A5: Detalhe de Entidade

**Files:**
- Modify: `templates/pessoas/entidades/detalhe.html`
- Reference: `prototipo/project/v1/entidade.html` + `templates/demandas/detalhe.html` + a Task A4 recém-feita

- [ ] **Step 1: Extrair contrato** — seções Identificação, Contatos plurais, Endereço, Pessoas vinculadas, Demandas, Tags; ações Editar/Alternar ativo.
- [ ] **Step 2: Reescrever** espelhando A4 (mesmo gabarito de detalhe), trocando "Vínculos" por "Pessoas vinculadas".
- [ ] **Step 3: Verificar render** — detalhe de uma entidade de teste.
- [ ] **Step 4: Rodar a suíte** — `uv run pytest -q` verde.
- [ ] **Step 5: Commit** — `git commit -m "feat(pessoas): detalhe de entidade refeito na nova identidade"`

**Acceptance:** simetria com A4; pessoas vinculadas e demandas exibidas.

---

### Task A6: CRUD de Tags (lista + form + confirmar remoção)

**Files:**
- Modify: `templates/pessoas/tags/lista.html`, `templates/pessoas/tags/form.html`, `templates/pessoas/tags/confirmar_remocao.html`
- Reference: `templates/demandas/lista.html` (lista), `templates/pessoas/form.html` (form), paleta de cores de tag em `tokens.css` (`--tag-*`); o popup "+ Nova tag" já existente em `pessoas/form.html` (color picker) é a referência do seletor de cor.

- [ ] **Step 1: Lista** — `.page-head` (Configurações / Tags) + `.head-actions` (Nova tag) + `.ledger` (Nome com swatch de cor, # de pessoas/entidades usando, ações Editar/Remover) ou `.empty-state`.
- [ ] **Step 2: Form** — seção única: nome + paleta de 11+3 cores (swatches clicáveis, mesma do popup inline) + preview do chip; `{% include "_form_erros_resumo.html" %}`; botões Cancelar/Salvar.
- [ ] **Step 3: Confirmar remoção** — card centrado `.msg.warning`, nome da tag, contagem de uso, `.btn.danger` Remover / `.btn.secondary` Cancelar.
- [ ] **Step 4: Verificar render** — criar, editar e abrir a confirmação de remoção de uma tag.
- [ ] **Step 5: Rodar a suíte** — `uv run pytest -q` verde.
- [ ] **Step 6: Commit** — `git commit -m "feat(pessoas): CRUD de tags na nova identidade"`

**Acceptance:** color picker consistente com o popup inline; preview do chip; confirmação clara.

---

### Task A7: CRUD de Temas (lista + form + confirmar remoção)

**Files:**
- Modify: `templates/demandas/temas/lista.html`, `templates/demandas/temas/form.html`, `templates/demandas/temas/confirmar_remocao.html`
- Reference: a Task A6 recém-feita (temas é gêmeo de tags — color picker) + popup "+ Novo tema" em `templates/demandas/form.html`

- [ ] **Step 1: Portar A6** para temas (lista/form/remoção), trocando rótulos (Tema, Configurações / Temas) e urls (`demandas:tema_*`).
- [ ] **Step 2: Verificar render** — criar/editar/remover tema.
- [ ] **Step 3: Rodar a suíte** — `uv run pytest -q` verde.
- [ ] **Step 4: Commit** — `git commit -m "feat(demandas): CRUD de temas na nova identidade"`

**Acceptance:** paridade visual total com A6 (tags).

---

### Task A8: Gestão de Usuários (lista + form) + Perfil

**Files:**
- Modify: `templates/accounts/usuarios/lista.html`, `templates/accounts/usuarios/form.html`, `templates/accounts/perfil.html`
- Reference: `templates/demandas/lista.html` (lista), `templates/pessoas/form.html` (form)
- **Dependência:** coordenar com **Task B2** (permissões). Se B2 já rodou, o form de usuário **não** terá mais `is_staff`. Fazer A8 **depois** de B2, ou deixar o `is_staff` fora do redesign e B2 remove o campo do form Python (o template só renderiza os fields do form).

- [ ] **Step 1: Lista de usuários** — `.page-head` (Configurações / Usuários) + Novo usuário + `.ledger` (Nome+avatar, Email, Cargo, Coordenação, Papel/Status como badges, ações Editar/Ativar-Desativar).
- [ ] **Step 2: Form de usuário** — seções: Identificação (email, nome, cargo, coordenação) + Acesso (ativo; senha em create). `{% include "_form_erros_resumo.html" %}`.
- [ ] **Step 3: Perfil** — form de auto-edição (nome, cargo; email read-only) no mesmo gabarito, enxuto.
- [ ] **Step 4: Verificar render** — lista, criar/editar usuário, editar próprio perfil.
- [ ] **Step 5: Rodar a suíte** — `uv run pytest accounts/tests.py -q` verde.
- [ ] **Step 6: Commit** — `git commit -m "feat(accounts): gestão de usuários e perfil na nova identidade"`

**Acceptance:** badges de papel/status; toggle ativar/desativar preservado; perfil read-only no email.

---

### Task A9: Hub de Configurações + Auditoria + Reuniões + Capturar

**Files:**
- Modify: `core/templates/core/configuracoes.html`, `templates/core/auditoria.html`, `templates/demandas/pendencias/reunioes.html`, `templates/demandas/inbox/capturar.html`
- Reference: `prototipo/project/v1/config.html` (hub), `templates/demandas/pendencias/lista.html` (reuniões é irmã de pendências — JÁ refeita), `templates/core/analise.html` (auditoria — filtros + cards)

- [ ] **Step 1: Configurações (hub)** — `.page-head` (Configurações) + grid de cards na identidade nova (cada card = ícone/título/descrição), substituindo os `bg-white border rounded-xl` crus. Preservar os `{% if perms.* %}`/`{% if papel_* %}` de cada card (Tags, Temas, Usuários, Auditoria, Análise).
- [ ] **Step 2: Auditoria** — `.page-head` (Auditoria) + bloco de filtros (usuário, modelo, ação, período) no padrão `.filtros-adv` + lista de eventos com diff visual antes/depois. Tratar `actor == None`. Paginação.
- [ ] **Step 3: Reuniões** — espelhar `templates/demandas/pendencias/lista.html` (horizontes Vencidas/Hoje/Amanhã/Esta semana/Próximas), filtrando reuniões; preservar ações marcar-realizada/cancelar.
- [ ] **Step 4: Capturar (standalone)** — porte enxuto do modal de captura (`layouts/app.html`) para página standalone: `.page-head` + textarea grande + Capturar. Preservar POST e mensagens.
- [ ] **Step 5: Verificar render** — abrir `/configuracoes/`, `/auditoria/`, `/minhas-reunioes/`, `/inbox/capturar/`.
- [ ] **Step 6: Rodar a suíte** — `uv run pytest -q` verde.
- [ ] **Step 7: Commit** — `git commit -m "feat(core): configurações, auditoria, reuniões e captura na nova identidade"`

**Acceptance:** hub com cards consistentes; auditoria com diff e filtros; reuniões idênticas a pendências; captura standalone coerente com o modal.

---

## Frente B — Fase 7 funcional (mexe em template)

### Task B1: Drop do campo `papel` / `papel_outro` (ADR 0054 / DT-013)

**Files:**
- Create: `demandas/migrations/00NN_drop_papel.py` (RemoveField em 4 colunas)
- Modify: `demandas/models.py` (PAPEL_* constants, PAPEL_CHOICES, campos `papel`/`papel_outro` em DemandaPessoa e DemandaEntidade, `papel_display`, `clean()` de papel, `__str__`)
- Modify: `demandas/forms.py` (`DemandaPessoaForm`, `DemandaEntidadeForm`: remover `papel`/`papel_outro` dos fields, widgets e `clean()`)
- Modify: `templates/demandas/form.html` (remover `{{ sub.papel }}{{ sub.papel_outro }}` dos `.hidden-field`)
- Modify: `templates/demandas/detalhe.html` (remover exibição `papel_display` no aside de partes)
- Modify: `static/js/autocomplete.js` (remover o IIFE final `bindPapelToggle`/`MPDPapelToggle`, ~linhas 629–fim)
- Modify: `demandas/tests.py` (remover `papel=...` de fixtures/calls; remover testes de papel)
- Modify: `roadmap.md` §7 (glossário "Parte"), `docs/debito-tecnico.md` (DT-013 resolvido)
- Nota: `processar.html` foi deletado neste branch — passo 4.2 do roteiro do roadmap é obsoleto. `criar_dados_teste.py` **não** referencia papel (verificado) — pular passo 7 do roteiro.

**Interfaces:**
- Produces: `DemandaPessoa`/`DemandaEntidade` sem `papel`; `__str__` retorna só o nome.

- [ ] **Step 1: Ajustar testes que usam papel (red→green via remoção)** — remover de `demandas/tests.py` os testes `test_demanda_pessoa_papel_outro_exige_descricao`, `test_demanda_pessoa_papel_outro_com_descricao_funciona`, `test_demanda_pessoa_papel_choice_padrao_usa_display` (e quaisquer que referenciem `papel`/`papel_display`); limpar `papel="..."` de todas as fixtures/calls restantes.
- [ ] **Step 2: Remover do model** — em `demandas/models.py`, apagar PAPEL_* constants, PAPEL_CHOICES, os 2 pares `papel`/`papel_outro`, `papel_display`, o `clean()` que valida `papel_outro`, e ajustar `__str__` para só o nome.
- [ ] **Step 3: Remover do form** — em `demandas/forms.py`, tirar `papel`/`papel_outro` de `DemandaPessoaForm`/`DemandaEntidadeForm` (fields, widgets, `clean()`).
- [ ] **Step 4: Gerar migration** — `uv run python manage.py makemigrations demandas -n drop_papel` → confirmar que é `RemoveField` nas 4 colunas.
- [ ] **Step 5: Limpar templates e JS** — remover os campos hidden de papel em `templates/demandas/form.html`; remover exibição de papel no aside de `templates/demandas/detalhe.html`; remover o IIFE de papel em `static/js/autocomplete.js`.
- [ ] **Step 6: Migrar e testar** — `uv run python manage.py migrate` + `uv run pytest -q` verde + `uv run python manage.py makemigrations --check` sincronizado.
- [ ] **Step 7: Docs** — atualizar `roadmap.md` §7 (glossário "Parte" sem papéis fechados) e marcar DT-013 resolvido em `docs/debito-tecnico.md`.
- [ ] **Step 8: Commit** — `git commit -m "refactor(demandas): drop do campo papel das partes (ADR 0054, DT-013)"`

**Acceptance:** `grep -rn "papel" demandas/models.py demandas/forms.py templates/demandas/ static/js/autocomplete.js` não retorna referências ativas (só strings históricas em migrations antigas); suíte verde; `makemigrations --check` limpo.

---

### Task B2: Permissões de gestão de usuários (DT-011)

**Files:**
- Modify: `accounts/views.py` (remover `StaffRequiredMixin`; usar `PermissionRequiredMixin` com `accounts.gerenciar_usuarios` nas 4 views)
- Modify: `accounts/forms.py` (remover `is_staff` dos fields de create/update; remover `clean_is_staff`)
- Create/Modify: data migration que cria a permissão custom `gerenciar_usuarios` e a atribui ao grupo "Administrador"
- Modify: `accounts/models.py` (Meta.permissions com `("gerenciar_usuarios", "Pode gerenciar usuários da equipe")`)
- Modify: `accounts/tests.py` (atualizar testes de gating: trocar checagem de `is_staff` por permissão; remover/ajustar testes de `clean_is_staff`)

**Interfaces:**
- Produces: permissão `accounts.gerenciar_usuarios`; views de usuário protegidas por ela.

- [ ] **Step 1: Teste do novo gating (TDD)** — em `accounts/tests.py`, escrever/ajustar teste: usuário **com** `accounts.gerenciar_usuarios` acessa `/configuracoes/usuarios/` (200); usuário sem ela recebe 403; usuário staff **sem** a permissão **não** acessa por ser staff (gating agora é por permissão).

```python
def test_gestao_usuarios_exige_permissao(client, django_user_model):
    from django.contrib.auth.models import Permission
    user = django_user_model.objects.create_user(email="a@b.com", password="x12345678")
    client.force_login(user)
    assert client.get("/configuracoes/usuarios/").status_code == 403
    perm = Permission.objects.get(codename="gerenciar_usuarios")
    user.user_permissions.add(perm)
    assert client.get("/configuracoes/usuarios/").status_code == 200
```

- [ ] **Step 2: Rodar e ver falhar** — `uv run pytest accounts/tests.py::test_gestao_usuarios_exige_permissao -q` → FAIL (permissão não existe / view ainda usa is_staff).
- [ ] **Step 3: Declarar a permissão no model** — adicionar a `accounts.Usuario.Meta.permissions`.
- [ ] **Step 4: Migration** — `makemigrations accounts` (cria a permissão) + data migration que faz `Group.objects.get(name="Administrador").permissions.add(perm)`.
- [ ] **Step 5: Trocar o gating** — em `accounts/views.py`, remover `StaffRequiredMixin`; as 4 views passam a `PermissionRequiredMixin` com `permission_required = "accounts.gerenciar_usuarios"`.
- [ ] **Step 6: Limpar o form** — remover `is_staff` dos fields em `accounts/forms.py` e remover `clean_is_staff`. Ajustar testes que dependiam disso (ADR 0040 vira obsoleta — promoção a staff só via Admin Django).
- [ ] **Step 7: Migrar e testar** — `uv run python manage.py migrate` + `uv run pytest -q` verde.
- [ ] **Step 8: Docs** — marcar DT-011 resolvido em `docs/debito-tecnico.md`; nota em `docs/permissoes.md`.
- [ ] **Step 9: Commit** — `git commit -m "feat(accounts): gating de usuários por permissão custom (DT-011)"`

**Acceptance:** `grep -rn "is_staff" accounts/views.py accounts/forms.py` não acha checagem de gating nem campo editável (só o model/admin); promoção a staff só pelo Admin Django; suíte verde.

---

## Frente C — Qualidade de front

### Task C1: Modal de confirmação ao classificar `resultado` (EstadoForm)

**Files:**
- Modify: `templates/demandas/detalhe.html` (onde o `EstadoForm`/bloco de Resultado é renderizado)
- Reference: o drawer/modal já existente no detalhe (Concluir/Arquivar) como padrão de markup+JS

**Interfaces:**
- Consumes: `EstadoForm` (campo `resultado`, `demandas/forms.py:346`) cuja classificação é **one-way** (`clean()` bloqueia volta a `pendente`).

- [ ] **Step 1: Identificar** o ponto exato no `detalhe.html` onde `resultado` é submetido (select + submit do EstadoForm inline).
- [ ] **Step 2: Adicionar confirmação** — ao tentar salvar uma classificação de `resultado` que sai de `pendente`, interceptar o submit (JS) e abrir um modal/drawer de confirmação explicando que a ação é irreversível ("Esta classificação não pode voltar a Pendente"). Confirmar prossegue; cancelar aborta. Reusar o padrão de drawer já no arquivo. Sem dependência de framework.
- [ ] **Step 3: Verificar** — classificar resultado de uma demanda de teste: o modal aparece; cancelar não salva; confirmar salva.
- [ ] **Step 4: Rodar a suíte** — `uv run pytest -q` verde (comportamento server inalterado; é UX client-side).
- [ ] **Step 5: Commit** — `git commit -m "feat(demandas): confirmação explícita ao classificar resultado (one-way)"`

**Acceptance:** classificar resultado pede confirmação; texto deixa claro que é irreversível; cancelar aborta sem POST.

---

### Task C2: Passada de responsividade (320–768px)

**Files:**
- Modify: as telas refeitas em A1–A9 (revisão), `static/css/components.css` (media queries faltantes), `templates/demandas/lista.html` e demais ledgers (scroll/colapso de tabela em mobile)

- [ ] **Step 1: Auditar** cada rota refeita em viewport 320/375/768px (DevTools ou subagente de smoke). Anotar quebras: tabelas estourando, grids não colapsando, page-head apertado, drawers/modais.
- [ ] **Step 2: Corrigir** — tabelas ledger viram scroll horizontal ou cards empilhados em <768px; grids de detalhe/hub colapsam para 1 coluna; `.filtros-adv` empilha (já tem media query — estender aos novos). Centralizar regras em `components.css` quando reutilizáveis.
- [ ] **Step 3: Verificar** — revisão visual final em 3 larguras; nenhum overflow horizontal indevido.
- [ ] **Step 4: Rodar a suíte** — `uv run pytest -q` verde.
- [ ] **Step 5: Commit** — `git commit -m "feat(ui): responsividade mobile das telas refeitas (320-768px)"`

**Acceptance:** sem overflow horizontal; todas as telas usáveis a 320px; menus/ações alcançáveis no toque.

---

### Task C3: Passada de acessibilidade

**Files:**
- Modify: telas refeitas (A1–A9) + `static/css/components.css` (foco visível) conforme necessário

- [ ] **Step 1: Auditar** — navegação só por teclado (Tab/Shift+Tab/Enter/Esc) nas rotas principais; foco visível (`--focus-ring`); `aria-label` em ícones-botão e links sem texto; contraste WCAG AA (badges/links); `alt`/`aria` em avatares decorativos (`aria-hidden`).
- [ ] **Step 2: Corrigir** — adicionar `aria-label` faltantes; garantir `:focus-visible` com anel em todos os interativos; corrigir pares de cor abaixo de AA; ordem de tabulação lógica nos forms/drawers; `role`/`aria-expanded` em toggles.
- [ ] **Step 3: Verificar** — percorrer login → lista → detalhe → form só com teclado; rodar checagem de contraste nas badges de status/resultado.
- [ ] **Step 4: Rodar a suíte** — `uv run pytest -q` verde.
- [ ] **Step 5: Commit** — `git commit -m "feat(a11y): foco visível, navegação por teclado e aria-labels"`

**Acceptance:** operável 100% por teclado; foco sempre visível; ícones-botão rotulados; contraste AA nas badges.

---

## Frente D — Revisão final

### Task D1: Revisão de consistência + verificação completa

**Files:** todas as telas tocadas.

- [ ] **Step 1: Varredura de consistência** — conferir tela a tela: breadcrumb presente e correto; h1 em display serif; botões usando `.btn` (não Tailwind cru); badges padronizadas; empty states presentes; nenhum `{# %}` multi-linha; nenhum `slate-*`/`rounded-xl` cru remanescente nas telas refeitas (`grep -rn "slate-\|rounded-xl" templates/ core/templates/`).
- [ ] **Step 2: Suíte + lint + migrations** — `uv run pytest -q` (≥230 verde) ; `uv run ruff check .` ; `uv run black --check .` ; `uv run python manage.py check` ; `uv run python manage.py makemigrations --check`.
- [ ] **Step 3: Smoke manual guiado** — rodar `criar_dados_teste`, percorrer o fluxo completo (lista → detalhe → form → drawer → conclusão) em desktop e mobile; entregar a Pedro uma checklist enxuta de pontos para ele bater o olho.
- [ ] **Step 4: Atualizar CLAUDE.md §5** — registrar o fechamento (telas na nova identidade, DT-011/DT-013 resolvidos, qualidade de front) e a contagem final de testes.
- [ ] **Step 5: Commit** — `git commit -m "docs: fechamento do redesign de front-end + Fase 7 (template)"`

**Acceptance:** suíte/lint/migrations verdes; zero markup cru remanescente nas telas refeitas; CLAUDE.md atualizado; checklist entregue a Pedro.

---

## Self-Review (cobertura vs. desenho aprovado)

- **Frente A (visual, ~18 telas):** A1–A9 cobrem todas as telas OLD/BRIDGE mapeadas (listas pessoas/entidades/encaminhamentos; detalhes pessoa/entidade; tags×3; temas×3; usuários×2 + perfil; configuracoes; auditoria; reunioes; capturar). ✔
- **Frente B (funcional):** B1 (drop papel, DT-013/ADR 0054) e B2 (permissões, DT-011). ✔
- **Frente C (qualidade):** C1 (EstadoForm confirm), C2 (responsividade), C3 (a11y). ✔
- **Frente D:** D1 (revisão + verificação + docs). ✔
- **Ordem/dependências:** B2 antes de A8 (ou A8 ignora is_staff); A6 antes de A7 (gêmeos); A4 antes de A5 (gêmeos); C2/C3 depois de A; B1 toca detalhe de demanda já refeito (cuidado, não é tela do A). ✔
- **Roadmap §4.6.2 não coberto de propósito** (fora do escopo "template-touching" escolhido): docker, backup `-Fc`, docs (manual/deploy), Sentry/whitenoise, Lighthouse/CI — pertencem ao deploy, fase seguinte. Registrado como fora de escopo deste branch.
