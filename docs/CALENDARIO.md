
## 3 nov 2026 (noche) — KYNIKOS deja de ser concierge
- Persona KYNIKOS como default (ADR-020); LEO queda como modo opcional
- Canal nuevo por webhook para serverless: app/channels/telegram_webhook.py + api/index.py
- Fusionadas de nanobot: sessions.py, backup_service.py, scripts y pruebas
- Corregido empaquetado: faltaban tenacity y loguru en requirements-bot.txt
- Pendiente del jefe: token de BotFather y elegir VPS con Ollama o Vercel con webhook

## 3 nov 2026 (noche) — KYNIKOS nodo primario (ADR-021)
- Canal web nuevo: POST /api/chat + historial + reinicio, probado en local
- PWA en web/: chat, IndexedDB, busqueda WASM con respaldo JS y Service Worker offline
- Crate wasm-busqueda (Rust + wasm-bindgen) listo para compilar en la PC del jefe
- MCP ampliado a 11 herramientas y mcp-servers.json con 5 servidores (Context7 + 4 internos)
- nodo/instalar.sh + kynikos.service: un comando deja la PC como nodo con Ollama
- Límite confirmado: el nodo local no consume créditos de Base44; los créditos se reservan a trabajo complejo

## 3 nov 2026 — calibración al nodo real (Ryzen 5 5500U / 16 GB)
- Medido: ~45 GB/s de ancho de banda → 5-8 tok/s en 7B Q4, 3 tok/s en 14B Q4, 1.4 tok/s en 32B
- Techo: 14B Q4 cabe (8.9 GB de 11.9 libres); 20B y 32B no caben; con 32 GB sí cabría 32B al límite
- Ajustado: max_tokens_salida 2048→768, timeout LLM 120→300s, num_ctx 4096 en OllamaProvider
- PWA: timeout de 120 s a 300 s para no cortar respuestas de modelo local

## 3 nov 2026 (noche) — CLI de instalación configurable (ADR-022)
- Nuevo cli/kynikos.py: doctor, plan, init, telegram, install, run, status, models, config, service
- Planificador con criterio medible: solo modelos >=4 tok/s; desempate por calidad en español
- Verificado en 3 escenarios: 16 GB → qwen2.5:7b; 24 GB VRAM → qwen2.5:32b; 8 GB → qwen2.5:3b
- Hallazgo: el bot @b44_6221857b05e8870c_bot es válido pero su webhook apunta a una app inexistente (huérfano)
- Pendiente de decisión: liberar ese webhook o crear bot nuevo en BotFather para el nodo

## 3 nov 2026 (noche) — bot definitivo @kynicOS_robot (ADR-023)
- Bot propio desde BotFather: id 9197997173, @kynicOS_robot, sin webhook (polling disponible)
- Perfil configurado: descripcion, descripcion corta y comandos /estado /modelo /reiniciar /ayuda
- CLI ampliado: kynikos telegram --configurar y alias TELEGRAM_BOT_TOKEN
- Token reenviado _5 invalido (Not Found); el operativo es _4: descartar el duplicado
- Pendiente del jefe: pulsar /start en t.me/kynicOS_robot y arrancar el nodo en la PC

## 3 nov 2026 (noche) — verificación de doble paso (ADR-025)
- Nuevo app/security/doble_paso.py: palabra clave, notificación con botones, palabra efímera de un solo uso
- 25/25 pruebas de lógica + integración con TestClient sin red
- Bug corregido: un return mal indentado aprobaba cualquier palabra; detectado por las pruebas
- Webhook acepta callback_query y reutiliza solicitud pendiente (una sola notificación)
- CLI: kynikos doble-paso estado|solicitar|verificar

## 3 nov 2026 (noche) — arranque en Windows documentado (ADR-026)
- `nodo/instalar.ps1`: instala Python/Ollama, descarga modelo, crea .env con token por entrada oculta
- `nodo/arranque-todo-en-uno.ps1`: bloque único de cinco pasos con verificación de configuración
- `docs/GUIA-ARRANQUE-WINDOWS.md`: pasos, tabla de configuración y problemas comunes
- Pendiente real: ejecutarlo en la PC para confirmar el arranque (aquí no hay PowerShell)

## 3 nov 2026 (noche, cierre) — arranque validado por comportamiento
- `nodo/arrancar-y-validar.ps1`: limpia tarea vieja, actualiza, instala, arranca y valida con el error 409 de Telegram
- Guía reducida a tres bloques con validación explícita; página `kynikos.html` reescrita al mismo flujo
- Pendiente: que Julián ejecute el bloque 2 en la PC (aquí no hay PowerShell)

