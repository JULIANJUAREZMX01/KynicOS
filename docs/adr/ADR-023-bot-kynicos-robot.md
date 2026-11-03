# ADR-023 — Bot `@kynicOS_robot`: el canal definitivo del nodo primario

- **Fecha:** 3 de noviembre de 2026
- **Estado:** Aceptada e implementada (canal verificado; nodo pendiente de arranque)
- **Relacionado:** ADR-020, ADR-021, ADR-022

## Contexto

El primer token entregado correspondía a un bot creado por la plataforma (`@b44_6221857b05e8870c_bot`) cuyo webhook apuntaba a una aplicación inexistente, lo que impedía usar polling en el nodo propio. Se ofrecieron dos salidas: liberar ese webhook o crear un bot nuevo. Julián eligió la segunda, que es la correcta: un bot propio desde BotFather no arrastra dependencias de la plataforma y sobrevive a cualquier cambio de infraestructura.

## Decisión

`@kynicOS_robot` (id 9197997173, nombre visible `kynicOS.dev`) es el canal oficial del nodo primario.

### Verificado

| Comprobación | Resultado |
| --- | --- |
| `getMe` | Válido: `@kynicOS_robot`, id 9197997173 |
| `getWebhookInfo` | Sin webhook: modo polling disponible |
| Descripción del perfil | Configurada |
| Descripción corta | Configurada |
| Comandos | `/estado`, `/modelo`, `/reiniciar`, `/ayuda` |

### Hallazgo sobre el token reenviado

El segundo token recibido, guardado por la plataforma como `TELEGRAM_BOT_TOKEN_5`, devuelve **`Not Found`**: no es válido. El operativo es el anterior (`TELEGRAM_BOT_TOKEN_4`). Conviene descartar el duplicado inválido para no confundir futuras sesiones.

### Pendiente que solo depende del propietario

`sendMessage` al id 8247886073 devuelve `chat not found`, que en Telegram significa una sola cosa: **el propietario aún no ha iniciado conversación con el bot**. Un bot no puede escribir primero a quien nunca le habló. Se resuelve abriendo `t.me/kynicOS_robot` y pulsando **Iniciar**.

Después de eso, el orden correcto es: arrancar el nodo en la PC (`kynikos run`) y escribirle al bot. Antes de arrancar, el bot recibe pero nadie responde.

## CLI ampliado

`kynikos telegram --configurar` deja el perfil del bot listo de forma idempotente (descripción, descripción corta y comandos). Además, el CLI acepta el alias `TELEGRAM_BOT_TOKEN` para leer el token desde el entorno, no solo `TELEGRAM_TOKEN`.

## Consecuencias

- El canal de Telegram ya no depende de Base44 ni de un webhook ajeno: es un bot independiente con polling al nodo propio.
- Con el nodo apagado el bot queda mudo, pero no roto: al arrancar retoma el polling sin configuración adicional.
- Queda pendiente la prueba de extremo a extremo, que requiere el nodo encendido y `/start` del propietario.
