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

**Fase corrente:** v0.2 — Fase 1 (Autenticação e usuários) **concluída**.

**O que está pronto:**
- Django 5.2 + PostgreSQL 16 + Tailwind v4 standalone rodando localmente.
- Settings split (`config/settings/{base,development,production,test}.py`).
- 4 apps Django: `core`, `accounts`, `pessoas`, `demandas`.
- `accounts.Usuario` completo: email como login, `nome_completo`, `cargo`, `UsuarioManager` customizado.
- Login/logout com templates Tailwind; sessão 12h / "lembrar-me" 30 dias.
- Gestão de usuários (criar, editar, desativar) restrita a `is_staff=True`.
- Página de perfil pessoal.
- Comando `criar_usuarios_iniciais`.
- Política de senha: mínimo 8 chars, sem exigências de complexidade.
- 22 testes passando (accounts + smoke).
- Revisão arquitetural completa: nomenclatura, M:N partes de demanda, anexos polimórficos, entidades expandidas — registrada em docs e ADRs 0018–0024.

**Próximo marco:** v0.3 — Fase 2 (Pessoas e Entidades). Ver [`roadmap.md`](./roadmap.md) §4.2.

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

*Atualizar este arquivo ao fim de cada fase. Última atualização: 2026-05-08 (Fase 1 concluída).*
