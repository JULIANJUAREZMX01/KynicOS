# KynicOS 🏨

**Sistema Operativo para Concierge de Ultra-Lujo en Cancún**

Monorepo unificado que fusiona:
- `nanobot-cloud` — Agent loop + Telegram + Groq/Anthropic
- `KYNYKOS_AI_Agent` — WhatsApp bridge (Twilio) + LLM router
- Skills propios — HVAC Triage + MueveCancún transport routing

Desplegado en Render: **https://nanobot-cloud-zjr0.onrender.com**

---

## Personas / Modos de Operación

| Persona | Variable | Descripción |
|---------|----------|-------------|
| `leo` | `PERSONA=leo` | Concierge de lujo para turistas (MVP Nexus Pilot) |
| `nexus` | `PERSONA=nexus` | Superagente personal de Julián (admin/dev) |
| `mueve` | `PERSONA=mueve` | Guía de transporte MueveCancún |

---

## Stack Técnico

- **LLM**: Groq (Llama 3.3 70B) → Anthropic Claude (fallback) — **$0 costo**
- **Channels**: Telegram Bot + WhatsApp (Twilio)
- **Skills**: HVAC Triage, MueveCancún routing
- **Deploy**: Render (servicio existente reutilizado)
- **Fase 2**: PostgreSQL + Stripe Connect (splits 70/25/5%)

---

## Deploy Rápido (actualizar servicio Render existente)

```bash
# 1. Clonar KynicOS
git clone https://github.com/JULIANJUAREZMX01/KynicOS.git
cd KynicOS

# 2. Copiar y configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Correr localmente
PERSONA=leo uvicorn app.main:app --reload

# 5. Push a main para auto-deploy en Render
git push origin main
```

---

## Configuración de Variables de Entorno en Render

Ir a: https://dashboard.render.com/web/srv-d6b9sihr0fns739m446g/env

Variables mínimas para arrancar:
- `PERSONA` = `leo`
- `TELEGRAM_TOKEN` = tu token de @BotFather
- `GROQ_API_KEY` = tu key de groq.com (gratis)
- `ANTHROPIC_API_KEY` = fallback

Variables para WhatsApp:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`

Variables para escalación de mantenimiento:
- `TECH_TELEGRAM_CHAT_ID` = chat_id del técnico

---

## Flujo de Mensajes

```
Huésped (WhatsApp/Telegram)
         ↓
  ConciergeAgentLoop
         ↓
  ┌──────────────────────────┐
  │ ¿Es problema de HVAC/AC? │ → Skill HVAC Triage → Respuesta + Telegram al técnico
  │ ¿Pregunta de transporte? │ → Skill MueveCancún → Rutas + Link app
  │ Pregunta general         │ → LLM (Groq/Claude) con prompt Leo
  └──────────────────────────┘
```

---

## Fase 2 (próximas semanas)
- [ ] PostgreSQL: guests, transactions, maintenance_tickets
- [ ] Stripe Connect: cobros one-click + splits 70/25/5%
- [ ] RAG con ChromaDB: manuales HVAC + menús + protocolos
- [ ] Dashboard multi-hotel (React + WebSocket)

---

**Arquitecto:** Julián Juárez | UNT TEAM | Cancún, México
