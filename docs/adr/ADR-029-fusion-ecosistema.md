# ADR-029 — Fusión del ecosistema en KynicOS

- **Fecha:** 3 de noviembre de 2026
- **Estado:** propuesto (requiere merge de Julián)
- **Complementa:** ADR-027 (orquestador único del nodo) y ADR-028 (capacidades avanzadas)
- **Decisión:** KynicOS es el núcleo. Los demás repositorios se integran por
  **registro de solo lectura y adaptadores**, no copiando su código dentro.

---

## 1. El problema real

La instrucción fue "fusiona todo el contenido y utilidad" de tres repositorios
dentro de KynicOS. Copiar el contenido es lo fácil y lo que rompe: cuatro copias
del mismo archivo divergen en una semana y nadie sabe cuál manda. El repositorio
`KYNYKOS_AI_Agent` tiene 128 archivos y buena parte son estados de fase
(`PHASE_1_COMPLETE.md`, `FASE_3_STATUS.md`, `FINAL_STATUS.md`) que no aportan
código, solo historia.

Lo que KynicOS necesita no es el contenido, es **acceso** al contenido.

## 2. Qué aporta cada repositorio

| Repositorio | Rol | Lo que sí se integra | Lo que no |
|---|---|---|---|
| `KynicOS` | núcleo | bucle, router, skills, canales, herramientas | — |
| `Wasm-Kalpixk_IA_DevOps` | defensa | personas `.jules` (bolt, sentinel, ordnance_ops), nodos de amenaza, CI de Rust | crates y binarios: se referencian por ruta |
| `KYNYKOS_AI_Agent` | memoria | `AGENTS.md`, workflows `agente-turno` y `memoria-guardian`, `MEMORIA.md` | los `PHASE_*` y `FINAL_STATUS`: historia, no código |
| `python-orchestrator-node` | orquestador | `audit_profiles.yaml`, `tool_registry.yaml`, auditoría de arquitectura | el servicio FastAPI completo: se llama, no se embebe |

## 3. Cómo se integra

### 3.1 Registro de solo lectura (hecho)
`app/core/ecosystem.py`, sin dependencias de terceros:

- `inventario()` resuelve cada repositorio en disco. Raíces en
  `KYNIKOS_ECOSYSTEM_ROOTS` (`;` en Windows, `:` en Linux) o, por defecto, el
  directorio actual, su padre y `~/Documents`.
- `leer(clave, ruta)` devuelve texto de un archivo. **Falla cerrado** ante
  `.env`, `.env.*`, `*.key`, `*.pem`, `.git`, `.kynikos` y cualquier ruta con
  `..` que se salga de la raíz.
- `buscar(patron)` recorre los repositorios saltando secretos, `node_modules`,
  `__pycache__`, `.venv`, `dist` y `build`.
- `catalogo()` responde la pregunta útil: qué tiene cada repositorio hoy, en
  disco, sin creerle a la documentación.
- `estado()` devuelve el resumen listo para un comando del bot.

Pruebas: `tests/test_ecosystem.py`, 8 casos, incluidos el rechazo de `.env` y el
rechazo de rutas que se escapan.

### 3.2 Exposición al agente
Tres formas, en este orden:

1. **Comando** `/ecosistema` en Telegram. Barato, sin modelo de por medio.
2. **Herramienta** del bucle (`ecosystem_read`, `ecosystem_search`) dentro del
   ciclo de la fase 1 del ADR-028, con doble paso para cualquier lectura fuera
   de `KynicOS`.
3. **Índice** para el `ShadowExplorer` existente: sus `base_paths` deberían
   incluir `KYNIKOS_ECOSYSTEM_ROOTS`, con lo que la búsqueda profunda que ya
   existe empieza a ver los cuatro repositorios sin escribir código nuevo.

### 3.3 Adaptadores, no copias
- **Kalpixk:** se leen sus personas `.jules` como texto de contexto para la
  persona KYNIKOS. Los crates no se tocan desde el agente.
- **Orquestador:** sus dos YAML se leen como datos. Cuando se quiera ejecutar
  una auditoría, se llama a su servicio HTTP; no se importa su módulo.
- **KYNYKOS_AI_Agent:** su `AGENTS.md` y su `MEMORIA.md` son fuente de verdad
  documental; el resto es archivo histórico.

## 4. Router y observabilidad

Según ADR-028, fase 5: `litellm` sustituye la capa de proveedores conservando
el orden AMD-first y el `token_tracker`. Langfuse **Cloud**, no self-host: el
nodo corre en la misma máquina que `qwen2.5:7b` con 15 GB de RAM, y Langfuse
self-hosted son Postgres, ClickHouse y Redis compitiendo por esa memoria.

## 5. Riesgos

| Riesgo | Mitigación |
|---|---|
| El agente lee un `.env` de otro repo y lo filtra al chat | Lista negra en el módulo, no en el prompt. Probada. |
| Divergencia entre repositorios | Se integra por referencia; una sola fuente de verdad por dato |
| Lentitud al recorrer 260 archivos de Kalpixk | Búsqueda acotada, saltos de carpeta y tamaño máximo por archivo |
| El agente escribe fuera de KynicOS | Este módulo es solo lectura. Escribir sigue siendo `write_file` con bases acotadas y doble paso |

## 6. Qué queda fuera a propósito

- No se copia código de otros repositorios a `app/`.
- No se ejecuta nada del orquestador dentro del proceso del nodo.
- No se indexan secretos ni bases de datos.
- No se toca `MEMORY.md` para "fusionar" memorias: se lee, no se reescribe.

## 7. Siguiente paso

Montar el comando `/ecosistema` en `app/cloud/telegram_bot.py` y añadir las dos
herramientas al ciclo de la fase 1. Ambas cosas caben en el mismo PR que abra la
fase 1, para no encadenar PRs abiertos.
