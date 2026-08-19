# Deploy do MPD no Render — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Colocar o MPD no ar em produção no Render (`mpd.onrender.com`), com banco PostgreSQL gerenciado, anexos em disco persistente e os três níveis de permissão funcionando, sem alterar uma linha do código de domínio.

**Architecture:** Infraestrutura declarada como código num `render.yaml` (Blueprint) que cria três recursos de uma vez: Web Service Python, PostgreSQL e disco persistente. O build compila o CSS do Tailwind (que não é versionado) e coleta os estáticos; o pre-deploy roda as migrações; o gunicorn serve a aplicação. As mudanças em código se limitam a `config/settings/production.py`, `pyproject.toml` e arquivos novos de infraestrutura.

**Tech Stack:** Django 5.2, PostgreSQL 16, gunicorn, WhiteNoise, `uv` (gerenciador de dependências, suportado nativamente pelo Render via `uv.lock`), Tailwind v4 standalone, pytest.

**Spec:** [docs/superpowers/specs/2026-08-18-deploy-render-design.md](../specs/2026-08-18-deploy-render-design.md)

## Global Constraints

- **Documentação é fonte de verdade** (CLAUDE.md §2): toda divergência do `roadmap.md` vira ADR antes do código.
- **Nunca pushar sem confirmação explícita de Pedro.** Commit local é livre. ⚠️ Este plano é a exceção parcial: o Render faz deploy a partir do repositório remoto, então **haverá um push**, e ele precisa ser autorizado explicitamente na Task 7 — não antes.
- **Commits incrementais**, Conventional Commits, escopo = app ou área afetada (`chore(deploy):`, `feat(deploy):`, `docs(deploy):`).
- **Suíte verde é gate de cada tarefa:** `uv run pytest -q` deve passar. **Linha de base: 239 testes** (verificada em 2026-08-18).
- **Lint é gate:** `uv run ruff check .` e `uv run black --check .` limpos antes de cada commit.
- **Plataforma de Pedro é Windows.** Todo comando destinado a ele vai em PowerShell; scripts `.sh` rodam apenas no servidor Linux do Render (ou em Git Bash, quando indicado para verificação local).
- **Idioma:** código em inglês, domínio/UI/comentários de negócio em português.
- **Nenhuma credencial no repositório.** Senhas e chaves só existem no painel do Render ou digitadas interativamente.
- **Nomes fixos deste deploy** (usados verbatim em todos os arquivos): serviço web `mpd`, banco `mpd-db`, disco `mpd-media`, ponto de montagem `/var/data`, `MEDIA_ROOT=/var/data/media`, host `mpd.onrender.com`.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade | Ação |
|---|---|---|
| `.python-version` | Fixa Python 3.12 no Render, em paridade com o local | Criar |
| `build.sh` | Instala deps, compila o CSS do Tailwind, coleta estáticos | Criar |
| `render.yaml` | Declara Web Service + Postgres + disco + variáveis | Criar |
| `config/settings/production.py` | Endurece produção: disco, CSRF, logs, axes atrás de proxy | Modificar |
| `pyproject.toml` | Acrescenta `gunicorn` | Modificar |
| `core/tests.py` | Testes que travam as garantias de `production.py` | Modificar |
| `.env.example` | Documenta as variáveis de produção | Modificar |
| `docs/deploy.md` | Guia executável por Pedro, com diagnóstico por sintoma | Criar |
| `docs/decisoes.md` | ADR 0061 | Modificar |
| `roadmap.md`, `docs/debito-tecnico.md`, `CLAUDE.md` | Refletir o entregue e o adiado | Modificar |

---

### Task 1: Fixar o runtime e a dependência de produção

Sem `.python-version`, o Render usa Python 3.14.3 por padrão — versão em que a suíte nunca rodou. Sem `gunicorn`, não há servidor para produção (o `runserver` do Django é ferramenta de desenvolvimento e não atende tráfego real).

**Files:**
- Create: `.python-version`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: nada (primeira tarefa)
- Produces: comando `uv run gunicorn` disponível; o `startCommand` da Task 4 depende dele

- [ ] **Step 1: Criar `.python-version`**

Arquivo com uma única linha (o ambiente local é Python 3.12.10; o Render aceita omitir o patch):

```
3.12
```

- [ ] **Step 2: Acrescentar gunicorn ao `pyproject.toml`**

Em `[project].dependencies`, após `"django-htmx>=1.17",` e mantendo a ordem existente do bloco, acrescentar:

```toml
    "gunicorn>=22.0",
```

- [ ] **Step 3: Sincronizar o lockfile**

Run: `uv sync --extra dev`
Expected: `uv.lock` atualizado incluindo `gunicorn`; nenhum erro de resolução.

