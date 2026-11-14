"""Verifica la conexión con Google Drive usando la configuración del .env.

- Muestra el correo de la cuenta de servicio (con ese correo hay que compartir los archivos).
- Descarga cada archivo configurado y revisa que tenga las hojas y columnas esperadas.
- Revisa que exista la malla vigente (MALLA_VIGENTE).
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
HOJAS_OPCIONALES = {"academico": ["equivalencias", "optativas"]}


def main() -> None:
    s = obtener_settings()
    credenciales = Path(s.google_credenciales)
    if not credenciales.exists():
        sys.exit(f"No existe '{credenciales}'. Descarga la llave JSON de la cuenta de servicio ahí.")

    correo = json.loads(credenciales.read_text(encoding="utf-8")).get("client_email")
    print(f"Cuenta de servicio: {correo}")
    print("(comparte los archivos con este correo como 'Editor' para poder registrar estudiantes y usuarios)\n")

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
            for hoja in HOJAS_OPCIONALES.get(nombre, []):
                estado = f"{len(libro[hoja])} filas" if hoja in libro else "no existe (opcional)"
                print(f"[..] {nombre} / {hoja}: {estado}")
            if nombre == "academico":
                versiones = {str(f.get("version")).split(".")[0] for f in libro["mallas"]}
                if s.malla_vigente in versiones:
                    print(f"[OK] malla vigente {s.malla_vigente} encontrada")
                else:
                    ok = False
                    print(f"[ERROR] la malla vigente {s.malla_vigente} no está en la hoja 'mallas' "
                          f"(hay: {', '.join(sorted(versiones))}). ¿Subiste el academico.xlsx nuevo?")
        except ErrorFuenteDatos as exc:
            ok = False
            print(f"[ERROR] {nombre}: {exc}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
