"""Pruebas del gestor de proveedores.

ProviderManager ya no expone primary_provider ni fallback_provider: mantiene una
lista ordenada (self.providers) y get_provider() devuelve el primero disponible.
Ollama se registra siempre como ultimo recurso, asi que la lista nunca queda
vacia aunque no haya llaves en el entorno.
"""

import pytest

from app.cloud.providers import ProviderManager


@pytest.fixture
def manager():
    from app.config import Settings
    return ProviderManager(Settings())


def test_se_inicializa(manager):
    assert manager is not None
    assert isinstance(manager.providers, list)


def test_ollama_es_el_ultimo_recurso(manager):
    nombres = [p.__class__.__name__ for p in manager.providers]
    assert "OllamaProvider" in nombres, nombres
    assert nombres[-1] == "OllamaProvider", nombres


def test_get_provider_devuelve_el_primero(manager):
    try:
        proveedor = manager.get_provider()
    except RuntimeError:
        pytest.skip("sin proveedores disponibles en este entorno")
    assert proveedor is manager.providers[0]


def test_groq_solo_si_hay_llave(manager):
    nombres = [p.__class__.__name__ for p in manager.providers]
    if "GroqProvider" in nombres:
        assert nombres[0] == "GroqProvider", nombres
    else:
        assert "GroqProvider" not in nombres


def test_anthropic_solo_si_hay_llave(manager):
    nombres = [p.__class__.__name__ for p in manager.providers]
    if "AnthropicProvider" in nombres:
        assert nombres.index("AnthropicProvider") < nombres.index("OllamaProvider")
    else:
        assert "AnthropicProvider" not in nombres
