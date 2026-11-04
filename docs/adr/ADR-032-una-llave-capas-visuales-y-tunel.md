# ADR-032 — Una sola llave, capas visuales y el túnel pendiente

- **Fecha:** 4 de noviembre de 2026
- **Estado:** Aceptada (capas visuales: recomendación, sin implementar)
- **Sustituye parcialmente:** ADR-031 (que conservaba los alias de compatibilidad)

## Contexto

ADR-031 declaró `nodo/kynikos.ps1` como llave maestra, pero conservó ocho alias de
compatibilidad para no romper accesos directos. Julián decide eliminarlos: una sola
llave y dos `.cmd`. También pide analizar las capas visuales posibles, aclarar el
estado del túnel acordado y saber qué puede leer el bot de la instalación.

## Decisión 1 — Una sola entrada

`nodo/` queda con cinco archivos: `kynikos.ps1` (lógica), `ARRANCAR.cmd` y
`CONFIGURAR.cmd` (atajos de doble clic), `centro.py` (capa de presentación) y
`.env.plantilla`. Todo lo demás se mueve a `nodo/legacy/` sin borrarse: son
recuperables desde git y desde esa carpeta, pero fuera del camino.

`tools/kynicos.ps1` se elimina: 252 líneas duplicando el orquestador bajo un nombre
con errata.

**Regla:** un archivo con lógica por cada cosa. Si aparece otra copia, se mueve a
`legacy/` en el mismo turno.

## Decisión 2 — Capas visuales, evaluadas por coste y provecho

| Capa | Coste | Provecho | Veredicto |
|---|---|---|---|
| Ratatui (Rust) | Alto: binario aparte, otro toolchain | Estética de terminal excelente | **Descartada.** Duplica el stack para lo que ya hace Python |
| `textual` (Python) | Medio: reescribir la capa visual de `centro.py` | TUI real: widgets, ratón, CSS propio | **Recomendada si el objetivo es vanidad de terminal** |
| `rich` (Python) | Bajo: adaptar `centro.py` | Paneles, tablas y color sin cambiar la estructura | **Recomendada como paso inmediato** |
| Panel web local en el FastAPI | Bajo: ya hay servidor en :8000 | Se ve desde el móvil, sin instalar nada, SSE en vivo | **Recomendada como la de mayor retorno** |

Decisión: la capa con mejor relación coste/provecho es el **panel web servido por el
propio nodo**, porque el servidor ya existe y se abre desde el teléfono en la misma
red. En segundo lugar `rich` sobre `centro.py`. `textual` queda como evolución si se
quiere TUI con ratón. Ratatui se descarta: añadiría un segundo lenguaje y un binario
más para algo que Python ya resuelve.

Ninguna se implementa en este ADR; quedan como opciones con orden de preferencia.

## Decisión 3 — El túnel no se construyó, y no debe hacerse todavía

Se acordó exponer el nodo con un túnel para tener dominio propio y login real, en
lugar del login decorativo de GitHub Pages (que es estático y no puede autenticar).
**No se implementó.** Dos razones:

1. El sandbox bloquea esa ruta por política, así que solo puede ejecutarse en la PC.
2. `GET /api/status` no exige autenticación. Publicarlo tal cual deja al descubierto
   modelo, PID, uptime y estado del token de cualquiera que acierte la URL.

**Requisito antes de abrir el túnel:** proteger `/api/status` y el panel con la
palabra de dos pasos que ya existe (`KYNIKOS_PALABRA_1`), o con un token por
cabecera. Abrir primero y proteger después es cómo se filtran los nodos.

## Decisión 4 — Qué puede y qué no puede el bot hoy

Verificado en el código, no supuesto:

**Puede:** `/estado` informa modelo, contexto, PID, minutos encendido, RAM y si el
polling está activo. `/logs` devuelve las últimas líneas del registro. `/modelo`,
`/id`, `/reiniciar` y `/ayuda` informan y controlan el ciclo del bot.

**No puede:** no existe instalación guiada por Telegram. El bot no lee el log de una
instalación, no detecta por qué falló un paso ni propone el siguiente. Lo más parecido
es `centro.py reporte`, que escribe `reporte.json` en local y no lo envía.

**Consecuencia:** toda la noche del 3 de noviembre el diagnóstico lo hice yo leyendo
pantallas. Un comando `/instalar` que lea el registro y responda "falló en X, prueba Y"
habría ahorrado la mitad de los turnos. Queda como el siguiente trabajo del bot.

## Consecuencias

- Un solo camino de ejecución; cualquier duplicado futuro se mueve a `legacy/`.
- Los `.cmd` llaman directamente a `kynikos.ps1`, sin eslabones intermedios.
- `legacy/` no se documenta ni se mantiene: es archivo histórico.
- Abrir el túnel exige autenticación previa como condición de entrada.
