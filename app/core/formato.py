"""Markdown del modelo a HTML de Telegram.

Los modelos locales escriben Markdown (### titulos, **negrita**, [txt](url)) y
Telegram, sin parse_mode, lo muestra literal. Aqui se convierte a las pocas
etiquetas que Telegram acepta. Todo lo demas se escapa, asi que el resultado
nunca rompe el parseo por un '<' suelto.
"""
import html
import re

_CODIGO_BLOQUE = re.compile(r"```[a-zA-Z0-9_+-]*\n?(.*?)```", re.S)
_CODIGO_LINEA = re.compile(r"`([^`\n]+)`")
_ENLACE = re.compile(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)")
_NEGRITA = re.compile(r"\*\*(.+?)\*\*", re.S)
_NEGRITA_2 = re.compile(r"__(.+?)__", re.S)
_CURSIVA = re.compile(r"(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])")
_TITULO = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", re.M)
_VINETA = re.compile(r"^(\s*)[-*]\s+", re.M)


def md_a_html_telegram(texto: str) -> str:
    """Convierte Markdown basico a HTML de Telegram, escapando el resto."""
    if not texto:
        return ""
    guardados: list[str] = []

    def _guardar(fragmento: str) -> str:
        guardados.append(fragmento)
        return f"\x00{len(guardados) - 1}\x00"

    # 1) El codigo se aparta primero: dentro no se interpreta nada.
    texto = _CODIGO_BLOQUE.sub(lambda m: _guardar(f"<pre>{html.escape(m.group(1).strip())}</pre>"), texto)
    texto = _CODIGO_LINEA.sub(lambda m: _guardar(f"<code>{html.escape(m.group(1))}</code>"), texto)
    # 2) Enlaces: se aparta tambien, con la URL escapada para el atributo.
    texto = _ENLACE.sub(
        lambda m: _guardar(f'<a href="{html.escape(m.group(2), quote=True)}">{html.escape(m.group(1))}</a>'),
        texto,
    )
    # 3) Escapar todo lo que quede, luego aplicar el formato.
    texto = html.escape(texto, quote=False)
    texto = _TITULO.sub(r"<b>\1</b>", texto)
    texto = _NEGRITA.sub(r"<b>\1</b>", texto)
    texto = _NEGRITA_2.sub(r"<b>\1</b>", texto)
    texto = _CURSIVA.sub(r"<i>\1</i>", texto)
    texto = _VINETA.sub(r"\1• ", texto)
    # 4) Restaurar lo apartado.
    return re.sub(r"\x00(\d+)\x00", lambda m: guardados[int(m.group(1))], texto)
