# MPD — Estrutura do Repositório

Organização física dos arquivos do projeto. Foco em simplicidade: nenhuma estrutura prematura, apenas o que cada fase realmente exige.

> **Princípio:** crescemos a estrutura quando o código aperta, não antes. Django tem convenções fortes que carregam o projeto sozinho até bem alto.

---

## 1. Visão Geral

```
mpd/
├── .github/                    # Workflows CI (Fase 6)
├── docs/                       # Projeto executivo (esta documentação)
├── scripts/                    # Scripts utilitários (backup, deploy)
├── core/                       # App: utilitários transversais
├── accounts/                   # App: usuários, perfis, LGPD
├── cidadaos/                   # App: cidadãos, entidades, vínculos, tags
├── casos/                      # App: casos, interações, encaminhamentos, anexos, inbox
├── config/                     # Settings Django (split por ambiente)
├── templates/                  # Templates compartilhados
├── static/                     # Assets estáticos
├── media/                      # Uploads (não versionado)
├── tests/                      # Testes E2E e fixtures globais
├── manage.py                   # Entry-point Django
├── pyproject.toml              # Dependências e config (uv)
├── .env.example                # Template de configuração
├── .env                        # Configuração local (não versionado)
├── .gitignore
├── .pre-commit-config.yaml
├── docker-compose.yml          # Produção (Fase 6)
├── docker-compose.dev.yml      # Desenvolvimento (Fase 6)
├── Dockerfile                  # Imagem de produção (Fase 6)
└── README.md
```

**Quatro apps Django, sem wrapper `apps/`.** Cada app é diretamente filho da raiz. Padrão Django mais comum, mais simples para imports, menos um nível de complexidade.

---

## 2. Pasta `docs/`

Documentação viva do projeto. Versionada junto com o código.

```
docs/
├── modelo-de-dados.md          # Schema completo
├── mapa-de-telas.md            # Rotas e perfis
├── permissoes.md               # Matriz de permissões
├── fluxos-de-estado.md         # Transições de estado
├── decisoes.md                 # ADRs cronológicas
├── estrutura-do-repositorio.md # Este arquivo
├── manual.md                   # Manual de uso (Fase 6)
└── deploy.md                   # Guia de hospedagem (Fase 6)
```

`roadmap.md` fica na raiz por ser o documento mais consultado.

---

## 3. Pasta `config/`

Settings Django split por ambiente. Padrão usado por times maduros.

```
config/
├── __init__.py
├── settings/
│   ├── __init__.py
│   ├── base.py                 # Settings comuns
│   ├── development.py          # DEBUG=True, console email, SQLite opcional
│   ├── production.py           # DEBUG=False, Whitenoise, logs estruturados
│   └── test.py                 # Settings para pytest
├── urls.py                     # URL conf raiz
├── wsgi.py
└── asgi.py
```

**Default:** `DJANGO_SETTINGS_MODULE=config.settings.development` no `.env`.

---

## 4. App `core/`

Utilitários transversais. Não modela nada de domínio próprio.

```
core/
├── __init__.py
├── apps.py
├── views.py                    # Dashboard, healthz
├── urls.py
├── permissions.py              # Helpers: is_admin, is_cg_or_above, etc.
├── middleware.py               # CurrentUserMiddleware (para signals)
├── templatetags/
│   ├── __init__.py
│   └── core_tags.py            # tem_grupo, formato_data_br, etc.
├── management/
│   └── commands/
│       └── verificar_integridade.py
└── tests.py
```

**Quando criar mais arquivos aqui:** apenas se um arquivo único passar de ~500 linhas, dividir por responsabilidade clara (não por convenção).

---

## 5. App `accounts/`

Usuários, perfis, LGPD.

```
accounts/
├── __init__.py
├── apps.py
├── models.py                   # Usuario (custom user), SolicitacaoLGPD
├── views.py                    # Login, perfil, gerenciamento de usuários, LGPD
├── urls.py
├── forms.py                    # LoginForm, UsuarioForm, SolicitacaoLGPDForm
├── admin.py                    # Django Admin
├── migrations/
├── management/
│   └── commands/
│       └── criar_usuarios_iniciais.py
└── tests.py
```

**`forms.py` aparece quando há lógica de formulário** (validações customizadas, layout). No início, podem viver dentro de `views.py` se forem simples.

---

## 6. App `cidadaos/`

Cidadãos, entidades, vínculos, tags.

```
cidadaos/
├── __init__.py
├── apps.py
├── models.py                   # Cidadao, Entidade, Vinculo, Tag
├── views.py                    # CRUD de todas as entidades
├── urls.py
├── forms.py                    # Forms com integração ViaCEP
├── viacep.py                   # Cliente ViaCEP isolado
├── deduplicacao.py             # Lógica de detecção de duplicatas
├── admin.py
├── migrations/
└── tests.py
```

**Por que `viacep.py` separado:** módulo de integração externa merece isolamento desde o início para facilitar mock em testes.

**Por que `deduplicacao.py` separado:** lógica suficientemente complexa (similaridade de strings, regras por campo) para merecer arquivo próprio. Importável de forma testável.

