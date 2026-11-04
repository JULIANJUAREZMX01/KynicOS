# ADR-031 — Llave maestra única y orden documental

- **Fecha:** 4 de noviembre de 2026
- **Estado:** Aceptada e implementada
- **Ámbito:** nodo KYNIKOS, documentación de arranque

## Contexto

El barrido del 4-nov encontró **nueve puntos de entrada** para arrancar el mismo nodo, creados en distintas sesiones sin coordinación:

| Archivo | Líneas | Qué era |
|---|---|---|
| `nodo/kynikos.ps1` | 496 | Orquestador con subcomandos (ADR-027) |
| `nodo/automatico.ps1` | 152 | Copia del orquestador |
| `nodo/arrancar-y-validar.ps1` | 229 | Orquestador anterior |
| `nodo/arranque-todo-en-uno.ps1` | 133 | Orquestador anterior |
| `nodo/asistente-instalacion.ps1` | — | Instalador guiado |
| `nodo/CENTRO.ps1` | 31 | Lanzador del menú |
| `nodo/centro.py` | 562 | Menú TUI **con lógica propia duplicada** |
| `nodo/instalar.sh` | — | Instalador de Linux |
| `tools/kynicos.ps1` | 380 | Tercer orquestador, con el nombre mal escrito |

Y la documentación estaba repartida entre `README.md` (28 KB), `docs/GUIA-ARRANQUE-WINDOWS.md`, `docs/despliegue/BOT-PROPIO.md`, `docs/ESTADO-ACTUAL.md`, `ROADMAP_AMD.md` y once ADR. Seis documentos explicaban cómo arrancar, cada uno con una versión distinta del comando.

Consecuencia medible: entre el 3 y el 4 de noviembre, de siete intentos de arranque, **seis fallaron por ejecutar la versión equivocada de la secuencia**, no por un defecto del nodo.

## Decisión

1. **Una sola llave maestra: `nodo\kynikos.ps1`.** Toda la lógica de arranque vive ahí y solo ahí.
2. **`nodo\ARRANCAR.cmd` es su atajo**, no una segunda implementación: doble clic, sin pegar comandos.
3. **Todo lo demás pasa a alias de cuatro líneas** que delegan en la llave maestra. Se conservan para no romper accesos directos, pero declaran su estado en la cabecera.
4. **`centro.py` deja de ser un camino paralelo.** Es la capa de presentación (menú) y delega las acciones de nodo en la llave maestra. Su propia lógica se retira por partes; lo que quede marcado como pendiente en este ADR.
5. **`instalar.sh` queda restringido a Linux/macOS** y aborta con mensaje explícito si detecta PowerShell.
6. **Un solo documento de arranque: `docs/ARRANQUE.md`.** Los demás documentos dejan de explicar comandos y apuntan a él.
7. **Regla de oro:** si un documento necesita copiar comandos de arranque, enlaza `docs/ARRANQUE.md`. Duplicar el comando es la forma más rápida de que quede obsoleto.

## Consecuencias

- Un solo archivo que corregir cuando algo cambie. Los siete fallos por versión equivocada dejan de ser posibles.
- Los alias no añaden valor a futuro y deberían irse, pero borrarlos hoy rompería los accesos directos que el dueño ya creó en su PC.
- `centro.py` conserva `accion_requisitos` y `accion_reporte` con lógica propia: son de solo lectura y de bajo riesgo, se migran cuando se toquen por otro motivo.
- El menú visual queda como **selección y encendido**: no decide cómo se arranca, solo cuándo.
- Coste asumido: dos archivos que hay que mantener sincronizados en la frontera (`kynikos.ps1` y `centro.py`), con una regla clara de quién manda.
