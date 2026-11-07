# Estado actual de KynicOS — 6 de noviembre de 2026, 20:10

> Documento de contexto para cualquier persona o agente que retome el proyecto.
> Las reglas operativas viven en `AGENTS.md`; la memoria compartida, en
> `docs/agentes/MEMORIA.md`; los límites del nodo, en ADR-021, ADR-027 y ADR-030.

## 1. Qué es KynicOS hoy

El **asistente operativo de Julián Juárez**, en hardware propio con modelo local.
No es un concierge de hotel: los modos de concierge son personas opcionales
(ADR-037).

## 2. Estado verificado

| Área | Estado | Evidencia |
| --- | --- | --- |
| Nodo (Windows) | **Operativo** | `VALIDADO: el nodo esta escuchando a Telegram`; commit `66da6ef` |
| Proceso | Vivo | PID nuevo tras `reiniciar` (20112 → 21748), sin duplicados |
| Arranque | Idempotente | La tarea de inicio compara commit, verifica dependencias por huella y arranca si hace falta (ADR-033) |
| Actualización | Automática | `git fetch` + `--ff-only`; nunca `reset --hard`; con commits locales avisa y no toca nada |
| Diagnóstico | Honesto | Token con tres estados, desfase por hora de arranque, puerto sin depender del idioma (ADR-031 a ADR-033) |
| Autoconocimiento | Verificado | `/info` lee del sistema; el prompt lleva configuración real (ADR-036) |
| Intención | Corregida | Palabra completa; solo el último mensaje del usuario (ADR-035) |
| Enlaces | Vivos | App de rutas en Vercel (200); Render desactivado (503) |
| CI | Verde | Suite completa en verde |

## 3. PRs abiertos (6-nov-2026)

| Repositorio | PRs | Criterio |
| --- | --- | --- |
| `KynicOS` | 0 | Limpio |
| `KYNYKOS_AI_Agent` | 10 | Seguridad primero (#49, #19), luego rendimiento (#52, #50) |
| `MueveCancun` | 10 | Nueve `dependabot` agrupables; #596 aparte |
| `Wasm-Kalpixk_IA_DevOps` | 10 | Ocho de Sentinel; agrupar en un PR de seguridad |
| `cantabria-pms-demo` | 2 | `dependabot`, merge si CI verde |
| `JULIANJUAREZMX01.github.io` | 1 | #2, revisión de contenido |

Regla intacta: máximo un PR por persona y repo; nada se mergea sin revisión de
Julián.

## 4. Reglas que no se negocian

1. `AGENTS.md` es la fuente única de reglas. Ninguna persona opera con
   instrucciones que no estén ahí.
2. `docs/agentes/MEMORIA.md` guarda lo aprendido, versionado en git.
3. Máximo **un PR abierto por agente**.
4. `.env.example` documenta cada variable; los valores reales nunca entran al
   repositorio.
5. Nada de secretos en `PUBLIC_*`, `public/` ni historial de git.
6. La salud se mide por API y por polling, no por puerto (ADR-030).

## 5. Cómo se arranca y se valida

```powershell
cd $HOME\Documents\KynicOS
git fetch origin
git merge --ff-only origin/main
.\nodo\kynikos.ps1 reiniciar
.\nodo\kynikos.ps1 estado
```

`reiniciar` garantiza proceso nuevo; `reparar` solo actúa si detecta entorno
incompleto o proceso desfasado. Comandos, subcomandos y mapa de archivos:
`docs/ARRANQUE.md`.

## 6. Riesgos abiertos

1. **`/api/status` sin autenticación.** No exponer el nodo hasta protegerlo con
   la palabra de dos pasos (ADR-032).
2. **WhatsApp desactivado** por falta de credenciales de Twilio.
3. **Duplicación de `app/`** entre KynicOS y KYNYKOS_AI_Agent: intencional hoy
   (ADR-034), a revisar módulo por módulo.
4. **Render suspendido** por facturación: todo lo estático debe vivir en Pages o
   Vercel.
