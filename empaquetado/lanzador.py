"""Lanzador de escritorio de "Transición de Mallas" (lo que ejecuta TransicionMallas.exe).

1. Usa una carpeta de datos con permiso de escritura: %LOCALAPPDATA%\\TransicionMallas
   (la carpeta de instalación en "Archivos de programa" es de solo lectura).
2. La primera vez crea ahí el .env (con una clave JWT aleatoria) y los Excel de prueba.
3. Arranca el servidor en http://127.0.0.1:8000 y abre el navegador.
   Si ya estaba abierto, solo abre el navegador.

Para usar Google Drive o tus propios Excel, edita el .env de esa carpeta y copia
ahí la carpeta credenciales/. Cerrar la ventana negra detiene la aplicación.
"""
from __future__ import annotations

import os
import secrets
import socket
import sys
import threading
import webbrowser
from pathlib import Path

NOMBRE = "TransicionMallas"
HOST = "127.0.0.1"
PUERTO = int(os.environ.get("TRANSICION_PUERTO", "8000"))   # se puede cambiar si el 8000 está ocupado
URL = f"http://{HOST}:{PUERTO}"

# Al correr sin empaquetar (python empaquetado/lanzador.py) el proyecto está una carpeta arriba.
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def carpeta_datos() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / NOMBRE
    (base / "data").mkdir(parents=True, exist_ok=True)
    return base


def preparar(base: Path) -> None:
    env = base / ".env"
    if not env.exists():
        env.write_text(
            "# Configuración de Transición de Mallas (creada automáticamente).\n"
            "# Para usar Google Drive: FUENTE_DATOS=drive, los links y la carpeta credenciales/ aquí mismo.\n"
            f"JWT_SECRET={secrets.token_urlsafe(48)}\n"
            "JWT_EXPIRACION_MINUTOS=60\n"
            "FUENTE_DATOS=local\n"
            "USUARIOS_EXCEL_PATH=data/usuarios.xlsx\n"
            "ACADEMICO_EXCEL_PATH=data/academico.xlsx\n"
            "USUARIOS_EXCEL_LINK=\n"
            "ACADEMICO_EXCEL_LINK=\n"
            "GOOGLE_CREDENCIALES=credenciales/service_account.json\n"
            "CACHE_SEGUNDOS=300\n"
            "MALLA_VIGENTE=2026\n"
            "NOTA_MINIMA=3.0\n"
            "TICKETS_PATH=data/tickets.json\n"
            "AUDITORIA_PATH=data/auditoria.jsonl\n",
            encoding="utf-8",
        )
        print("  Se creó la configuración (.env).")
    if not (base / "data" / "academico.xlsx").exists():
        from scripts.crear_datos_ejemplo import generar

        generar(base / "data")
        print("  Se crearon los Excel de prueba (usuario admin / Admin2025*).")


def puerto_en_uso() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, PUERTO)) == 0


def main() -> None:
    print("=" * 62)
    print("  Transición de Mallas — Ingeniería Química")
    print("=" * 62)
    base = carpeta_datos()
    os.chdir(base)                       # el .env y data/ se leen desde aquí
    print(f"  Datos: {base}")

    if puerto_en_uso():
        print(f"  La aplicación ya está abierta. Abriendo {URL} ...")
        webbrowser.open(URL)
        return

    preparar(base)

    import uvicorn

    from app.presentation.api.main import crear_app

    app = crear_app()
    print(f"\n  Abra {URL} en el navegador (se abre solo).")
    print("  Para cerrar la aplicación, cierre esta ventana.\n")
    threading.Timer(1.5, lambda: webbrowser.open(URL)).start()
    uvicorn.run(app, host=HOST, port=PUERTO, log_level="warning")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # que el error se pueda leer antes de que se cierre la ventana
        print(f"\n  ERROR: {exc}")
        input("\n  Presione Enter para cerrar...")
        raise
