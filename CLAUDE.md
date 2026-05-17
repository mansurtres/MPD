# CLAUDE.md — Bússola para sessões com Claude Code

> Este arquivo é carregado automaticamente em toda sessão neste repositório. Mantenha curto, factual, fonte-de-verdade. Evolua a cada fase.

---

## 1. O que é o MPD

**Mandato Parlamentar Digital** — sistema de rastreabilidade de relacionamento político (categoria *constituent management*) para um mandato municipal. **Pessoa** é o núcleo; **demandas** orbitam a pessoa. Cada `Demanda` tem **dois eixos independentes**:

- `status` — ciclo de trabalho (`novo → em_andamento → respondido → arquivado`).
- `resultado` — desfecho material (`atendido | atendido_parcialmente | nao_atendido | inviavel | nao_se_aplica`).

**Regra de ouro do domínio:** demanda só vai para `respondida` com **retorno documentado** (data + conteúdo) **e** `resultado` classificado. Codificada no `clean()` do model — vale em qualquer porta de entrada.

**Multiplicidades:** demanda pode ter múltiplas pessoas e entidades como partes (M:N). Anexos são polimórficos — podem ser pendurados em Demanda, Pessoa, Entidade ou Encaminhamento.

---

## 2. Regra de ouro do projeto: documentação é fonte de verdade

Os documentos em [`docs/`](./docs/) e [`roadmap.md`](./roadmap.md) **são a fonte de verdade** do que o produto é. **Código nunca vai além da documentação.** Quando surge uma necessidade nova:

1. Atualizar o doc relevante (ou abrir uma ADR em `docs/decisoes.md`).
2. Validar com Pedro.
3. Só então codar.

Ideia que parece "óbvia" e não está no doc → primeiro vira ADR ou backlog.

---

## 3. Onde estão os docs

| Arquivo | Conteúdo |
|---|---|
| [`roadmap.md`](./roadmap.md) | Plano fase-a-fase (v0.1 → v6.x) com critérios de aceite. **Documento mais consultado.** |
| [`docs/modelo-de-dados.md`](./docs/modelo-de-dados.md) | Schema completo: entidades, campos, regras de validação, signals. |
| [`docs/mapa-de-telas.md`](./docs/mapa-de-telas.md) | Rotas, perfis que acessam, fluxos de navegação. |
| [`docs/permissoes.md`](./docs/permissoes.md) | Matriz de permissões por perfil/ação. |
| [`docs/fluxos-de-estado.md`](./docs/fluxos-de-estado.md) | Transições válidas de status, resultado, etc. |
| [`docs/decisoes.md`](./docs/decisoes.md) | ADRs cronológicas. Cada decisão arquitetural vira uma entrada aqui. |
| [`docs/debito-tecnico.md`](./docs/debito-tecnico.md) | Cheiros e refactors pendentes (`DT-NNN`). Por prioridade e gatilho de quando atacar. |
| [`docs/estrutura-do-repositorio.md`](./docs/estrutura-do-repositorio.md) | Organização de pastas, convenções, padrões de commit. |

---

## 4. Princípios operacionais

- **Produto sobre técnica.** Decisões técnicas servem o produto, não o contrário. Quando em dúvida, escolha a opção mais simples para o usuário final.
- **Fase a fase.** Não se adianta uma fase do roadmap para "ganhar tempo". Cada fase tem critério de aceite e é fechada com tag (`v0.1`, `v0.2`...).
- **Simplicidade vence.** Boring stack, padrões Django nativos, menos abstrações. `tests.py` único por app até apertar; `models/` virou pasta só quando passar de ~800 linhas.
- **Pedro é leigo em técnica.** Decisões técnicas são *do Claude*. Pedro decide produto. Quando uma escolha técnica afetar a experiência do usuário ou o roadmap, explicar trade-offs antes.
- **Idiomas:** código em **inglês**, domínio (modelos, campos, UI) em **português**. Ver `docs/estrutura-do-repositorio.md` §13.1.

---

## 5. Estado atual

**Fase corrente:** v0.4.2 — **Fase 3 (Demandas e Interações) concluída.** ADR 0042 separa Tema de Tag; ADR 0043 redesenha o fechamento da demanda (devolutiva como Interação + status `concluida` + bifurcação por origem).

**Fundação (Fase 0/1, mantido):**
- Django 5.2 + PostgreSQL 16 + Tailwind v4 standalone.
- Settings split (`config/settings/{base,development,production,test}.py`).
- 4 apps: `core`, `accounts`, `pessoas`, `demandas`.
- `accounts.Usuario` (email como login), login/logout, sessão 12h / "lembrar-me" 30 dias, gestão de usuários, perfil.
- Política de senha: mínimo 8 chars, sem complexidade obrigatória (ADR 0023).

