"""Verificación de doble paso para operaciones elevadas.

Cómo funciona, en lenguaje llano:

1. Se pronuncia la palabra clave del primer paso.
2. El nodo **no ejecuta nada**: envía una sola notificación a Telegram con dos
   botones, Autorizar y Rechazar.
3. Solo si se autoriza, se emite una palabra nueva, efímera y de un solo uso.
4. Esa palabra es la que permite la operación elevada. Caduca sola.

Principios de diseño:

- **Falla cerrado.** Sin palabra de primer paso configurada, no hay flujo. Sin
  segundo paso autorizado, no hay palabra. Nunca se adivina ni se busca la clave
  en otro lado.
- **Una sola notificación.** Si ya existe una solicitud pendiente del mismo
  chat, se reutiliza: no se bombardea al usuario.
- **La palabra no se guarda en claro.** Se almacena su hash; se muestra una vez,
  al emitirse, y después no se puede recuperar.
- **Un solo uso.** Verificada una vez, muere. Reintentar con la misma palabra
  falla.
- **Con caducidad.** La solicitud para autorizar dura 2 minutos; la palabra
  emitida, 5. Pasado el plazo, hay que empezar de nuevo.
- **Con freno anti fuerza bruta.** Tres intentos fallidos bloquean el flujo 15
  minutos.

Esto **no desactiva** ningún control de seguridad existente: agrega una
confirmación humana en dos pasos para operaciones que ya estaban marcadas como
elevadas. Un segundo factor que apaga las protecciones no es un segundo factor,
es una puerta.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Plazos en segundos
TTL_SOLICITUD = 120          # ventana para pulsar Autorizar
VIDA_PALABRA = 300           # vida de la palabra emitida
MAX_INTENTOS = 3             # fallos antes de bloquear
BLOQUEO = 900                # duración del bloqueo tras agotar intentos

PALABRA_PREFIJO = "KALPIXK"


class ErrorDoblePaso(Exception):
    """Fallo del flujo, con mensaje apto para mostrarse al usuario."""


@dataclass
class Solicitud:
    id: str
    chat_id: int
    creada: float
    estado: str = "pendiente"          # pendiente | autorizada | rechazada | expirada
    hash_palabra: str | None = None
    emitida: float | None = None
    usada: bool = False
    motivo: str = ""


@dataclass
class Estado:
    solicitudes: dict[str, Solicitud] = field(default_factory=dict)
    intentos: int = 0
    bloqueado_hasta: float = 0.0
    auditoria: list[dict] = field(default_factory=list)
    candado: threading.Lock = field(default_factory=threading.Lock)


_estado = Estado()


def _ruta_estado():
    """Archivo de estado. En serverless cada petición es un proceso nuevo, así
    que sin persistencia el flujo se rompería entre el paso 1 y el paso 2."""
    from pathlib import Path
    base = Path(os.environ.get("KYNIKOS_ESTADO_DIR", ".kynikos"))
    base.mkdir(parents=True, exist_ok=True)
    return base / "doble_paso.json"


def _persistir() -> None:
    try:
        destino = _ruta_estado()
        datos = {
            "solicitudes": {k: vars(v) for k, v in _estado.solicitudes.items()},
            "intentos": _estado.intentos,
            "bloqueado_hasta": _estado.bloqueado_hasta,
            "auditoria": _estado.auditoria[-200:],
        }
        temporal = destino.with_suffix(".tmp")
        temporal.write_text(json.dumps(datos, ensure_ascii=False))
        os.replace(temporal, destino)
    except Exception:
        pass  # si el disco no es escribible, el flujo sigue en memoria


def _cargar() -> None:
    try:
        crudo = json.loads(_ruta_estado().read_text())
        for clave, valor in (crudo.get("solicitudes") or {}).items():
            _estado.solicitudes[clave] = Solicitud(**valor)
        _estado.intentos = crudo.get("intentos", 0)
        _estado.bloqueado_hasta = crudo.get("bloqueado_hasta", 0.0)
        _estado.auditoria = crudo.get("auditoria", [])
    except Exception:
        pass  # sin archivo previo se arranca limpio


def _ahora() -> float:
    return time.time()


def _sello(momento: float) -> str:
    return datetime.fromtimestamp(momento, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _auditar(evento: str, detalle: str = "") -> None:
    """Bitácora sin valores sensibles: nunca guarda la palabra ni su hash."""
    _estado.auditoria.append({"t": _sello(_ahora()), "evento": evento, "detalle": detalle})
    del _estado.auditoria[:-200]  # ventana acotada


def palabra_primer_paso() -> str:
    """Palabra que inicia el flujo. Se lee del entorno, nunca del código."""
    return os.environ.get("KYNIKOS_PALABRA_1", "").strip()


def configurado() -> bool:
    return bool(palabra_primer_paso())


def _comparar_seguro(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def _generar_palabra() -> str:
    """Palabra legible, difícil de adivinar: KALPIXK-3F9A-C21B."""
    crudo = secrets.token_hex(4).upper()
    return f"{PALABRA_PREFIJO}-{crudo[:4]}-{crudo[4:]}"


def _hash(palabra: str) -> str:
    return hashlib.sha256(palabra.strip().upper().encode()).hexdigest()


def _expirar_vencidas() -> None:
    ahora = _ahora()
    for solicitud in _estado.solicitudes.values():
        if solicitud.estado == "pendiente" and ahora - solicitud.creada > TTL_SOLICITUD:
            solicitud.estado = "expirada"
            _auditar("expirada", solicitud.id)


def detectar_primer_paso(texto: str) -> bool:
    """¿El mensaje es la palabra del primer paso? Sin distinguir mayúsculas."""
    clave = palabra_primer_paso()
    if not clave:
        return False
    return _comparar_seguro(texto.strip().lower(), clave.lower())


def solicitar(chat_id: int) -> tuple[Solicitud, bool]:
    """Crea (o reutiliza) la solicitud de autorización.

    Devuelve (solicitud, es_nueva). Si ya había una pendiente para ese chat, se
    reutiliza y `es_nueva` es False: así el usuario recibe **una sola**
    notificación, no una por intento.
    """
    if not configurado():
        raise ErrorDoblePaso("El primer paso no está configurado en este nodo.")

    with _estado.candado:
        if _ahora() < _estado.bloqueado_hasta:
            restante = int(_estado.bloqueado_hasta - _ahora())
            raise ErrorDoblePaso(f"Flujo bloqueado por intentos fallidos. Espera {restante} s.")
        _expirar_vencidas()
        for solicitud in _estado.solicitudes.values():
            if solicitud.chat_id == chat_id and solicitud.estado == "pendiente":
                return solicitud, False
        solicitud = Solicitud(id=secrets.token_urlsafe(12), chat_id=chat_id, creada=_ahora())
        _estado.solicitudes[solicitud.id] = solicitud
        _auditar("solicitada", solicitud.id)
        _persistir()
        return solicitud, True


def autorizar(id_solicitud: str, chat_id: int) -> tuple[str, float]:
    """Autoriza y emite la palabra. Devuelve (palabra, expira_en_epoch).

    La palabra se devuelve **una sola vez**; después solo queda su hash.
    """
    with _estado.candado:
        solicitud = _estado.solicitudes.get(id_solicitud)
        if not solicitud:
            raise ErrorDoblePaso("Solicitud inexistente o ya consumida.")
        if solicitud.chat_id != chat_id:
            _auditar("rechazada_por_chat", id_solicitud)
            raise ErrorDoblePaso("Esta solicitud no pertenece a este chat.")
        if solicitud.estado != "pendiente":
            raise ErrorDoblePaso(f"La solicitud ya está {solicitud.estado}.")
        if _ahora() - solicitud.creada > TTL_SOLICITUD:
            solicitud.estado = "expirada"
            raise ErrorDoblePaso("La ventana de autorización expiró. Empieza de nuevo.")

        palabra = _generar_palabra()
        solicitud.hash_palabra = _hash(palabra)
        solicitud.estado = "autorizada"
        solicitud.emitida = _ahora()
        _auditar("autorizada", id_solicitud)
        _persistir()
        return palabra, solicitud.emitida + VIDA_PALABRA


def rechazar(id_solicitud: str, chat_id: int) -> None:
    with _estado.candado:
        solicitud = _estado.solicitudes.get(id_solicitud)
        if not solicitud or solicitud.chat_id != chat_id:
            return
        solicitud.estado = "rechazada"
        solicitud.motivo = "rechazo explícito del usuario"
        _auditar("rechazada", id_solicitud)


def verificar(palabra: str) -> bool:
    """Verifica y consume la palabra del segundo paso. Un solo uso."""
    with _estado.candado:
        if _ahora() < _estado.bloqueado_hasta:
            _auditar("verificacion_bloqueada")
            return False

        candidato = _hash(palabra)
        for solicitud in _estado.solicitudes.values():
            if solicitud.estado != "autorizada" or not solicitud.hash_palabra:
                continue
            if solicitud.usada:
                continue
            if solicitud.emitida and _ahora() - solicitud.emitida > VIDA_PALABRA:
                solicitud.estado = "expirada"
                _auditar("palabra_expirada", solicitud.id)
                continue
            if hmac.compare_digest(solicitud.hash_palabra, candidato):
                solicitud.usada = True
                solicitud.estado = "consumida"
                _estado.intentos = 0
                _auditar("verificada", solicitud.id)
                _persistir()
                return True

        _estado.intentos += 1
        _auditar("fallo_verificacion", f"intento {_estado.intentos}")
        if _estado.intentos >= MAX_INTENTOS:
            _estado.bloqueado_hasta = _ahora() + BLOQUEO
            _estado.intentos = 0
            _auditar("bloqueo_activado", f"{BLOQUEO} s")
        _persistir()
        return False


def estado_publico() -> dict:
    """Resumen para diagnóstico, sin datos sensibles."""
    _expirar_vencidas()
    pendientes = [s for s in _estado.solicitudes.values() if s.estado == "pendiente"]
    return {
        "configurado": configurado(),
        "pendientes": len(pendientes),
        "bloqueado": _ahora() < _estado.bloqueado_hasta,
        "ttl_solicitud_s": TTL_SOLICITUD,
        "vida_palabra_s": VIDA_PALABRA,
        "auditoria": _estado.auditoria[-10:],
    }


def reiniciar_para_pruebas() -> None:
    """Solo para pruebas: limpia memoria y archivo de estado."""
    global _estado
    _estado = Estado()
    try:
        _ruta_estado().unlink(missing_ok=True)
    except Exception:
        pass


_cargar()