---

## 7. App `casos/`

Coração do sistema. Casos, interações, encaminhamentos, anexos, inbox.

```
casos/
├── __init__.py
├── apps.py                     # Registra signals
├── models.py                   # Caso, Interacao, Encaminhamento, Anexo, ItemInbox
├── views.py                    # Todas as views: casos, interações, inbox, pendências
├── urls.py
├── forms.py                    # CasoForm, InteracaoForm (com follow-up), etc.
├── signals.py                  # Geração de interações automáticas
├── numero.py                   # Geração thread-safe de número de caso
├── admin.py
├── migrations/
├── management/
│   └── commands/
│       └── atualizar_prazos_vencidos.py
└── tests.py
```

**Por que `signals.py` separado:** signals são código não-óbvio. Centralizar em arquivo dedicado facilita auditoria e debugging.

**Por que `numero.py` separado:** geração thread-safe via `select_for_update` é lógica delicada. Isolamento facilita testes de concorrência.

**`tests.py` único** no início. Quando passar de ~1500 linhas, virar pasta `tests/` com `test_caso.py`, `test_interacao.py`, etc.

---

## 8. Pasta `templates/`

Templates compartilhados (não específicos de app).

```
templates/
├── base.html                   # Template raiz com topbar, sidebar, layout
├── layouts/
│   ├── public.html             # Layout para páginas públicas (login, LGPD)
│   └── auth.html               # Layout para páginas autenticadas
├── components/
│   ├── topbar.html
│   ├── sidebar.html
│   ├── modal_captura.html
│   ├── badge_pendencias.html
│   ├── timeline_interacoes.html
│   ├── form_field.html
│   └── empty_state.html
├── partials/                   # Fragments HTMX
│   └── (gerados conforme necessidade)
├── 403.html
├── 404.html
└── 500.html
```

**Templates específicos de app vivem em `<app>/templates/<app>/`.** Padrão Django.

---

## 9. Pasta `static/`

Assets estáticos.

```
static/
├── css/
│   ├── tailwind-input.css      # Input do Tailwind
│   └── tailwind-output.css     # Build (gerado, não versionado em dev)
├── js/
│   └── htmx-config.js          # Configuração mínima de HTMX
└── img/
    └── logo.svg
```

**HTMX e Alpine via CDN no MVP.** Quando quiser local-first total (Fase 6), baixar para `static/vendor/`.

---

## 10. Pasta `tests/`

Testes que cruzam apps (E2E) e fixtures globais.

```
tests/
├── __init__.py
├── conftest.py                 # Fixtures pytest globais
├── factories.py                # factory_boy para todos os modelos
├── test_fluxo_completo.py      # E2E: cidadão → caso → encaminhamento → resposta → arquivamento
└── test_permissoes_globais.py  # Permissões cross-app
```

**Testes unitários ficam em `<app>/tests.py`.** Testes que cruzam apps moram aqui.

---

## 11. Pasta `scripts/`

Scripts utilitários executados manualmente ou por cron.

```
scripts/
├── backup.sh                   # Dump PostgreSQL + tar de media/
├── restore.sh                  # Restauração de backup
└── setup-dev.sh                # Setup automatizado de ambiente dev
```

Não há `setup.py` aqui — é só shell. Comandos Python ficam em `<app>/management/commands/`.

---

## 12. Configuração de raiz

### `.env.example`

```bash
# === Aplicação ===
DJANGO_SETTINGS_MODULE=config.settings.development
DJANGO_SECRET_KEY=changeme-generate-with-secrets-token-urlsafe-50
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# === Banco de dados ===
DATABASE_URL=postgres://mpd:mpd@localhost:5432/mpd_dev

# === E-mail (Fase 1) ===
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=mandato@exemplo.com

# === Identidade do Mandato ===
NOME_DO_MANDATO=Mandato Exemplo
NOME_CURTO_DO_MANDATO=Mandato
SIGLA_MANDATO=MPD

# === Storage ===
MEDIA_ROOT=./media
STATIC_ROOT=./staticfiles

# === Integrações ===
VIACEP_TIMEOUT=3

# === Sentry (opcional, Fase 6) ===
# SENTRY_DSN=
```

### `pyproject.toml`

```toml
[project]
name = "mpd"
version = "0.1.0"
description = "Mandato Parlamentar Digital"
requires-python = ">=3.12"
dependencies = [
    "django>=5.0,<6.0",
    "psycopg[binary]>=3.1",
    "django-environ>=0.11",
    "django-auditlog>=3.0",
    "django-ratelimit>=4.1",
    "django-htmx>=1.17",
    "django-tailwind>=3.8",
    "whitenoise>=6.6",
    "pillow>=10.0",
    "requests>=2.31",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-django>=4.8",
    "pytest-cov>=5.0",
    "factory-boy>=3.3",
    "ruff>=0.5",
    "black>=24.0",
    "pre-commit>=3.7",
    "detect-secrets>=1.5",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "DJ"]
ignore = ["E501"]  # black cuida da linha

[tool.black]
line-length = 100
target-version = ["py312"]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.test"
python_files = ["tests.py", "test_*.py"]
addopts = "--reuse-db --no-cov-on-fail"
```

