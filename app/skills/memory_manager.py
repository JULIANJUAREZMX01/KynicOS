"""
KynicOS — Skill: Memory Manager
El agente escribe y lee su propia memoria persistente.
Autárquico: solo archivos locales, sin DB externa.

Estructura:
  workspace/memory/MEMORY.md     ← memoria principal (human-readable)
  workspace/memory/entities/     ← entidades estructuradas (JSON)
  workspace/memory/learned/      ← skills aprendidos (context persistido)
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

MEMORY_ROOT = Path("workspace/memory")
MEMORY_FILE = MEMORY_ROOT / "MEMORY.md"
ENTITIES_DIR = MEMORY_ROOT / "entities"
LEARNED_DIR = MEMORY_ROOT / "learned"


def _ensure_dirs():
    MEMORY_ROOT.mkdir(parents=True, exist_ok=True)
    ENTITIES_DIR.mkdir(exist_ok=True)
    LEARNED_DIR.mkdir(exist_ok=True)


def remember(key: str, value: str, category: str = "general") -> str:
    """Guarda un hecho en la memoria persistente."""
    _ensure_dirs()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    entry = f"\n### [{now}] [{category.upper()}] {key}\n{value}\n---"

    current = MEMORY_FILE.read_text(encoding="utf-8") if MEMORY_FILE.exists() else "# KYNIKOS Memory\n"
    MEMORY_FILE.write_text(current + entry, encoding="utf-8")
    return f"✅ Memorizado: [{category}] {key}"


def recall(query: str, max_results: int = 5) -> str:
    """Busca en la memoria. Sin vector DB: búsqueda simple por keywords."""
    _ensure_dirs()
    if not MEMORY_FILE.exists():
        return "📭 Memoria vacía."

    lines = MEMORY_FILE.read_text(encoding="utf-8").splitlines()
    query_lower = query.lower()
    matches = []
    current_entry = []

    for line in lines:
        if line.startswith("###"):
            if current_entry:
                entry_text = "\n".join(current_entry)
                if query_lower in entry_text.lower():
                    matches.append(entry_text)
            current_entry = [line]
        else:
            current_entry.append(line)

    if current_entry:
        entry_text = "\n".join(current_entry)
        if query_lower in entry_text.lower():
            matches.append(entry_text)

    if not matches:
        return f"🔍 Sin resultados para '{query}' en memoria."

    result = f"🧠 **Memoria — '{query}':**\n\n"
    for m in matches[-max_results:]:
        result += m.strip() + "\n\n"
    return result.strip()


def save_entity(entity_type: str, entity_id: str, data: Dict[str, Any]) -> str:
    """Guarda una entidad estructurada (hotel, huésped, ticket, etc.)."""
    _ensure_dirs()
    entity_dir = ENTITIES_DIR / entity_type
    entity_dir.mkdir(exist_ok=True)
    entity_file = entity_dir / f"{entity_id}.json"
    data["_updated_at"] = datetime.utcnow().isoformat()
    entity_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return f"✅ Entidad guardada: {entity_type}/{entity_id}"


def get_entity(entity_type: str, entity_id: str) -> Optional[Dict]:
    """Recupera una entidad estructurada."""
    entity_file = ENTITIES_DIR / entity_type / f"{entity_id}.json"
    if not entity_file.exists():
        return None
    return json.loads(entity_file.read_text(encoding="utf-8"))


def list_entities(entity_type: str) -> List[str]:
    """Lista IDs de entidades de un tipo."""
    entity_dir = ENTITIES_DIR / entity_type
    if not entity_dir.exists():
        return []
    return [f.stem for f in entity_dir.glob("*.json")]


def run(action: str = "recall", key: str = "", value: str = "", category: str = "general") -> str:
    """
    Función principal:
    - action='remember': guarda key/value
    - action='recall': busca por key
    - action='list': muestra últimas 10 entradas
    """
    if action == "remember":
        if not key or not value:
            return "❌ Se requiere key y value para recordar."
        return remember(key, value, category)
    elif action == "recall":
        if not key:
            return "❌ Se requiere key para buscar."
        return recall(key)
    elif action == "list":
        if not MEMORY_FILE.exists():
            return "📭 Memoria vacía."
        lines = MEMORY_FILE.read_text(encoding="utf-8").splitlines()
        entries = [l for l in lines if l.startswith("###")][-10:]
        return "🧠 **Últimas memorias:**\n" + "\n".join(entries)
    else:
        return f"❌ Acción desconocida: {action}. Usa: remember | recall | list"
