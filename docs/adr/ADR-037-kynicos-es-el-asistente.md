# ADR-037 — KynicOS es el asistente del jefe, no un concierge

- **Fecha:** 6 de noviembre de 2026
- **Estado:** Aceptada e implementada
- **Modifica:** el posicionamiento del README y de `docs/ESTADO-ACTUAL.md`

## Contexto

El README abría con "Cognitive Operations System for Hospitality — Concierge,
Automation & AI Orchestration" y describía KynicOS como una plataforma para
hoteles en Cancún. Ese texto es de abril, cuando el proyecto era el motor de
concierge de Cantabria.

Desde entonces el nodo cambió de naturaleza: corre en la PC del jefe, atiende
solo a Julián por Telegram, administra su infraestructura, verifica versiones,
se actualiza solo y ejecuta skills técnicas. Un asistente personal. El
concierge es ahora uno de sus modos, no su identidad.

El desajuste tiene coste real: quien lee el README espera un producto hotelero y
no encuentra cómo se arranca un asistente; y el propio bot, cuando le preguntan
qué es, mezcla ambos papeles.

## Decisión

1. El README declara a KynicOS como **asistente operativo de Julián Juárez**.
2. Las personas heredadas (`leo` concierge, `mueve`, `nexus`) se mantienen como
   modos opcionales por `PERSONA=<nombre>`. El default es `kynicos`.
3. El caso hotelero se conserva como ejemplo de capacidad, no como propósito.
4. Se documentan en el README, con datos verificados, tres cosas que antes no
   estaban juntas: qué habilidades existen, qué canales y conectores están
   activos, y qué PRs hay pendientes de merge con su criterio.
5. Se añade un roadmap corto con lo inmediato, lo de mediano plazo y lo que
   requiere decisión del jefe.

## Consecuencias

- Coincide lo que el repositorio dice con lo que el nodo hace.
- Las menciones restantes a "concierge" son técnicas (`ConciergeAgentLoop`) o de
  personas opcionales: no cambian el posicionamiento.
- El roadmap deja explícito el orden: primero seguridad de `/api/status`, luego
  `/instalar`, después el triaje de PRs.
- Riesgo asumido: el ejemplo hotelero del README sigue ocupando espacio. Se
  conserva porque explica bien el ciclo conversación → acción verificable.
