# MPD — Mandato Parlamentar Digital

Sistema de rastreabilidade de relacionamento político (categoria *constituent management*) para um mandato parlamentar municipal.

> Status atual: **v0.1 — Fase 0 (Fundação)**. Esqueleto técnico funcionando: Django + PostgreSQL + Tailwind.

A documentação completa do projeto está em [`docs/`](./docs/) e em [`roadmap.md`](./roadmap.md). O `CLAUDE.md` na raiz é a bússola para sessões de desenvolvimento com Claude Code.

---

## Pré-requisitos

| Ferramenta | Versão | Onde obter |
|---|---|---|
| Python | 3.12+ | https://www.python.org/downloads/ |
| PostgreSQL | 16+ | https://www.postgresql.org/download/windows/ |
| `uv` | 0.4+ | `pip install uv` ou https://docs.astral.sh/uv/ |
| Git | 2.40+ | https://git-scm.com/downloads |

---

## Setup do zero

### 1. Clonar e instalar dependências

```bash
git clone https://github.com/mansurtres/MPD.git mpd
cd mpd
uv sync --extra dev
```

Isso cria `.venv/` e instala dependências de prod + dev.

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Edite `.env`:

- `DJANGO_SECRET_KEY` — gere com `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`.
- `DATABASE_URL` — ajuste se seu Postgres local usa outra senha/porta.

### 3. Criar banco PostgreSQL

No SQL Shell (psql) ou pgAdmin, conectado como `postgres`:

```sql
CREATE USER mpd WITH PASSWORD 'mpd';
CREATE DATABASE mpd_dev OWNER mpd ENCODING 'UTF8';
GRANT ALL PRIVILEGES ON DATABASE mpd_dev TO mpd;
```

### 4. Aplicar migrações + criar superusuário

```bash
uv run python manage.py migrate
uv run python manage.py createsuperuser
```

### 5. Compilar Tailwind (uma vez ou em watch)

O binário do Tailwind standalone fica em `bin/tailwindcss.exe` (Windows) ou `bin/tailwindcss` (Linux/macOS) — **não versionado**, baixe na primeira vez:

**Windows (PowerShell):**
```powershell
Invoke-WebRequest -Uri "https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-windows-x64.exe" -OutFile "bin/tailwindcss.exe"
```

**Linux:**
```bash
curl -L -o bin/tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
chmod +x bin/tailwindcss
```

**macOS (Apple Silicon):**
```bash
curl -L -o bin/tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-macos-arm64
chmod +x bin/tailwindcss
```

Build pontual:
```bash
./bin/tailwindcss -i ./static/css/tailwind-input.css -o ./static/css/tailwind-output.css
```

Build em watch (recompila a cada mudança em template):
```bash
./bin/tailwindcss -i ./static/css/tailwind-input.css -o ./static/css/tailwind-output.css --watch
```

### 6. Subir o servidor de desenvolvimento

```bash
uv run python manage.py runserver
```

Abra http://localhost:8000/ — deve mostrar a página inicial. Em http://localhost:8000/admin/ entra com o superusuário.

### 7. Pre-commit

```bash
uv run pre-commit install
```

Os hooks (ruff, black, detect-secrets) rodam automaticamente em cada commit.

---

## Comandos úteis

| O que | Comando |
|---|---|
| Subir servidor | `uv run python manage.py runserver` |
| Aplicar migrações | `uv run python manage.py migrate` |
| Criar migrações | `uv run python manage.py makemigrations` |
| Criar superusuário | `uv run python manage.py createsuperuser` |
| Rodar testes | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Format check | `uv run black --check .` |
| Format apply | `uv run black .` |
| Tailwind watch | `./bin/tailwindcss -i ./static/css/tailwind-input.css -o ./static/css/tailwind-output.css --watch` |
| Django shell | `uv run python manage.py shell` |
| Health check da app | `curl http://localhost:8000/healthz/` |

---

## Estrutura do repositório

Documentada em [`docs/estrutura-do-repositorio.md`](./docs/estrutura-do-repositorio.md). Resumo:

- `config/settings/{base,development,production,test}.py` — settings split por ambiente.
- `core/`, `accounts/`, `cidadaos/`, `casos/` — apps de domínio.
- `templates/`, `static/` — assets compartilhados.
- `tests/` — testes E2E e fixtures globais.
- `docs/` — projeto executivo.

---

## Convenções

- **Idioma:** código em inglês, domínio em português ([`docs/estrutura-do-repositorio.md`](./docs/estrutura-do-repositorio.md) §13.1).
- **Branches:** `main` (estável, com tags), `dev` (ativo), `feature/<nome>` (PRs).
- **Commits:** Conventional Commits — `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.

---

## Licença

A definir.