- [ ] **Step 4: Verificar que o gunicorn instalou**

Run: `uv run gunicorn --version`
Expected: imprime a versão (ex.: `gunicorn (version 23.0.0)`).

- [ ] **Step 5: Confirmar que nada quebrou**

Run: `uv run pytest -q`
Expected: `239 passed`.

- [ ] **Step 6: Commit**

```bash
git add .python-version pyproject.toml uv.lock
git commit -m "chore(deploy): fixa Python 3.12 e adiciona gunicorn

Render usaria 3.14.3 por padrao, versao em que a suite nunca rodou.
gunicorn substitui o runserver como servidor de producao."
```

---

### Task 2: Endurecer `config/settings/production.py`

Quatro garantias que precisam valer em produção e hoje não valem. Cada uma ganha um teste que falha antes da mudança — inclusive a que já funciona por acidente (`DEBUG=False`), porque ela é a que mais custa caro se regredir.

**Files:**
- Modify: `config/settings/production.py`
- Test: `core/tests.py` (acrescentar ao final)

**Interfaces:**
- Consumes: `env` de `config/settings/base.py`
- Produces: as variáveis de ambiente `MEDIA_ROOT`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_PROXY_COUNT` — consumidas pelo `render.yaml` da Task 4 e documentadas no `.env.example` da Task 5

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar ao **final** de `core/tests.py`:

```python
# ---------------------------------------------------------------------------
# Settings de produção (ADR 0061)
#
# Carregam config.settings.production com um ambiente simulado e travam as
# garantias que o deploy no Render depende. Nenhum destes testes toca no banco.
# ---------------------------------------------------------------------------

import os
import sys
from unittest import mock

from django.conf import Settings

ENV_PRODUCAO = {
    "DJANGO_SETTINGS_MODULE": "config.settings.production",
    "DJANGO_SECRET_KEY": "chave-apenas-para-teste-nao-usar-em-producao-0000",
    "DJANGO_ALLOWED_HOSTS": "mpd.onrender.com",
    "DATABASE_URL": "postgres://usuario:senha@localhost:5432/mpd",
    "DJANGO_TRUST_PROXY_SSL_HEADER": "True",
    "DJANGO_CSRF_TRUSTED_ORIGINS": "https://mpd.onrender.com",
    "MEDIA_ROOT": "/var/data/media",
    "DJANGO_PROXY_COUNT": "1",
}


def _settings_de_producao():
    """Reimporta config.settings.production sob o ambiente simulado.

    O pop em sys.modules é necessário: sem ele a segunda chamada devolveria o
    módulo em cache, com os valores calculados no primeiro import.
    """
    with mock.patch.dict(os.environ, ENV_PRODUCAO):
        sys.modules.pop("config.settings.production", None)
        return Settings("config.settings.production")


def test_producao_nunca_roda_com_debug_ligado():
    assert _settings_de_producao().DEBUG is False


def test_producao_guarda_anexos_no_disco_persistente():
    assert _settings_de_producao().MEDIA_ROOT == "/var/data/media"


def test_producao_confia_no_proxy_ssl_quando_a_variavel_esta_ligada():
    settings = _settings_de_producao()
    assert settings.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")


def test_producao_le_csrf_trusted_origins_do_ambiente():
    assert _settings_de_producao().CSRF_TRUSTED_ORIGINS == ["https://mpd.onrender.com"]


def test_producao_ensina_o_axes_a_ler_o_ip_real_atras_do_proxy():
    settings = _settings_de_producao()
    assert settings.AXES_IPWARE_PROXY_COUNT == 1
    assert settings.AXES_IPWARE_META_PRECEDENCE_ORDER[0] == "HTTP_X_FORWARDED_FOR"


def test_producao_manda_log_para_a_saida_padrao():
    logging = _settings_de_producao().LOGGING
    assert logging["handlers"]["console"]["class"] == "logging.StreamHandler"
    assert logging["root"]["handlers"] == ["console"]
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `uv run pytest core/tests.py -q -k producao`
Expected: FAIL. `test_producao_guarda_anexos_no_disco_persistente`, `test_producao_le_csrf_trusted_origins_do_ambiente`, `test_producao_ensina_o_axes_...` e `test_producao_manda_log_...` falham com `AttributeError` ou valor divergente. `test_producao_nunca_roda_com_debug_ligado` e o de proxy SSL já passam — são regressão, não construção.

- [ ] **Step 3: Reescrever `config/settings/production.py`**

Substituir o conteúdo inteiro do arquivo por:

