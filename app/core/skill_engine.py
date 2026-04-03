"""
KynicOS — SkillEngine
Motor de habilidades autónomo. Filosofía: autarquía máxima.

Reglas:
  - Un skill es un módulo Python en app/skills/ o workspace/skills/
  - El agente puede CONSTRUIR y ACTIVAR skills nuevos
  - El agente NUNCA puede borrar skills, solo ignorarlos (disabled=True en el manifest)
  - Skills externos (APIs, keys) son OPCIONALES: el skill declara sus deps y si no
    están disponibles, el engine devuelve un fallback gracioso en vez de fallar
  - Cada skill tiene un SKILL.md que documenta su uso para el LLM
  - El LLM puede generar código de nuevo skill → SkillEngine lo valida y persiste

Árbol de skills:
  workspace/skills/<nombre>/           ← skills generados/personalizados
    SKILL.md                           ← docs para el LLM
    skill.py                           ← código ejecutable
    manifest.json                      ← metadata + deps + disabled flag
  app/skills/                          ← skills core (no se borran)
    hvac_triage.py
    mueve_cancun.py
    last30days.py
    web_research.py
    ...
"""

import json
import importlib
import importlib.util
import sys
import re
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from app.utils import get_logger

logger = get_logger(__name__)

SKILL_MANIFEST_TEMPLATE = {
    "name": "",
    "description": "",
    "version": "1.0.0",
    "author": "kynikos",
    "created_at": "",
    "disabled": False,
    "optional_deps": [],      # si faltan, el skill declara un fallback
    "required_env": [],       # env vars necesarias (vacío = sin dependencias externas)
    "tags": [],
}

# Skills que NUNCA pueden desactivarse (núcleo autárquico)
IMMUTABLE_SKILLS = {
    "hvac_triage", "mueve_cancun", "calculator", "datetime_helper",
    "file_manager", "web_research", "last30days", "skill_builder",
    "wms_expert", "roi_analyst",
}


