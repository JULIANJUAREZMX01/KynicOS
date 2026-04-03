"""
KynicOS — Canal: WhatsApp via Evolution API
Sin Twilio, sin licencias. Evolution API es open-source (MIT).
https://github.com/EvolutionAPI/evolution-api

Filosofía Diógenes.Dev:
  - Evolution API corre en tu propio Docker (docker-compose --profile whatsapp up)
  - Sin dependencias de pago: solo EVOLUTION_API_KEY (string local que tú defines)
  - Fallback a Twilio solo si Evolution no está disponible Y hay credenciales Twilio
  - Si ni Evolution ni Twilio: WhatsApp simplemente no funciona, bot sigue operativo

Flujo:
  Mensaje WhatsApp → Evolution webhook → /api/whatsapp/webhook → ConciergeAgentLoop → respuesta
"""

import asyncio
from typing import Optional
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from app.utils import get_logger
from app.core.context import AgentContext

logger = get_logger(__name__)

router = APIRouter()


class EvolutionClient:
    """Cliente para Evolution API (open-source WhatsApp gateway)."""

    def __init__(self, api_url: str, api_key: str, instance_name: str = "kynikos"):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.instance_name = instance_name
        self.headers = {"apikey": api_key, "Content-Type": "application/json"}

    async def is_available(self) -> bool:
        """Verifica si Evolution API está corriendo."""
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{self.api_url}/instance/fetchInstances", headers=self.headers)
                return r.status_code == 200
        except Exception:
            return False

    async def send_text(self, phone: str, message: str) -> bool:
        """Envía mensaje de texto al número dado."""
        try:
            # Normalizar número
            phone = phone.replace("+", "").replace(" ", "").replace("-", "")
            if not phone.endswith("@s.whatsapp.net"):
                phone = f"{phone}@s.whatsapp.net"

            # Dividir mensajes largos
            chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
            for chunk in chunks:
                async with httpx.AsyncClient(timeout=15) as c:
                    r = await c.post(
                        f"{self.api_url}/message/sendText/{self.instance_name}",
                        headers=self.headers,
                        json={"number": phone, "text": chunk},
                    )
                    if r.status_code not in (200, 201):
                        logger.warning(f"[Evolution] Send error: {r.status_code} {r.text[:100]}")
                        return False
            return True
        except Exception as e:
            logger.error(f"[Evolution] send_text error: {e}")
            return False

    async def create_instance(self) -> bool:
        """Crea instancia si no existe. Solo necesario la primera vez."""
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(
                    f"{self.api_url}/instance/create",
                    headers=self.headers,
                    json={
                        "instanceName": self.instance_name,
                        "qrcode": True,
                        "integration": "WHATSAPP-BAILEYS",
                    },
                )
                return r.status_code in (200, 201)
        except Exception as e:
            logger.error(f"[Evolution] create_instance error: {e}")
            return False

    async def get_qr(self) -> Optional[str]:
        """Obtiene QR para conectar WhatsApp (solo primera vez)."""
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(
                    f"{self.api_url}/instance/connect/{self.instance_name}",
                    headers=self.headers,
                )
                if r.status_code == 200:
                    data = r.json()
                    return data.get("base64") or data.get("qrcode", {}).get("base64")
        except Exception as e:
            logger.error(f"[Evolution] get_qr error: {e}")
        return None


class TwilioFallback:
    """Fallback opcional a Twilio si Evolution no está disponible."""

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    async def send_text(self, phone: str, message: str) -> bool:
        try:
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)
            chunks = [message[i:i+1500] for i in range(0, len(message), 1500)]
            for chunk in chunks:
                client.messages.create(
                    from_=f"whatsapp:{self.from_number}",
                    to=f"whatsapp:{phone}",
                    body=chunk,
                )
            return True
        except Exception as e:
            logger.error(f"[Twilio] send error: {e}")
            return False


# ── Singleton cliente ────────────────────────────────────────────
_evolution: Optional[EvolutionClient] = None
_twilio: Optional[TwilioFallback] = None


def init_whatsapp(settings) -> None:
    """Inicializa el canal WhatsApp según disponibilidad."""
    global _evolution, _twilio

    evo_url = getattr(settings, "evolution_api_url", None) or "http://localhost:8080"
    evo_key = getattr(settings, "evolution_api_key", None) or "kynikos-evo-key"

    _evolution = EvolutionClient(evo_url, evo_key)
    logger.info(f"[WhatsApp] Evolution API configurado en {evo_url}")

    # Twilio como fallback secundario
    if getattr(settings, "twilio_account_sid", None) and getattr(settings, "twilio_auth_token", None):
        _twilio = TwilioFallback(
            settings.twilio_account_sid,
            settings.twilio_auth_token,
            settings.twilio_whatsapp_from,
        )
        logger.info("[WhatsApp] Twilio configurado como fallback")


async def send_message(phone: str, message: str) -> bool:
    """Envía mensaje WhatsApp. Usa Evolution → Twilio → falla silenciosamente."""
    if _evolution:
        available = await _evolution.is_available()
        if available:
            return await _evolution.send_text(phone, message)
        else:
            logger.warning("[WhatsApp] Evolution no disponible")

    if _twilio:
        logger.info("[WhatsApp] Usando Twilio fallback")
        return await _twilio.send_text(phone, message)

    logger.warning("[WhatsApp] Sin canal disponible — mensaje descartado")
    return False


# ── Webhook FastAPI ──────────────────────────────────────────────

@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    """Recibe mensajes entrantes de Evolution API."""
    try:
        data = await request.json()

        # Evolution API payload
        event_type = data.get("event", "")
        if event_type != "messages.upsert":
            return JSONResponse({"ok": True})

        msg_data = data.get("data", {}).get("messages", [{}])[0]
        from_number = msg_data.get("key", {}).get("remoteJid", "").replace("@s.whatsapp.net", "")
        text = (
            msg_data.get("message", {}).get("conversation")
            or msg_data.get("message", {}).get("extendedTextMessage", {}).get("text")
            or ""
        )

        if not text or msg_data.get("key", {}).get("fromMe"):
            return JSONResponse({"ok": True})

        logger.info(f"[WhatsApp] Mensaje de {from_number}: {text[:60]}...")

        # Procesar con agent loop
        asyncio.create_task(_process_whatsapp(from_number, text))
        return JSONResponse({"ok": True})

    except Exception as e:
        logger.error(f"[WhatsApp] Webhook error: {e}")
        return JSONResponse({"ok": True})  # siempre 200 al webhook


async def _process_whatsapp(phone: str, text: str) -> None:
    """Procesa mensaje WhatsApp con el agent loop."""
    try:
        from app.main import _agent_loop, _session_manager
        if not _agent_loop:
            return

        session_id = f"whatsapp_{phone}"
        ctx = await _session_manager.load_session(session_id)
        if not ctx:
            ctx = AgentContext(session_id=session_id, user_id=phone, channel="whatsapp")

        ctx.add_message("user", text)
        response = await _agent_loop.process_message(ctx)
        await _session_manager.save_session(ctx)
        await send_message(phone, response)

    except Exception as e:
        logger.error(f"[WhatsApp] Process error: {e}")
        await send_message(phone, "⚠️ Error procesando tu mensaje. Intenta de nuevo.")


def create_whatsapp_routes() -> APIRouter:
    return router
