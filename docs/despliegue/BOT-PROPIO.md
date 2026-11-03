# Levantar KYNIKOS como bot propio

Dos caminos. Elige uno según lo que importe más: tokens ilimitados o cero servidores.

## Camino A — VPS o máquina propia (tokens ilimitados)

Requisitos: un equipo encendido con Ollama y una dirección accesible.

```bash
# 1. Modelo local
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2          # o qwen2.5:7b para español

# 2. KYNIKOS
git clone https://github.com/JULIANJUAREZMX01/KynicOS.git && cd KynicOS
python3 -m venv .venv && .venv/bin/pip install -r requirements-bot.txt

# 3. Entorno (nunca en el repo)
export TELEGRAM_TOKEN="token de BotFather"
export TELEGRAM_USER_ID="8247886073"
export PERSONA="kynicos"
export OLLAMA_URL="http://127.0.0.1:11434"
export OLLAMA_MODEL="llama3.2"

# 4. Arrancar con polling (proceso persistente)
.venv/bin/python -m app.main
```

Ventaja: sin costo por token y sin depender de nadie.
Costo: velocidad según el equipo, y el equipo debe seguir encendido.

## Camino B — Vercel (serverless, webhook)

```bash
brew install vercel-cli        # o: npm i -g vercel
vercel link                    # proyecto nuevo
vercel env add TELEGRAM_TOKEN
vercel env add TELEGRAM_USER_ID      # 8247886073
vercel env add TELEGRAM_WEBHOOK_SECRET   # cadena aleatoria larga
vercel env add GROQ_API_KEY          # opcional: respaldo en la nube
vercel --prod
```

Luego registra el webhook una sola vez:

```bash
python -m app.channels.telegram_webhook https://<proyecto>.vercel.app
```

Ventaja: no hay servidor que mantener.
Límite honesto: el modelo tiene que venir de una API, así que hay techo de tokens o costo por uso. Ollama no corre en Vercel.

## Verificación

```bash
curl https://<url>/api/telegram/salud
# {"token_configurado":true,"persona":"kynicos","usuario_autorizado":true,
#  "secreto_webhook":true,"ollama":"http://127.0.0.1:11434"}
```

Escribe al bot desde Telegram. Si responde con el saludo de KYNIKOS, quedó enlazado.

## Higiene

- `TELEGRAM_TOKEN` y `TELEGRAM_WEBHOOK_SECRET` solo en variables de entorno o en la bóveda, nunca en el repo.
- El bot solo atiende al usuario `8247886073`; cualquier otro remitente se ignora.
- Si el bot deja de responder, revisa `/api/telegram/salud`: dice qué falta sin exponer nada.
