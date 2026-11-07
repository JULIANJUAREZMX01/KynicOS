# ADR-051: El diagrama del README describe el código real

## Contexto
El diagrama de arquitectura del README nombraba `SkillRouter` y `MemoryInject`.
Ninguna de las dos clases existe en el repositorio: quien buscara ese código no
lo encontraría, y quien leyera el diagrama creería que hay un enrutador genérico
que en realidad no está implementado.

Lo que hay de verdad (verificado el 2026-11-06):
- `ConciergeAgentLoop.process_message` detecta skills con reglas explícitas e
  imports directos (`app/skills/hvac_triage.py`, `app/skills/mueve_cancun.py`).
  Solo evalúa el último mensaje del usuario, para que el bot no se realimente
  con sus propias respuestas.
- `Memory.get_memory_context` inyecta el contenido de `workspace/memory/MEMORY.md`.
- `ProviderManager` elige proveedor (Groq, Anthropic, Ollama como último recurso).
- `ToolExecutor` ejecuta las herramientas que pide el modelo.

## Decisión
El diagrama usa esos cuatro nombres. Se añadió una nota bajo el diagrama que
explica que la detección de skills es por reglas explícitas y no por un router
genérico, porque ese matiz cambia cómo se añade una skill nueva.

## Consecuencias
- El diagrama sirve para navegar el código, no solo para presentarlo.
- Añadir una skill exige tocar `process_message`; queda dicho en el README.
- Si algún día se implementa un enrutador real, este ADR se sustituye.
