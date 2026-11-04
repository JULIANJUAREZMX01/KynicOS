# Arranque del nodo KYNIKOS en Windows

Guía única, en orden, para dejar `@kynicOS_robot` respondiendo desde tu propia PC.
Cada bloque se copia y se pega tal cual. Cada paso dice qué debe pasar y qué hacer si no pasa.

**Tiempo total:** unos 20 minutos, casi todo esperando la descarga del modelo.
**Costo:** cero. Telegram es gratis, Ollama corre en tu máquina, no hay servicio de pago en ningún punto.

---

## Antes de empezar

Necesitas tres cosas. Tenlas a mano antes de abrir la terminal, porque el instalador te las va a pedir en el camino y si no las tienes hay que reiniciar el proceso.

| Qué | Dónde se consigue |
| --- | --- |
| **Token del bot** | En Telegram, habla con `@BotFather`, comando `/mybots`, elige `kynicOS_robot`, luego **API Token**. Es una cadena con dos puntos en medio. |
| **Palabra del primer paso** | La inventas tú. Es la que activa la verificación de doble paso. No la escribas en ningún chat. |
| **Tu ID de Telegram** | Es `8247886073`, ya viene configurado. No lo cambies. |

**Requisitos del equipo:** Windows 10 u 11, al menos 8 GB de RAM (16 GB es lo ideal), y unos 6 GB libres en disco para el modelo.

---

## Paso 1 · Abrir PowerShell

Pulsa la tecla Windows, escribe `PowerShell`, y abre **Windows PowerShell** con doble clic. No hace falta administrador para este flujo.

Comprueba que estás en una terminal moderna antes de seguir:

```powershell
$PSVersionTable.PSVersion
```

Debe mostrar versión 5.1 o superior. Si dice 2.x, tu Windows es viejo y hay que actualizar PowerShell antes de continuar.

---

## Paso 2 · Instalar Git si no lo tienes

```powershell
git --version
```

Si responde con una versión, salta al paso 3. Si dice que no se reconoce el comando, instálalo:

```powershell
winget install --id Git.Git -e --source winget
```

Al terminar, **cierra esa ventana y abre una nueva**. Windows solo reconoce los programas nuevos en terminales abiertas después de la instalación. Vuelve a comprobar con `git --version`.

---

## Paso 3 · Traer el repositorio a tu equipo

```powershell
cd $HOME\Documents
git clone https://github.com/JULIANJUAREZMX01/KynicOS.git
cd KynicOS
```

Debe aparecer un mensaje de clonación y una carpeta nueva llamada `KynicOS` dentro de Documentos. Esa carpeta es el nodo completo: no hace falta descargar nada más.

---

## Paso 4 · Ejecutar el instalador

```powershell
.\nodo\instalar.ps1
```

El script hace cuatro cosas y te avisa de cada una: instala Python y Ollama si faltan, descarga el modelo, arma el entorno de Python y crea el archivo `.env` pidiéndote el token sin mostrarlo en pantalla.

**Si Windows bloquea el script** con un mensaje sobre directivas de ejecución, es normal en un archivo descargado. Se resuelve solo para esa ventana, sin cambiar la configuración del sistema:

```powershell
Set-ExecutionPolicy -Scope Process -Bypass -Force
.\nodo\instalar.ps1
```

**Si el script instala Python u Ollama**, te pedirá cerrar y reabrir PowerShell, y volver a ejecutarlo. Es el mismo motivo del paso 2: Windows no ve los programas recién instalados desde una terminal vieja.

**Qué esperar:** la descarga del modelo (`qwen2.5:7b`, unos 4.7 GB) es el paso largo. Con buena conexión son 5 o 10 minutos. Verás el progreso por porcentaje.

---

## Paso 5 · Entender el archivo de configuración

El instalador crea un archivo llamado `.env` en la raíz del repo. Nunca se sube a GitHub: está en `.gitignore` a propósito. Esto es lo que contiene y para qué sirve cada línea:

