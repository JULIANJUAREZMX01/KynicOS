"""MCP Server integration for Claude Code CLI"""

# This module provides MCP Server capabilities for integration with Claude Code
# allowing direct interaction with Nanobot from Claude CLI

"""
MCP Server Tools:
- read_nanobot_memory(key: str) -> Get memory content
- add_nanobot_skill(name: str, content: str) -> Create/update skill
- list_sessions() -> List conversations
- send_telegram_message(user_id: str, msg: str) -> Send message
- get_nanobot_status() -> Health check

Usage:
    mcp connect app/cloud/mcp_server.py
"""

from pathlib import Path
import json
from typing import Any


def read_nanobot_memory(key: str = "profile") -> dict:
    """Read Nanobot memory by key"""
    memory_file = Path("./workspace/memory/MEMORY.md")
    if memory_file.exists():
        return {"content": memory_file.read_text(encoding="utf-8")}
    return {"error": "Memory not found"}


def add_nanobot_skill(name: str, content: str) -> dict:
    """Add or update a skill"""
    skill_dir = Path(f"./workspace/skills/{name}")
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    
    return {"success": True, "skill": name}


def list_sessions(limit: int = 50) -> dict:
    """List recent sessions"""
    sessions_dir = Path("./data/sessions")
    if not sessions_dir.exists():
        return {"sessions": []}
    
    sessions = []
    for session_file in sorted(
        sessions_dir.glob("*.jsonl"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )[:limit]:
        with open(session_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    sessions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    return {"sessions": sessions}


def send_telegram_message(user_id: str, msg: str) -> dict:
    """Send message via Telegram (requires bot to be running)"""
    # TODO: Implement via telegram.ext Application
    return {"sent": False, "reason": "Not implemented yet"}


def get_nanobot_status() -> dict:
    """Get current Nanobot status"""
    return {
        "status": "running",
        "version": "0.1.0",
        "environment": "cloud",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat()
    }

# ---------------------------------------------------------------------------
# Herramientas del nodo primario (ADR-021)
# Añadidas sin tocar las existentes: el servidor MCP sigue siendo compatible.
# ---------------------------------------------------------------------------

def buscar_web(consulta: str, limite: int = 5) -> dict:
    """Busca en la web sin API key y devuelve título y enlace."""
    import httpx
    from bs4 import BeautifulSoup  # opcional; si falta, se devuelve crudo

    try:
        with httpx.Client(timeout=20, follow_redirects=True) as cliente:
            r = cliente.get(
                "https://html.duckduckgo.com/html/",
                params={"q": consulta},
                headers={"User-Agent": "Mozilla/5.0 (KYNIKOS nodo)"},
            )
        soup = BeautifulSoup(r.text, "html.parser")
        resultados = []
        for bloque in soup.select(".result")[: max(1, min(limite, 10))]:
            enlace = bloque.select_one(".result__a")
            extracto = bloque.select_one(".result__snippet")
            if not enlace:
                continue
            resultados.append({
                "titulo": enlace.get_text(" ", strip=True),
                "url": enlace.get("href", ""),
                "extracto": (extracto.get_text(" ", strip=True) if extracto else "")[:280],
            })
        return {"consulta": consulta, "resultados": resultados, "total": len(resultados)}
    except Exception as error:  # noqa: BLE001
        return {"consulta": consulta, "error": f"{type(error).__name__}: {error}"}


def leer_archivo(ruta: str, maximo_bytes: int = 20000) -> dict:
    """Lee un archivo del nodo con límite de tamaño y sin salir del workspace."""
    from pathlib import Path

    base = Path.cwd().resolve()
    destino = (base / ruta).resolve() if not Path(ruta).is_absolute() else Path(ruta).resolve()
    if base not in destino.parents and destino != base:
        return {"error": "ruta fuera del workspace"}
    if not destino.exists() or not destino.is_file():
        return {"error": "no existe o no es archivo", "ruta": str(destino)}
    datos = destino.read_bytes()[:maximo_bytes]
    return {"ruta": str(destino.relative_to(base)), "bytes": len(datos),
            "contenido": datos.decode("utf-8", errors="replace")}


def ejecutar_comando(comando: str, timeout: int = 30) -> dict:
    """Ejecuta un comando en el nodo usando el ejecutor endurecido del proyecto."""
    try:
        from app.core.tools import ToolExecutor

        ejecutor = ToolExecutor(agent_context={"modo": "nodo", "overdrive": False})
        import asyncio
        return asyncio.run(ejecutor.execute_shell(comando=comando, timeout=timeout))
    except Exception as error:  # noqa: BLE001
        return {"error": f"{type(error).__name__}: {error}"}


def listar_mcp() -> dict:
    """Lista los servidores MCP configurados para el nodo."""
    import json
    from pathlib import Path

    ruta = Path(__file__).resolve().parents[2] / "mcp-servers.json"
    if not ruta.exists():
        return {"servidores": [], "nota": "sin mcp-servers.json"}
    try:
        datos = json.loads(ruta.read_text())
        return {"servidores": datos.get("servidores", []), "total": len(datos.get("servidores", []))}
    except Exception as error:  # noqa: BLE001
        return {"error": f"{type(error).__name__}: {error}"}

