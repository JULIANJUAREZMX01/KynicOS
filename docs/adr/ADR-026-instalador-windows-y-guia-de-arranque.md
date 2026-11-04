# ADR-026 — Instalador para Windows y guía única de arranque

- **Fecha:** 3 de noviembre de 2026
- **Estado:** Aceptada e implementada
- **Archivos:** `nodo/instalar.ps1`, `nodo/arranque-todo-en-uno.ps1`, `docs/GUIA-ARRANQUE-WINDOWS.md`
- **Related:** ADR-025 (verificación de doble paso), ADR-021 (nodo primario)

## Contexto

El nodo primario tenía instalador solo para Linux y Mac (`nodo/instalar.sh`). La PC designada como nodo — «patricia73», HP Pavilion All-in-One, Ryzen 5 5500U, 16 GB — corre **Windows**. Ese desajuste explica por qué el bot `@kynicOS_robot` recibía mensajes y no respondía: el cerebro nunca llegó a arrancar, porque no había un camino de instalación para el sistema operativo real.

Además, el conocimiento del arranque vivía disperso en conversaciones: qué instalar, en qué orden, qué variable significa qué, y qué hacer cuando Windows dice que no reconoce `python` o `ollama`.

## Decisión

Tres piezas complementarias, cada una con un propósito distinto:

1. **`nodo/instalar.ps1`** — instalador interactivo. Verifica Python y Ollama, los instala con `winget` si faltan, descarga el modelo, crea el entorno y escribe el `.env` pidiendo el token con entrada oculta (`Read-Host -AsSecureString`), de modo que no queda en el historial de la terminal ni en pantalla.
2. **`nodo/arranque-todo-en-uno.ps1`** — un solo bloque para copiar y pegar. Hace los cinco pasos sin que el usuario tenga que entender el orden: Git, repositorio, instalador, revisión de la configuración y comprobación del bot. Si algo falta en el `.env`, se detiene y dice exactamente qué editar, en lugar de arrancar a medias.
3. **`docs/GUIA-ARRANQUE-WINDOWS.md`** — el documento explicativo: cada comando con su porqué, qué debe pasar, qué hacer si no pasa, y una tabla de problemas comunes con síntoma, causa y arreglo.

## Decisiones de detalle

- **Sin administrador.** Nada del flujo requiere elevar privilegios; `winget` instala por usuario.
- **Política de ejecución solo para la ventana** (`-Scope Process`), nunca a nivel de sistema. Un script descargado no justifica bajar la seguridad del equipo de forma permanente.
- **El token nunca se escribe en pantalla** ni se pasa como argumento: se lee en forma segura y se guarda directo en `.env`, que está en `.gitignore`.
- **Falla con mensaje claro, no con error críptico.** Si falta una variable, el script la nombra. Si el instalador dejó algo a medias, lo dice y sugiere reabrir la terminal, que es la causa real del 90% de los tropiezos en Windows.

## Verificación (y su límite honesto)

- **Sintaxis:** ambos `.ps1` se validaron por análisis estático propio (balance de llaves, paréntesis y corchetes ignorando cadenas y comentarios, verificación de `$env:` y ausencia de credenciales embebidas). Sin desbalance y sin secretos.
- **Referencias:** los cuatro comandos del CLI citados en la guía (`run`, `doctor`, `telegram`, `doble-paso`) existen y fueron probados en este entorno; `doble-paso estado` y `verificar` se ejecutaron con salida real.
- **Límite:** en este sandbox **no hay PowerShell**, así que los scripts no se ejecutaron en un Windows real. La validación fue estática. Por eso la guía incluye la tabla de problemas comunes: el primer arranque en la PC es la prueba definitiva, y conviene hacerlo con la guía abierta.

## Consecuencias

- Existe un camino de instalación para el sistema operativo que realmente se usa, no para el ideal.
- El arranque deja de depender de memoria conversacional: está escrito, versionado y con verificaciones automáticas de configuración.
- Si mañana otra PC se suma como nodo, el mismo bloque sirve sin reescribir nada.
- Riesgo residual: depende de `winget`, disponible en Windows 10 actualizado y Windows 11. En equipos sin `winget` hay que instalar Python, Git y Ollama a mano; la guía lo cubre en la tabla de problemas.

## Primer arranque real (3 nov 2026, noche) — lo que aprendimos

Se probó en la PC de destino y apareció un fallo que el análisis estático no podía ver:

- **Síntoma:** `ObjectNotFound: (.\.venv\Scripts\python.exe) CommandNotFoundException`.
- **Causa raíz doble:** (1) el instalador terminaba con `exit 0` al instalar Python u Ollama, con un mensaje fácil de pasar por alto, así que nunca creaba el `.venv`; (2) la guía listaba «Actualizar» como último paso y se ejecutó antes de haber instalado.
- **Corrección:** `Actualizar-Ruta` recarga el PATH de la sesión tras `winget`, de modo que normalmente **ya no hace falta reabrir PowerShell**; si aun así no aparece el programa, el script sale con `exit 1` y un aviso en rojo en lugar de `exit 0`. Además hay una verificación dura al final: si no existe `.venv\Scripts\python.exe`, falla con aviso grande. La guía dejó la advertencia sobre el orden y una fila nueva en la tabla de problemas.
- **Lección:** un `exit 0` en una ruta de «falta algo» es un éxito falso. Toda salida prematura de un instalador debe ser distinguible a simple vista.
