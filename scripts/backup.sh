#!/usr/bin/env bash
# Backup do banco PostgreSQL do MPD via pg_dump.
#
# Uso:
#   bash scripts/backup.sh [destino]
#
# Sem argumento, escreve em ./backups/ no diretório do projeto.
# Nome do arquivo: backup-AAAA-MM-DD-HHMMSS.sql
#
# Em produção, rodar via cron diário. Exemplo (crontab):
#   0 3 * * * /caminho/para/mpd/scripts/backup.sh /var/backups/mpd
#
# Variáveis de ambiente lidas (do .env via decouple ou shell):
#   DATABASE_URL — preferida quando presente, formato postgres dsn  # pragma: allowlist secret
#   variáveis individuais POSTGRES_* — fallback se DATABASE_URL não estiver setada.

set -euo pipefail

DESTINO="${1:-$(dirname "$0")/../backups}"
mkdir -p "$DESTINO"

TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
ARQUIVO="$DESTINO/backup-$TIMESTAMP.sql"

# Carrega .env se existir (não falha se ausente)
ENV_FILE="$(dirname "$0")/../.env"
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC2046
    export $(grep -E '^[A-Z_]+=' "$ENV_FILE" | xargs -d '\n')
fi

if [ -n "${DATABASE_URL:-}" ]; then
    # pg_dump entende DATABASE_URL diretamente
    pg_dump "$DATABASE_URL" > "$ARQUIVO"
else
    PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD não definida}" \
        pg_dump \
            -h "${POSTGRES_HOST:-localhost}" \
            -p "${POSTGRES_PORT:-5432}" \
            -U "${POSTGRES_USER:-mpd}" \
            "${POSTGRES_DB:-mpd}" > "$ARQUIVO"
fi

# Validação leve: arquivo não-vazio
if [ ! -s "$ARQUIVO" ]; then
    echo "ERRO: backup vazio. Verifique credenciais e conectividade." >&2
    exit 1
fi

echo "Backup gerado: $ARQUIVO ($(du -h "$ARQUIVO" | cut -f1))"
