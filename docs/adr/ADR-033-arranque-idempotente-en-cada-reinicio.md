# ADR-033 — Arranque idempotente en cada reinicio

- **Fecha:** 4 de noviembre de 2026
- **Estado:** Aceptada e implementada

## Contexto

El nodo arrancaba en cada inicio de sesión lanzando `cli\kynikos.py run` directamente. Eso dejaba dos huecos: nunca comprobaba si había versión nueva del repositorio, y nunca verificaba que las dependencias siguieran completas. La única forma de actualizar era entrar a mano, hacer `git pull` y volver a arrancar.

El paso de repositorio además mentía: `git pull -q --ff-only` se ejecutaba con la salida silenciada y el código comparaba el commit antes y después, así que cuando el pull fallaba —por cambios locales, por ejemplo— informaba "ya estaba al día".

El riesgo opuesto también estaba presente. La forma obvia de "arreglar" un entorno incompleto es borrar `.venv` y recrearlo, y eso destruye 300 MB de paquetes, invalida el modelo descargado y puede tocar `.env` y la sesión. En una máquina que se apaga a diario, repetir la instalación completa cada mañana es inviable.

## Decisión

1. **Nueva acción `inicio`**, es la que registra la tarea programada. Hace, en este orden: actualizar el repositorio si hay novedades, verificar dependencias, arrancar solo si no hay nodo vivo y validar.
2. **Actualización no destructiva.** Se hace `git fetch`, se compara `HEAD` con `origin/main` y solo se aplica un `--ff-only`. Nunca `reset --hard`. Si hay commits locales sin subir, se avisa y no se toca nada. `.env`, `.venv`, el modelo, `.kynikos/` y `workspace/` no se modifican jamás.
3. **Dependencias por huella.** Se calcula un SHA-256 de `requirements.txt` y `requirements-bot.txt` y se guarda en `.kynikos/deps.sha`. Si la huella coincide y el entorno importa `telegram`, `loguru` y `httpx`, no se instala nada. Si cambian los requirements, se instala **encima** del entorno existente, sin recrearlo.
4. **Creación del entorno solo la primera vez.** `.venv` se crea únicamente si `Scripts\python.exe` no existe.
5. **El repositorio informa la verdad.** Se distinguen cuatro casos: al día, actualizado, commits locales sin subir, y sin conexión. En ninguno se pierde trabajo.
6. **El nodo publica su versión.** El comando `/version` del bot compara el commit local con el último de `main` en GitHub, así se sabe desde Telegram si hace falta actualizar sin abrir la consola.

## Consecuencias

- Arrancar la PC actualiza el nodo sola, en segundos, sin descargar modelos ni reinstalar paquetes.
- Un fallo de red en el arranque no impide que el nodo funcione con la versión local.
- Nunca se pierde trabajo local: si hay commits propios, el script se detiene y explica cómo integrarlos.
- La sesión y el `.env` quedan fuera del alcance de la actualización por diseño.
- Coste asumido: la tarea de inicio depende ahora de PowerShell y del propio `kynikos.ps1`; si ese archivo se corrompe, hay que arrancar a mano. Se mitiga porque `/version` y `/estado` reportan el estado desde el propio nodo.
