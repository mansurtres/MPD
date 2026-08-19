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
# tailwind-output.css nao e versionado (ver README). Sem este passo o MPD
# sobe como HTML cru, sem estilo nenhum.
curl --silent --show-error --location --fail --retry 3 --retry-delay 2 \
  --output ./tailwindcss "$TAILWIND_URL"
chmod +x ./tailwindcss
./tailwindcss -i ./static/css/tailwind-input.css -o ./static/css/tailwind-output.css --minify

if [ ! -s ./static/css/tailwind-output.css ]; then
  echo "ERRO: tailwind-output.css saiu vazio. O site subiria sem estilo." >&2
  exit 1
fi

echo "==> [4/4] Coletando arquivos estaticos"
# --ignore tailwind-input.css: é arquivo-FONTE do compilador, nao asset servido.
# Contem `@import "tailwindcss"`, que o CompressedManifestStaticFilesStorage
# tenta resolver como caminho relativo (css/tailwindcss) e nao encontra,
# abortando o collectstatic inteiro.
uv run python manage.py collectstatic --no-input --ignore tailwind-input.css

echo "==> Build concluido"
