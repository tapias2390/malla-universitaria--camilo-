"""Punto de entrada: `python run.py` y abrir http://127.0.0.1:8000

La documentación interactiva de la API queda en http://127.0.0.1:8000/docs
"""
import subprocess
import sys
from pathlib import Path

# Si se ejecuta con el Python del sistema (sin las librerías del proyecto),
# se vuelve a lanzar automáticamente con el Python del entorno .venv.
VENV_PYTHON = Path(__file__).resolve().parent / ".venv" / "Scripts" / "python.exe"
if VENV_PYTHON.exists() and Path(sys.prefix).resolve() != VENV_PYTHON.parent.parent.resolve():
    try:
        sys.exit(subprocess.call([str(VENV_PYTHON), *sys.argv]))
    except KeyboardInterrupt:
        sys.exit(0)

import logging  # noqa: E402

import uvicorn  # noqa: E402

from app.presentation.api.main import crear_app  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = crear_app()

if __name__ == "__main__":
    # 127.0.0.1: solo accesible desde este equipo (la app es local).
    uvicorn.run(app, host="127.0.0.1", port=8000)
