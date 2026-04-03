"""WhatsApp bridge integration via Twilio for Nanobot"""

import asyncio
from typing import Optional

from fastapi import APIRouter, Form, Request, Response
from twilio.rest import Client
from twilio.request_validator import RequestValidator

from app.config import Settings
from app.core.context import AgentContext
from app.utils import get_logger

logger = get_logger(__name__)

_twilio_client: Optional[Client] = None
_settings: Optional[Settings] = None


def init_whatsapp_bridge(settings: Settings) -> None:
    """Initialize the Twilio client for WhatsApp"""
    global _twilio_client, _settings
    _settings = settings

    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.warning("⚠️  Twilio credentials not configured — WhatsApp bridge disabled")
        return

    _twilio_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    logger.info("✅ WhatsApp bridge (Twilio) initialized")


def create_whatsapp_routes() -> APIRouter:
    """Return an APIRouter with the Twilio WhatsApp webhook endpoint"""
    router = APIRouter()

    @router.post("/webhook/whatsapp")
    async def whatsapp_webhook(
        request: Request,
        From: str = Form(...),
        Body: str = Form(""),
        MediaUrl0: Optional[str] = Form(None),
    ) -> Response:
        """Handle incoming WhatsApp messages from Twilio"""
        # Reject requests when Twilio credentials are not configured
        if not _settings or not _settings.twilio_auth_token:
            logger.warning("Twilio WhatsApp webhook called but credentials are not configured — request rejected")
            return Response(content="Service unavailable", status_code=503)

        # Validate Twilio signature using already-parsed Form parameters to avoid
        # reading the request body a second time (bodies can only be consumed once).
        validator = RequestValidator(_settings.twilio_auth_token)
        signature = request.headers.get("X-Twilio-Signature", "")
        url = str(request.url)
        form_data: dict = {"From": From, "Body": Body}
        if MediaUrl0 is not None:
            form_data["MediaUrl0"] = MediaUrl0
        if not validator.validate(url, form_data, signature):
            client_ip = request.client.host if request.client else "unknown"
            logger.warning(
                "Invalid Twilio signature — request rejected "
                f"(ip={client_ip}, path={request.url.path}, signature_present={bool(signature)})"
            )
            return Response(content="Forbidden", status_code=403)

        # Strip "whatsapp:" prefix added by Twilio
        user_phone = From.replace("whatsapp:", "")
        if Body:
            body_preview = Body if len(Body) <= 60 else Body[:60] + "..."
            logger.info(f"WhatsApp message from {user_phone}: {body_preview}")
        else:
            logger.info(f"WhatsApp message from {user_phone} with empty body")

        response_text = await _process_with_agent(user_phone, Body, MediaUrl0)
        _send_whatsapp_reply(user_phone, response_text)

        # Return empty TwiML so Twilio doesn't attempt its own reply
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml",
        )

    return router


async def send_whatsapp_alert(message_text: str, settings: Settings) -> bool:
    """Send a proactive WhatsApp alert to the configured phone number"""
    global _twilio_client
    if not _twilio_client or not settings.twilio_whatsapp_from or not settings.twilio_whatsapp_to:
        logger.warning(
            "Twilio client or WhatsApp settings not ready — cannot send WhatsApp alert "
            f"(client_ready={bool(_twilio_client)}, "
            f"from_configured={bool(getattr(settings, 'twilio_whatsapp_from', None))}, "
            f"to_configured={bool(getattr(settings, 'twilio_whatsapp_to', None))})"
        )
        return False

    try:
        _twilio_client.messages.create(
            from_=f"whatsapp:{settings.twilio_whatsapp_from}",
            to=f"whatsapp:{settings.twilio_whatsapp_to}",
            body=f"🐕 **CENTINELA KYNIKOS ALERT**:\n\n{message_text}",
        )
        return True
    except Exception as e:
        logger.error(f"Error sending WhatsApp alert: {e}")
        return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _send_whatsapp_reply(to_phone: str, text: str) -> None:
    """Send a WhatsApp reply via Twilio REST API"""
    if not _twilio_client or not _settings or not _settings.twilio_whatsapp_from:
        logger.warning("Twilio client not ready — cannot send WhatsApp reply")
        return

    # Twilio message body max is 1600 chars; split if needed and add
    # continuation indicators when multiple chunks are required.
    max_len = 1600
    chunks = _chunk_message(text, max_len)

    for chunk in chunks:
        try:
            _twilio_client.messages.create(
                from_=f"whatsapp:{_settings.twilio_whatsapp_from}",
                to=f"whatsapp:{to_phone}",
                body=chunk,
            )
        except Exception as e:
            logger.error(f"Error sending WhatsApp message to {to_phone}: {e}")


