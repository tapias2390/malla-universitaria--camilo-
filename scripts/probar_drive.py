"""Verifica la conexión con Google Drive usando la configuración del .env.

- Muestra el correo de la cuenta de servicio (con ese correo hay que compartir las hojas).
- Descarga cada archivo configurado y revisa que tenga las hojas y columnas esperadas.
- No muestra contraseñas ni hashes: solo cuántas filas hay.

Uso:  python scripts/probar_drive.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.domain.exceptions import ErrorFuenteDatos  # noqa: E402
from app.infrastructure.config import obtener_settings  # noqa: E402
from app.infrastructure.data_sources.fuentes import FuenteGoogleDrive  # noqa: E402
from app.infrastructure.data_sources.lector_excel import exigir_hoja, leer_libro  # noqa: E402
from app.infrastructure.repositories import excel_academico, excel_usuarios  # noqa: E402

HOJAS = {
    "usuarios": {"usuarios": excel_usuarios.COLUMNAS},
    "academico": {
        "estudiantes": excel_academico.COLUMNAS_ESTUDIANTES,
        "materias_vistas": excel_academico.COLUMNAS_VISTAS,
        "mallas": excel_academico.COLUMNAS_MALLAS,
    },
}


def main() -> None:
    s = obtener_settings()
    credenciales = Path(s.google_credenciales)
    if not credenciales.exists():
        sys.exit(f"No existe '{credenciales}'. Descarga la llave JSON de la cuenta de servicio ahí.")

    correo = json.loads(credenciales.read_text(encoding="utf-8")).get("client_email")
    print(f"Cuenta de servicio: {correo}\n(comparte las hojas con este correo como 'Lector')\n")

    ok = True
    for nombre, link in (("usuarios", s.usuarios_excel_link), ("academico", s.academico_excel_link)):
        if not link:
            print(f"[--] {nombre}: sin link en el .env (se usa el archivo local)")
            continue
        try:
            libro = leer_libro(FuenteGoogleDrive(link, credenciales).obtener_bytes())
            for hoja, columnas in HOJAS[nombre].items():
                filas = exigir_hoja(libro, hoja, columnas)
                print(f"[OK] {nombre} / {hoja}: {len(filas)} filas")
        except ErrorFuenteDatos as exc:
            ok = False
            print(f"[ERROR] {nombre}: {exc}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
