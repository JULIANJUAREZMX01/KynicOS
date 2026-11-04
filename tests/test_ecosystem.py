"""Pruebas del registro del ecosistema (app/core/ecosystem.py).

Cubren lo que puede romper en silencio:
  - resolución de repositorios por variable de entorno
  - lectura normal de un archivo de texto
  - rechazo de secretos (.env, claves)
  - rechazo de rutas que se salen de la raíz
  - tolerancia a repositorios ausentes
  - búsqueda que salta secretos
"""

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.core import ecosystem  # noqa: E402


@pytest.fixture()
def ecosistema(tmp_path, monkeypatch):
    """Crea un ecosistema falso en disco y apunta el registro ahí."""
    base = tmp_path / "dev"
    base.mkdir()
    kynicos = base / "KynicOS"
    (kynicos / "app" / "skills").mkdir(parents=True)
    (kynicos / "app" / "skills" / "hvac_triage.py").write_text("valor = 42\n", encoding="utf-8")
    (kynicos / "README.md").write_text("KynicOS nucleo\n", encoding="utf-8")
    (kynicos / ".env").write_text("TELEGRAM_TOKEN=secreto\n", encoding="utf-8")
    (kynicos / "docs" / "adr").mkdir(parents=True)
    (kynicos / "docs" / "adr" / "ADR-001.md").write_text("decision\n", encoding="utf-8")

    kalpixk = base / "Wasm-Kalpixk_IA_DevOps"
    (kalpixk / ".jules").mkdir(parents=True)
    (kalpixk / ".jules" / "sentinel.md").write_text("postura defensiva\n", encoding="utf-8")

    monkeypatch.setenv("KYNIKOS_ECOSYSTEM_ROOTS", str(base))
    return base


def test_resuelve_repositorio_presente(ecosistema):
    ruta = ecosystem.resolver("kynicos")
    assert ruta is not None
    assert ruta.name == "KynicOS"


def test_repositorio_ausente_no_falla(ecosistema):
    inv = ecosystem.inventario()
    assert inv["kynicos"].presente is True
    assert inv["orquestador"].presente is False
    texto = ecosystem.estado()
    assert "ausente" in texto


def test_lee_archivo_de_texto(ecosistema):
    contenido = ecosystem.leer("kynicos", "app/skills/hvac_triage.py")
    assert "valor = 42" in contenido


def test_rechaza_env(ecosistema):
    with pytest.raises(ecosystem.ArchivoProtegido):
        ecosystem.leer("kynicos", ".env")


def test_rechaza_ruta_que_sale_de_la_raiz(ecosistema):
    with pytest.raises(ecosystem.FueraDeRaiz):
        ecosystem.leer("kynicos", "../../fuera.txt")


def test_busqueda_salta_secretos(ecosistema):
    hallazgos = ecosystem.buscar("secreto")
    assert hallazgos == []
    hallazgos = ecosystem.buscar("defensiva")
    assert hallazgos and hallazgos[0]["repo"] == "kalpixk"


def test_catalogo_refleja_artefactos(ecosistema):
    datos = ecosystem.catalogo()
    assert datos["total_presentes"] == 2
    assert "skills" in datos["repos"]["kynicos"]["artefactos"]
    assert "personas_jules" in datos["repos"]["kalpixk"]["artefactos"]


def test_patron_corto_rechazado(ecosistema):
    with pytest.raises(ValueError):
        ecosystem.buscar("a")
