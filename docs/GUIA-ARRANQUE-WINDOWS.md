# Arranque del nodo KYNIKOS en Windows

Tres bloques. Copias, pegas y el propio script te confirma si quedó bien.
No hay que decidir nada ni editar archivos a mano.

| Bloque | Qué hace | Cuánto tarda |
| --- | --- | --- |
| 1 | Trae el repositorio | 1 minuto |
| 2 | Instala y valida contra Telegram | 10 a 20 min (descarga el modelo) |
| 3 | Prueba en Telegram | 2 minutos |

**Antes de empezar, ten a mano:** el token de `@BotFather` (en `/mybots` → `kynicOS_robot` → API Token) y una palabra secreta inventada por ti. El script te las pedirá en el bloque 2. Sin esas dos cosas no avanza.

---

## Bloque 1 · Traer el repositorio

Abre **Windows PowerShell** (tecla Windows, escribe `PowerShell`, doble clic). Pega esto:

```powershell
cd $HOME\Documents
git clone https://github.com/JULIANJUAREZMX01/KynicOS.git
cd KynicOS
```

**Debe aparecer:** un mensaje de clonación y ninguna palabra en rojo.
**Si dice que `git` no se reconoce:** cierra la ventana, abre PowerShell otra vez y repite. Si sigue, instala Git con `winget install --id Git.Git -e --source winget`, cierra, reabre y repite.

---

## Bloque 2 · Instalar, arrancar y validar

Este bloque hace seis cosas por su cuenta: borra tareas viejas que estorben, actualiza el repositorio, comprueba requisitos, instala lo que falte, arranca el nodo y **verifica con Telegram que esté escuchando de verdad**.

```powershell
cd $HOME\Documents\KynicOS
Set-ExecutionPolicy -Scope Process -Bypass -Force
.\nodo\arrancar-y-validar.ps1
```

Te pedirá dos datos. El token **no se muestra al pegarlo**: es normal, pégalo con clic derecho y pulsa Enter.

**Debe terminar así:**

```
===============================================
   OK   VALIDADO: el nodo está escuchando a Telegram.
===============================================
```

Esa validación no es un adorno: el script consulta la API de Telegram y espera el error de conflicto, que solo ocurre si el nodo está ocupando el canal. Si no lo recibe, te dice `FALLO` y no te deja creer que funcionó.

**Si se detiene antes**, el mensaje te dice exactamente qué falta. Los tres casos reales:

| Lo que dice | Qué hacer |
| --- | --- |
| `Falta: git` / `python` / `ollama` | Ejecuta el `winget install` que te muestra, cierra la ventana, abre otra y repite el bloque |
| `El proceso murió al arrancar` | El script imprime el error real abajo. Mándamelo y lo resuelvo |
| `Telegram no reporta que alguien escuche` | El token del `.env` no es el de `@kynicOS_robot`. Se rehace con `notepad .env` |

---

## Bloque 3 · Probar en Telegram

Abre Telegram y escribe en `@kynicOS_robot`:

```
/estado
```

**Debe contestar** con su estado. Si contesta, el nodo está operativo de verdad y ya puedes usarlo.

Dos pruebas más, opcionales pero recomendables:

1. Escribe cualquier frase normal. Debe responder como asistente.
2. Escribe tu palabra secreta. Debe llegar **una sola** notificación con botones **Autorizar** y **Rechazar**. Al autorizar recibes una palabra tipo `KALPIXK-304F-0897`, válida cinco minutos y un solo uso.

---

## Bloque 4 · Que arranque solo (opcional)

Solo después de que el bloque 3 haya contestado:

```powershell
cd $HOME\Documents\KynicOS
.\nodo\registrar-tarea.ps1
```

Ese script comprueba que el proceso esté vivo antes de darse por bueno; no se fía del estado `Ready` de Windows, que solo significa "registrada".

Para detener el nodo:

```powershell
Stop-Process -Id (Get-Content $HOME\Documents\KynicOS\.kynikos\nodo.pid)
```

Para quitarlo del arranque automático:

```powershell
Unregister-ScheduledTask -TaskName "KYNIKOS nodo" -Confirm:$false
```

---

## Configuración, por si algún día hay que mirarla

El bloque 2 crea `.env` en la carpeta del repositorio. Nunca se sube a GitHub. Se edita con `notepad .env`.

| Variable | Para qué sirve |
| --- | --- |
| `TELEGRAM_TOKEN` | Credencial del bot. Sin ella no hay canal |
| `TELEGRAM_USER_ID` | Solo tu ID puede hablarle. Es el candado |
| `PERSONA` | Tono y reglas de respuesta |
| `OLLAMA_URL` | Dónde escucha el modelo (`http://127.0.0.1:11434`) |
| `OLLAMA_MODEL` | Modelo local (`qwen2.5:7b`, el que va fluido en CPU) |
| `OLLAMA_NUM_CTX` | Conversación que recuerda a la vez (`4096`) |
| `MAX_TOKENS_SALIDA` | Tope de largo por respuesta (`768`) |
| `TIMEOUT_LLM` | Paciencia en segundos (`300`, holgado porque es CPU) |
| `KYNIKOS_PALABRA_1` | La palabra del primer paso del doble factor |
| `KYNIKOS_ESTADO_DIR` | Dónde guarda el estado del doble paso (`.kynikos`) |

---

## Comandos sueltos, para después

```powershell
# arrancar y validar (lo mismo del bloque 2, sin reinstalar)
.\nodo\arrancar-y-validar.ps1

# diagnóstico de hardware, modelo y configuración
.\.venv\Scripts\python.exe cli\kynikos.py doctor

# estado del doble paso, sin mostrar nada sensible
.\.venv\Scripts\python.exe cli\kynikos.py doble-paso estado

# ver actividad en vivo
Get-Content kynikos.log -Tail 20 -Wait

# actualizar cuando haya cambios
git pull
.\.venv\Scripts\python.exe -m pip install -q -r requirements-bot.txt
```

---

## Lo que no se hace nunca

1. Pegar el token o la palabra del primer paso en un chat, un issue o una captura de pantalla.
2. Subir el `.env` a GitHub. Ya está ignorado.
3. Repartir el enlace del bot. El candado por ID protege, pero el enlace no se comparte.
4. Instalarlo en un equipo ajeno: quien sea dueño de esa máquina puede leer el `.env`.

---

## Historia de esta guía

Este documento cambió tres veces la noche del 3 de noviembre de 2026, cada vez por un fallo real encontrado al ejecutarlo:

- **v1:** el instalador terminaba con éxito falso (`exit 0`) al instalar Python u Ollama, así que nunca creaba el entorno.
- **v2:** la guía ponía "Actualizar" al final sin condicionarlo, y se ejecutaba antes de instalar, dando `ObjectNotFound: .venv`.
- **v3 (esta):** el flujo se redujo a tres bloques con validación automática. La tarea programada dejó de ser un paso suelto y ahora tiene su propio script que comprueba que el proceso viva.

Detalle técnico en `docs/adr/ADR-026-instalador-windows-y-guia-de-arranque.md`.