**Fase 2 (pessoas):**
- Models `Pessoa`, `Telefone`, `EmailPessoa`, `RedeSocial`, `Entidade`, `Vinculo`, `Tag`. Pessoa com endereço inline, validação de CPF, soft delete, anonimização. Contatos como entidades plurais (telefones, e-mails, redes sociais) — UI agrupa em seção "Contatos" com 3 sub-blocos dinâmicos. Validação por tipo: celular 11 dígitos com 9 após DDD, fixo 10 dígitos; rede social "Outro" exige rótulo. Pelo menos 1 canal de qualquer tipo é obrigatório. Ver ADR 0035 e ADR 0037.
- Entidade com 14 tipos (formais a `familia`/`grupo_informal`); CNPJ opcional UNIQUE NULLS DISTINCT.
- CRUDs com `PermissionRequiredMixin`, listas paginadas (25/pg), busca, filtros.
- ViaCEP em `pessoas/viacep.py` (tolerante a falha); deduplicação em `pessoas/deduplicacao.py`.
- Django Admin com fieldsets.
- 4 grupos padrão ("Administrador", "Chefe de Gabinete", "Coordenador", "Assessor") via data migration com permissões customizadas (`pode_desativar_*`, `pode_reativar_*`, `pode_anonimizar_pessoa`).
- ADR 0025: `BigAutoField` (supersede ADR 0002).

**Refactor de débito técnico (concluído na v0.3.2):**
- `core/utils.py` — formatação e validação de CPF/CNPJ/CEP/dígitos consolidadas. Resolve [DT-003](docs/debito-tecnico.md).
- `core/mixins.py` — `EnderecavelMixin` (7 campos de endereço) e `AuditavelMixin` (timestamps). Pessoa e Entidade herdam. Resolve [DT-002](docs/debito-tecnico.md).
- `pessoas/signals.py` — normalização via `pre_save` cobre todas as portas (ORM, Admin, Forms). Resolve [DT-001](docs/debito-tecnico.md).
- `Pessoa.anonimizar()` agora atômica (`@transaction.atomic`). Resolve [DT-004](docs/debito-tecnico.md).
- Migration `0001_initial` regenerada do zero (sem produção, ADR 0026).
- `slug_publico` (CharField hex de 12 chars, único, gerado por uuid4 no `pre_save`) implementado em Pessoa e Entidade — completa o trabalho de URLs com slug que estava parcial em views/urls/templates/tests.

**Hardening v0.3.1 (ADRs 0026–0033):**
- `DeduplicacaoCheckView` exige `view_pessoa` (fechou vazamento de PII) — ADR 0028.
- `auditlog` registra `Pessoa`, `Entidade`, `Vinculo`, `Tag`, `Telefone`, `EmailPessoa`, `RedeSocial` (LGPD) — ADR 0029, estendido em ADR 0037 para cobrir os canais plurais.
- `criar_usuarios_iniciais` exige `DEBUG=True` (anti-backdoor em prod) — ADR 0030.
- Toggle views padronizadas com `PermissionRequiredMixin` + `PermissionDenied` — ADR 0031.
- Rate limiting de login via `django-axes` (5 falhas / 30min, lockout por IP+username) — ADR 0032.
- `SECURE_PROXY_SSL_HEADER` env-driven, default off — ADR 0033.
- Identidade do mandato genérica em `.env.example` e docs (licenciabilidade) — ADR 0027.
- Tabela de credenciais permanece no `.env` local por escolha do proprietário — ADR 0026.
- Link `/admin/` removido da home pública.

**Polimento v0.3.2 (ADRs 0034–0039):**
- 4 flags LGPD (`nao_telefonar` etc.) removidas — YAGNI até newsletter (ADR 0034 supersede ADR 0012).
- `Telefone` como entidade própria 1:N com tipo (celular/fixo) e `eh_whatsapp` — ADR 0035.
- Geocodificação registrada como compromisso para v2.x junto com multi-endereço — ADR 0036.
- `EmailPessoa` e `RedeSocial` como entidades plurais sob seção "Contatos" — ADR 0037.
- `Tag.categoria` removida — agrupamento via tag plana é mais fluido (ADR 0039).
- Auditlog Correlation ID via middleware (`core/auditlog.py`) — cascata de delete aparece como conjunto único de LogEntries.
- UI: paleta de 11 cores fixas para Tag, fluxo de arquivar (não deletar), WhatsApp como ícone wa.me em listas, home autenticada com cards.
- fix: `PessoaForm` DateInput com `format="%Y-%m-%d"` — sem isso edição apagava `data_nascimento` silenciosamente.
- Comando `criar_dados_teste` para popular dev (idempotente, exige `DEBUG=True`).