```python
"""Settings de produção. Mapa das variáveis no Render: docs/deploy.md."""

import sys

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# Anexos vivem no disco persistente do Render. Fora do ponto de montagem o
# filesystem é efêmero: todo arquivo enviado some no deploy seguinte. Ref: ADR 0061.
MEDIA_ROOT = env("MEDIA_ROOT", default="/var/data/media")

# Origens confiáveis para POST sob HTTPS atrás do proxy. Sem isso, formulários
# rejeitam com "CSRF verification failed" em produção.
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Só confiar em X-Forwarded-Proto quando atrás de proxy estrito que sanitize
# essa header (nginx, Caddy, Cloudflare, Render). Caso contrário, clientes podem
# mandar a header e bypassar SSL_REDIRECT/Cookie_Secure. Ref: ADR 0033.
if env("DJANGO_TRUST_PROXY_SSL_HEADER"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# django-axes atrás de proxy: sem isto todo acesso chega com o IP do proxy e a
# auditoria de tentativa de login fica cega — o lockout continua funcionando
# (o par inclui username), mas o endereço registrado é inútil. Ref: ADR 0061.
AXES_IPWARE_PROXY_COUNT = env.int("DJANGO_PROXY_COUNT", default=1)
AXES_IPWARE_META_PRECEDENCE_ORDER = ("HTTP_X_FORWARDED_FOR", "REMOTE_ADDR")

# O Render captura a saída padrão como log do serviço. Sem isto, erro em
# produção não aparece em lugar nenhum.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simples": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "simples",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        # Segunda linha de defesa do registro de exportações (ADR 0053).
        "mpd.exports": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `uv run pytest core/tests.py -q -k producao`
Expected: `6 passed`.

- [ ] **Step 5: Rodar a suíte inteira**

Run: `uv run pytest -q`
Expected: `245 passed` (239 da linha de base + 6 novos).

- [ ] **Step 6: Lint**

Run: `uv run ruff check . --fix` e `uv run black .`
Expected: limpo.

- [ ] **Step 7: Commit**

```bash
git add config/settings/production.py core/tests.py
git commit -m "feat(deploy): endurece production.py para o Render

MEDIA_ROOT no disco persistente, CSRF_TRUSTED_ORIGINS por env var,
logging para stdout e axes lendo o IP real atras do proxy. 6 testes
travam cada garantia."
```

---

### Task 3: `build.sh` — o passo que impede o site de subir sem CSS

`templates/base.html` carrega `css/tailwind-output.css`, que está no `.gitignore` e não existe no repositório. Sem este script, o MPD sobe como HTML cru.

**Files:**
- Create: `build.sh`

**Interfaces:**
- Consumes: `uv.lock`, `static/css/tailwind-input.css`
- Produces: `static/css/tailwind-output.css` e a pasta `staticfiles/`; o `buildCommand` do `render.yaml` (Task 4) chama `./build.sh`

- [ ] **Step 1: Criar `build.sh`**

```bash
#!/usr/bin/env bash
# Build do MPD no Render — roda a cada deploy, antes das migrações e do start.
# Documentado em docs/deploy.md. Ref: ADR 0061.
set -o errexit   # aborta no primeiro erro: build falho e barulhento é melhor
set -o nounset   # que site publicado sem CSS ou sem dependências
set -o pipefail

TAILWIND_URL="https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64"

echo "==> [1/4] Garantindo o uv"
if ! command -v uv > /dev/null 2>&1; then
  pip install uv
fi

echo "==> [2/4] Instalando dependencias a partir do uv.lock"
uv sync --frozen --no-dev

echo "==> [3/4] Compilando o CSS do Tailwind"
curl --silent --show-error --location --fail --retry 3 --retry-delay 2 \
  --output ./tailwindcss "$TAILWIND_URL"
chmod +x ./tailwindcss
./tailwindcss -i ./static/css/tailwind-input.css -o ./static/css/tailwind-output.css --minify

if [ ! -s ./static/css/tailwind-output.css ]; then
  echo "ERRO: tailwind-output.css saiu vazio. O site subiria sem estilo." >&2
  exit 1
fi

echo "==> [4/4] Coletando arquivos estaticos"
uv run python manage.py collectstatic --no-input

