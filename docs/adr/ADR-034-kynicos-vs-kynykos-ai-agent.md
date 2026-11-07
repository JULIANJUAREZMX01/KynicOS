# ADR-034 — Distinguir KynicOS de KYNYKOS_AI_Agent

- **Fecha:** 6 de noviembre de 2026
- **Estado:** Aceptada (documental)

## Contexto

Existen dos repositorios con nombres casi idénticos y estructura de carpetas
casi idéntica. Editar el equivocado produce cambios invisibles: el código
parece modificado pero el nodo que corre en la PC no cambia.

Evidencia comparada el 6-nov-2026 con la API de GitHub:

| | **KynicOS** | **KYNYKOS_AI_Agent** |
|---|---|---|
| URL | JULIANJUAREZMX01/KynicOS | JULIANJUAREZMX01/KYNYKOS_AI_Agent |
| Creado | 2026-04-03 | 2026-02-19 (más antiguo) |
| Tamaño | 6 866 KB | 457 KB |
| Descripción | Sistema Operativo para Concierge de Ultra-Lujo (monorepo) | sin descripción |
| Issues abiertos | 0 | 13 |
| `app/core/tools.py` | 7 017 bytes | 44 391 bytes |
| `app/main.py` | 6 661 bytes | 7 431 bytes |

Estructura de `app/` en ambos: agents, channels, cloud, concierge, config,
core, services, skills, utils. Mismo linaje, código divergente: los SHA de
los tres archivos clave son distintos.

Rasgos propios de cada uno:

- **KynicOS**: directorios `nodo/`, `cli/`, `wasm-busqueda/`, `web/`, `api/`.
  Es el que tiene `nodo/kynikos.ps1`, el bot @kynicOS_robot y el centro de
  mando. Corre en la PC Windows con Ollama y qwen2.5:7b.
- **KYNYKOS_AI_Agent**: directorios `infrastructure/`, `old/`, `upload-repo/`,
  `fly.toml`, `Procfile`, y una veintena de documentos de fases de despliegue.
  Motor de herramientas mucho mayor (44 KB frente a 7 KB). Lo trabajan las
  personas de Jules (Sentinel en seguridad, palette en UX) y es donde están
  los PRs de inyección de comandos.

## Decisión

1. **KynicOS es el nodo primario soberano**: el que corre en hardware propio,
   el que atiende @kynicOS_robot y donde vive la llave maestra `kynikos.ps1`.
   Todo trabajo de arranque, instalación o centro de mando va aquí.
2. **KYNYKOS_AI_Agent es el agente de nube y motor de herramientas**: su foco
   son despliegues gestionados (Render/Fly), el ToolExecutor grande y las
   personas de revisión. Los PRs de seguridad de herramientas van aquí.
3. No se copian archivos de uno a otro sin un ADR que lo justifique: la
   divergencia es intencional, no un olvido.
4. Antes de editar, confirmar el remoto con `git remote -v` y el rol con este
   ADR. Si el `pwd` no coincide con el repo declarado, detenerse.

## Consecuencias

- Queda un criterio escrito para no confundirlos, con la fecha y los datos
  que lo sustentan.
- La duplicación de `app/` sigue existiendo. Consolidarla es una decisión
  aparte y más grande: requiere comparar módulo por módulo y no se hace sin
  revisión de Julián.
- Documentos canónicos: este ADR para la distinción, `docs/ARRANQUE.md` para
  el arranque del nodo, `AGENTS.md` para reglas de trabajo.