## 4 nov 2026 — Orquestador único del nodo (ADR-027)

- `nodo/kynikos.ps1` concentra instalación, configuración, arranque, validación,
  diagnóstico y arranque automático. El resto de scripts son alias.
- Pendiente en la PC de Julián: ejecutar `.
odo\kynikos.ps1` y confirmar con
  `/estado` en @kynicOS_robot.
- Siguiente: replicar en las demás computadoras usando `doctor` para elegir
  modelo según RAM.

## 3 nov 2026 - Nodo KynicOS operativo en la PC de Julián

- @kynicOS_robot responde en Telegram con qwen2.5:7b sobre Ollama, en la PC
  "patricia73" (Ryzen 5 5500U, 16 GB). Polling activo en el puerto 8000.
- Orquestador unico `nodo/kynikos.ps1` (ADR-027); los seis scripts previos son alias.
- Pendiente: registrar el arranque automatico (`kynikos.ps1 tarea`) y confirmar
  que responde tras reiniciar Windows.
- Falso negativo corregido: la validacion ya no usa getUpdates, que robaba
  mensajes al bot y fallaba mientras este procesaba uno.
| 2026-11-04 | Nodo KynicOS | Unificacion: automatico.ps1 pasa a alias, se corrige $pid (variable de solo lectura) y CIM/netstat protegidos. Validado con pwsh real instalado en el sandbox. |
| 2026-11-04 | Nodo KynicOS | Barrido: 9 formas de arrancar, 3 orquestadores y 6 documentos con comandos distintos. Se declara `kynikos.ps1` llave maestra única y `docs/ARRANQUE.md` fuente única (ADR-031). |
| 2026-11-04 | Nodo KynicOS | ADR-032: una sola llave (alias a legacy/), evaluacion de capas visuales (panel web > rich > textual > ratatui) y el tunel queda condicionado a autenticacion previa. |
| 2026-11-04 | Nodo KynicOS | Arranque idempotente (ADR-033): la tarea de inicio actualiza el repo, verifica dependencias por huella y arranca solo si hace falta. Nada se borra. Nuevo /version en el bot. |
| 2026-11-06 | Repos | Validada la distincion KynicOS (nodo primario, hardware propio, @kynicOS_robot) frente a KYNYKOS_AI_Agent (agente de nube, motor de herramientas grande, personas Jules). ADR-034. |
| 2026-11-06 | Nodo KynicOS | Actualizacion bloqueada por un ADR-034 sin versionar en la PC del jefe. La llave maestra ya aparta esos archivos como .local-<fecha> y reintenta, sin borrar nada. |
| 2026-11-06 | Nodo KynicOS | Falso negativo del puerto: netstat en Windows en espanol dice ESCUCHANDO, no LISTENING. Detectado porque uvicorn decia "running on 0.0.0.0:8000" mientras la validacion decia puerto:False. Ahora usa Get-NetTCPConnection y el polling como prueba. |
| 2026-11-06 | Nodo KynicOS | El bot contestaba rutas a quien saludaba: la skill de transporte detectaba por substring (el "bus" de "busco"). Deteccion por palabra completa, solo mensaje del usuario, y enlaces movidos de Render (503) a Vercel (200). |
| 2026-11-06 | Nodo KynicOS | El bot inventaba su propia configuracion (decia que su modelo era Ollama y daba una URL de GitHub inexistente). Modulo app/core/autoconocimiento.py inyecta datos verificados en el system prompt y expone /info. |
| 2026-11-06 | Nodo KynicOS | `reparar` decia "nada que reparar" y no reiniciaba: el menu de Telegram mostraba /info pero el proceso vivo corria el codigo anterior. Ahora sella el commit al arrancar, avisa cuando el proceso esta desfasado y reinicia. |
| 2026-11-06 | Nodo KynicOS | `estado` decia "sin token valido" con el bot respondiendo: un fallo de red se pintaba igual que un token revocado. Y `reparar` creia estar al dia por un sello en disco. Ahora el token tiene tres estados y el desfase se mide por la hora de arranque del proceso. |
| 2026-11-06 | Nodo KynicOS | `reparar` seguia creyendo al sello de disco y decia estar al dia con un PID sin reiniciar. Ahora manda la hora de arranque del proceso, y se añade la accion `reiniciar` que detiene y arranca sin diagnosticar: reinicio garantizado. |