echo "==> Build concluido"
```

- [ ] **Step 2: Tornar o script executável no índice do git**

O Render roda em Linux e precisa do bit de execução. No Windows isso se registra direto no git:

Run: `git update-index --add --chmod=+x build.sh`
Expected: sem saída. Confirmar com `git ls-files -s build.sh` — o modo deve ser `100755`, não `100644`.

- [ ] **Step 3: Rodar o script localmente para provar que funciona**

Em **Git Bash** (não PowerShell), com `DJANGO_SETTINGS_MODULE` de produção e as variáveis mínimas:

```bash
DJANGO_SETTINGS_MODULE=config.settings.production \
DJANGO_SECRET_KEY=teste-local-000000000000000000000000000000 \
DJANGO_ALLOWED_HOSTS=localhost \
DATABASE_URL=postgres://u:p@localhost:5432/mpd \
STATIC_ROOT=./staticfiles \
./build.sh
```

Expected: as quatro etapas imprimem, `static/css/tailwind-output.css` existe e não está vazio, `staticfiles/` é criada com os estáticos coletados e comprimidos.

- [ ] **Step 4: Confirmar que o CSS compilado tem conteúdo real**

Run: `wc -c static/css/tailwind-output.css`
Expected: dezenas de milhares de bytes, não zero. Um arquivo de poucos bytes indica que o `@source` do `tailwind-input.css` não encontrou os templates.

- [ ] **Step 5: Confirmar que os artefatos continuam ignorados pelo git**

Run: `git status --short`
Expected: `tailwind-output.css` e `staticfiles/` **não** aparecem (ambos estão no `.gitignore`). Apenas `build.sh` aparece como novo.

- [ ] **Step 6: Commit**

```bash
git add build.sh
git commit -m "feat(deploy): build.sh compila o CSS e coleta estaticos

tailwind-output.css nao e versionado: sem este passo o MPD sobe sem
estilo nenhum. Falha ruidosa se o download do binario nao completar."
```

---

### Task 4: `render.yaml` — o Blueprint

Um arquivo cria os três recursos. As duas variáveis destacadas abaixo são os deploy-breakers silenciosos identificados na investigação.

**Files:**
- Create: `render.yaml`

**Interfaces:**
- Consumes: `build.sh` (Task 3), `gunicorn` (Task 1), as variáveis lidas por `production.py` (Task 2)
- Produces: a infraestrutura que a Task 7 instancia no painel do Render

- [ ] **Step 1: Criar `render.yaml`**

```yaml
# Blueprint do MPD no Render. Guia de uso: docs/deploy.md. Ref: ADR 0061.
#
# Duas variaveis abaixo derrubam o deploy em silencio se saírem daqui:
#   DJANGO_SETTINGS_MODULE — manage.py usa "development" por padrao. Sem esta
#     variavel o collectstatic gera os estaticos no formato errado e TODA
#     pagina responde 500, alem de rodar migracoes com DEBUG ligado.
#   DJANGO_TRUST_PROXY_SSL_HEADER — sem ela o Django nao enxerga que a
#     requisicao chegou por HTTPS e o navegador entra em loop de redirecionamento.

services:
  - type: web
    name: mpd
    runtime: python
    plan: starter
    region: oregon
    branch: main
    buildCommand: "./build.sh"
    preDeployCommand: "uv run python manage.py migrate --no-input"
    startCommand: "uv run gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --timeout 60 --access-logfile - --error-logfile -"
    healthCheckPath: /healthz/
    disk:
      name: mpd-media
      mountPath: /var/data
      sizeGB: 1
    envVars:
      - key: DJANGO_SETTINGS_MODULE
        value: config.settings.production
      - key: DJANGO_SECRET_KEY
        generateValue: true
      - key: DJANGO_DEBUG
        value: "False"
      - key: DJANGO_ALLOWED_HOSTS
        value: mpd.onrender.com
      - key: DJANGO_CSRF_TRUSTED_ORIGINS
        value: https://mpd.onrender.com
      - key: DJANGO_TRUST_PROXY_SSL_HEADER
        value: "True"
      - key: DJANGO_PROXY_COUNT
        value: "1"
      - key: MEDIA_ROOT
        value: /var/data/media
      - key: STATIC_ROOT
        value: /opt/render/project/src/staticfiles
      - key: WEB_CONCURRENCY
        value: "2"
      - key: DATABASE_URL
        fromDatabase:
          name: mpd-db
          property: connectionString
      # Identidade do mandato: preenchidas por Pedro no painel na criacao,
      # nunca versionadas (licenciabilidade — ADR 0027).
      - key: NOME_DO_MANDATO
        sync: false
      - key: NOME_CURTO_DO_MANDATO
        sync: false
      - key: SIGLA_MANDATO
        sync: false
      - key: DEFAULT_FROM_EMAIL
        sync: false

databases:
  - name: mpd-db
    plan: basic-256mb
    databaseName: mpd
    user: mpd
    postgresMajorVersion: "16"
