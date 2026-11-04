# Memoria compartida de agentes — KynicOS

> Una sola bitácora para todos los agentes y herramientas. Léela antes de trabajar; agrega UNA entrada al terminar.
> Formato: fecha · área · problema · técnica · resultado. No dupliques. Esta memoria sobrevive aunque cambie la herramienta.

| Fecha | Área | Problema | Técnica aplicada | Resultado |
|---|---|---|---|---|
| 2026-11-03 | Inicio | Memoria creada | Sembrada al migrar de Jules | Pendiente de aprendizajes |
| 2026-11-03 | Nodo / Windows | El instalador solo existía para Linux y Mac; el nodo no arrancaba en la PC real (Windows) | `nodo/instalar.ps1` + `nodo/arranque-todo-en-uno.ps1` + `docs/GUIA-ARRANQUE-WINDOWS.md`; token por entrada oculta, política de ejecución solo por proceso | Camino de instalación para Windows, validado por análisis estático (sin pwsh en el sandbox) |
| 2026-11-03 | Nodo / Windows | Primer arranque real: `.venv` inexistente, `ObjectNotFound`. El instalador salía con `exit 0` tras instalar Python/Ollama y la guía ponía «Actualizar» sin condicionar | PATH refrescado en sesión, `exit 1` con aviso en rojo, verificación dura de `.venv`, advertencia de orden en la guía | Corregido en `nodo/instalar.ps1`; pendiente reintento del usuario |
| 2026-11-03 | Nodo / Windows | Tarea programada en `Ready` sin entorno: falso éxito, el nodo no corría | `registrar-tarea.ps1`: exige .venv y .env, reintentos, y comprueba proceso vivo a los 8 s | Verificar siempre el comportamiento (Telegram sin acumular), no el estado del Programador |
