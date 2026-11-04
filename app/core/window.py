"""Ventana de historial para el LLM.

Ollama con `qwen2.5:7b` corre en una Ryzen 5 5500U con 4096 tokens de contexto.
Un historial de 20 mensajes con prompts de sistema lo satura y la llamada muere
con "Error processing message". En la nube sobra espacio y recortar de más
empeora las respuestas.

Este módulo es puro: no importa config, ni red, ni proveedores. Se puede probar
sin levantar nada.
"""

from __future__ import annotations

from typing import Any, Iterable

LIMITE_LOCAL = 8
LIMITE_NUBRE = 24
MAX_CARACTERES = 2000

_PROVEEDORES_LOCALES = ("ollama", "local", "llamacpp", "llama_cpp", "vllm")


def es_local(nombre_proveedor: str | None) -> bool:
    """True si el proveedor corre en la máquina, con contexto acotado."""
    if not nombre_proveedor:
        return False
    nombre = nombre_proveedor.lower()
    return any(marca in nombre for marca in _PROVEEDORES_LOCALES)


def limite_historial(nombre_proveedor: str | None,
                     limite_local: int = LIMITE_LOCAL,
                     limite_nube: int = LIMITE_NUBRE) -> int:
    """Cuántos mensajes de historial se pueden mandar."""
    if es_local(nombre_proveedor):
        return max(1, limite_local)
    return max(1, limite_nube)


def recortar(mensajes: Iterable[Any], limite: int,
             max_caracteres: int = MAX_CARACTERES) -> tuple[list[Any], int]:
    """Devuelve los últimos `limite` mensajes y cuántos se dejaron fuera.

    Se conserva el final de la conversación porque ahí está el mensaje que se
    está respondiendo. Cada mensaje se recorta en caracteres para que un pegado
    enorme no se coma el contexto entero.
    """
    lista = list(mensajes)
    recortados = 0
    if limite > 0 and len(lista) > limite:
        recortados = len(lista) - limite
        lista = lista[-limite:]
    if max_caracteres > 0:
        salida = []
        for msg in lista:
            contenido = getattr(msg, "content", None)
            if isinstance(contenido, str) and len(contenido) > max_caracteres:
                margen = max_caracteres - 20
                recortado = contenido[:margen] + "\n[... recortado]"
                try:
                    msg.content = recortado
                except Exception:
                    # objetos inmutables: se copia sin tocar el original
                    from copy import copy
                    copia = copy(msg)
                    copia.content = recortado
                    msg = copia
            salida.append(msg)
        lista = salida
    return lista, recortados