```

- [ ] **Step 2: Validar a sintaxe YAML**

Run: `uv run --with pyyaml python -c "import yaml; d=yaml.safe_load(open('render.yaml')); print(d['services'][0]['name'], d['databases'][0]['plan'])"`
Expected: imprime `mpd basic-256mb`. O `--with` traz o PyYAML de forma efêmera, sem sujar as dependências do projeto.

- [ ] **Step 3: Conferir que o health check bate com a rota real**

`core/urls.py` registra `path("healthz/", ...)` — **com barra no final**. Como o Django faz `APPEND_SLASH`, um health check em `/healthz` responderia 301 em vez de 200.

Run: `grep -n "healthCheckPath" render.yaml`
Expected: `healthCheckPath: /healthz/` — com a barra.

- [ ] **Step 4: Conferir a suíte e o lint**

Run: `uv run pytest -q && uv run ruff check .`
Expected: `245 passed`, ruff limpo.

- [ ] **Step 5: Commit**

```bash
git add render.yaml
git commit -m "feat(deploy): render.yaml declara web service, postgres e disco

Blueprint cria os tres recursos de uma vez. Destaque para as duas
variaveis que derrubam o deploy em silencio: DJANGO_SETTINGS_MODULE e
DJANGO_TRUST_PROXY_SSL_HEADER."
```

---

### Task 5: Documentação operacional — `.env.example` e `docs/deploy.md`

O guia é o entregável mais importante para Pedro: ele executa o deploy sozinho. Escrito para quem nunca fez deploy, com diagnóstico por sintoma — não só o caminho feliz.

**Files:**
- Modify: `.env.example`
- Create: `docs/deploy.md`

**Interfaces:**
- Consumes: os nomes de variáveis definidos nas Tasks 2 e 4
- Produces: o roteiro que a Task 7 executa

- [ ] **Step 1: Acrescentar o bloco de produção ao `.env.example`**

Substituir a seção `# === Produção ===` existente por:

```
# === Produção (Render — ver docs/deploy.md) ===
# Estas variáveis vivem no painel do Render, não neste arquivo. Listadas aqui
# como documentação do contrato de configuração.
#
# DJANGO_SETTINGS_MODULE=config.settings.production
#   OBRIGATÓRIA. manage.py usa "development" por padrão; sem esta variável o
#   collectstatic gera estáticos no formato errado e toda página responde 500.
#
# DJANGO_TRUST_PROXY_SSL_HEADER=True
#   OBRIGATÓRIA no Render. Ative APENAS atrás de proxy estrito que sanitize o
#   header X-Forwarded-Proto (nginx, Caddy, Cloudflare, Render). Ativar sem
#   proxy estrito permite que clientes bypassem o redirect SSL. Ref: ADR 0033.
#   Sem ela no Render: loop infinito de redirecionamento, o site não abre.
#
# DJANGO_CSRF_TRUSTED_ORIGINS=https://mpd.onrender.com
#   Origens confiáveis para POST sob HTTPS. Sem ela: "CSRF verification failed"
#   em todo formulário.
#
# DJANGO_PROXY_COUNT=1
#   Quantos proxies há na frente da aplicação. Faz o django-axes registrar o IP
#   real de quem tenta logar, em vez do IP do proxy. Ref: ADR 0061.
#
# MEDIA_ROOT=/var/data/media
#   Dentro do disco persistente. Fora dele, todo anexo some no próximo deploy.
```

- [ ] **Step 2: Escrever `docs/deploy.md`**

Documento em português, dirigido a Pedro, com esta estrutura e conteúdo:

**§1. O que você vai ter no fim** — três recursos no Render, custo de ~US$ 13,25/mês discriminado por item, endereço `mpd.onrender.com` com HTTPS automático.

**§2. Antes de começar** — conta no Render criada; repositório conectado ao GitHub (o Render lê o código de lá); a decisão de que o banco entra vazio.

**§3. Criar tudo de uma vez (Blueprint)** — passo a passo numerado: New → Blueprint → conectar o repositório → o Render lê `render.yaml` → preencher as quatro variáveis marcadas `sync: false` (`NOME_DO_MANDATO`, `NOME_CURTO_DO_MANDATO`, `SIGLA_MANDATO`, `DEFAULT_FROM_EMAIL`) → Apply. Avisar que a primeira criação leva alguns minutos e que **o primeiro deploy pode falhar no health check** enquanto o banco ainda está provisionando — nesse caso, um "Manual Deploy" resolve.

**§4. Se o nome `mpd` estiver ocupado** — o subdomínio é global no Render. Trocar o `name:` do serviço em `render.yaml` e, junto, `DJANGO_ALLOWED_HOSTS` e `DJANGO_CSRF_TRUSTED_ORIGINS` para o mesmo nome. Os três precisam concordar.