| Variable | Para qué sirve | Valor típico |
| --- | --- | --- |
| `TELEGRAM_TOKEN` | La credencial del bot. Sin ella no hay canal. | Lo que te dio BotFather |
| `TELEGRAM_USER_ID` | Solo este usuario puede hablarle al bot. Es tu candado. | `8247886073` |
| `PERSONA` | El tono y las reglas con que responde. | `kynikos` |
| `OLLAMA_URL` | Dónde escucha el modelo local. | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Qué modelo usa. El 7B es el que va fluido en tu equipo. | `qwen2.5:7b` |
| `OLLAMA_NUM_CTX` | Cuánta conversación recuerda a la vez. | `4096` |
| `MAX_TOKENS_SALIDA` | Tope de largo por respuesta, en tokens. | `768` |
| `TIMEOUT_LLM` | Segundos de paciencia antes de rendirse. En CPU hace falta holgura. | `300` |
| `KYNIKOS_PALABRA_1` | La palabra que abre la verificación de doble paso. | La que inventaste |
| `KYNIKOS_ESTADO_DIR` | Dónde guarda el estado del doble paso. | `.kynikos` |

Si necesitas cambiar algo después, se edita con:

```powershell
notepad .env
```

**Nunca pegues este archivo en un chat, ni en una captura, ni en un issue.** Si se filtra el token, se rota en BotFather con `/revoke` y se genera otro.

---

## Paso 6 · Arrancar el nodo

```powershell
.\.venv\Scripts\python.exe cli\kynikos.py run
```

**Qué debe pasar:** el bot queda en modo escucha. La terminal se queda ocupada mostrando actividad cada vez que llega un mensaje. Eso es correcto: mientras esa ventana esté abierta, el bot está vivo.

Para detenerlo, `Ctrl + C`. Si cierras la ventana, el bot deja de responder.

**Comprobación rápida desde otra terminal**, mientras el nodo corre:

```powershell
.\.venv\Scripts\python.exe cli\kynikos.py doctor
```

Revisa hardware, modelo y configuración, y te dice si algo falta.

---

## Paso 7 · Probar que funciona de verdad

Tres pruebas, en este orden. Si la primera falla, no sigas: no tiene sentido probar el resto.

**Prueba 1, el canal.** Abre Telegram y escríbele a `@kynicOS_robot` cualquier cosa, por ejemplo `hola`. Debe contestar algo. Si no contesta y la terminal no muestra nada, el token del `.env` no es el de ese bot.

**Prueba 2, el candado.** Desde otro Telegram, o pidiéndole a alguien, escríbele al bot. No debe responder: solo atiende a tu ID.

**Prueba 3, el doble paso.** Escribe la palabra del primer paso. Debe llegar **una sola** notificación con dos botones, Autorizar y Rechazar. Al autorizar recibes una palabra tipo `KALPIXK-304F-0897`, válida cinco minutos y un solo uso.

Desde la terminal también puedes ver el estado del flujo sin mostrar nada sensible:

```powershell
.\.venv\Scripts\python.exe cli\kynikos.py doble-paso estado
```

---

## Paso 8 · Dejarlo arrancando solo (opcional)

> **Solo cuando el paso 6 ya funcione a mano.** Si registras la tarea antes de que el nodo arranque, Windows mostrará `Ready` y creerás que está vivo, pero la tarea morirá al instante sin avisar. `Ready` no significa que esté corriendo.

```powershell
.\nodo\registrar-tarea.ps1
```

El script se niega a registrar nada si falta el entorno o el `.env`, y después **espera 8 segundos y comprueba que el proceso siga vivo**. Si no lo está, te dice el código de error de Windows y cómo ver el fallo real.

Para quitarlo:

```powershell
Unregister-ScheduledTask -TaskName "KYNIKOS nodo" -Confirm:$false
```

---

## Paso 9 · Actualizar el nodo

