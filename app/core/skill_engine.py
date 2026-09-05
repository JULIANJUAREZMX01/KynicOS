"""
KynicOS — SkillEngine
Motor de habilidades autónomo. Filosofía: autarquía máxima.
"""

import ast
import asyncio
import importlib.util
import json
import re
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

# These are the core skills currently shipped in app/skills.
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
        fn = getattr(module, "run", None) or getattr(module, "execute", None)
        if not fn:
            return f"❌ Skill '{skill_name}' no tiene función run() o execute()."
        try:
            if asyncio.iscoroutinefunction(fn):
                return str(await fn(**args))
            return str(fn(**args))
        except Exception as e:
            logger.error(f"[SkillEngine] Error en {skill_name}: {e}")
            return f"⚠️ Error en skill {skill_name}: {str(e)[:200]}"

    async def build_skill(
        self,
        name: str,
        description: str,
        code: str,
        tags: List[str] = None,
        required_env: List[str] = None,
        optional_deps: List[str] = None,
    ) -> str:
        """Persist a generated skill only after syntax/security validation."""
        name = _normalize_skill_name(name)
        if not name:
            return "❌ Nombre de skill inválido."
        if name in IMMUTABLE_SKILLS:
            return f"🛡️ El skill '{name}' es parte del núcleo inmutable. Crea una variante con otro nombre."
        if not _validate_skill_code(code):
            return "❌ Código de skill rechazado por política de seguridad."

        skill_dir = self.skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "skill.py").write_text(code, encoding="utf-8")
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
        (skill_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        (skill_dir / "SKILL.md").write_text(
            f"# Skill: {name}\n\n{description}\n\n## Uso\n\n```python\nskill_engine.execute('{name}', {{...}})\n```\n",
            encoding="utf-8",
        )
        self._load_workspace_skill(skill_dir)
        logger.info(f"[SkillEngine] ✅ Nuevo skill construido: {name}")
        return f"✅ Skill '{name}' construido y activado.\nUbicación: workspace/skills/{name}/"

    def disable_skill(self, name: str) -> str:
        if name in IMMUTABLE_SKILLS:
            return f"🛡️ El skill '{name}' es inmutable. No puede desactivarse."
        entry = self._registry.get(name)
        if not entry:
            return f"❌ Skill '{name}' no existe."
        skill_dir = entry.get("skill_dir")
        if skill_dir:
            manifest_file = skill_dir / "manifest.json"
            manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}
            manifest["disabled"] = True
            manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        entry["disabled"] = True
        return f"⏸️ Skill '{name}' desactivado (no eliminado). Reactiva con enable_skill('{name}')."

    def enable_skill(self, name: str) -> str:
        entry = self._registry.get(name)
        if not entry:
            return f"❌ Skill '{name}' no existe."
        skill_dir = entry.get("skill_dir")
        if skill_dir:
            manifest_file = skill_dir / "manifest.json"
            manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}
            manifest["disabled"] = False
            manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        entry["disabled"] = False
        return f"▶️ Skill '{name}' reactivado."

    def list_skills(self, show_disabled: bool = False) -> str:
        lines = ["🐕 **KynicOS — Skills disponibles**\n", "**Core (inmutables):**"]
        core = [(n, e) for n, e in self._registry.items() if e["source"] == "core"]
        workspace = [(n, e) for n, e in self._registry.items() if e["source"] == "workspace"]
        for name, entry in sorted(core):
            status = "✅" if not entry.get("disabled") else "⏸️"
            lines.append(f"  {status} `{name}` — {entry['manifest'].get('description', '')[:60]}")
        if workspace:
            lines.append("\n**Workspace (personalizados):**")
            for name, entry in sorted(workspace):
                if entry.get("disabled") and not show_disabled:
                    continue
                status = "✅" if not entry.get("disabled") else "⏸️"
                lines.append(f"  {status} `{name}` — {entry['manifest'].get('description', '')[:60]}")
        lines.append(f"\nTotal: {len(self._registry)} skills | Inmutables: {len(core)}")
        return "\n".join(lines)

    def get_skill_docs(self) -> str:
        docs = []
        for name, entry in self._registry.items():
            if entry.get("disabled"):
                continue
            skill_dir = entry.get("skill_dir")
            desc = entry["manifest"].get("description", "")
            if skill_dir and (skill_dir / "SKILL.md").exists():
                md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")[:400]
                docs.append(f"**{name}**: {desc}\n{md}")
            else:
                docs.append(f"**{name}**: {desc}")
        return "\n---\n".join(docs[:15])


# ── Validación de seguridad ───────────────────────────────────

DANGEROUS_IMPORTS = {
    "os", "subprocess", "shutil", "socket", "ctypes", "multiprocessing",
    "pathlib", "importlib", "builtins",
}
DANGEROUS_CALLS = {"eval", "exec", "compile", "__import__", "system", "popen", "remove", "unlink", "rmtree"}
DANGEROUS_ATTRIBUTES = {"__globals__", "__builtins__", "__subclasses__", "__bases__", "__mro__"}


def _normalize_skill_name(name: str) -> str:
    """Return a safe Python-like directory/module name."""
    normalized = re.sub(r"[^a-zA-Z0-9_]", "_", (name or "").strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized or normalized[0].isdigit() or normalized in {"none", "true", "false"}:
        return ""
    return normalized


def _validate_skill_code(code: str) -> bool:
    """Validate generated Python structurally rather than with bypassable strings."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            root = node.names[0].name.split(".")[0] if isinstance(node, ast.Import) else (node.module or "").split(".")[0]
            if root in DANGEROUS_IMPORTS:
                return False
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_CALLS:
                return False
            if isinstance(node.func, ast.Attribute) and node.func.attr in DANGEROUS_CALLS:
                return False
        elif isinstance(node, ast.Attribute) and node.attr in DANGEROUS_ATTRIBUTES:
            return False
    return True