### `.gitignore`

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/

# Django
*.sqlite3
media/
staticfiles/

# Ambiente
.env
.env.local
.env.production

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Tests
.pytest_cache/
.coverage
htmlcov/

# Tailwind
static/css/tailwind-output.css
node_modules/

# Logs
*.log
```

### `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/psf/black
    rev: 24.4.0
    hooks:
      - id: black

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

---

## 13. Convenções de código

### 13.1. Idioma

- **Código** (nomes de variáveis, funções, classes, comentários técnicos): inglês.
- **Domínio** (nomes de modelos, campos do banco, mensagens de UI): português.

Exemplo:
```python
class Caso(models.Model):
    """Caso registrado no sistema."""
    titulo = models.CharField(max_length=200)  # Campo em PT
    status = models.CharField(...)              # Campo em PT

    def get_absolute_url(self):                # Método em EN
        return reverse('casos:detalhe', args=[self.pk])

    def can_be_closed(self):                   # Método em EN
        """Check if case has retorno preenchido."""
        return self.retorno_data and self.retorno_conteudo
```

Razão: código fica legível para qualquer dev (incluindo IA), e o produto fica natural para o usuário brasileiro.

### 13.2. Imports

Ordem (PEP 8 / isort):

1. Stdlib (`os`, `datetime`).
2. Third-party (`django`, `requests`).
3. Local (`from accounts.models import Usuario`).

`ruff` ordena automaticamente.

### 13.3. Docstrings

Modelos e funções públicas têm docstrings em português, curtas:

```python
class Cidadao(models.Model):
    """Pessoa física que se relaciona com o mandato."""
```

### 13.4. Migrations

- Geradas via `python manage.py makemigrations`.
- **Nunca editadas manualmente** após aplicadas, exceto data migrations.
- Nomes descritivos: `python manage.py makemigrations -n criar_grupos_iniciais`.

### 13.5. Templates

- Sempre estendem um layout (`{% extends "layouts/auth.html" %}`).
- Componentes via `{% include "components/badge_pendencias.html" %}`.
- HTMX por convenção: `hx-get`, `hx-post`, `hx-target`, `hx-swap`.

---

## 14. Branches e commits

### 14.1. Branches

- `main` — estável. Cada commit tem uma tag `v0.x` ou `v1.x`.
- `dev` — desenvolvimento ativo. PRs vão para cá.
- `feature/<nome-curto>` — features pontuais. Mergeadas em `dev` via PR.

### 14.2. Conventional Commits

```
feat(casos): permite agendar interação no futuro
fix(inbox): corrige perda de foco ao reabrir modal
docs(decisoes): adiciona ADR sobre proposições legislativas
refactor(cidadaos): extrai lógica de deduplicação para módulo próprio
test(accounts): cobre permissões de Coordenador
chore(deps): atualiza Django para 5.1.4
```

Tipos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`, `perf`.

Escopo opcional, mas recomendado: nome do app afetado.

### 14.3. Tags de versão

```bash
git tag -a v0.1 -m "Fase 0: Fundação"
git push origin v0.1
```

Cada tag tem release notes no GitHub.

---

## 15. Onde adicionar coisas novas

| Tipo de mudança | Onde fica |
|---|---|
| Nova tabela | `<app>/models.py` ou novo app se a entidade for raiz semântica |
| Nova rota | `<app>/urls.py` + `<app>/views.py` |
| Nova permissão helper | `core/permissions.py` |
| Nova validação cruzada | `<app>/models.py` (método `clean()`) ou `<app>/forms.py` |
| Nova integração externa | módulo isolado: `<app>/<integracao>.py` |
| Nova decisão arquitetural | `docs/decisoes.md` (nova ADR) |
| Novo signal | `<app>/signals.py` (criar se não existir) |
| Novo comando manual | `<app>/management/commands/<comando>.py` |
| Novo template compartilhado | `templates/components/` ou `templates/partials/` |
| Novo asset estático | `static/<tipo>/` |
| Nova fixture de teste | `tests/factories.py` |
| Novo teste E2E | `tests/test_<fluxo>.py` |

---

## 16. Quando dividir um app

Se um app passa dos seguintes limites, considerar divisão:

- `models.py` > 800 linhas → virar pasta `models/` com módulos por entidade.
- `views.py` > 1000 linhas → virar pasta `views/` por entidade.
- `tests.py` > 1500 linhas → virar pasta `tests/`.

**Não dividir antes do limite chegar.** Premature optimization is the root of all evil.

---

## 17. Quando criar novo app

Considerar quando:

- Funcionalidade é claramente independente (ex: agenda em v2.x).
- Modelo central novo, com fluxos próprios (ex: proposições em v2.x).
- Há ambição de virar plugin desinstalável (raro).

**Não criar antes da necessidade.** Move-se rápido com poucos apps; perde-se tempo organizando muitos.

---

*Documento atualizado quando organização muda. Versão atual: planejamento, pré-Fase 0.*
