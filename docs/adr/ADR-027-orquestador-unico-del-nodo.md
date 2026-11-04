# ADR-027 — Orquestador único del nodo KYNIKOS

**Fecha:** 4 de noviembre de 2026
**Estado:** aceptado

## Contexto

La instalación del nodo en Windows acabó repartida en seis scripts con lógica
repetida: `instalar.ps1`, `configurar.ps1`, `arrancar-y-validar.ps1`,
`arranque-todo-en-uno.ps1`, `asistente-instalacion.ps1` y `registrar-tarea.ps1`.

Esa duplicación produjo fallos reales durante la puesta en marcha en la PC de
Julián:

- `arranque-todo-en-uno.ps1` pedía el token por su cuenta, lo validaba mal y
  reescribía el `.env`, dejando un token inválido donde ya había uno bueno
  (`Token inválido o sin red: Not Found`).
- El paso que daba el entorno por bueno solo comprobaba que existiera `.venv`,
  no que tuviera `python-telegram-bot`, así que el nodo moría con
  `ModuleNotFoundError: No module named 'telegram'`.
- Una guía indicaba `Set-ExecutionPolicy -Bypass`, parámetro que no existe.
- Se pegó `instalar.sh` (Linux) en PowerShell, generando decenas de errores.

Cada corrección había que aplicarla en varios archivos, y siempre quedaba uno
atrás.

## Decisión

Un solo orquestador, `nodo/kynikos.ps1`, con subcomandos:

| Acción | Qué hace |
|---|---|
| *(ninguna)* | flujo completo: repo, requisitos, modelo, entorno, `.env`, arranque, validación, tarea |
| `instalar` | dependencias, modelo y entorno |
| `configurar` | `.env` con token validado contra Telegram |
| `arrancar` | lanza el nodo en segundo plano |
| `validar` | confirma el polling por el conflicto 409 |
| `estado` | entorno, token, proceso y tarea |
| `detener` | para el nodo |
| `reparar` | verifica imports y reinstala lo que falte |
| `tarea` | arranque automático al iniciar sesión |
| `doctor` | diagnóstico de la máquina |
| `logs` | últimas líneas del nodo |

Los seis scripts anteriores se conservan como alias de cuatro líneas, para no
romper accesos directos ni guías ya escritas.

Reglas de diseño:

1. **Idempotencia.** Cada paso comprueba antes de actuar; volver a ejecutarlo no
   duplica modelos, entornos ni tareas.
2. **Verificación real, no de existencia.** El entorno se valida importando
   `telegram`, `loguru` y `httpx`; el token con `getMe`; el arranque con el
   conflicto 409 de Telegram.
3. **Un solo `.env`.** Se escribe en UTF-8 sin BOM y con respaldo `.env.anterior`.
4. **ASCII en el código.** La consola de Windows usa cp1252 y los acentos y
   emojis provocaban `UnicodeEncodeError`.
5. **Nada de lógica en los alias.** Si un arreglo aplica a un script, aplica a
   todos, porque solo hay un archivo con lógica.

## Consecuencias

- Instalar en otra PC es un comando: `.
odo\kynikos.ps1` o doble clic en
  `nodo\ARRANCAR.cmd`.
- Un fallo se diagnostica en un sitio, no en seis.
- Los alias quedan como deuda técnica menor y pueden borrarse cuando ninguna
  guía antigua los mencione.
