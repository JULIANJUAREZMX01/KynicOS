#!/usr/bin/env bash
# Instalador del nodo primario KYNIKOS en una PC del jefe.
# Uso:  bash nodo/instalar.sh
# Deja el bot corriendo con modelo local (tokens ilimitados) y Telegram por polling.
# No requiere exponer puertos ni pagar nada.
set -euo pipefail

echo "== KYNIKOS · nodo primario =="
command -v python3 >/dev/null || { echo "Falta python3"; exit 1; }

if ! command -v ollama >/dev/null; then
  echo "-- instalando Ollama (modelo local, sin costo por token)"
  curl -fsSL https://ollama.com/install.sh | sh
fi

MODELO="${KYNIKOS_MODELO:-qwen2.5:7b}"   # óptimo para 16 GB de RAM sin GPU dedicada
echo "-- descargando modelo $MODELO (una sola vez)"
ollama pull "$MODELO" || true

echo "-- entorno de Python"
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements-bot.txt

if [ ! -f .env ]; then
  cat > .env <<'ENV'
# Rellena estos dos valores. El token se obtiene en @BotFather de Telegram.
TELEGRAM_TOKEN=
TELEGRAM_USER_ID=8247886073
PERSONA=kynikos
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_NUM_CTX=4096
MAX_TOKENS_SALIDA=768
TIMEOUT_LLM=300
ENV
  echo "!! Edita .env y pon el TELEGRAM_TOKEN antes de arrancar"
fi

echo "-- comprobando modelo"
curl -s "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1 && echo "   Ollama responde" || echo "   Ollama aún no responde; el servicio arrancará al iniciar sesión"

cat <<'FIN'
Listo. Para arrancar:
  set -a && source .env && set +a
  .venv/bin/python -m app.main

Para que arranque solo al encender el equipo, crea el servicio:
  sudo systemctl enable --now kynikos
FIN
