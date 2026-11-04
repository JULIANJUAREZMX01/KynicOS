"""Logging configuration"""

import sys
from loguru import logger as _logger


def _asegurar_utf8() -> None:
    """La consola de Windows usa cp1252 y revienta con ✅ o ·.

    El nodo escribe emojis en los logs; sin esto, cada línea con un carácter
    fuera de cp1252 lanza UnicodeEncodeError y puede tumbar el arranque.
    """
    if sys.platform != "win32":
        return
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def get_logger(name: str = "nanobot"):
    """Get configured logger instance"""
    _logger.remove()
    _asegurar_utf8()
    _logger.add(
        sys.stdout,
        format="<level>{level: <8}</level> | {name}:{function}:{line} - <level>{message}</level>",
        level="INFO"
    )
    return _logger
