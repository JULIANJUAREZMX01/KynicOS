"""Pruebas de la ventana de historial (app/core/window.py)."""

import sys
from pathlib import Path
from types import SimpleNamespace

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.core import window  # noqa: E402


def mensajes(n):
    return [SimpleNamespace(role="user" if i % 2 == 0 else "assistant", content=f"m{i}") for i in range(n)]


def test_ollama_es_local():
    assert window.es_local("OllamaProvider") is True
    assert window.es_local("ollama") is True
    assert window.es_local("LocalProvider") is True


def test_nube_no_es_local():
    assert window.es_local("AnthropicProvider") is False
    assert window.es_local("GroqProvider") is False
    assert window.es_local(None) is False


def test_limites_por_proveedor():
    assert window.limite_historial("OllamaProvider") == window.LIMITE_LOCAL
    assert window.limite_historial("AnthropicProvider") == window.LIMITE_NUBRE


def test_recorta_al_final_conservando_el_ultimo():
    lista, fuera = window.recortar(mensajes(20), 8)
    assert len(lista) == 8
    assert fuera == 12
    assert lista[-1].content == "m19"


def test_no_recorta_si_cabe():
    lista, fuera = window.recortar(mensajes(5), 8)
    assert len(lista) == 5
    assert fuera == 0


def test_recorta_mensajes_gigantes():
    grande = SimpleNamespace(role="user", content="x" * 5000)
    lista, _ = window.recortar([grande], 8, max_caracteres=1000)
    assert len(lista[0].content) < 1100
    assert lista[0].content.endswith("[... recortado]")


def test_limite_cero_no_explota():
    lista, fuera = window.recortar(mensajes(3), 0)
    assert len(lista) == 3
    assert fuera == 0
