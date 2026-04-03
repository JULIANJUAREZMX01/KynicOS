# 🚀 KynicOS × AMD MI300X — Roadmap de Convergencia

> **Estado:** Monorepo convergido ✅ | AMD GPU: pendiente activación
> **Repo canónico:** https://github.com/JULIANJUAREZMX01/KynicOS

---

## 📦 Repos convergidos en KynicOS

| Repo | Estado | Qué aportó |
|------|--------|------------|
| `KYNYKOS_AI_Agent` | ✅ Portado | Skills: last30days, web_research, skill_builder, memory_manager. Core: sentinel, skill_engine, explorer |
| `nanobot-cloud` | ✅ Origen | Arquitectura base (Groq/Anthropic router, Telegram bot, WhatsApp bridge) |
| `KynicOS` | ✅ **CANONICAL** | Todo converge aquí. Personas: leo/nexus/mueve |
| `MueveCancún` | 🔗 Integrado vía skill | `app/skills/mueve_cancun.py` ya listo |
| `SAC` | 📋 Fase 2 | Módulos de DB2, anomaly detector, email engine → cuando AMD esté listo |
| `SAC_OS` | 🗄️ Archivado | Base histórica, migrada a SAC |

---

## 🏗️ Arquitectura AMD-Ready

```
[Telegram/WhatsApp] → [KynicOS FastAPI]
                              │
                    [LLM Router — llm_config.yaml]
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
  AMD MI300X           Groq (free)         Anthropic
  (vLLM local)        llama-3.3-70b      claude-haiku
  PRIORITY 1          PRIORITY 3         PRIORITY 4
  $0/token            $0 (límite)         fallback
         │
   192 GB VRAM
   8x MI300X
   llama3.1:70B
```

### Activar AMD cuando esté listo el droplet:
```bash
# En Render.com → Environment Variables de KynicOS:
AMD_VLLM_URL=http://<ip-droplet>:8000/v1
# Luego en config/llm_config.yaml:
# amd_vllm.enabled: true
```

---

## 🏆 Concursos AMD activos

### 1. Code for Hardware ROCm Challenge 🎯 PRIORIDAD ALTA
**Premio:** HP Strix Halo 128GB laptop
**Estrategia:** Submit KynicOS como agente multidominio corriendo en ROCm
- Leo (concierge turístico) + MueveCancún + HVAC triage
- Narrativa: "El primer OS de hospitalidad hotelera sobre AMD MI300X"
- **Deadline:** Revisar en developer.amd.com

### 2. Lemonade Developer Challenge
**Premio:** HP Strix Halo 128GB laptop  
**Estrategia:** Demo de inferencia local con vLLM en AMD GPU

### 3. E2E Kernel Speedrun ($1M)
**Estrategia:** Fase 3 — después de completar cursos AMD AI Academy

---

## 📚 Plan DeepLearning.AI (código AMDAIDEV43)

| Curso | Puntos AMD | Relevancia |
|-------|-----------|------------|
| Complete Profile | +100 pts | ⚡ Ya disponible |
| Fine-Tune LoRA en AMD | +200 pts | Para iDoctor custom model |
| Run LLMs on AMD GPUs | +200 pts | Para activar vLLM en MI300X |
| DeepSeek con SGLang | +200 pts | Alternativa a vLLM |
| Inference Serving AMD | +200 pts | Producción |
| **5 cursos bonus** | +100 pts | Total: **1,000 pts** |

---

## 📅 Timeline 30 días

### Semana 1 — AMD Setup (cuando se liberen GPUs)
- [ ] SSH key generada y pegada en AMD Developer Cloud
- [ ] VM activada con Quick Start: vLLM + ROCm
- [ ] `AMD_VLLM_URL` configurado en Render → KynicOS apuntando a GPU local
- [ ] Benchmark: tokens/s con Llama 3.1 70B

### Semana 2 — KynicOS Production
- [ ] Leo corriendo con 70B local (cero costo de API)
- [ ] MueveCancún integrado en contexto del concierge
- [ ] SAC anomaly detector portado como skill

### Semana 3 — Fine-tuning iDoctor
- [ ] Dataset: 45 Q&A → generados con 70B → 500+ pares
- [ ] Fine-tune Qwen2.5-7B en MI300X
- [ ] Deploy como modelo iDoctor permanente

### Semana 4 — Submit concursos
- [ ] Code for Hardware ROCm Challenge submission
- [ ] Video demo: KynicOS en MI300X
- [ ] Blog post en AMD Developer Portal (+puntos)

---

## 🔑 Variables de entorno (Render → KynicOS)

```bash
# Actuales (ya configuradas)
TELEGRAM_BOT_TOKEN=...
GROQ_API_KEY=...
ANTHROPIC_API_KEY=...
PERSONA=leo

# Agregar cuando AMD esté listo
AMD_VLLM_URL=http://<ip>:8000/v1
OLLAMA_URL=http://<ip>:11434  # alternativa

# Agregar Fase 2 (SAC)
DB2_HOST=...
DB2_DATABASE=...
DB2_USER=...
DB2_PASSWORD=...
```

---

*Generado por el agente — $(date +%Y-%m-%d)*
*KynicOS v1.1 — Convergencia completada*