def _chunk_message(text: str, max_len: int) -> list:
    """Split ``text`` into chunks of at most ``max_len`` characters.

    When more than one chunk is needed, each chunk is suffixed with a
    (n/total) indicator so the recipient can tell the message continues.
    """
    if len(text) <= max_len:
        return [text]

    # Reserve space for the worst-case indicator, then recalculate
    total_len = len(text)
    total_chunks = max(1, -(-total_len // max_len))  # ceiling division

    while True:
        indicator_example = f" ({total_chunks}/{total_chunks})"
        content_len = max_len - len(indicator_example)
        if content_len <= 0:
            # Fallback: no indicators if they'd consume all space
            return [text[i : i + max_len] for i in range(0, total_len, max_len)]
        new_total = max(1, -(-total_len // content_len))
        if new_total == total_chunks:
            break
        total_chunks = new_total

    chunks = []
    for idx, start in enumerate(range(0, total_len, content_len), start=1):
        indicator = f" ({idx}/{total_chunks})"
        chunk_content = text[start : start + content_len]
        chunks.append(f"{chunk_content}{indicator}")

    return chunks


async def _download_media(media_url: str, auth_token: str, account_sid: str) -> Optional[str]:
    """Download a Twilio media attachment and save it to workspace/logic.

    Returns the local file path on success, or None on failure.
    """
    import httpx
    from pathlib import Path

    try:
        logic_dir = Path("workspace/logic")
        logic_dir.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient() as client:
            resp = await client.get(media_url, auth=(account_sid, auth_token), follow_redirects=True)
            resp.raise_for_status()

            # Derive a filename from the URL path
            url_path = media_url.split("?")[0].rstrip("/")
            filename = url_path.split("/")[-1] or "whatsapp_media"
            content_type = resp.headers.get("content-type", "")
            if "." not in filename:
                ext = content_type.split("/")[-1].split(";")[0].strip()
                if ext:
                    filename = f"{filename}.{ext}"

            save_path = logic_dir / filename
            save_path.write_bytes(resp.content)
            logger.info(f"WhatsApp media saved: {save_path}")
            return str(save_path)
    except Exception as e:
        logger.error(f"Error downloading WhatsApp media {media_url}: {e}")
        return None


async def _process_with_agent(user_phone: str, text: str, media_url: Optional[str]) -> str:
    """Process an incoming WhatsApp message through the agent loop"""
    try:
        from app.main import _agent_loop, _session_manager

        if not _agent_loop:
            return "❌ Agent loop no iniciado"

        if not _session_manager:
            return "❌ Session manager no iniciado"

        session_id = f"whatsapp_{user_phone}"
        ctx = await _session_manager.load_session(session_id)
        if not ctx:
            ctx = AgentContext(
                session_id=session_id,
                user_id=user_phone,
                channel="whatsapp",
            )

        # Download media attachment and make it available to the agent
        if media_url and _settings and _settings.twilio_account_sid and _settings.twilio_auth_token:
            local_path = await _download_media(
                media_url, _settings.twilio_auth_token, _settings.twilio_account_sid
            )
            if local_path:
                ctx.add_file(local_path)
                text = f"{text}\n[Adjunto guardado: {local_path}]".strip()
            else:
                text = f"{text}\n[Adjunto: {media_url}]".strip()

        ctx.add_message("user", text)
        response = await _agent_loop.process_message(ctx)
        await _session_manager.save_session(ctx)
        return response

    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {e}", exc_info=True)
        return f"❌ Error: {str(e)[:120]}"

async def connect(settings: Settings) -> None:
    """
    Initialize connection to WhatsApp bridge.
    Designed to be started as a background task during application startup.
    """
    logger.info("🔌 Connecting to WhatsApp Bridge...")
    init_whatsapp_bridge(settings)

    if _twilio_client:
        logger.info("✅ WhatsApp Bridge Connected & Listening")
    else:
        logger.warning("⚠️ WhatsApp Bridge initialized but not connected (No credentials)")