> **Solo después de haber completado el paso 4 y arrancado el nodo al menos una vez.** Si lo ejecutas antes, el segundo comando falla con `ObjectNotFound: .\.venv\Scripts\python.exe` porque el entorno de Python todavía no existe. Eso no es un error del repositorio: significa que falta instalar.

Cuando haya cambios nuevos en el repositorio:

```powershell
cd $HOME\Documents\KynicOS
git pull
.\.venv\Scripts\python.exe -m pip install -q -r requirements-bot.txt
```

El segundo comando solo hace falta si cambiaron las dependencias. Ante la duda, córrelo: si no hay nada nuevo, no hace nada.

---

## Problemas comunes

| Síntoma | Causa | Arreglo |
| --- | --- | --- |
| `git no se reconoce` | Terminal abierta antes de instalar Git | Cierra y abre PowerShell de nuevo |
| `python no se reconoce` | Igual, tras instalar Python | Cierra y abre PowerShell |
| `ollama no se reconoce` | Igual, tras instalar Ollama | Cierra y abre PowerShell |
| El script no corre y habla de directivas | Archivo descargado, política de ejecución | `Set-ExecutionPolicy -Scope Process -Bypass -Force` |
| El bot recibe pero no contesta | El nodo no está corriendo | Ejecuta el paso 6 y deja la ventana abierta |
| `Unauthorized` o `401` al arrancar | Token mal copiado, con espacio o incompleto | Edita `.env`, revisa que no haya comillas ni espacios |
| Respuestas muy lentas | Modelo grande para el hardware | Usa `qwen2.5:7b`; el 14B baja a ~3 tokens por segundo |
| `Conflict: can't use getUpdates with webhook active` | Quedó un webhook registrado de una prueba anterior | `curl "https://api.telegram.org/bot<TU_TOKEN>/deleteWebhook"` |
| `ObjectNotFound: .\.venv\Scripts\python.exe` | El instalador no terminó o se saltó: el entorno `.venv` todavía no existe | Ejecuta `.\nodo\instalar.ps1` completo. **No** corras el paso de actualizar antes de instalar |
| Tarea en `Ready` pero el bot no contesta | La tarea se registró sin entorno: arranca y muere al instante | Borra la tarea (`Unregister-ScheduledTask`), completa `instalar.ps1` y usa `.\nodo\registrar-tarea.ps1` |
| Se corta solo | Windows suspendió la PC o se cerró la terminal | Usa la tarea del paso 8 |
| No llega la notificación del doble paso | El chat con el bot no está iniciado | Escribe `/start` en `@kynicOS_robot` una vez |

---

## Lo que no se hace nunca

1. Pegar el token o la palabra del primer paso en un chat, un issue o una captura.
2. Subir el `.env` a GitHub. Ya está ignorado, no lo saques de ahí.
3. Compartir el enlace del bot con gente que no deba usarlo. El candado por ID ayuda, pero el enlace no se reparte.
4. Instalar el nodo en una computadora compartida o de un tercero. La persona dueña del equipo puede leer el `.env`.

---

## Referencia rápida

```powershell
# instalación completa desde cero
cd $HOME\Documents
git clone https://github.com/JULIANJUAREZMX01/KynicOS.git
cd KynicOS
.\nodo\instalar.ps1

# arrancar
.\.venv\Scripts\python.exe cli\kynikos.py run

# diagnóstico
.\.venv\Scripts\python.exe cli\kynikos.py doctor
.\.venv\Scripts\python.exe cli\kynikos.py telegram
.\.venv\Scripts\python.exe cli\kynikos.py doble-paso estado

# actualizar
git pull
```

Documentos relacionados: `docs/adr/ADR-025-verificacion-doble-paso.md` (cómo funciona el segundo factor), `docs/adr/ADR-026-instalador-windows-y-guia-de-arranque.md` (por qué existe esta guía), y la página operativa de la bóveda en `https://julianjuarezmx01.github.io/boveda.html`.
