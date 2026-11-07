# ADR-050: Convertir el Markdown del modelo a HTML de Telegram

## Contexto
Los modelos locales (qwen2.5:7b) contestan en Markdown. El bot enviaba el texto
sin parse_mode y Telegram mostraba literales los `###`, los `**negrita**` y los
enlaces `[txt](url)`. Verificado en capturas del 2026-11-06.

## Decision
- `app/core/formato.py`: `md_a_html_telegram()` convierte titulos, negrita,
  cursiva, vinetas, codigo y enlaces a las etiquetas que Telegram acepta. Lo
  demas se escapa, asi que un `<` suelto nunca rompe el parseo.
- `_enviar_respuesta()` trocea a 3500 caracteres (margen por las etiquetas) y,
  si Telegram rechaza el HTML, reenvia ese trozo en texto plano.

## Consecuencias
- Las respuestas se leen con formato; la respuesta nunca se pierde por un error de parseo.
- Alcance: solo el canal Telegram. WhatsApp usa otro formato y queda fuera.
- No se toca el prompt del modelo: el formato se resuelve al enviar, no pidiendole al 7B que obedezca.
