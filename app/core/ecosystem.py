"""KynicOS — Registro del ecosistema de repositorios.

Un solo punto que sabe dónde vive cada repositorio del ecosistema de Julián,
qué aporta cada uno y cómo leer su contenido sin abrir secretos.

Repositorios conocidos:
  - KynicOS                 núcleo: bucle, router, skills, canales
  - Wasm-Kalpixk_IA_DevOps  defensa WASM, SIEM, personas de Jules
  - KYNYKOS_AI_Agent        memoria, AGENTS.md, workflows de agentes
  - python-orchestrator-node auditorías, perfiles y registro de herramientas

Reglas de este módulo, sin excepciones:
  1. Solo lectura. Aquí no se escribe ni se borra nada.
  2. Nunca abre secretos: .env, .env.*, claves privadas, .git, sesiones ni bases.
  3. Nunca sale de la raíz del repositorio: no hay rutas con ..
  4. Si un repositorio no está en disco, se reporta ausente y se sigue adelante.

Sin dependencias de terceros: solo biblioteca estándar, para que las pruebas
corran en cualquier máquina, incluida la de Julián sin venv.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# ── Definición del ecosistema ────────────────────────────────────────────────

REPOS: dict[str, dict] = {
    "kynicos": {
        "github": "JULIANJUAREZMX01/KynicOS",
        "carpetas": ["KynicOS", "kynicos"],
        "rol": "nucleo",
        "aporta": [
            "bucle de agente y router de proveedores",
            "skills, canales (Telegram, WhatsApp, web)",
            "ejecutor de herramientas y verificación en dos pasos",
        ],
    },
    "kalpixk": {
        "github": "JULIANJUAREZMX01/Wasm-Kalpixk_IA_DevOps",
        "carpetas": ["Wasm-Kalpixk_IA_DevOps", "kalpixk"],
        "rol": "defensa",
        "aporta": [
            "núcleo WASM de defensa y nodos de amenaza",
            "personas de Jules (.jules): bolt, sentinel, ordnance_ops",
            "benchmarks y CI de Rust",
        ],
    },
    "kynykos_ai_agent": {
        "github": "JULIANJUAREZMX01/KYNYKOS_AI_Agent",
        "carpetas": ["KYNYKOS_AI_Agent", "kynykos_ai_agent"],
        "rol": "memoria",
        "aporta": [
            "AGENTS.md y estándar de agentes",
            "workflows: agente-turno, memoria-guardian, claude-code",
            "documentación de despliegue y fases",
        ],
    },
    "orquestador": {
        "github": "JULIANJUAREZMX01/python-orchestrator-node",
        "carpetas": ["python-orchestrator-node", "orchestrator"],
        "rol": "orquestador",
        "aporta": [
            "auditoría de arquitectura",
            "audit_profiles.yaml y tool_registry.yaml",
            "reporteros y listeners",
        ],
    },
}

# Artefactos que delatan qué ofrece un repositorio, para el catálogo.
ARTEFACTOS = {
    "skills": ["app/skills", "skills"],
    "agentes": ["app/agents", "agents"],
    "adr": ["docs/adr"],
    "personas_jules": [".jules"],
    "workflows": [".github/workflows"],
    "pruebas": ["tests"],
    "auditorias": ["app/audit_modules"],
    "registro_herramientas": ["tool_registry.yaml"],
    "perfiles_auditoria": ["audit_profiles.yaml"],
    "memoria": ["docs/agentes/MEMORIA.md", "workspace/memory/MEMORY.md"],
}

# Nombres que jamás se abren, ni para leer ni para indexar.
_SECRETOS_EXACTOS = {
    ".env", ".env.local", ".env.production", ".env.anterior",
    "id_rsa", "id_ed25519", "credentials.json", "token.pickle",
    "secrets.json", "kynikos.log",
}
_SECRETOS_PREFIJOS = (".env.", "secrets.", "id_rsa", "id_ed25519")
_CARPETAS_PROHIBIDAS = {".git", "node_modules", "__pycache__", ".venv", "venv",
                        "dist", "build", ".astro", ".kynikos"}
_EXTENSIONES_TEXTO = {
    ".py", ".md", ".json", ".yaml", ".yml", ".toml", ".txt", ".cfg", ".ini",
    ".rs", ".ts", ".tsx", ".js", ".jsx", ".sql", ".sh", ".ps1", ".html", ".css",
}

MAX_BYTES_LECTURA = 200_000


class FueraDeRaiz(ValueError):
    """La ruta pedida se sale del repositorio."""


class ArchivoProtegido(ValueError):
    """La ruta pedida es un secreto y no se abre."""


@dataclass
class Repo:
    clave: str
    github: str
    rol: str
    ruta: Path | None = None
    aporta: list[str] = field(default_factory=list)

    @property
    def presente(self) -> bool:
        return self.ruta is not None and self.ruta.exists()

    def como_dict(self) -> dict:
        return {
            "clave": self.clave,
            "github": self.github,
            "rol": self.rol,
            "ruta": str(self.ruta) if self.ruta else None,
            "presente": self.presente,
            "aporta": self.aporta,
        }


# ── Resolución de rutas ──────────────────────────────────────────────────────

def raices() -> list[Path]:
    """Directorios donde se buscan los repositorios.

    Se fija con KYNIKOS_ECOSYSTEM_ROOTS separando rutas con el separador del
    sistema (; en Windows, : en Linux). Si no se fija, se busca en el directorio
    actual y en su padre, que es donde suelen convivir los repos de Julián.
    """
    crudo = os.environ.get("KYNIKOS_ECOSYSTEM_ROOTS", "").strip()
    candidatas: list[Path] = []
    if crudo:
        for trozo in crudo.split(os.pathsep):
            trozo = trozo.strip()
            if trozo:
                candidatas.append(Path(trozo).expanduser())
    # Si la variable esta puesta, manda ella: no se anaden cwd ni home.
    # Antes se anadian siempre y un repo hermano del directorio padre colaba
    # como presente, rompiendo el catalogo y la busqueda (tests/test_ecosystem).
    if not crudo:
        cwd = Path.cwd()
        candidatas += [cwd, cwd.parent, Path.home() / "Documents"]
    vistas: list[Path] = []
    for c in candidatas:
        try:
            r = c.resolve()
        except OSError:
            continue
        if r not in vistas:
            vistas.append(r)
    return vistas


def resolver(clave: str, raices_explicitas: Iterable[Path] | None = None) -> Path | None:
    """Devuelve la ruta en disco de un repositorio, o None si no está."""
    if clave not in REPOS:
        raise KeyError(f"repositorio desconocido: {clave}")
    candidatas = raices_explicitas if raices_explicitas is not None else raices()
    for base in candidatas:
        for nombre in REPOS[clave]["carpetas"]:
            posible = Path(base) / nombre
            if posible.is_dir():
                return posible
    return None


def inventario(raices_explicitas: Iterable[Path] | None = None) -> dict[str, Repo]:
    """Mapa clave → Repo con su ruta ya resuelta."""
    salida: dict[str, Repo] = {}
    for clave, datos in REPOS.items():
        salida[clave] = Repo(
            clave=clave,
            github=datos["github"],
            rol=datos["rol"],
            ruta=resolver(clave, raices_explicitas),
            aporta=list(datos["aporta"]),
        )
    return salida


def estado(raices_explicitas: Iterable[Path] | None = None) -> str:
    """Resumen legible, pensado para un comando del bot."""
    inv = inventario(raices_explicitas)
    lineas = ["<b>KYNIKOS · ecosistema</b>", ""]
    presentes = 0
    for repo in inv.values():
        if repo.presente:
            presentes += 1
            lineas.append(f"• {repo.clave}: <code>{repo.ruta}</code>")
        else:
            lineas.append(f"• {repo.clave}: ausente ({repo.github})")
    lineas.append("")
    lineas.append(f"{presentes} de {len(inv)} repositorios en disco")
    return "\n".join(lineas)


# ── Guards ───────────────────────────────────────────────────────────────────

def _es_secreto(ruta: Path) -> bool:
    nombre = ruta.name.lower()
    if nombre in _SECRETOS_EXACTOS:
        return True
    if nombre.startswith(_SECRETOS_PREFIJOS):
        return True
    if any(parte.lower() in _CARPETAS_PROHIBIDAS for parte in ruta.parts):
        return True
    return ruta.suffix.lower() in {".pem", ".key", ".p12", ".pfx", ".kdbx"}


def _dentro_de(ruta: Path, raiz: Path) -> Path:
    destino = (raiz / ruta).resolve()
    base = raiz.resolve()
    if destino != base and base not in destino.parents:
        raise FueraDeRaiz(f"{ruta} se sale de {base}")
    return destino


# ── Lectura y búsqueda ───────────────────────────────────────────────────────

def leer(clave: str, ruta_relativa: str, max_bytes: int = MAX_BYTES_LECTURA,
         raices_explicitas: Iterable[Path] | None = None) -> str:
    """Lee un archivo de texto del repositorio. Falla cerrado ante secretos."""
    repo = inventario(raices_explicitas)[clave]
    if not repo.presente:
        raise FileNotFoundError(f"repositorio ausente: {clave}")
    destino = _dentro_de(Path(ruta_relativa), repo.ruta)
    if _es_secreto(destino.relative_to(repo.ruta.resolve())):
        raise ArchivoProtegido(f"{ruta_relativa} es un secreto y no se lee")
    if destino.suffix.lower() not in _EXTENSIONES_TEXTO:
        raise ArchivoProtegido(f"{ruta_relativa} no es texto indexable")
    if not destino.is_file():
        raise FileNotFoundError(ruta_relativa)
    return destino.read_text(encoding="utf-8", errors="replace")[:max_bytes]


def buscar(patron: str, clave: str | None = None, max_resultados: int = 40,
           raices_explicitas: Iterable[Path] | None = None) -> list[dict]:
    """Busca un texto en los repositorios. Salta secretos y carpetas pesadas."""
    if not patron or len(patron) < 2:
        raise ValueError("el patrón necesita al menos 2 caracteres")
    inv = inventario(raices_explicitas)
    objetivos = [inv[clave]] if clave else list(inv.values())
    aguja = patron.lower()
    resultados: list[dict] = []
    for repo in objetivos:
        if not repo.presente:
            continue
        for raiz, dirs, archivos in os.walk(repo.ruta):
            dirs[:] = [d for d in dirs if d.lower() not in _CARPETAS_PROHIBIDAS]
            for nombre in archivos:
                archivo = Path(raiz) / nombre
                try:
                    relativa = archivo.relative_to(repo.ruta.resolve())
                except ValueError:
                    continue
                if _es_secreto(relativa):
                    continue
                if archivo.suffix.lower() not in _EXTENSIONES_TEXTO:
                    continue
                try:
                    if archivo.stat().st_size > MAX_BYTES_LECTURA:
                        continue
                    for numero, linea in enumerate(
                        archivo.read_text(encoding="utf-8", errors="replace").splitlines(), 1
                    ):
                        if aguja in linea.lower():
                            resultados.append({
                                "repo": repo.clave,
                                "archivo": str(relativa),
                                "linea": numero,
                                "texto": linea.strip()[:200],
                            })
                            if len(resultados) >= max_resultados:
                                return resultados
                except OSError:
                    continue
    return resultados


def catalogo(raices_explicitas: Iterable[Path] | None = None) -> dict:
    """Qué aporta cada repositorio, verificado contra el disco."""
    inv = inventario(raices_explicitas)
    salida: dict = {"repos": {}, "total_presentes": 0}
    for clave, repo in inv.items():
        entrada = repo.como_dict()
        hallados: dict[str, list[str]] = {}
        if repo.presente:
            for artefacto, rutas in ARTEFACTOS.items():
                encontrados = [r for r in rutas if (repo.ruta / r).exists()]
                if encontrados:
                    hallados[artefacto] = encontrados
            salida["total_presentes"] += 1
        entrada["artefactos"] = hallados
        salida["repos"][clave] = entrada
    return salida


def catalogo_json(raices_explicitas: Iterable[Path] | None = None) -> str:
    return json.dumps(catalogo(raices_explicitas), ensure_ascii=False, indent=2)
