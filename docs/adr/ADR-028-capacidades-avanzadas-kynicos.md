# ADR-028 — Capacidades avanzadas de KYNIKOS: MCP, herramientas, memoria y router

- **Fecha:** 3 de noviembre de 2026
- **Estado:** propuesto (requiere merge de Julián)
- **Contexto:** KynicOS hoy conversa bien, pero no actúa. El objetivo es darle
  músculo real: herramientas, MCP, memoria con recuperación y un router con
  observabilidad.
- **Decisión:** adoptar las capacidades por fases, con la puerta cerrada por
  defecto. Nada de "omnipotente". Verificable o no existe.

---

## 1. Lo que ya hay (auditado el 3-nov-2026)

| Pieza | Archivo | Estado real |
|---|---|---|
| Router multi-proveedor | `app/services/llm_router.py` | Funciona. Orden AMD vLLM → Ollama → Groq → Anthropic → OpenAI. Contabilidad de tokens local. |
| Ejecutor de herramientas | `app/core/tools.py` | **Existe y ya hace shell, read/write file, git y web fetch**, con `_bases_seguras()` acotando rutas. |
| Motor de skills | `app/core/skill_engine.py` | Carga skills de `app/skills/`, construye y habilita/deshabilita. |
| Verificación en dos pasos | `app/security/doble_paso.py` | Ya está. Es la pieza que permite abrir herramientas sin abrir la puerta de par en par. |
| MCP | `app/cloud/mcp_server.py` | **No es un servidor MCP.** Es un módulo de funciones sueltas con un docstring que menciona `mcp connect`. Ni protocolo ni transporte. |
| Memoria | `app/core/memory.py` + `MEMORY.md` | Archivo Markdown. Sirve para decenas de entradas, no para miles. |

**Conclusión de la auditoría:** el cuello de botella no es la falta de
herramientas, es que **el bucle no las llama**. `app/core/loop.py` manda el
mensaje al modelo y devuelve texto. No hay ciclo de tool-calling. Ese es el
trabajo de mayor impacto y el más barato de todos.

---

## 2. Correcciones a las fuentes propuestas

| Lo que se propuso | Realidad |
|---|---|
| `modelcontextprotocol/servers` | Correcto. Es el catálogo oficial. |
| `mcp-extensions/filesystem` | No existe. El servidor de filesystem vive en `modelcontextprotocol/servers/src/filesystem`. |
| `cloudflare/mcp-server-cloudflare` | Correcto. Pero da poder para tocar Workers, KV y red. Ver sección 5. |
| `crewAIInc/crewAI` | Correcto. |
| `langchain-ai/langgraph` | Correcto. |
| `chroma-core/chroma` | Correcto. |
| `run-llama/llama_index` | Correcto. |
| `features-engineering/lelo` | **No existe.** Para sandboxing: `extism/extism` (real) o `wasmtime` vía `wasmtime-py`. |
| `BerriAI/litellm` | Correcto. |
| `langfuse/langfuse` | Correcto. |

Ninguna de estas piezas se instala "para probar". Cada una entra con su
criterio de reversión.

---

## 3. Orden de ataque

El criterio es **impacto sobre coste de mantenimiento**, no novedad.

### Fase 1 — Tool loop propio (1 semana)
**Sin dependencias nuevas.** En `app/core/loop.py`:
- Ciclo `modelo → tool_call → resultado → modelo`, máximo 4 vueltas.
- Tool calling nativo de Ollama (`qwen2.5:7b` lo soporta) y de Groq.
- Herramientas expuestas: `read_file`, `write_file`, `shell`, `git`, `web_fetch`
  de `app/core/tools.py`. **Ninguna nueva.**
- Toda llamada que escriba o ejecute exige `doble_paso` confirmado por el dueño
  (`TELEGRAM_USER_ID`). Si no, se rechaza y se pide confirmación.
- Tope duro: 3 herramientas por minuto por usuario, 30 por hora. Sin esto, un
  bucle del modelo te deja sin máquina.

**Criterio de aceptación:** test que verifica que `shell` sin confirmación
devuelve rechazo, y que el ciclo se corta a la cuarta vuelta.

### Fase 2 — KYNIKOS como servidor MCP de verdad (3 días)
Reescribir `app/cloud/mcp_server.py` con el SDK `mcp` de Python, transporte
stdio, herramientas declaradas con esquema JSON. Expone: `estado_nodo`,
`leer_memoria`, `listar_skills`, `ejecutar_skill`. **Solo lectura en esta
fase.** Eso permite que Claude Code, Windsurf o cualquier cliente MCP operen
el nodo sin shell.