## 6 nov 2026 — auditoría de repos, PRs y reposicionamiento
- KynicOS deja de presentarse como concierge de hotel: es el asistente de Julián (ADR-037)
- Barrido de PRs: KynicOS 0 · KYNYKOS_AI_Agent 10 · MueveCancun 10 (9 dependabot) · Wasm-Kalpixk 10 · cantabria-pms-demo 2 (dependabot) · portafolio 1
- README reescrito con estado verificado, 6 skills, canales/conectores y roadmap por plazos
- Nodo operativo en commit 66da6ef, con /info y reinicio garantizado
- Próximos pasos: proteger /api/status, /instalar en el bot, triaje de seguridad en KYNYKOS_AI_Agent
| 2026-11-06 | Nodo KynicOS | "El bot no responde": dos procesos del nodo (13644 y 21748) peleando por el mismo token de Telegram (409). Paso-Detener ahora mata todos los procesos del nodo y estado avisa de duplicados. ADR-038. |
| 2026-11-06 | Repos | /info verificado en Telegram (ficha real, commit y ruta correctos). Actualizada la descripcion del repositorio en GitHub, que aun decia Concierge de Ultra-Lujo. La RAM ya se lee del sistema sin psutil. |
| 2026-11-06 | Nodo KynicOS | /reiniciar dejaba el bot mudo: detenia el updater desde su propio handler y la tarea se cancelaba a si misma, asi que start nunca corria. Ahora solo confirma el polling y remite al reinicio desde la PC. ADR-039. |
| 2026-11-06 | Nodo KynicOS | Cerradas las dos deudas de fondo (ADR-040): /api/status exige token y falla cerrado con 503 sin el; /api/health es publico y minimo; nuevo /instalar diagnostica los registros con ocho patrones reales, sin modelo. Suite 49. |
| 2026-11-06 | Nodo KynicOS | Los dos PIDs con la misma hora eran padre e hijo: cli/kynikos.py lanzaba python -m app.main. Ahora se lanza el servidor directo, un proceso por nodo. /api/status deja de inventar: whatsapp segun Twilio, skills leidas del disco, deploy_url del entorno. |
| 2026-11-06 | Nodo KynicOS | Inventario de la superficie publica antes de publicar (ADR-041): /api/persona estaba abierta y pasa a exigir token; el router de chat web exige token cuando hay; queda publica solo la PWA y /api/health. La apertura del tunel la ejecuta Julian en su maquina. |
| 2026-11-06 | Nodo KynicOS | Tunel publico verificado desde fuera: PWA 200, /api/health 200 minimo, /api/status y /api/persona 401 sin token. El arranque ahora comprueba que el PID lanzado es el que atiende: antes decia 23848 con 23632 respondiendo y la validacion pasaba igual. |
| 2026-11-06 | Nodo KynicOS | PWA con login por token (ADR-042): campo de token guardado en localStorage, cabecera X-Kynikos-Token en cada peticion, boton Olvidar token y cinco estados de nodo. Deja de llamar a /api/telegram/salud, que no existe en el nodo local, y usa health + status. |
| 2026-11-06 | Nodo KynicOS | Publicacion en un solo comando (ADR-043): nodo/publicar.ps1 actualiza, reinicia, verifica PID y token, y solo entonces abre el tunel. Verificado en tres casos con nodo simulado; corregido el retorno contaminado de la funcion que invocaba el nodo. |
| 2026-11-06 | Nodo KynicOS | Canal web montado en el nodo local (ADR-044): /api/chat solo existia en el despliegue serverless, asi que la PWA recibia 404 y mostraba (sin respuesta) con el nodo sano. Verificado 401 sin token y 200 con token. |
| 2026-11-06 | Nodo KynicOS | Corregido el reinicio (ADR-045): el script usaba $PID como variable de iteracion y es automatica de solo lectura, asi que abortaba con "no se puede sobrescribir". Ademas el PID 0 se trataba como proceso y sugeria Stop-Process -Id 0. Ahora se filtra el 0 y, si el puerto esta ocupado sin PID visible, se pide Get-NetTCPConnection. |
| 2026-11-06 | Nodo KynicOS | Una sola persona por defecto (ADR-046): /start usaba os.getenv("PERSONA", "leo") y el resto Settings().persona = kynicos. Con el .env sin PERSONA, el saludo hablaba como Leo mientras los logs decian KYNIKOS. Ahora todos leen la misma fuente. |
