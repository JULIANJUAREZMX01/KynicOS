"""
KynicOS — Skill: SkillBuilder (Meta-skill)
El agente puede construir, investigar y clonar skills nuevos.
Filosofía: el nanobot se expande a sí mismo sin pedir permiso a nadie.

Acciones:
  - research: investiga cómo implementar algo (web_research + last30days)
  - build: genera código de skill y lo persiste via SkillEngine
  - clone: clona la lógica de un skill existente con un nombre nuevo
  - list: lista todos los skills y su estado
"""

import asyncio
from typing import Optional
from app.utils import get_logger

logger = get_logger(__name__)


async def _research_implementation(topic: str) -> str:
    """Investiga antes de construir."""
    from app.skills.web_research import run as web_run
    from app.skills.last30days import run as trends_run
    web = await web_run(query=f"{topic} python implementation", source="github")
    trends = await trends_run(topic=topic, source="github_trending")
    return f"**Investigación: {topic}**\n\n{web[:800]}\n\n{trends[:600]}"


async def run(
    action: str = "list",
    name: Optional[str] = None,
    description: Optional[str] = None,
    topic: Optional[str] = None,
    source_skill: Optional[str] = None,
) -> str:
    """
    action: research | build | clone | list | disable | enable
    """
    # Import lazy para evitar circular imports
    from app.core.skill_engine import SkillEngine
    engine = SkillEngine()

    if action == "list":
        return engine.list_skills(show_disabled=True)

    elif action == "research":
        if not topic:
            return "❌ Requiere topic para investigar."
        return await _research_implementation(topic)

    elif action == "build":
        if not name or not description:
            return "❌ Requiere name y description para construir un skill."
        # Generar código base mínimo funcional
        code = f'''"""
KynicOS — Skill: {name}
{description}
Generado automáticamente por SkillBuilder.
"""

async def run(**kwargs) -> str:
    """Implementación pendiente. Edita workspace/skills/{name}/skill.py"""
    return "🔧 Skill '{name}' creado. Implementación pendiente de desarrollo."
'''
        return await engine.build_skill(
            name=name,
            description=description,
            code=code,
            tags=["auto-generated"],
        )

    elif action == "clone":
        if not name or not source_skill:
            return "❌ Requiere name (nuevo nombre) y source_skill (origen)."
        # Buscar código fuente
        source_entry = engine._registry.get(source_skill)
        if not source_entry or not source_entry.get("module"):
            return f"❌ Skill origen '{source_skill}' no encontrado o sin código."
        import inspect
        module = source_entry["module"]
        try:
            source_code = inspect.getsource(module)
            return await engine.build_skill(
                name=name,
                description=f"Clon de {source_skill}. {description or 'Modificar según necesidad.'}",
                code=source_code,
                tags=["cloned", f"from:{source_skill}"],
            )
        except Exception as e:
            return f"❌ Error al clonar: {e}"

    elif action == "disable":
        if not name:
            return "❌ Requiere name."
        return engine.disable_skill(name)

    elif action == "enable":
        if not name:
            return "❌ Requiere name."
        return engine.enable_skill(name)

    else:
        return f"❌ Acción desconocida: {action}. Usa: list | research | build | clone | disable | enable"
