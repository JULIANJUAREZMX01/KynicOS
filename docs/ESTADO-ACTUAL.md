# Estado actual de KynicOS — 3 de noviembre de 2026, 22:50

> Documento de contexto para cualquier persona o agente que retome el proyecto. Las reglas operativas viven en `AGENTS.md`; la memoria compartida, en `docs/agentes/MEMORIA.md`; los límites del nodo, en los ADR-021, ADR-027 y ADR-030.

## 1. Qué está pasando

| Área | Estado | Evidencia |
| --- | --- | --- |
| Nodo local (Windows) | Estable | PID vivo en el puerto 8000, `/api/status` responde con `agent_loop` y `telegram_token` en `true`; arranca solo con la tarea programada `KYNIKOS nodo` |
| Código | Activo | PR #5 (`fix/prompt-anti-alucinacion`): 13 archivos, +1500/-8, CI en verde |
| CI | Verde | `KynicOS Tests` y job `memoria` en verde sobre la rama del PR #5; los 6 fallos consecutivos de la tarde quedaron resueltos |
| PRs | 1 abierto | #5 en este repo; la regla de un PR por agente se respeta |
| Despliegue | Suspendido | Render acumula servicios suspendidos por facturación; lo estático migra a GitHub Pages según ADR-006 |

## 2. Reglas que no se negocian

1. `AGENTS.md` es la fuente única de reglas. Ninguna persona (Bolt, Sentinel, Palette, Speedy) opera con instrucciones que no estén ahí.
2. `docs/agentes/MEMORIA.md` guarda lo aprendido, versionado en git. Se actualiza al cerrar cada tarea.
3. Máximo **un PR abierto por agente**. Sin merge automático: el humano decide.
4. `.env.example` documenta cada variable. Los valores reales nunca entran al repositorio.
5. Nada de secretos en `PUBLIC_*`, `public/` ni historial de git.
6. **La salud se mide por API, no por puerto.** `agent_loop` y `telegram_token` en `/api/status` deciden; el puerto solo sirve para liberar duplicados (ADR-030).

## 3. Cómo se arranca y cómo se valida

Un solo comando, idempotente, sin preguntas:

```powershell
.\nodo\automatico.ps1
```

Qué hace, en orden: comprueba el `.venv` de la raíz, instala dependencias si faltan (`requirements.txt` y `requirements-bot.txt`), libera el puerto matando duplicados, arranca `cli\kynikos.py run` con stdout y stderr en archivos distintos, y espera hasta que `/api/status` devuelva `agent_loop=true` y `telegram_token=true`.

Para operar a mano: `.\nodo\CENTRO.ps1` (estado, arrancar, detener, reiniciar, logs, configuración, requisitos, reparar, reporte).

Reglas de convivencia:

- **Una sola instancia.** La dueña es la tarea programada `KYNIKOS nodo`. Arrancar otra a mano produce PIDs peleando el mismo long-poll.
- **Los scripts se ejecutan como archivo, nunca pegados línea por línea.** Pegados, `$MyInvocation.MyCommand.Definition` viene vacío y el script resuelve su raíz como `C:\Users\<usuario>`, creando entornos donde no van.
- **PowerShell exige `.\`** para todo lo que esté en la carpeta actual.

## 4. Fechas que mandan

- **11-nov-2026:** Jules pasa a solo lectura. Todo lo que solo viva en su consola o en `.jules/` deja de ser accesible ese día.
- **31-dic-2026:** Jules se apaga. Lo que no esté documentado se pierde.

Migración detallada: `docs/agentes/MIGRACION-JULES-Y-BUCLE-KYNICOS.md` en el repo de estándares.

## 5. Bucle de entrenamiento (el objetivo de KynicOS)

1. **Ingesta** de `AGENTS.md`, `docs/agentes/MEMORIA.md` y `ROADMAP_AMD.md`.
2. **Propuesta** en un PR con rama descriptiva.
3. **Contraste** contra los ADR vigentes y los gates de CI.
4. **Prueba** primero en `Wasm-Kalpixk_IA_DevOps` (build + tests + humo) y luego en el resto.
5. **Registro** en `MEMORIA.md` y decisión humana.
6. **Medición** con los monitores de 6 horas (DACC y RC Caribe).

Señal de salud: un PR por agente, CI en verde y `MEMORIA.md` creciendo con decisiones, no con transcripciones.

## 6. Qué falta

1. Fusionar el PR #5. Es decisión humana y es el único paso que separa al nodo de la validación honesta.
2. Conectar `app/core/ecosystem.py` al bucle de herramientas (`app/core/tools.py`), hoy disponible pero desconectado.
3. Drenar el backlog de PRs de Kalpixk y MueveCancun.
4. Cerrar la migración de Jules antes del 11-nov.
5. Resolver el hosting: Pages para lo estático, y decidir Worker o Render para el bot.

## 7. Monitoreo

Cada 6 horas se guardan snapshots verificables (repos, CI, proyectos, correos de claves y accesos) y se entregan como reporte ejecutivo. Lo que no se puede verificar sin credenciales (Render, créditos de AMD) se reporta como limitación, nunca como dato.
