"""Punto de entrada serverless (Vercel) para KYNIKOS.

Expone el canal de Telegram por webhook sin arrancar el bot de polling.
El resto de la app (dashboard, MCP) sigue disponible en el despliegue de VPS.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.channels.telegram_webhook import router as telegram_router
from app.channels.web_chat import router as web_router

app = FastAPI(title="KYNIKOS bot propio", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(telegram_router)
app.include_router(web_router)


@app.get("/api")
def raiz() -> dict:
    return {"servicio": "kynikos", "estado": "en linea", "canal": "telegram-webhook"}
