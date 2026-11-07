"""KynicOS — Autoconocimiento verificado.

El modelo no debe adivinar que hardware lo ejecuta, que modelo usa ni donde
vive su codigo. Cuando se le pregunto, invento: dijo "mi modelo es Ollama"
(Ollama es el motor, no el modelo), afirmo que no tiene acceso al sistema y
dio una URL de GitHub que no existe.

Este modulo lee los datos del sistema en tiempo de ejecucion y arma un bloque
que se inyecta en el system prompt, de modo que responda con hechos.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
REPO = "https://github.com/JULIANJUAREZMX01/KynicOS"
AUTOR = "Julian Juarez Alvarado (@JAJA.DEV), UNT Tecnologias Computacionales Cancun"


def _git(args: list[str], defecto: str = "-") -> str:
    """Lee git sin romper si no esta o si el repo no es valido."""
    try:
        r = subprocess.run(
            ["git", "-C", str(RAIZ), *args],
            capture_output=True, text=True, timeout=5,
        )
        return (r.stdout or "").strip() or defecto
    except Exception:
        return defecto


def _ram_gb() -> str:
    """RAM total sin depender de psutil.

    En la PC del jefe /info decia "desconocida RAM" porque psutil no esta en el
    entorno del nodo. Se lee del sistema: GlobalMemoryStatusEx en Windows,
    /proc/meminfo en Linux.
    """
    try:
        import psutil
        return f"{psutil.virtual_memory().total / 1024 ** 3:.1f} GB"
    except Exception:
        pass
    try:
        if os.name == "nt":
            import ctypes

            class _Memoria(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            m = _Memoria()
            m.dwLength = ctypes.sizeof(_Memoria)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                return f"{m.ullTotalPhys / 1024 ** 3:.1f} GB"
        else:
            with open("/proc/meminfo", encoding="utf-8") as f:
                for linea in f:
                    if linea.startswith("MemTotal:"):
                        kb = int(linea.split()[1])
                        return f"{kb / 1024 ** 2:.1f} GB"
    except Exception:
        pass
    return "desconocida"

def _hay(clave: str) -> bool:
    return bool(os.getenv(clave, "").strip())


def datos() -> dict:
    """Datos verificados del nodo. Nada inferido."""
    proveedores = []
    if _hay("GROQ_API_KEY"):
        proveedores.append("Groq")
    if _hay("ANTHROPIC_API_KEY"):
        proveedores.append("Anthropic")
    proveedores.append("Ollama local (ultimo recurso)")

    canales = ["Telegram (polling)"]
    if _hay("TWILIO_ACCOUNT_SID") and _hay("TWILIO_AUTH_TOKEN"):
        canales.append("WhatsApp (Twilio)")
    else:
        canales.append("WhatsApp desactivado (sin credenciales Twilio)")

    return {
        "modelo": os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        "contexto": os.getenv("OLLAMA_NUM_CTX", "4096"),
        "salida_max": os.getenv("MAX_TOKENS_SALIDA", "768"),
        "motor": os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
        "proveedores": proveedores,
        "canales": canales,
        "python": platform.python_version(),
        "version_python_completa": sys.version.split()[0],
        "so": f"{platform.system()} {platform.release()}",
        "arquitectura_cpu": platform.machine(),
        "nucleos": os.cpu_count() or 0,
        "ram": _ram_gb(),
        "commit": _git(["rev-parse", "--short", "HEAD"]),
        "commit_fecha": _git(["log", "-1", "--format=%cd", "--date=short"]),
        "rama": _git(["rev-parse", "--abbrev-ref", "HEAD"]),
        "repo": REPO,
        "autor": AUTOR,
        "ruta": str(RAIZ),
        "skills": ["hvac_triage", "mueve_cancun"],
    }


def bloque_sistema() -> str:
    """Version CORTA para el system prompt.

    La ficha completa (/info) son 15 lineas; en el prompt cuesta ~900 tokens de
    los 4096 disponibles en la maquina del jefe y deja al historial sin aire.
    Aqui van solo los datos que evitan una alucinacion.

    Las claves de datos() son planas: 'modelo' es texto, no un diccionario.
    Se comprobo: asumir lo contrario lanzaba KeyError, el except devolvia "" y
    el bot se quedaba sin ficha y volvia a inventar.
    """
    try:
        d = datos()
        return (
            "\n\n== DATOS VERIFICADOS DE TI (no inventar) ==\n"
            f"- Eres {d.get('nombre', 'KYNIKOS')}, asistente operativo de {d['autor']}.\n"
            f"- Modelo: {d['modelo']} por Ollama (Ollama es el motor). Contexto {d['contexto']} tokens, salida {d['salida_max']}.\n"
            f"- Stack: Python {d['python']}, FastAPI, python-telegram-bot. SO: {d['so']}.\n"
            f"- Codigo: {d['repo']} rama {d['rama']}, commit {d['commit']}.\n"
            "- Si te preguntan un dato tecnico que no este aqui, di que no lo tienes "
            "verificado y sugiere /info. Nunca inventes URLs, versiones ni repositorios.\n"
        )
    except Exception:
        # Nunca devolver vacio: sin ficha el modelo rellena el hueco inventando.
        return (
            "\n\n== DATOS VERIFICADOS DE TI ==\n"
            "- Si no tienes un dato tecnico verificado, dilo. Nunca inventes URLs, "
            "versiones ni repositorios. Puedes remitir a /info para la ficha real.\n"
        )

def texto_para_usuario() -> str:
    """Version legible del bloque, para el comando /info."""
    d = datos()
    lineas = [
        "<b>KYNIKOS · ficha tecnica</b>",
        "",
        f"<b>Quien soy</b>: nodo primario de {d['autor']}",
        f"<b>Modelo</b>: <code>{d['modelo']}</code> via Ollama (motor en {d['motor']})",
        f"<b>Contexto</b>: {d['contexto']} tokens · salida {d['salida_max']}",
        "",
        f"<b>Stack</b>: Python {d['python']} · FastAPI · python-telegram-bot · loguru",
        f"<b>Maquina</b>: {d['so']} · {d['nucleos']} nucleos · {d['ram']} RAM",
        f"<b>Proveedores</b>: {', '.join(d['proveedores'])}",
        f"<b>Canales</b>: {', '.join(d['canales'])}",
        f"<b>Skills</b>: {', '.join(d['skills'])}",
        "",
        f"<b>Repositorio</b>: {d['repo']}",
        f"<b>Version</b>: rama <code>{d['rama']}</code>, commit <code>{d['commit']}</code> del {d['commit_fecha']}",
        f"<b>Instalado en</b>: <code>{d['ruta']}</code>",
    ]
    return "\n".join(lineas)
