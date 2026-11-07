"""Crea data/usuarios.xlsx y data/academico.xlsx con datos de ejemplo.

Sirven para probar en local y como PLANTILLA de las hojas y columnas que deben
tener los archivos reales en Google Drive.

Uso:  python scripts/crear_datos_ejemplo.py
"""
import sys
from pathlib import Path

from openpyxl import Workbook

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.infrastructure.security.bcrypt_hasher import BcryptHasher  # noqa: E402

DATA = RAIZ / "data"


def guardar(ruta: Path, hojas: dict[str, list[list]]) -> None:
    libro = Workbook()
    libro.remove(libro.active)
    for nombre, filas in hojas.items():
        hoja = libro.create_sheet(nombre)
        for fila in filas:
            hoja.append(fila)
    libro.save(ruta)
    print(f"Creado {ruta.relative_to(RAIZ)}")


def main() -> None:
    DATA.mkdir(exist_ok=True)
    hasher = BcryptHasher()

    # ------------------------------------------------------------- usuarios
    guardar(DATA / "usuarios.xlsx", {
        "usuarios": [
            ["username", "password_hash", "nombre", "rol", "activo"],
            ["admin", hasher.hashear("Admin2025*"), "Administrador", "admin", "si"],
            ["consultor", hasher.hashear("Consulta2025*"), "Consultor Académico", "consultor", "si"],
            ["inactivo", hasher.hashear("Inactivo2025*"), "Usuario Inactivo", "consultor", "no"],
        ]
    })

    # ------------------------------------------------------------- académico
    mallas = [["version", "codigo", "nombre", "creditos", "semestre", "tipo"]]
    # Malla antigua 2020
    mallas += [
        ["2020", "MAT101", "Cálculo I", 4, 1, "obligatoria"],
        ["2020", "PRO101", "Programación I", 3, 1, "obligatoria"],
        ["2020", "FIS101", "Física I", 4, 1, "obligatoria"],         # se elimina en 2025
        ["2020", "HUM101", "Ética profesional", 2, 1, "obligatoria"],  # se elimina en 2025
        ["2020", "QUI101", "Química general", 3, 2, "obligatoria"],    # se elimina en 2025
        ["2020", "MAT102", "Cálculo II", 4, 2, "obligatoria"],
        ["2020", "PRO102", "Programación II", 3, 2, "obligatoria"],
        ["2020", "BD201", "Bases de datos", 3, 3, "obligatoria"],      # cambia de código
        ["2020", "ELE01", "Electiva I", 3, 4, "electiva"],
    ]
    # Malla nueva 2025 (vigente)
    mallas += [
        ["2025", "MAT101", "Cálculo I", 4, 1, "obligatoria"],
        ["2025", "PRO101", "Programación I", 3, 1, "obligatoria"],
        ["2025", "MAT102", "Cálculo II", 4, 2, "obligatoria"],
        ["2025", "PRO102", "Programación II", 3, 2, "obligatoria"],
        ["2025", "IA201", "Introducción a la IA", 3, 2, "obligatoria"],
        ["2025", "BDD201", "Bases de datos", 3, 3, "obligatoria"],
        ["2025", "NUB301", "Computación en la nube", 3, 3, "obligatoria"],
        ["2025", "ELE01", "Electiva profesional I", 3, 4, "electiva"],
        ["2025", "ELE02", "Electiva profesional II", 2, 5, "electiva"],
    ]

    guardar(DATA / "academico.xlsx", {
        "estudiantes": [
            ["codigo", "nombre", "documento", "malla_version", "estado"],
            ["1001", "Ana Gómez", "1012345678", "2025", "activo"],     # nueva: ve la malla nueva
            ["2001", "Carlos Ruiz", "1023456789", "2020", "activo"],   # antigua: todo se homologa
            ["2002", "Laura Pérez", "1034567890", "2020", "activo"],   # antigua: genera ticket
        ],
        "materias_vistas": [
            ["codigo_estudiante", "codigo_materia", "nombre_materia", "creditos", "nota", "periodo"],
            ["1001", "MAT101", "Cálculo I", 4, 4.2, "2025-1"],
            ["1001", "PRO101", "Programación I", 3, 3.8, "2025-1"],

            ["2001", "MAT101", "Cálculo I", 4, 4.0, "2022-1"],
            ["2001", "PRO101", "Programación I", 3, 3.5, "2022-1"],
            ["2001", "FIS101", "Física I", 4, 3.9, "2022-1"],
            ["2001", "HUM101", "Ética profesional", 2, 4.5, "2022-1"],
            ["2001", "BD201", "Bases de datos", 3, 4.1, "2023-1"],
            ["2001", "MAT102", "Cálculo II", 4, 2.5, "2022-2"],        # reprobada
            ["2001", "MAT102", "Cálculo II", 4, 3.4, "2023-1"],        # la repitió y aprobó

            ["2002", "FIS101", "Física I", 4, 4.0, "2023-1"],
            ["2002", "QUI101", "Química general", 3, 3.6, "2023-2"],
            ["2002", "HUM101", "Ética profesional", 2, 3.2, "2023-1"],
            ["2002", "PRO101", "Programación I", 3, 2.1, "2023-1"],    # reprobada
        ],
        "mallas": mallas,
        "equivalencias": [
            ["codigo_anterior", "codigo_nuevo"],
            ["BD201", "BDD201"],
        ],
    })

    print("\nUsuarios de prueba:  admin / Admin2025*   consultor / Consulta2025*")


if __name__ == "__main__":
    main()
