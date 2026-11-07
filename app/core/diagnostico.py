"""KynicOS — Diagnóstico a partir de los registros del nodo.

Toda la noche del 6 de noviembre el diagnóstico lo hizo una persona leyendo
pantallas. Los fallos que aparecieron están todos en el registro y todos tienen
una causa reconocible: dependencia ausente, puerto ocupado, doble instancia,
token rechazado, Ollama caído.

Este módulo lee los registros y devuelve en qué falló y qué hacer. No usa el
modelo: un diagnóstico determinista no puede alucinar.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# (patrón, título, causa, remedio)
PATRONES = [
    (
        r"ModuleNotFoundError: No module named '([\w\.]+)'",
        "Falta una dependencia",
        "el entorno no tiene el paquete {0}",
        ".\\nodo\\kynikos.ps1 reparar",
    ),
    (
        r"Address already in use|WinError 10048",
        "Puerto 8000 ocupado",
        "otra instancia sigue escuchando",
        ".\\nodo\\kynikos.ps1 reiniciar",
    ),
    (
        r"Conflict: terminated by other getUpdates|409",
        "Doble instancia",
        "dos procesos piden mensajes al mismo token; Telegram corta a uno",
        ".\\nodo\\kynikos.ps1 reiniciar",
    ),
    (
        r"Unauthorized|InvalidToken|401",
        "Token rechazado",
        "el token del .env no es valido",
        ".\\nodo\\kynikos.ps1 configurar  (token nuevo de @BotFather)",
    ),
    (
        r"connection refused.*11434|11434.*refused|ollama: command not found",
        "Ollama no responde",
        "el motor del modelo no esta levantado",
        "ollama serve   y comprueba: ollama list",
    ),
    (
        r"out of memory|insufficient memory|CUDA error",
        "Sin memoria para el modelo",
        "el modelo no cabe con ese contexto",
        "baja OLLAMA_NUM_CTX o usa un modelo menor",
    ),
    (
        r"UnicodeEncodeError|charmap",
        "Problema de codificación",
        "un emoji no se puede escribir en la consola de Windows",
        ".\\nodo\\kynikos.ps1 reiniciar  (el nodo fija UTF-8 al arrancar)",
    ),
    (
        r"SyntaxError|ParserError",
        "Error de sintaxis",
        "un archivo se corrompio al copiarlo o pegarlo",
        "git checkout -- nodo/kynikos.ps1  y vuelve a arrancar",
    ),
]

REGISTROS = ("kynikos.err.log", "kynikos.log")


def _leer(nombre: str, lineas: int = 400) -> str:
    ruta = RAIZ / nombre
    if not ruta.exists():
        return ""
    try:
        with ruta.open("r", encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-lineas:])
    except Exception:
        return ""


def hallazgos(texto: str) -> list[dict]:
    """Patrones reconocidos, sin repetir el mismo título."""
    vistos = {}
    for patron, titulo, causa, remedio in PATRONES:
        m = re.search(patron, texto, re.IGNORECASE)
        if m and titulo not in vistos:
            detalle = causa
            if m.groups():
                try:
                    detalle = causa.format(m.group(1))
                except Exception:
                    pass
            vistos[titulo] = {"titulo": titulo, "causa": detalle, "remedio": remedio}
    return list(vistos.values())


def diagnosticar() -> dict:
    """Informe crudo para quien lo consuma (bot, consola o pruebas)."""
    partes = {n: _leer(n) for n in REGISTROS}
    todo = "\n".join(partes.values())
    return {
        "registros": {n: len(t.splitlines()) for n, t in partes.items()},
        "hallazgos": hallazgos(todo),
        "ultimas": [l for l in todo.splitlines() if l.strip()][-8:],
        "vacio": not todo.strip(),
    }


def texto_para_usuario() -> str:
    """Informe en HTML para Telegram. Determinista: no llama al modelo."""
    d = diagnosticar()
    lineas = ["<b>KYNIKOS · diagnóstico</b>", ""]

    if d["vacio"]:
        return ("<b>KYNIKOS · diagnóstico</b>\n\n"
                "No encuentro registros todavía. Si el nodo no arranca, ejecuta:\n"
                "<pre>.\\nodo\\kynikos.ps1 auto</pre>")

    reg = " · ".join(f"{n}: {c} líneas" for n, c in d["registros"].items() if c)
    lineas.append(f"Leído: {reg}")

    if d["hallazgos"]:
        lineas.append("")
        lineas.append("<b>Lo que encontré</b>")
        for h in d["hallazgos"]:
            lineas.append(f"• <b>{h['titulo']}</b>: {h['causa']}")
            lineas.append(f"  → <code>{h['remedio']}</code>")
    else:
        lineas.append("")
        lineas.append("Sin fallos conocidos en el registro. Últimas líneas:")
        bloque = "\n".join(d["ultimas"][-6:])
        lineas.append(f"<pre>{bloque[:1200]}</pre>")

    return "\n".join(lineas)
