# ADR-041 — Qué queda expuesto si se publica el nodo

- **Fecha:** 6 de noviembre de 2026
- **Estado:** Aceptada e implementada (protección); publicación manual del jefe

## Contexto

Con `/api/status` protegido (ADR-040), el paso siguiente era publicar el nodo con
dominio propio. Antes de hacerlo hay que saber **exactamente qué quedaría a la
vista**, porque publicar no es un cambio de código: es abrir una puerta.

Inventario de rutas del nodo local:

| Ruta | Antes | Ahora |
| --- | --- | --- |
| `/` (PWA en `web/`) | Abierta | Abierta — es la interfaz, no expone datos |
| `/api/health` | No existía | Pública y mínima (`{"ok":true}`) |
| `/api/status` | **Abierta** | Token obligatorio, 503 sin configurar |
| `/api/persona` | **Abierta** | Token obligatorio |
| `/api/webhook/whatsapp` | Secret | Sin cambios |
| `/api/chat` | No existe en el nodo | Se protege igual: el router solo se monta en `api/index.py` |

`/api/persona` era el hueco olvidado: publicaba nombre, tono, idioma y saludo del
bot sin autenticación. No es un dato crítico, pero tampoco hay razón para
regalarlo.

## Decisión

1. `/api/persona` exige el mismo `KYNIKOS_API_TOKEN` que `/api/status`.
2. El router de chat web (`/api/chat`, `/api/chat/historial`,
   `/api/chat/reiniciar`) exige el token **cuando está configurado**. Si no lo
   está, permite el paso: eso solo ocurre en una instalación recién hecha, sin
   exposición, y romper el arranque por eso sería peor.
3. La publicación del nodo **no se automatiza desde este entorno**. Los túneles
   de acceso remoto son una operación del jefe en su máquina, con dos comandos.
4. Se documenta el inventario de arriba para que publicar sea una decisión
   informada y no una sorpresa.

## Consecuencias

- Verificado: `/api/persona` responde 401 sin token y 200 con él.
- Con el nodo publicado quedan visibles la PWA y el latido de salud. Nada más.
- El webhook de WhatsApp sigue validando su secret; no depende de este token.
- Riesgo residual: la PWA no tiene login. Publicar la interfaz permite a
  cualquiera verla, aunque no puede hablar con el nodo porque el chat no está
  montado. Si más adelante se monta, ya exige token.