**Consumir** servidores MCP externos se pospone a la fase 4: primero servimos,
después consumimos. Al revés se convierte en un agujero.

### Fase 3 — Memoria con recuperación (1 semana)
`MEMORY.md` se queda como memoria curada a mano. Para el resto: SQLite +
`sqlite-vec` o Chroma embebido. Ganancia real: recordar meses de conversaciones
de Telegram sin quemar contexto.
- Embeddings por Ollama (`nomic-embed-text`), no por API: cero coste marginal.
- Recuperación híbrida: últimos N mensajes siempre, más los K fragmentos
  relevantes por similitud.
- Presupuesto: 1200 tokens de contexto recuperado, medido.

Chroma antes que LlamaIndex. LlamaIndex se justifica cuando haya que indexar
PDFs y repos completos, no antes.

### Fase 4 — MCP externo con lista blanca (2 semanas)
Un registro `app/mcp/registry.json` con servidor, comando, herramientas
permitidas y si es lectura o escritura. Arranque bajo demanda en subproceso,
timeout de 20 s, muerte del subproceso al terminar.
Primeros tres: `filesystem` (acotado a `./workspace`), `git`, `sqlite`.
Cloudflare entra al final y solo lectura: Workers y KV se tocan con el CLI y
un humano delante, no con un agente autónomo despertado por Telegram.

### Fase 5 — Router con litellm y observabilidad (1 semana)
`litellm` sustituye la capa de proveedores actual. Ventaja concreta: fallbacks
y reintentos ya resueltos, y formato OpenAI único. Se conserva la prioridad
AMD-first y `token_tracker`.
Para telemetría, **no self-host de Langfuse**: son Postgres, ClickHouse y Redis
en la misma máquina que corre `qwen2.5:7b`. Se usa Langfuse Cloud en su capa
gratuita o, si se quiere cero dependencia, traza local en SQLite con las
mismas métricas: latencia, tokens, proveedor elegido, motivo del fallback.

### Fase 6 — Multi-agente (solo si se demuestra necesario)
`crewAI` y `langgraph` son un cambio de arquitectura, no una mejora. El bucle
síncrono con herramientas cubre el 90% de los casos de KynicOS. Antes de
adoptarlos hay que tener tres tareas reales que se beneficien de paralelismo.
Si se adopta, será LangGraph por control explícito del estado, no CrewAI.

---

## 4. Qué NO se hace

- **No** se da shell libre ni sistema de archivos sin acotar a un agente que
  responde a mensajes de Telegram. Un `TELEGRAM_USER_ID` mal configurado es
  ejecución remota de código en la máquina de Julián.
- **No** se instala nada que escriba en la nube (Cloudflare, deploys) sin
  confirmación humana por evento.
- **No** se mete un framework de orquestación para resolver un problema que
  todavía no existe.
- **No** se cambia `MEMORY.md` por una base vectorial sin migrar y verificar el
  contenido existente primero.

---

## 5. Riesgos y reversión

| Riesgo | Mitigación | Reversión |
|---|---|---|
| El modelo encadena herramientas y borra algo | `doble_paso` + bases acotadas + tope por minuto | Rama por fase, sin merge automático |
| Latencia insostenible en 15 GB de RAM con 7b | Embeddings locales pequeños, contexto recuperado medido | Desactivar fase 3 por variable de entorno |
| Subproceso MCP colgado | Timeout 20 s y matar el árbol de procesos | Registry vacío = comportamiento actual |
| Coste de proveedor descontrolado | litellm con presupuesto por sesión y alerta | Volver a `llm_router.py`, que se conserva |

Cada fase entra por PR separado, con test y con su reversión documentada. Un
PR abierto a la vez. Sin merge automático.

---

## 6. Primer entregable

Fase 1, porque es la única que convierte a KYNIKOS en algo que **hace** sin
añadir una sola dependencia y sin abrir ningún puerto nuevo.

Orden concreto:
1. `app/core/loop.py`: ciclo de herramientas con límite de vueltas.
2. `app/core/tools.py`: envolver los cinco ejecutores con `doble_paso`.
3. `tests/test_tool_loop.py`: rechazo sin confirmación, corte en la cuarta vuelta,
   tope de frecuencia.
4. Actualizar `docs/ESTADO-ACTUAL.md` y la persona KYNIKOS con la lista real de
   herramientas disponibles.
