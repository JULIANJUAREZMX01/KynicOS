# Estado actual de KynicOS — 3 de noviembre de 2026

> Documento de contexto para cualquier persona o agente que retome el proyecto. Las reglas operativas viven en `AGENTS.md`; la memoria compartida, en `docs/agentes/MEMORIA.md`.

## 1. Qué está pasando

| Área | Estado | Evidencia |
| --- | --- | --- |
| Código | Activo | 8 commits el 3-nov; último `d3d5572` (bot @kynicOS_robot configurable desde el CLI, ADR-023) |
| Despliegue | Suspendido | Render acumula servicios suspendidos por facturación; el sitio público migra a GitHub Pages según ADR-006 |
| CI | Rojo | `KynicOS Tests` falló 6 veces consecutivas el 3-nov, entre 21:26 y 22:22 UTC |
| PRs | Backlog alto | 0 abiertos en este repo; 30 en Kalpixk, 13 en MueveCancun y 8 en KYNYKOS_AI_Agent |

## 2. Reglas que no se negocian

1. `AGENTS.md` es la fuente única de reglas. Ninguna persona (Bolt, Sentinel, Palette, Speedy) opera con instrucciones que no estén ahí.
2. `docs/agentes/MEMORIA.md` guarda lo aprendido, versionado en git. Se actualiza al cerrar cada tarea.
3. Máximo **un PR abierto por agente**. Sin merge automático: el humano decide.
4. `.env.example` documenta cada variable. Los valores reales nunca entran al repositorio.
5. Nada de secretos en `PUBLIC_*`, `public/` ni historial de git.

## 3. Fechas que mandan

- **11-nov-2026:** Jules pasa a solo lectura. Todo lo que solo viva en su consola o en `.jules/` deja de ser accesible ese día.
- **31-dic-2026:** Jules se apaga. Lo que no esté documentado se pierde.

Migración detallada: `docs/agentes/MIGRACION-JULES-Y-BUCLE-KYNICOS.md` en el repo de estándares.

## 4. Bucle de entrenamiento (el objetivo de KynicOS)

1. **Ingesta** de `AGENTS.md`, `docs/agentes/MEMORIA.md` y `ROADMAP_AMD.md`.
2. **Propuesta** en un PR con rama descriptiva.
3. **Contraste** contra los ADR vigentes y los gates de CI.
4. **Prueba** primero en `Wasm-Kalpixk_IA_DevOps` (build + tests + humo) y luego en el resto.
5. **Registro** en `MEMORIA.md` y decisión humana.
6. **Medición** con los monitores de 6 horas (DACC y RC Caribe).

Señal de salud: un PR por agente, CI en verde y `MEMORIA.md` creciendo con decisiones, no con transcripciones.

## 5. Qué falta para que el bucle arranque

1. Poner `KynicOS Tests` en verde. Sin CI confiable no hay autocorrección posible.
2. Drenar el backlog de PRs de Kalpixk y MueveCancun.
3. Cerrar la migración de Jules antes del 11-nov.
4. Resolver el hosting: Pages para lo estático, y decidir Worker o Render para el bot.

## 6. Monitoreo

Cada 6 horas se guardan snapshots verificables (repos, CI, proyectos, correos de claves y accesos) y se entregan como reporte ejecutivo. Lo que no se puede verificar sin credenciales (Render, créditos de AMD) se reporta como limitación, nunca como dato.
