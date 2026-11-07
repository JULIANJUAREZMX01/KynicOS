"""Canal web: la consola PWA habla con el nodo por HTTP.

Complementa el canal de Telegram con el mismo cerebro (persona KYNIKOS y cadena
de proveedores). Pensado para correr en la PC del jefe: sin coste por token
cuando el modelo es local.
"""

from __future__ import annotations

import secrets

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Header, Query, Depends
from pydantic import BaseModel

from app.config.schema import Settings
from app.concierge.persona import get_persona

logger = logging.getLogger(__name__)
router = APIRouter()

_settings: Settings | None = None
_historial: list[dict[str, str]] = []
MAX_TURNOS = 16


class Peticion(BaseModel):
    mensaje: str
    reiniciar: bool = False


def _s() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def _token_configurado() -> str:
    try:
        from app.config import Settings
        return (getattr(Settings(), "kynikos_api_token", "") or "").strip()
    except Exception:
        return ""


async def requiere_token_web(
    x_kynikos_token: str = Header(default=""),
    token: str = Query(default=""),
):
    """El chat web exige el token cuando el nodo esta configurado.

    Al abrir el tunel, /api/chat quedaba accesible a cualquiera: un desconocido
    podria conversar con el bot y gastar el modelo. Si no hay token configurado
    se permite (nodo recien instalado, solo local); si lo hay, obliga.
    """
    esperado = _token_configurado()
    if not esperado:
        return True
    recibido = (x_kynikos_token or token or "").strip()
    if not recibido or not secrets.compare_digest(recibido, esperado):
        raise HTTPException(status_code=401, detail="token requerido")
    return True


@router.post("/api/chat", dependencies=[Depends(requiere_token_web)])
async def chat(peticion: Peticion) -> dict[str, Any]:
    """Responde con el modelo configurado (local primero)."""
    global _historial
    texto = (peticion.mensaje or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="mensaje vacío")
    if peticion.reiniciar:
        _historial = []

    try:
        from app.cloud.providers import ProviderManager

        s = _s()
        persona = get_persona(s.persona)
        _historial.append({"role": "user", "content": texto})
        mensajes = [{"role": "system", "content": persona.system_prompt}] + _historial[-MAX_TURNOS:]

        manager = ProviderManager(s)
        resultado = await manager.call(mensajes, max_tokens=getattr(s, "max_tokens_salida", 768), temperature=0.6)
        respuesta = (resultado or {}).get("content") or "Sin respuesta del modelo."
        _historial.append({"role": "assistant", "content": respuesta})
        return {
            "respuesta": respuesta,
            "persona": persona.name,
            "proveedor": (resultado or {}).get("provider", "desconocido"),
            "turnos": len(_historial),
        }
    except Exception as error:  # noqa: BLE001
        logger.exception("fallo en canal web")
        return {"error": f"{type(error).__name__}: {error}", "pista": "¿Ollama encendido y el modelo descargado?"}


@router.get("/api/chat/historial", dependencies=[Depends(requiere_token_web)])
async def historial() -> dict[str, Any]:
    return {"turnos": len(_historial), "mensajes": _historial[-MAX_TURNOS:]}


@router.post("/api/chat/reiniciar", dependencies=[Depends(requiere_token_web)])
async def reiniciar() -> dict[str, Any]:
    global _historial
    _historial = []
    return {"ok": True, "mensajes": 0}
