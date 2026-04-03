"""
KynicOS — Main Entry Point
Monorepo unificado: nanobot-cloud + KYNYKOS_AI_Agent + MueveCancún skills

Modos de operación:
  - PERSONA=leo       → Concierge de lujo para turistas (MVP Nexus Pilot)
  - PERSONA=nexus     → Superagente personal de Julián (admin)
  - PERSONA=mueve     → Guía de transporte MueveCancún

Deploy en Render (existente): https://nanobot-cloud-zjr0.onrender.com
Service ID: srv-d6b9sihr0fns739m646g
"""

import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.config import Settings
from app.utils import get_logger
from app.cloud.dashboard import create_dashboard_routes
from app.cloud.telegram_bot import start_telegram_bot, stop_telegram_bot
from app.cloud.backup_service import BackupService
from app.core.memory import Memory
from app.cloud.sessions import SessionManager
from app.concierge.persona import get_persona

logger = get_logger(__name__)

# Globals
_agent_loop = None
_session_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / Shutdown"""
    global _agent_loop, _session_manager

    logger.info("=" * 70)
    logger.info("🏨 KYNICOS OS — STARTING UP")
    logger.info("=" * 70)

    settings = Settings()

    # Determinar persona activa
    persona_name = os.getenv("PERSONA", "leo")
    persona = get_persona(persona_name)
    logger.info(f"👤 Persona activa: {persona.name}")

    try:
        # Memoria y sesiones
        memory = Memory(workspace_path="./workspace")
        session_manager = SessionManager(data_dir="./data")
        _session_manager = session_manager
        logger.info("✅ Memory + Sessions OK")

        # LLM Provider (Groq primary → Anthropic fallback)
        from app.cloud.providers import ProviderManager
        from app.agents.concierge_loop import ConciergeAgentLoop

        provider_manager = ProviderManager(settings)
        _agent_loop = ConciergeAgentLoop(settings, provider_manager, persona=persona)
        logger.info(f"✅ ConciergeAgentLoop ({persona.name}) OK")

        # WhatsApp bridge (Twilio) — opcional
        try:
            from app.cloud.whatsapp_bridge import init_whatsapp_bridge
            init_whatsapp_bridge(settings)
        except Exception as e:
            logger.warning(f"WhatsApp bridge no disponible: {e}")

        # Telegram Bot
        logger.info("📱 Iniciando Telegram bot...")
        telegram_task = asyncio.create_task(start_telegram_bot(settings))

        logger.info("=" * 70)
        logger.info(f"🟢 KYNICOS OS ACTIVO — Persona: {persona.name.upper()}")
        logger.info("=" * 70)

        yield

        # Shutdown
        telegram_task.cancel()
        try:
            await telegram_task
        except asyncio.CancelledError:
            pass
        await stop_telegram_bot()
        logger.info("✅ KynicOS shutdown OK")

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise


# ── FastAPI App ──────────────────────────────────────────────
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

# Static files (dashboard)
web_path = Path(__file__).parent.parent / "web"
if web_path.exists():
    app.mount("/static", StaticFiles(directory=web_path), name="static")


# ── Routes ───────────────────────────────────────────────────

@app.get("/")
async def root():
    dashboard_path = Path(__file__).parent.parent / "web" / "index.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return {
        "name": "KynicOS",
        "version": "1.0.0",
        "status": "running",
        "persona": os.getenv("PERSONA", "leo"),
        "docs": "/docs",
    }


@app.get("/api/status")
async def status():
    persona_name = os.getenv("PERSONA", "leo")
    return JSONResponse({
        "status": "ok",
        "version": "1.0.0",
        "persona": persona_name,
        "agent_loop": _agent_loop is not None,
        "llm": "groq (llama-3.3-70b) → anthropic (fallback)",
        "channels": ["telegram", "whatsapp"],
        "skills": ["hvac_triage", "mueve_cancun", "concierge_llm"],
        "deploy_url": "https://nanobot-cloud-zjr0.onrender.com",
    })


@app.get("/api/persona")
async def get_current_persona():
    from app.concierge.persona import get_persona
    persona = get_persona(os.getenv("PERSONA", "leo"))
    return {
        "name": persona.name,
        "tone": persona.tone,
        "language": persona.language,
        "greeting_preview": persona.greeting[:100] + "...",
    }


# WhatsApp webhook (Twilio)
try:
    from app.cloud.whatsapp_bridge import create_whatsapp_routes
    app.include_router(create_whatsapp_routes(), prefix="/api")
    logger.info("✅ WhatsApp webhook registrado en /api/webhook/whatsapp")
except Exception:
    pass

# Dashboard routes
try:
    app.include_router(create_dashboard_routes(), prefix="/api")
except Exception:
    pass


# ── Entry Point ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    settings = Settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
    )