**Limpeza pós-auditoria v0.3.3 (ADR 0040, DT-011/012):**
- `DeduplicacaoCheckView` JSON troca `id` por `slug_publico` — coerência com ADR 0038.
- `CEPLookupView` agora exige `view_pessoa` — fecha endpoint que estava só com login.
- `accounts.Usuario` registrado em auditlog (excluindo `password` e `last_login`) — fecha gap LGPD da gestão da equipe.
- `UsuarioUpdateForm` bloqueia auto-edição de `is_staff` (ADR 0040, mitigação tática).
- DT-011 registra refactor arquitetural pendente para gestão de usuários (Groups + permissão custom em `accounts`).
- DT-012 registra `create_user(password=None)` cria conta inutilizável silenciosamente.

**Fechamento de débito técnico v0.3.4 (DT-005, 006, 007, 008, 010, 012):**
- Unicidade de canais por pessoa: `UniqueConstraint` em Telefone(pessoa, numero), EmailPessoa(pessoa, endereco), RedeSocial(pessoa, plataforma, valor). Decisão de produto: rede social pode repetir handle em plataformas diferentes.
- Tailwind nos forms via `aplicar_tailwind()` em `pessoas/forms.py` — JS de injeção de classes removido dos 3 templates de form. Padrão herdável por Demanda.
- `pode_alternar_ativo` calculado nas DetailViews (Pessoa/Entidade) — templates simplificados.
- `_PessoaFormMixin.post()` em `transaction.atomic`: salva tudo, chama `pessoa.tem_meio_de_contato()`, rollback se falhar. Regra mora só no model.
- `create_user(password=None)` agora levanta `ValueError` em vez de criar conta sem login utilizável.
- DT-009 (toggle duplicado, YAGNI) e DT-011 (gestão usuários arquitetural, antes de produção) ficam adiados.

**100 testes passando** ao final da v0.3.4. ADRs 0001–0040 em [`docs/decisoes.md`](./docs/decisoes.md).

**Verificação de prontidão v0.3.5–v0.3.6:**
- `pytest`: 100/100 verde.
- `ruff` + `black`: limpo.
- `manage.py check`: sem issues.
- `manage.py makemigrations --check`: sincronizado (após gerar `accounts/0003_alter_usuario_managers` — registro do `UsuarioManager` no migration state, sem schema change).
- `criar_dados_teste`: idempotente, OK.
- Smoke test manual: criar pessoa, rollback de canal vazio (DT-008), unicidade de telefone (DT-010), Tailwind nos forms (DT-006), permissões de Assessor (DT-007). 5/5 ok.
- 2 fixes UX descobertos na verificação manual: botão "Cancelar" no form de Pessoa/Entidade volta para o detalhe quando editando (em vez de ir para a lista); template do form passa a renderizar `non_form_errors` dos formsets (erros tipo "duplicado" agora aparecem no topo).

**Polimento pré-Fase 3 (revisão de repo, v0.3.6):**
- `aplicar_tailwind` movido de `pessoas/forms.py` para `core/forms.py` — demandas/forms.py herda o mesmo helper.
- Dead code removido: `class="input"` em widgets de `accounts/forms.py` (templates do app renderizam HTML manual e ignoram widgets) e fallback `or self.kwargs.get("pk")` em `_PessoaFormMixin.post` (URLs sempre passam slug).
- `validate_cnpj_tamanho` ganha comentário explicando por que não valida DV (assimetria deliberada com CPF).
- `core/tests.py` deixa de ser placeholder: cobre `healthz`, `inicio` (anônimo vs autenticado) e `aplicar_tailwind` (idempotência).

