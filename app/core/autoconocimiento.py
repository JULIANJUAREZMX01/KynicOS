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
    try:
        import psutil
        return f"{psutil.virtual_memory().total / 1024 ** 3:.1f} GB"
    except Exception:
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
    """Bloque compacto para el system prompt.

    Se mantiene corto a proposito: el nodo trabaja con 4096 tokens de contexto
    y este texto compite con la conversacion.
    """
    d = datos()
    return (
        "\n\n== TU CONFIGURACION REAL (verificada, no inventar) ==\n"
        f"- Eres KYNICOS, el nodo primario de {d['autor']}.\n"
        f"- Modelo de lenguaje: {d['modelo']} por Ollama (Ollama es el motor, "
        f"no el modelo). Contexto: {d['contexto']} tokens. Salida maxima: {d['salida_max']}.\n"
        f"- Stack: Python {d['python']}, FastAPI, python-telegram-bot, loguru.\n"
        f"- Sistema: {d['so']}, {d['nucleos']} nucleos, RAM {d['ram']}.\n"
        f"- Codigo: {d['repo']} (rama {d['rama']}, commit {d['commit']}), en {d['ruta']}.\n"
        f"- Proveedores LLM disponibles en orden: {', '.join(d['proveedores'])}.\n"
        f"- Canales: {'; '.join(d['canales'])}.\n"
        f"- Skills locales: {', '.join(d['skills'])}.\n"
        "- SI tienes acceso al sistema donde corres: puedes leer archivos, ver "
        "procesos y ejecutar skills. No digas lo contrario.\n"
        "- Si te preguntan algo tecnico de ti mismo que no este aqui, di que no "
        "lo tienes verificado; nunca inventes URLs, versiones ni repositorios.\n"
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
