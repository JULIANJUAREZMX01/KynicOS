"""Pruebas del ejecutor de herramientas.

Escritas contra la API actual: ToolExecutor no toma argumentos y todo pasa por
execute({"name": ..., "args": {...}}). Las versiones anteriores llamaban a
metodos que ya no existen (read_file, list_files) e instanciaban la clase con
un directorio, asi que fallaban siempre y tapaban el resto del CI.
"""

import pytest
from pathlib import Path

from app.core.tools import ToolExecutor


@pytest.fixture
def executor():
    return ToolExecutor()


@pytest.mark.asyncio
async def test_se_crea_sin_argumentos(executor):
    assert executor is not None


@pytest.mark.asyncio
async def test_herramienta_desconocida(executor):
    salida = await executor.execute({"name": "no_existe", "args": {}})
    assert "desconocida" in salida.lower()


@pytest.mark.asyncio
async def test_comando_vacio(executor):
    salida = await executor.execute({"name": "execute_shell", "args": {"command": "   "}})
    assert "vacío" in salida.lower() or "vacio" in salida.lower()


@pytest.mark.asyncio
async def test_comando_peligroso_bloqueado(executor):
    salida = await executor.execute({"name": "execute_shell", "args": {"command": "rm -rf /"}})
    assert "bloqueado" in salida.lower() or "denegado" in salida.lower() or "❌" in salida


@pytest.mark.asyncio
async def test_escribir_y_leer_archivo(executor, tmp_path):
    destino = tmp_path / "prueba.txt"
    escrito = await executor.execute(
        {"name": "write_file", "args": {"path": str(destino), "content": "Hola, KynicOS"}}
    )
    assert "❌" not in escrito, escrito

    leido = await executor.execute({"name": "read_file", "args": {"path": str(destino)}})
    assert "Hola, KynicOS" in leido


@pytest.mark.asyncio
async def test_leer_archivo_inexistente(executor, tmp_path):
    salida = await executor.execute(
        {"name": "read_file", "args": {"path": str(tmp_path / "no-existe.txt")}}
    )
    assert "no existe" in salida.lower() or "❌" in salida


@pytest.mark.asyncio
async def test_ruta_vacia(executor):
    salida = await executor.execute({"name": "read_file", "args": {"path": ""}})
    assert "vacía" in salida.lower() or "vacia" in salida.lower()