**§5. Criar seu usuário** — abrir o Shell do serviço no painel e rodar `uv run python manage.py createsuperuser`; e-mail e senha digitados na hora, nunca gravados em arquivo. Explicar que `criar_usuarios_iniciais` não funciona em produção de propósito (ADR 0030).

**§6. Cadastrar a equipe** — entrar em `/configuracoes/`, criar cada pessoa e atribuir Chefe de Gabinete ou Assessor; os três grupos já existem. Lembrete de que **não há "esqueci minha senha"**: quem esquecer, você redefine por aqui.

**§7. Backup** — explicar as duas camadas: recuperação automática dos últimos 3 dias (nada a fazer) e o export manual mensal (Dashboard → banco → Recovery → Create export → baixar e guardar fora do Render). Sugerir lembrete recorrente no calendário.

**§8. Quando algo der errado** — tabela de diagnóstico por sintoma, o coração do documento:

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| O navegador diz "redirecionou você muitas vezes" e o site não abre | `DJANGO_TRUST_PROXY_SSL_HEADER` não está `True` | Environment → conferir o valor → Save (redeploy automático) |
| Toda página dá erro 500, inclusive o login | `DJANGO_SETTINGS_MODULE` não é `config.settings.production` — o `collectstatic` rodou no modo errado | Corrigir a variável e disparar Manual Deploy |
| O site abre, mas sem nenhum estilo (texto cru) | O passo do Tailwind falhou no build | Ver o log do build: se o download do binário falhou, disparar Manual Deploy; o build aborta de propósito nesse caso |
| Formulário recusa com "CSRF verification failed" | `DJANGO_CSRF_TRUSTED_ORIGINS` ausente ou com endereço divergente | Precisa ser `https://` + exatamente o host do serviço |
| Anexo enviado ontem sumiu hoje | O disco não está montado ou `MEDIA_ROOT` está fora dele | Conferir se o disco `mpd-media` existe em `/var/data` e se `MEDIA_ROOT=/var/data/media` |
| "Bad Request (400)" ao abrir o site | O host não está em `DJANGO_ALLOWED_HOSTS` | Acrescentar o endereço exato do serviço |
| O deploy trava em "in progress" e o health check falha | O banco ainda está provisionando, ou a migração falhou | Ver a aba Logs; a saída do pre-deploy mostra o erro da migração |
| O site demora ~1 min para responder após cada atualização | Comportamento esperado: disco persistente impede troca sem interrupção | Nada a fazer — decisão registrada na ADR 0061 |

**§9. Trocar para domínio próprio no futuro** — registrar o domínio, apontar CNAME conforme o painel, acrescentar o host em `DJANGO_ALLOWED_HOSTS` e a origem em `DJANGO_CSRF_TRUSTED_ORIGINS`. Nenhuma mudança de código; HTTPS é emitido automaticamente.

**§10. Atualizar o sistema depois** — cada push no branch `main` dispara deploy automático. Como acompanhar em Logs e como usar "Rollback" para voltar à versão anterior.

- [ ] **Step 3: Conferir os links internos do documento**

Run: `grep -n "](" docs/deploy.md`
Expected: todo caminho relativo citado existe no repositório. Corrigir os que não existirem.

- [ ] **Step 4: Commit**

```bash
git add .env.example docs/deploy.md
git commit -m "docs(deploy): guia de deploy no Render e contrato de variaveis

Guia executavel por leigo, com tabela de diagnostico por sintoma para as
falhas silenciosas conhecidas (loop de redirect, 500 por settings module,
site sem CSS, anexo sumindo)."
```

---

### Task 6: Fechar a documentação-fonte-de-verdade

Pela regra do projeto (CLAUDE.md §2), divergência do roadmap vira ADR. São três divergências: Docker adiado, backup automatizado adiado, recuperação de senha adiada.

**Files:**
- Modify: `docs/decisoes.md`, `roadmap.md`, `docs/debito-tecnico.md`, `CLAUDE.md`

**Interfaces:**
- Consumes: as decisões registradas nas Tasks 1–5
- Produces: rastro documental; nada depende disto tecnicamente

- [ ] **Step 1: Escrever a ADR 0061 em `docs/decisoes.md`**

Acrescentar ao final, seguindo o formato das ADRs existentes no arquivo (ler a ADR 0059 antes para espelhar estrutura e tom). Conteúdo:

- **Título:** ADR 0061 — Deploy em produção no Render via Blueprint
- **Contexto:** MPD pronto para uso real; Pedro nunca fez deploy; roadmap §4.6.2 previa Docker e backup automatizado.
- **Decisão:** (a) Render com `render.yaml`, runtime Python nativo; (b) anexos em disco persistente de 1 GB em `/var/data`, não em object storage; (c) backup em duas camadas — PITR de 3 dias do Render + export manual mensal; (d) Docker adiado; (e) recuperação de senha por e-mail adiada.
- **Consequências:** ~1 min de indisponibilidade por deploy e instância única (efeito do disco); build depende do download do binário do Tailwind; janela de recuperação automática é de 3 dias; senha esquecida exige intervenção do Admin.
- **Alternativas descartadas:** Docker agora (uma camada a mais entre um operador leigo e o diagnóstico, sem benefício presente); object storage R2/S3 (conta e credenciais adicionais para o volume de um gabinete); versionar `tailwind-output.css` (passo manual esquecível, sintoma silencioso).
- **Errata sobre a ADR 0033:** o default desligado de `DJANGO_TRUST_PROXY_SSL_HEADER` permanece correto; no Render a variável é ligada porque a plataforma é proxy estrito.

- [ ] **Step 2: Atualizar `roadmap.md` §Fase 7**

Marcar como entregue: configuração de produção, Whitenoise, logging estruturado, `docs/deploy.md`. Marcar como **adiado com ADR 0061**: Docker (item 4) e backup robusto com `pg_dump -Fc`/rotação/criptografia (item 3). Registrar que Sentry segue opcional e não foi ativado.

- [ ] **Step 3: Registrar os débitos técnicos novos**

Acrescentar a `docs/debito-tecnico.md`, no formato `DT-NNN` já usado no arquivo (conferir o último número em uso e continuar a sequência):

- Backup automatizado off-site (`pg_dump -Fc`, rotação, criptografia). **Gatilho:** volume de dados ou criticidade tornarem a janela de 3 dias insuficiente, ou a equipe passar a depender de restauração seletiva.
- Recuperação de senha por e-mail. **Gatilho:** primeira vez que o custo de redefinir senha manualmente incomodar, ou a equipe passar de ~10 pessoas.
- `Dockerfile` para portabilidade. **Gatilho:** decisão de sair do Render, ou necessidade de rodar o mesmo artefato em outro ambiente.
- `scripts/backup.sh` é inoperante no Windows do único operador. **Gatilho:** junto com o backup automatizado acima.

- [ ] **Step 4: Atualizar `CLAUDE.md` §5**

Acrescentar a entrada da v1.0 descrevendo o deploy, e **corrigir a contagem de testes** — o arquivo registra 235; a linha de base verificada é 239, e sobe para 245 com a Task 2.

- [ ] **Step 5: Conferir a suíte**

Run: `uv run pytest -q`
Expected: `245 passed`.

- [ ] **Step 6: Commit**

```bash
git add docs/decisoes.md roadmap.md docs/debito-tecnico.md CLAUDE.md
git commit -m "docs(deploy): ADR 0061, roadmap Fase 7 e debitos do deploy

Registra Render via Blueprint e as tres divergencias assumidas do
roadmap: Docker, backup automatizado e recuperacao de senha adiados,
cada um com gatilho de revisita."
```

---

### Task 7: Executar o deploy com Pedro

Esta tarefa **não é automatizável** — depende de cliques no painel do Render e de credenciais que só Pedro digita. O agente conduz, Pedro executa.

**Files:** nenhum (execução operacional)

**Interfaces:**
- Consumes: tudo das Tasks 1–6, no branch `feature/deploy-render`
- Produces: o MPD no ar

- [ ] **Step 1: Verificação final antes de qualquer coisa ir para fora**

```bash
uv run pytest -q
uv run ruff check .
uv run black --check .
uv run python manage.py check --deploy
```

Expected: `245 passed`; ruff e black limpos. O `check --deploy` roda com settings de desenvolvimento e vai reclamar de `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE` e afins — **esperado e correto**, já que essas garantias vivem em `production.py`. Nenhum aviso deve mencionar `SECRET_KEY` fraca ou `DEBUG` em produção.

- [ ] **Step 2: Pedir autorização explícita de push**

⚠️ **Gate.** Este é o primeiro push desta linha de trabalho e o Render lê o código do GitHub. Perguntar a Pedro, em texto, se autoriza:
- fazer merge de `feature/deploy-render` em `main`;
- **pushar `main` para o `origin`** — lembrando que a `main` local está muitas dezenas de commits à frente do remoto, então este push publica todo o trabalho acumulado, não só o deploy.

Não prosseguir sem um "sim" explícito. Se ele preferir, oferecer pushar apenas o branch de feature e abrir PR.

- [ ] **Step 3: Merge e push (só após o "sim")**

```bash
git checkout main
git merge --no-ff feature/deploy-render
git push origin main
```

- [ ] **Step 4: Criar o Blueprint no Render (Pedro executa)**

