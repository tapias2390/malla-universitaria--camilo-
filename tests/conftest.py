"""Datos compartidos por las pruebas: cada sesión genera Excel nuevos en una carpeta temporal.

Así las pruebas nunca tocan los archivos de data/ ni los de Google Drive.
"""
import pytest

from scripts.crear_datos_ejemplo import generar


@pytest.fixture(scope="session")
def datos_dir(tmp_path_factory):
    destino = tmp_path_factory.mktemp("datos")
    generar(destino)
    return destino
