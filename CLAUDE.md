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

**Fase corrente:** v0.3.2 — Fase 2 (Pessoas e Entidades) + hardening + polimento **concluídos**.

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
- 4 grupos padrão (ADM, CG, CO, AS) via data migration com permissões customizadas (`pode_desativar_*`, `pode_reativar_*`, `pode_anonimizar_pessoa`).
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
- `auditlog` registra `Pessoa`, `Entidade`, `Vinculo`, `Tag` (LGPD) — ADR 0029.
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

**90 testes passando** ao final da v0.3.2. ADRs 0001–0039 em [`docs/decisoes.md`](./docs/decisoes.md).

**Próximo marco:** v0.4 — Fase 3 (Demandas e Interações). Ver [`roadmap.md`](./roadmap.md) §4.3.

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

*Atualizar este arquivo ao fim de cada fase. Última atualização: 2026-05-09 (v0.3.2 — Fase 2 + hardening + polimento).*