**Fase 3 — Demandas e Interações (v0.4.0):**
- App `demandas` com `Demanda`, `DemandaPessoa`, `DemandaEntidade`, `Interacao`, `Encaminhamento`, `Anexo` (polimórfico via GenericForeignKey), `ItemInbox` (modelo só; UX em Fase 4).
- Demanda com 2 eixos independentes: `status` (novo→em_andamento→aguardando_*→respondido→arquivado) e `resultado` (pendente, atendido, parcial, não atendido, inviável, não se aplica). Regra de fechamento codificada em `clean()`: `respondido` exige retorno + resultado classificado. Resultado classificado não volta a pendente.
- Geração de número thread-safe `MPD-AAAA-NNNNN` via `select_for_update`.
- Mudanças de status/responsável/resultado disparam **Interacao automática** via `post_save`. Snapshot de estado original em `__init__`. Middleware `UsuarioAtualMiddleware` repassa `request.user` para os signals.
- Schedule follow-up: ao salvar Interacao realizada, opcionalmente cria nova agendada com `interacao_origem` apontando para a anterior. Cadeia reconstruível.
- Janela de edição de 24h codificada em `Interacao.pode_editar`. Automáticas são imutáveis para todos. ADM/CG editam alheia.
- Encaminhamento com tipos de documento + status; resposta exige data + conteúdo. Reflete na timeline como interação manual.
- Anexo polimórfico com whitelist de mime + 25 MB. Limpeza de órfãos via `pre_delete` em Demanda/Pessoa/Entidade/Encaminhamento (GenericForeignKey não cascateia).
- Coordenação como atributo de `Usuario` (ADR 0041) — pré-requisito para regras de visibilidade restrita por coordenação.
- Permissões customizadas: `pode_arquivar_demanda`, `pode_arquivar_sem_responder`, `pode_marcar_restrita`, `pode_atribuir_responsavel`, `pode_reabrir_demanda`, `pode_excluir_demanda`, `pode_editar_interacao_alheia`, `pode_excluir_encaminhamento`. Distribuídas aos 4 grupos via `0002_grupos_padrao_demandas`.
- Auditlog: `Demanda`, `Encaminhamento`, `Anexo` registrados.
- Templates: lista com 8 quick filters (minhas, da minha coordenação, vencidas, sem retorno +30d, atendidas, não atendidas, sem resultado), detalhe com timeline cronológica + partes + encaminhamentos + anexos + bloco de Resultado inline + modais de "Marcar respondida" e "Arquivar". Formulário com formsets de partes (pessoas + entidades) e validação cross-objeto via `transaction.atomic` (padrão herdado de Pessoa).
- `criar_dados_teste` estendido com 2 demandas exemplo (responsiva + proativa).

**142 testes passando** ao final da v0.4.0 (37 novos no app `demandas` cobrindo os 22 critérios de aceite). ADRs 0001–0041.

**Redesign do fechamento da demanda (v0.4.2, ADR 0043):**
- Vocabulário polissêmico ("respondida" colidia com Encaminhamento e com retorno externo) eliminado: status `respondido` → **`concluida`**. Devolutiva ao demandante deixou de ser campo da Demanda e virou **Interação** (`tipo='devolutiva'`).
- Regra de fechamento bifurcada por origem em `Demanda.clean()`:
  - Responsiva: exige `Interacao(tipo=devolutiva, status=realizada)` vinculada **e** `resultado != pendente`.
  - Proativa: exige apenas `resultado != pendente`.
- UX: link discreto "Marcar como respondida" virou **CTA sólido** no topo do detalhe ("Concluir demanda — devolutiva ao demandante" para responsivas; "Concluir ação" para proativas). Modal centralizado pé-da-página virou **drawer lateral** (não cobre conteúdo, fecha por backdrop/Esc).
- `ConcluirDemandaView` orquestra tudo em `transaction.atomic`: cria Interacao(devolutiva), atualiza resultado/observação, muda status para `concluida`, roda `full_clean()` — rollback se qualquer passo falhar.
- Tipo `devolutiva` é exclusivo do fluxo de conclusão; não aparece no seletor genérico de "Adicionar interação" (evita devolutivas órfãs).
- Migration `0005_devolutiva_como_interacao` com data migration: para cada `Demanda.status='respondido'` com `retorno_data` preenchido, cria Interacao a partir dos campos `retorno_*` (com canal como prefixo do conteúdo), depois `UPDATE status='respondido' → 'concluida'`, depois drop dos campos.
- Quick filter `sem_retorno_30d` na lista vira "Sem devolutiva +30d" — agora busca por demandas responsivas abertas há +30d sem `Interacao(tipo=devolutiva)`.
- Permissões: labels atualizadas ("Pode arquivar demanda concluída", "Pode reabrir demanda concluída").

**148 testes passando** ao final da v0.4.2 (+6 sobre v0.4.0: novos casos cobrem responsiva sem devolutiva, responsiva com devolutiva + resultado pendente, responsiva concluída ok, proativa sem devolutiva ok, proativa sem resultado bloqueada). ADRs 0001–0043.

**Próximo marco:** v0.5 — **Fase 4 (Visões Transversais)** — lista de Encaminhamentos como leitura agregada + quick filters operacionais nas listas existentes. Demanda continua como núcleo do sistema; partículas não viram entidades autônomas (ADR 0046). Fase 5 (Inbox GTD) foi renumerada para v0.6.

