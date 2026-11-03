"""Canal de Telegram por WEBHOOK — para despliegue serverless (Vercel y similares).

Por qué existe: el bot histórico de KynicOS/nanobot usaba polling
(`updater.start_polling()`), que exige un proceso vivo 24/7. En Vercel no hay
procesos persistentes: solo funciones que responden a una petición y mueren.
Telegram sí soporta webhook, que es exactamente ese modelo.

Uso en Vercel:
    POST https://<proyecto>.vercel.app/api/telegram  <- Telegram entrega aquí

Uso en VPS (proceso persistente):
    se mantiene app/cloud/telegram_bot.py con polling, no se toca.

Contrato de este módulo:
    - responde 200 siempre y rápido (Telegram reintenta si no)
    - valida el secreto de Telegram para que nadie más invoque el bot
    - solo atiende al usuario autorizado
    - nunca registra el texto completo de la conversación en logs
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from app.config.schema import Settings
from app.concierge.persona import get_persona

logger = logging.getLogger(__name__)
router = APIRouter()

TELEGRAM_API = "https://api.telegram.org"
_settings: Settings | None = None
_historial: dict[int, list[dict[str, str]]] = {}
MAX_TURNOS = 12  # ventana de contexto por chat, para no crecer sin límite


def _settings_actual() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


async def enviar_mensaje(chat_id: int, texto: str) -> None:
    s = _settings_actual()
    if not s.telegram_token:
        logger.error("telegram_token vacío: no se puede responder")
        return
    async with httpx.AsyncClient(timeout=30) as cliente:
        respuesta = await cliente.post(
            f"{TELEGRAM_API}/bot{s.telegram_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": texto[:4096],
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
        )
        if respuesta.status_code >= 400:
            # Reintento sin Markdown: un asterisco suelto no debe tumbar la respuesta
            await cliente.post(
                f"{TELEGRAM_API}/bot{s.telegram_token}/sendMessage",
                json={"chat_id": chat_id, "text": texto[:4096]},
            )


async def procesar(chat_id: int, texto: str) -> None:
    """Genera la respuesta con la cadena de proveedores y la envía."""
    try:
        from app.cloud.providers import ProviderManager  # import diferido: arranque rápido

        s = _settings_actual()
        persona = get_persona(s.persona)
        historial = _historial.setdefault(chat_id, [])
        historial.append({"role": "user", "content": texto})
        mensajes = [{"role": "system", "content": persona.system_prompt}] + historial[-MAX_TURNOS:]

        manager = ProviderManager(s)
        resultado = await manager.call(mensajes, max_tokens=2048, temperature=0.6)
        contenido = (resultado or {}).get("content") or "Sin respuesta del modelo."
        historial.append({"role": "assistant", "content": contenido})
        await enviar_mensaje(chat_id, contenido)
    except Exception as error:  # noqa: BLE001 - el webhook nunca debe caerse
        logger.exception("fallo procesando mensaje")
        await enviar_mensaje(chat_id, f"⚠️ KYNIKOS no pudo responder: {type(error).__name__}")


@router.post("/api/telegram")
async def recibir_actualizacion(
    request: Request,
    tareas: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, Any]:
    """Endpoint que Telegram invoca. Responde 200 y trabaja en segundo plano."""
    s = _settings_actual()

    if s.telegram_webhook_secret and x_telegram_bot_api_secret_token != s.telegram_webhook_secret:
        raise HTTPException(status_code=403, detail="secreto de webhook inválido")

    datos = await request.json()
    mensaje = datos.get("message") or datos.get("edited_message") or {}
    chat_id = (mensaje.get("chat") or {}).get("id")
    texto = mensaje.get("text") or ""
    autor = (mensaje.get("from") or {}).get("id")

    if not chat_id:
        return {"ok": True, "ignorado": "sin chat"}
    if s.telegram_user_id and str(autor) != str(s.telegram_user_id):
        logger.warning("mensaje de usuario no autorizado ignorado")
        return {"ok": True, "ignorado": "no autorizado"}
    if not texto:
        await enviar_mensaje(chat_id, "Por ahora solo entiendo texto, jefe.")
        return {"ok": True, "ignorado": "sin texto"}

    tareas.add_task(procesar, chat_id, texto)
    return {"ok": True}


@router.get("/api/telegram/salud")
async def salud() -> dict[str, Any]:
    """Diagnóstico sin exponer credenciales."""
    s = _settings_actual()
    return {
        "token_configurado": bool(s.telegram_token),
        "persona": s.persona,
        "usuario_autorizado": bool(s.telegram_user_id),
        "secreto_webhook": bool(s.telegram_webhook_secret),
        "ollama": s.ollama_url,
    }


async def registrar_webhook(base_url: str, secreto: str = "") -> dict[str, Any]:
    """Registra el webhook en Telegram. Útil para el primer despliegue."""
    s = _settings_actual()
    if not s.telegram_token:
        return {"ok": False, "error": "telegram_token vacío"}
    if not base_url.startswith("https://"):
        return {"ok": False, "error": "Telegram exige HTTPS"}
    cuerpo: dict[str, Any] = {
        "url": base_url.rstrip("/") + "/api/telegram",
        "allowed_updates": ["message", "edited_message"],
        "drop_pending_updates": True,
    }
    if secreto:
        cuerpo["secret_token"] = secreto
    async with httpx.AsyncClient(timeout=30) as cliente:
        r = await cliente.post(f"{TELEGRAM_API}/bot{s.telegram_token}/setWebhook", json=cuerpo)
        return {"ok": r.status_code == 200, "respuesta": r.json()}


if __name__ == "__main__":  # registro manual: python -m app.channels.telegram_webhook https://x.vercel.app
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else _settings_actual().public_base_url
    print(asyncio.run(registrar_webhook(url, _settings_actual().telegram_webhook_secret)))
