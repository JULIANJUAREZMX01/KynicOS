"""Pruebas del diagnostico por registros.

Cada caso es un fallo real de la noche del 6-nov-2026 en la PC del jefe.
"""

import pytest

from app.core.diagnostico import hallazgos


@pytest.mark.parametrize(
    "registro, esperado",
    [
        ("ERROR telegram Conflict: terminated by other getUpdates request", "Doble instancia"),
        ("OSError: [WinError 10048] Address already in use", "Puerto 8000 ocupado"),
        ("ModuleNotFoundError: No module named 'telegram'", "Falta una dependencia"),
        ("The token was rejected by the server. Unauthorized", "Token rechazado"),
        ("httpx.ConnectError: connection refused to 127.0.0.1:11434", "Ollama no responde"),
        ("UnicodeEncodeError: 'charmap' codec can't encode", "Problema de codificación"),
    ],
)
def test_detecta_fallos_conocidos(registro, esperado):
    titulos = [h["titulo"] for h in hallazgos(registro)]
    assert esperado in titulos, f"no detecto {esperado} en {registro!r}"


def test_no_inventa_fallos_en_un_registro_sano():
    sano = (
        "INFO:     Started server process [4284]\n"
        "INFO:     Application startup complete.\n"
        "INFO:     Uvicorn running on http://0.0.0.0:8000\n"
        "INFO     | telegram_bot:start_telegram_bot:291 - Telegram bot polling started\n"
    )
    assert hallazgos(sano) == []


def test_no_repite_el_mismo_hallazgo():
    repetido = "Unauthorized\n" * 20
    assert len(hallazgos(repetido)) == 1


def test_cada_hallazgo_trae_remedio():
    h = hallazgos("ModuleNotFoundError: No module named 'loguru'")
    assert h and h[0]["remedio"].strip()
    assert "loguru" in h[0]["causa"]