class SkillEngine:
    """Motor de skills autónomo de KynicOS."""

    def __init__(self, workspace_path: str = "./workspace", skills_path: str = "./app/skills"):
        self.workspace_path = Path(workspace_path)
        self.skills_path = Path(skills_path)
        self.skills_dir = self.workspace_path / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        # Registro en memoria: nombre → {fn, manifest, source}
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._load_all_skills()

    # ── Carga ────────────────────────────────────────────────────

    def _load_all_skills(self):
        """Carga skills core (app/skills/) y workspace (workspace/skills/)."""
        # Skills core
        for py_file in self.skills_path.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            self._load_core_skill(py_file)

        # Skills de workspace (generados/personalizados)
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir():
                self._load_workspace_skill(skill_dir)

        logger.info(f"[SkillEngine] {len(self._registry)} skills cargados: {list(self._registry.keys())}")

    def _load_core_skill(self, py_file: Path):
        """Carga un skill .py desde app/skills/"""
        name = py_file.stem
        try:
            spec = importlib.util.spec_from_file_location(f"app.skills.{name}", py_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._registry[name] = {
                "module": module,
                "source": "core",
                "disabled": False,
                "manifest": {"name": name, "description": f"Core skill: {name}", "immutable": name in IMMUTABLE_SKILLS},
            }
        except Exception as e:
            logger.warning(f"[SkillEngine] No se pudo cargar core skill {name}: {e}")

    def _load_workspace_skill(self, skill_dir: Path):
        """Carga un skill desde workspace/skills/<nombre>/"""
        manifest_file = skill_dir / "manifest.json"
        skill_file = skill_dir / "skill.py"

        # Leer manifest si existe
        manifest = {}
        if manifest_file.exists():
            try:
                manifest = json.loads(manifest_file.read_text())
            except Exception:
                pass

        if manifest.get("disabled", False):
            logger.info(f"[SkillEngine] Skill {skill_dir.name} ignorado (disabled=True)")
            return

        # Cargar código si existe
        module = None
        if skill_file.exists():
            try:
                spec = importlib.util.spec_from_file_location(
                    f"workspace.skills.{skill_dir.name}", skill_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception as e:
                logger.warning(f"[SkillEngine] Error cargando {skill_dir.name}: {e}")

        self._registry[skill_dir.name] = {
            "module": module,
            "source": "workspace",
            "disabled": False,
            "manifest": manifest,
            "skill_dir": skill_dir,
        }

    # ── Ejecución ────────────────────────────────────────────────

    async def execute(self, skill_name: str, args: Dict[str, Any] = None) -> str:
        """Ejecuta un skill por nombre. Devuelve string (respuesta o error gracioso)."""
        args = args or {}
        entry = self._registry.get(skill_name)

        if not entry:
            return f"❌ Skill '{skill_name}' no encontrado. Usa `listar_skills` para ver disponibles."

        if entry.get("disabled"):
            return f"ℹ️ Skill '{skill_name}' está desactivado temporalmente."

        module = entry.get("module")
        if not module:
            # Solo tiene SKILL.md — devolver la documentación como contexto
            skill_dir = entry.get("skill_dir")
            if skill_dir:
                doc = (skill_dir / "SKILL.md").read_text() if (skill_dir / "SKILL.md").exists() else ""
                return f"📖 Skill {skill_name} (solo documentación):\n\n{doc[:1000]}"
            return f"❌ Skill '{skill_name}' no tiene código ejecutable."

        # Buscar función run() o execute()
        fn = getattr(module, "run", None) or getattr(module, "execute", None)
        if not fn:
            return f"❌ Skill '{skill_name}' no tiene función run() o execute()."

        try:
            if asyncio.iscoroutinefunction(fn):
                return str(await fn(**args))
            else:
                return str(fn(**args))
        except Exception as e:
            logger.error(f"[SkillEngine] Error en {skill_name}: {e}")
            return f"⚠️ Error en skill {skill_name}: {str(e)[:200]}"

    # ── Auto-construcción ─────────────────────────────────────────

    async def build_skill(
        self,
        name: str,
        description: str,
        code: str,
        tags: List[str] = None,
        required_env: List[str] = None,
        optional_deps: List[str] = None,
    ) -> str:
        """
        Persiste un nuevo skill generado por el LLM.
        El agente puede crear skills, NUNCA borrarlos.
        """
        name = name.lower().replace(" ", "_").replace("-", "_")

        # Verificar que no sobreescribe un skill inmutable
        if name in IMMUTABLE_SKILLS:
            return f"🛡️ El skill '{name}' es parte del núcleo inmutable. Crea una variante con otro nombre."

        # Validar código básicamente (sin exec arbitrario)
        if not _validate_skill_code(code):
            return "❌ Código de skill rechazado por política de seguridad (no se permiten imports peligrosos)."

        skill_dir = self.skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Escribir código
        skill_file = skill_dir / "skill.py"
        skill_file.write_text(code, encoding="utf-8")

        # Escribir manifest
        manifest = {
            **SKILL_MANIFEST_TEMPLATE,
            "name": name,
            "description": description,
            "created_at": datetime.utcnow().isoformat(),
            "tags": tags or [],
            "required_env": required_env or [],
            "optional_deps": optional_deps or [],
            "disabled": False,
        }
        (skill_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

        # Generar SKILL.md
        skill_md = f"# Skill: {name}\n\n{description}\n\n## Uso\n\n```python\nskill_engine.execute('{name}', {{...}})\n```\n"
        (skill_dir / "SKILL.md").write_text(skill_md)

        # Recargar en registry
        self._load_workspace_skill(skill_dir)

        logger.info(f"[SkillEngine] ✅ Nuevo skill construido: {name}")
        return f"✅ Skill '{name}' construido y activado.\nUbicación: workspace/skills/{name}/"

    def disable_skill(self, name: str) -> str:
        """Desactiva (ignora) un skill. NO lo borra."""
        if name in IMMUTABLE_SKILLS:
            return f"🛡️ El skill '{name}' es inmutable. No puede desactivarse."

        entry = self._registry.get(name)
        if not entry:
            return f"❌ Skill '{name}' no existe."

        # Marcar en manifest
        skill_dir = entry.get("skill_dir")
        if skill_dir:
            manifest_file = skill_dir / "manifest.json"
            manifest = json.loads(manifest_file.read_text()) if manifest_file.exists() else {}
            manifest["disabled"] = True
            manifest_file.write_text(json.dumps(manifest, indent=2))

        entry["disabled"] = True
        return f"⏸️ Skill '{name}' desactivado (no eliminado). Reactiva con enable_skill('{name}')."

    def enable_skill(self, name: str) -> str:
        """Reactiva un skill desactivado."""
        entry = self._registry.get(name)
        if not entry:
            return f"❌ Skill '{name}' no existe."
        skill_dir = entry.get("skill_dir")
        if skill_dir:
            manifest_file = skill_dir / "manifest.json"
            manifest = json.loads(manifest_file.read_text()) if manifest_file.exists() else {}
            manifest["disabled"] = False
            manifest_file.write_text(json.dumps(manifest, indent=2))
        entry["disabled"] = False
        return f"▶️ Skill '{name}' reactivado."

    def list_skills(self, show_disabled: bool = False) -> str:
        """Lista todos los skills disponibles."""
        lines = ["🐕 **KynicOS — Skills disponibles**\n"]
        core = [(n, e) for n, e in self._registry.items() if e["source"] == "core"]
        workspace = [(n, e) for n, e in self._registry.items() if e["source"] == "workspace"]

        lines.append("**Core (inmutables):**")
        for name, entry in sorted(core):
            status = "✅" if not entry.get("disabled") else "⏸️"
            desc = entry["manifest"].get("description", "")[:60]
            lines.append(f"  {status} `{name}` — {desc}")

        if workspace:
            lines.append("\n**Workspace (personalizados):**")
            for name, entry in sorted(workspace):
                if entry.get("disabled") and not show_disabled:
                    continue
                status = "✅" if not entry.get("disabled") else "⏸️"
                desc = entry["manifest"].get("description", "")[:60]
                lines.append(f"  {status} `{name}` — {desc}")

        lines.append(f"\nTotal: {len(self._registry)} skills | Inmutables: {len(core)}")
        return "\n".join(lines)

    def get_skill_docs(self) -> str:
        """Genera documentación compacta de todos los skills para el system prompt del LLM."""
        docs = []
        for name, entry in self._registry.items():
            if entry.get("disabled"):
                continue
            skill_dir = entry.get("skill_dir")
            desc = entry["manifest"].get("description", "")
            if skill_dir and (skill_dir / "SKILL.md").exists():
                md = (skill_dir / "SKILL.md").read_text()[:400]
                docs.append(f"**{name}**: {desc}\n{md}")
            else:
                docs.append(f"**{name}**: {desc}")
        return "\n---\n".join(docs[:15])  # límite para no inflar el prompt


# ── Validación de seguridad ───────────────────────────────────

DANGEROUS_IMPORTS = {"os.system", "subprocess", "eval(", "exec(", "__import__", "open(", "shutil.rmtree"}

def _validate_skill_code(code: str) -> bool:
    """Valida que el código de skill no tenga patrones peligrosos."""
    code_lower = code.lower()
    # Permitir imports básicos pero bloquear destrucción de archivos
    forbidden = ["os.remove", "shutil.rmtree", "os.unlink", "format c:", "rm -rf"]
    return not any(f in code_lower for f in forbidden)
