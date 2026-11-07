"""Punto de entrada: `python run.py` y abrir http://127.0.0.1:8000

La documentación interactiva de la API queda en http://127.0.0.1:8000/docs
"""
import logging

import uvicorn

from app.presentation.api.main import crear_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = crear_app()

if __name__ == "__main__":
    # 127.0.0.1: solo accesible desde este equipo (la app es local).
    uvicorn.run(app, host="127.0.0.1", port=8000)