---

## 6. Comandos úteis

```bash
# Setup inicial
uv sync --extra dev

# Servidor
uv run python manage.py runserver

# Migrações
uv run python manage.py makemigrations
uv run python manage.py migrate

# Superusuário
uv run python manage.py createsuperuser

# Testes
uv run pytest

# Lint + format
uv run ruff check . --fix
uv run black .

# Tailwind watch (recompila CSS automaticamente)
./bin/tailwindcss -i ./static/css/tailwind-input.css -o ./static/css/tailwind-output.css --watch
```

---

## 7. Convenções

- **Branches:** `main` (estável, com tags `v0.x`), `dev` (ativo), `feature/<nome-curto>`.
- **Commits:** Conventional Commits — `feat(casos):`, `fix(inbox):`, `docs(decisoes):`, `refactor`, `test`, `chore`. Escopo = nome do app afetado.
- **`tests.py` único por app** até passar de ~1500 linhas; aí vira pasta `tests/`.
- **Migrations:** geradas via `makemigrations -n <descricao>`. Nunca editadas manualmente após aplicadas (exceto data migrations).
- **Templates:** sempre estendem um layout (`base.html`, `layouts/auth.html`, `layouts/public.html`). Componentes via `{% include %}`.

---

## 8. O que NÃO está pronto (escopo entregue na Fase 0)

A Fase 0 deliberadamente **não** entrega:

- Modelos de domínio (`Pessoa`, `Demanda`, `DemandaPessoa`, `DemandaEntidade`, `Interacao`, `Encaminhamento`, `Anexo`, `ItemInbox`, `SolicitacaoLGPD`, `Tag`, `Entidade`, `Vinculo`) — `models.py` dos apps `cidadaos` e `casos` estão vazios (serão renomeados para `pessoas` e `demandas` antes da Fase 2).
- Login/logout customizado — **entregue na Fase 1**. Grupos Django (ADM/CG/CO/AS) e permissões por perfil — Fase 2 em diante, criados junto com os models que protegem.
- `core/permissions.py`, `core/middleware.py`, `core/templatetags/` — sem código de produto que os use ainda.
- `django-auditlog` instalado mas **sem registrar nenhum modelo** ainda — registros entram por modelo, fase a fase.
- HTMX/Alpine local — via CDN no MVP (Fase 6 considera baixar para `static/vendor/`).
- `Dockerfile`, CI/CD, deploy — Fase 6.

---

## 9. Pendência registrada para a próxima sessão (Fase 1)

**Decisão tomada (2026-05-08):** sistema de permissões modular via Django Groups + Permissions nativos. Ver ADRs 0022 e 0024.

- Grupos padrão criados na **Fase 2** (junto com `Pessoa`/`Entidade`) e expandidos na **Fase 3** (junto com `Demanda`). Fase 1 usa apenas `is_staff` para distinguir quem gerencia usuários.
- Toda verificação de permissão usa `user.has_perm()` — nunca checar nome de grupo diretamente no código.
- ADM pode criar/editar grupos sem deploy. A matriz documentada é configuração padrão, não regra de código.

**Apps renomeados (2026-05-08):** `cidadaos/` → `pessoas/`, `casos/` → `demandas/`. Django check e smoke tests passando.

---

## 10. Decisões técnicas registradas (resumo)

Para o histórico completo ver [`docs/decisoes.md`](./docs/decisoes.md). Decisões da Fase 0 que talvez mereçam ADR:

- **Tailwind standalone v4** (binário em `bin/`) em vez de `django-tailwind`. Razão: zero dependência de Node.js. Trade-off: cada dev baixa o binário (script no README).
- **`accounts.Usuario(AbstractUser)` desde a Fase 0**, mesmo sem campos extras. Razão: `AUTH_USER_MODEL` precisa ser definido antes da primeira `migrate`; trocar depois exige drop+recreate do banco.
- **SQLite in-memory para `pytest`** ([`config/settings/test.py`](./config/settings/test.py)). Razão: testes da Fase 0 não dependem de features Postgres-only; evita acoplar `pytest` ao banco rodando. Quando a suíte usar JSONB, full-text, etc., migrar para Postgres em testes.
- **`uv sync --extra dev`** (não `[dependency-groups]`). Razão: fidelidade ao esboço em `docs/estrutura-do-repositorio.md` §12.

---

*Atualizar este arquivo ao fim de cada fase. Última atualização: 2026-05-16 (v0.4.2 — redesign do fechamento da demanda, ADR 0043).*
