"""
KynicOS — SkillEngine
Motor de habilidades autónomo. Filosofía: autarquía máxima.
"""

import ast
import asyncio
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app.utils import get_logger

logger = get_logger(__name__)

SKILL_MANIFEST_TEMPLATE = {
    "name": "",
    "description": "",
    "version": "1.0.0",
    "author": "kynikos",
    "created_at": "",
    "disabled": False,
    "optional_deps": [],
    "required_env": [],
    "tags": [],
}

# These names are the immutable core skills currently shipped in app/skills.
IMMUTABLE_SKILLS = {
    "hvac_triage",
    "mueve_cancun",
    "last30days",
    "memory_manager",
    "skill_builder",
    "web_research",
}


class SkillEngine:
    """Motor de skills autónomo de KynicOS."""

    def __init__(self, workspace_path: str = "./workspace", skills_path: str = "./app/skills"):
        self.workspace_path = Path(workspace_path)
        self.skills_path = Path(skills_path)
        self.skills_dir = self.workspace_path / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._load_all_skills()

    def _load_all_skills(self):
        """Carga skills core y workspace."""
        for py_file in self.skills_path.glob("*.py"):
            if not py_file.name.startswith("_"):
                self._load_core_skill(py_file)
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir():
                self._load_workspace_skill(skill_dir)
        logger.info(f"[SkillEngine] {len(self._registry)} skills cargados: {list(self._registry.keys())}")

    def _load_core_skill(self, py_file: Path):
        name = py_file.stem
        try:
            spec = importlib.util.spec_from_file_location(f"app.skills.{name}", py_file)
            if not spec or not spec.loader:
                raise ImportError(f"No loader available for {py_file}")
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
        manifest_file = skill_dir / "manifest.json"
        skill_file = skill_dir / "skill.py"
        manifest = {}
        if manifest_file.exists():
            try:
                manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"[SkillEngine] Manifest inválido en {skill_dir.name}: {e}")
        if manifest.get("disabled", False):
            logger.info(f"[SkillEngine] Skill {skill_dir.name} ignorado (disabled=True)")
            return

        module = None
        if skill_file.exists():
            try:
                spec = importlib.util.spec_from_file_location(f"workspace.skills.{skill_dir.name}", skill_file)
                if not spec or not spec.loader:
                    raise ImportError(f"No loader available for {skill_file}")
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

    async def execute(self, skill_name: str, args: Dict[str, Any] = None) -> str:
        args = args or {}
        entry = self._registry.get(skill_name)
        if not entry:
            return f"❌ Skill '{skill_name}' no encontrado. Usa `listar_skills` para ver disponibles."
        if entry.get("disabled"):
            return f"ℹ️ Skill '{skill_name}' está desactivado temporalmente."
        module = entry.get("module")
        if not module:
            skill_dir = entry.get("skill_dir")
            if skill_dir:
                doc = (skill_dir / "SKILL.md").read_text(encoding="utf-8") if (skill_dir / "SKILL.md").exists() else ""
                return f"📖 Skill {skill_name} (solo documentación):\n\n{doc[:1000]}"
            return f"❌ Skill '{skill_name}' no tiene código ejecutable."
