# ADR-020 — KYNIKOS deja de ser concierge y pasa a ser el bot propio de Julián

- **Fecha:** 3 de noviembre de 2026
- **Estado:** Aceptada (implementación en curso)
- **Repositorio:** `JULIANJUAREZMX01/KynicOS`

## Contexto

KynicOS nació como sistema operativo de concierge de ultra-lujo para Cancún, con la persona `LEO` atendiendo huéspedes. La fusión parcial con `nanobot-cloud` ya había traído lo valioso: cadena de proveedores con respaldo local en Ollama y el bot de Telegram.

Julián pide algo distinto: que KynicOS no atienda turistas, sino que **sea su propio agente**, el mismo con el que habla en su chat principal, pero corriendo en su infraestructura. Su referencia es "el kiloclaw extinto": un bot propio, sin dependencia de plataformas que se apagan, sin límite de tokens, lento pero seguro.

Restricción real que hay que decir sin adornos: **ninguna plataforma serverless puede ofrecer tokens ilimitados**, porque no puede ejecutar un modelo. Vercel solo corre funciones cortas. Los tokens ilimitados solo existen si el modelo corre en una máquina propia o alquilada por tiempo, no por consumo.

## Decisión

1. **Persona.** `KYNIKOS` pasa a ser la persona por defecto (`persona = "kynicos"`). `LEO`, `NEXUS_ADMIN` y `MUEVE_CANCUN` quedan disponibles por nombre; el modo concierge no se borra, se desactiva como comportamiento inicial.
2. **Rol.** KYNIKOS atiende backend, infraestructura, seguridad y automatización. No asume interfaz, diseño ni copy.
3. **Fusión.** Se incorporan de `nanobot-cloud` las piezas que faltaban en KynicOS: `sessions.py`, `backup_service.py`, `scripts/backup_s3.py`, `scripts/verify_setup.py` y las pruebas de proveedores y herramientas.
4. **Dos canales, dos despliegues:**
   - **VPS o máquina propia (recomendado para "sin límite de tokens").** Proceso persistente con polling y Ollama local. Costo fijo, cero costo por token, velocidad menor. Es el camino que cumple literalmente lo pedido.
   - **Vercel (serverless).** Canal por webhook nuevo en `app/channels/telegram_webhook.py` más `api/index.py`. Funciona al instante y sin servidor propio, pero el modelo debe venir de una API externa, así que **no** es ilimitado: es gratuito con techo (Groq) o de pago por uso.
5. **Seguridad del canal.** El webhook valida `X-Telegram-Bot-Api-Secret-Token`, atiende solo al usuario autorizado (`8247886073`) y nunca registra el texto completo de la conversación.
6. **Sin secretos en el repositorio.** Token, secreto de webhook y llaves viven en variables de entorno.

## Verificado en este turno

- `GET /api` responde 200 y `GET /api/telegram/salud` reporta estado sin exponer credenciales.
- `POST /api/telegram` acepta la actualización de Telegram y encola el trabajo en segundo plano.
- La cadena de proveedores arranca correctamente con solo Ollama configurado: `['ollama']`, persona `kynicos`, modelo `llama3.2`.
- Se detectó y corrigió un fallo real de empaquetado: `providers.py` requiere `tenacity` y `app/utils/logger.py` requiere `loguru`; ambos faltaban en `requirements-bot.txt`.

## Pendientes para cerrar el enlace

1. **Token del bot** desde BotFather (no lo tengo y no puedo generarlo). Sin él, el bot no existe para Telegram.
2. **Decisión de alojamiento:** VPS con Ollama (ilimitado, costo fijo) o Vercel con webhook (gratis con techo).
3. **Registro del webhook** con `python -m app.channels.telegram_webhook https://<url>` una vez desplegado.

## Consecuencias

- KynicOS deja de ser un producto de concierge y se convierte en la pieza de continuidad del ecosistema: sobrevive al apagón de Jules y a la suspensión de Render.
- El modo concierge sigue disponible para el PMS de Cantabria si se reactiva; no se pierde trabajo.
- La calidad de la respuesta depende del modelo elegido: con Ollama local será más lento y menos capaz que una API, y eso es una decisión consciente, no un defecto.