Conduzir por `docs/deploy.md` §3: New → Blueprint → selecionar o repositório → conferir os três recursos detectados → preencher as quatro variáveis `sync: false` → Apply.

- [ ] **Step 5: Acompanhar o primeiro deploy**

Ler os logs junto com Pedro. Confirmar, em ordem: build imprime as quatro etapas do `build.sh`; pre-deploy aplica as migrações sem erro; o serviço fica `live`; o health check em `/healthz/` responde.

- [ ] **Step 6: Criar o primeiro usuário**

Pedro abre o Shell do serviço e roda `uv run python manage.py createsuperuser`. Senha digitada por ele, nunca compartilhada em conversa nem gravada em arquivo.

- [ ] **Step 7: Rodar o roteiro de aceite em produção**

Marcar cada item, na ordem:

- [ ] `https://mpd.onrender.com/healthz/` responde 200
- [ ] A home abre **com o visual correto** — se estiver sem estilo, o passo do Tailwind falhou
- [ ] Login do superusuário funciona
- [ ] Criar uma Pessoa de teste
- [ ] Criar uma Demanda de teste
- [ ] Enviar um anexo nessa demanda e baixá-lo de volta
- [ ] **Disparar um Manual Deploy e, depois que voltar, baixar o mesmo anexo** — prova o disco persistente. Se o arquivo sumir, o disco está mal configurado e nada mais importa até corrigir
- [ ] Criar um usuário Assessor; entrar com ele (janela anônima) e confirmar que **não** vê a demanda criada por outro, nem as listas de pessoas e entidades
- [ ] Confirmar que o Assessor recebe recusa em `/analise`, `/auditoria` e `/configuracoes/`
- [ ] Logs do serviço aparecem no painel
- [ ] Fazer um export manual do banco e baixá-lo — valida a Camada 2 do backup

- [ ] **Step 8: Limpar os dados de teste**

Remover a Pessoa, a Demanda, o anexo e o usuário Assessor de teste criados no Step 7, para que a equipe comece com base limpa. O usuário de teste pode ser desativado em vez de excluído, se for aproveitado por alguém da equipe.

- [ ] **Step 9: Configurar alerta de cobrança**

No painel do Render, ativar notificação de gastos para que nenhuma surpresa de fatura passe despercebida.

- [ ] **Step 10: Tag da versão**

```bash
git tag -a v1.0 -m "v1.0 — MPD em producao no Render"
```

Push da tag só após nova confirmação de Pedro.

---

## Auto-revisão do plano

**Cobertura da spec:**

| Seção da spec | Tarefa que implementa |
|---|---|
| §3 Arquitetura (3 recursos) | Task 4 |
| §3.1 Disco persistente | Task 2 (MEDIA_ROOT), Task 4 (disco), Task 7 Step 7 (prova) |
| §3.2 Anexos sem rota pública | Nada a fazer — já é assim no código; verificado na investigação |
| §4.1 `render.yaml`, `build.sh`, `.python-version` | Tasks 4, 3, 1 |
| §4.2 Passo do Tailwind | Task 3 |
| §4.3 gunicorn | Task 1 |
| §4.4 production.py (4 ajustes) | Task 2 |
| §4.5 `.env.example` | Task 5 |
| §4.6 `DJANGO_TRUST_PROXY_SSL_HEADER` | Task 4 (valor), Task 5 (documentação) |
| §5.1 Migrações no pre-deploy | Task 4 |
| §5.2 Primeiro usuário | Task 7 Step 6 |
| §6 Backup em duas camadas | Task 5 §7, Task 7 Step 7 |
| §7 Documentação | Tasks 5 e 6 |
| §9 Critérios de aceite | Task 7 Steps 1 e 7 |

**Achado incorporado depois da spec:** `manage.py` usa settings de desenvolvimento por padrão, enquanto `wsgi.py` usa produção. Sem `DJANGO_SETTINGS_MODULE` explícita, `collectstatic` e `migrate` rodariam em modo desenvolvimento e toda página responderia 500. Coberto na Task 4 (variável), Task 5 (diagnóstico) e nos comentários do `render.yaml`. A spec deve ganhar uma nota nesse sentido na §4.6.

**Consistência de nomes:** serviço `mpd`, banco `mpd-db`, disco `mpd-media`, montagem `/var/data`, `MEDIA_ROOT=/var/data/media`, host `mpd.onrender.com` — conferidos idênticos entre `render.yaml` (Task 4), os testes (Task 2), o `.env.example` (Task 5) e o guia (Task 5).

**Contagem de testes:** 239 (base) → 245 (após Task 2). Usada consistentemente nas Tasks 2, 4, 6 e 7.
