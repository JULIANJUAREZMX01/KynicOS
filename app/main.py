"""
KynicOS — Main Entry Point
Monorepo unificado: nanobot-cloud + KYNYKOS_AI_Agent + MueveCancún skills
"""

import asyncio
import os
import secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, Query, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.config import Settings
from app.utils import get_logger
from app.utils.logger import _asegurar_utf8
from app.cloud.telegram_bot import start_telegram_bot, stop_telegram_bot
from app.core.memory import Memory
from app.cloud.sessions import SessionManager
from app.concierge.persona import get_persona

_asegurar_utf8()
logger = get_logger(__name__)
_agent_loop = None
_session_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown."""
    global _agent_loop, _session_manager

    logger.info("=" * 70)
    logger.info("🏨 KYNICOS OS — STARTING UP")
    logger.info("=" * 70)

    settings = Settings()
    persona_name = os.getenv("PERSONA", settings.persona)
    persona = get_persona(persona_name)
    telegram_task = None
    sentinel_task = None
    sentinel = None

    try:
        Memory(workspace_path="./workspace")
        _session_manager = SessionManager(data_dir="./data")
        logger.info("✅ Memory + Sessions OK")

        from app.cloud.providers import ProviderManager
        from app.agents.concierge_loop import ConciergeAgentLoop

        provider_manager = ProviderManager(settings)
        _agent_loop = ConciergeAgentLoop(settings, provider_manager, persona=persona)
        logger.info(f"✅ ConciergeAgentLoop ({persona.name}) OK")

        try:
            from app.core.sentinel import LogSentinel
            sentinel = LogSentinel(settings)
            if settings.sentinel_enabled:
                sentinel_task = asyncio.create_task(sentinel.run())
                logger.info("🐕 Sentinel lifecycle task started")
            else:
                logger.info("🐕 Sentinel disabled by configuration")
        except Exception as e:
            logger.warning(f"Sentinel no disponible: {e}")

        try:
            from app.cloud.whatsapp_bridge import init_whatsapp_bridge
            init_whatsapp_bridge(settings)
        except Exception as e:
            logger.warning(f"WhatsApp bridge no disponible: {e}")

        if settings.telegram_token:
            logger.info("📱 Iniciando Telegram bot...")
            telegram_task = asyncio.create_task(start_telegram_bot(settings))
        else:
            logger.info("📱 Telegram deshabilitado: TELEGRAM_TOKEN no configurado")

        logger.info("=" * 70)
        logger.info(f"🟢 KYNICOS OS ACTIVO — Persona: {persona.name.upper()}")
        logger.info("=" * 70)
        yield

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise
    finally:
        if sentinel is not None:
            sentinel.stop()
        if sentinel_task:
            sentinel_task.cancel()
            try:
                await sentinel_task
            except asyncio.CancelledError:
                pass
        if telegram_task:
            telegram_task.cancel()
            try:
                await telegram_task
            except asyncio.CancelledError:
                pass
            await stop_telegram_bot()
        _agent_loop = None
        _session_manager = None
        logger.info("✅ KynicOS shutdown OK")


app = FastAPI(
    title="KynicOS — Luxury Concierge & Transit Assistant",
    description=(
        "Sistema operativo hotelero para hospitalidad de ultra-lujo en Cancún. "
        "Telegram + WhatsApp + HVAC Triage + MueveCancún integration."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

web_path = Path(__file__).parent.parent / "web"
if web_path.exists():
    app.mount("/static", StaticFiles(directory=web_path), name="static")


@app.get("/")
async def root():
    dashboard_path = Path(__file__).parent.parent / "web" / "index.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return {
        "name": "KynicOS",
        "version": "1.0.0",
        "status": "running",
        "persona": os.getenv("PERSONA", Settings().persona),
        "docs": "/docs",
    }


def _token_esperado() -> str:
    try:
        return (getattr(Settings(), "kynikos_api_token", "") or "").strip()
    except Exception:
        return (os.getenv("KYNIKOS_API_TOKEN") or "").strip()


async def requiere_token(
    x_kynikos_token: str = Header(default=""),
    token: str = Query(default=""),
):
    """Protege el estado del nodo.

    Falla cerrado: si no hay KYNIKOS_API_TOKEN configurado, la ruta responde 503
    en vez de abrirse. Un endpoint de diagnostico abierto revela PID, persona y
    estado del token a cualquiera que acierte la URL; con un tunel delante, eso
    incluye a todo internet.
    """
    esperado = _token_esperado()
    if not esperado:
        raise HTTPException(
            status_code=503,
            detail="KYNIKOS_API_TOKEN no configurado: el estado esta cerrado por seguridad",
        )
    recibido = (x_kynikos_token or token or "").strip()
    if not recibido or not secrets.compare_digest(recibido, esperado):
        raise HTTPException(status_code=401, detail="token requerido")
    return True


@app.get("/api/health")
async def health():
    """Latido minimo para monitores y tuneles. No revela nada del nodo."""
    return {"ok": True, "service": "kynikos"}


@app.get("/api/status", dependencies=[Depends(requiere_token)])
async def status():
    """Estado real, no un saludo.

    Antes devolvia "ok" escrito a mano: respondia 200 con el agente caido y sin
    token, que es justo lo que hacia imposible diagnosticar el nodo. Ahora "ok"
    exige bucle construido y canal de Telegram cargado; si falta algo dice
    "degradado" y expone que falta.
    """
    persona_name = os.getenv("PERSONA", Settings().persona)
    settings = Settings()
    token = bool(getattr(settings, "telegram_token", ""))
    loop_vivo = _agent_loop is not None
    # Canales y skills reales, no escritos a mano: whatsapp figuraba activo sin
    # credenciales de Twilio y "concierge_llm" no existe como skill. Un endpoint
    # de estado que miente no sirve para diagnosticar nada.
    whatsapp_on = bool(os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"))
    skills_dir = Path(__file__).parent / "skills"
    skills = sorted(
        p.stem for p in skills_dir.glob("*.py")
        if not p.stem.startswith("_") and p.stem != "__init__"
    )
    return JSONResponse({
        "status": "ok" if (loop_vivo and token) else "degradado",
        "version": "1.0.0",
        "pid": os.getpid(),
        "persona": persona_name,
        "agent_loop": loop_vivo,
        "telegram_token": token,
        "llm": "groq → anthropic → ollama",
        "channels": [
            channel for channel, enabled in (
                ("telegram", token),
                ("whatsapp", whatsapp_on),
            ) if enabled
        ],
        "skills": skills,
        "deploy_url": os.getenv("KYNIKOS_DEPLOY_URL", ""),
    })


@app.get("/api/persona", dependencies=[Depends(requiere_token)])
async def get_current_persona():
    persona = get_persona(os.getenv("PERSONA", Settings().persona))
    return {
        "name": persona.name,
        "tone": persona.tone,
        "language": persona.language,
        "greeting_preview": persona.greeting[:100] + "...",
    }


try:
    from app.cloud.whatsapp_bridge import create_whatsapp_routes
    app.include_router(create_whatsapp_routes(), prefix="/api")
    logger.info("✅ WhatsApp webhook registrado en /api/webhook/whatsapp")
except Exception as e:
    logger.warning(f"WhatsApp webhook no disponible: {e}")

# Canal web: la consola PWA. Sin este include, la PWA llamaba a /api/chat,
# recibia 404 y mostraba "(sin respuesta)" con el nodo perfectamente sano.
try:
    from app.channels.web_chat import router as web_chat_router

    app.include_router(web_chat_router)
    logger.info("✅ Chat web registrado en /api/chat")
except Exception as e:
    logger.warning(f"Chat web no disponible: {e}")

try:
    from app.cloud.dashboard import create_dashboard_routes
    app.include_router(create_dashboard_routes(), prefix="/api")
except Exception as e:
    logger.warning(f"Dashboard routes no disponibles: {e}")


if __name__ == "__main__":
    import uvicorn

    settings = Settings()
    # Con el nombre como texto ("app.main:app"), uvicorn importa el modulo por
    # SEGUNDA vez: el bloque de nivel de modulo se ejecuta dos veces y se ve en
    # los logs del nodo real ("Chat web registrado" repetido bajo `main` y bajo
    # `app.main`), duplicando routers y la carga de personas. Pasando el objeto
    # no hay reimportacion. El texto solo hace falta para el reload de desarrollo.
    if settings.environment == "development":
        uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
    else:
        uvicorn.run(app, host=settings.host, port=settings.port)
