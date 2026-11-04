
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
