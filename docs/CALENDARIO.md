
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
