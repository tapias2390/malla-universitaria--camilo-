"""Crea data/usuarios.xlsx y data/academico.xlsx con las mallas REALES de Ingeniería Química.

Contenido:
- Mallas 2016 (Acuerdo 252) y 2026 (vigente), catálogo de optativas y equivalencias.
- Tres estudiantes de prueba anonimizados (casos reales sin datos personales).
- Usuarios de prueba (admin, consultor y una cuenta por estudiante).

Cada archivo trae una hoja LEEME que explica sus hojas y columnas, listas
desplegables para los campos con valores fijos y encabezados congelados.
Sirven tal cual para subirlos a Google Drive.

Uso:  python scripts/crear_datos_ejemplo.py           (no sobrescribe sin preguntar)
      python scripts/crear_datos_ejemplo.py --forzar  (sobrescribe)
"""
from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.infrastructure.security.bcrypt_hasher import BcryptHasher  # noqa: E402
from scripts import datos_ingenieria_quimica as datos  # noqa: E402

AZUL = PatternFill("solid", fgColor="1F5FBF")
GRIS = PatternFill("solid", fgColor="EEF2F7")
AMARILLO = PatternFill("solid", fgColor="FFF4CC")
BLANCO_NEGRITA = Font(bold=True, color="FFFFFF")


# ---------------------------------------------------------------------------
# Utilidades de formato
# ---------------------------------------------------------------------------
def hoja_datos(libro: Workbook, nombre: str, encabezados: list[str], filas: list, listas: dict[str, str] | None = None):
    """Crea una hoja con encabezado azul congelado, filtros, anchos y listas desplegables."""
    hoja = libro.create_sheet(nombre)
    hoja.append(encabezados)
    for fila in filas:
        hoja.append(list(fila))

    for celda in hoja[1]:
        celda.font, celda.fill = BLANCO_NEGRITA, AZUL
        celda.alignment = Alignment(vertical="center")
    hoja.freeze_panes = "A2"
    hoja.auto_filter.ref = hoja.dimensions

    for indice, encabezado in enumerate(encabezados, start=1):
        valores = [encabezado] + [str(f[indice - 1]) for f in filas if f[indice - 1] is not None]
        ancho = min(max(len(v) for v in valores) + 3, 60)
        hoja.column_dimensions[get_column_letter(indice)].width = ancho

    for columna, opciones in (listas or {}).items():
        letra = get_column_letter(encabezados.index(columna) + 1)
        validacion = DataValidation(type="list", formula1=f'"{opciones}"', allow_blank=True)
        validacion.error = f"Valores permitidos: {opciones}"
        validacion.errorTitle = "Valor no válido"
        hoja.add_data_validation(validacion)
        validacion.add(f"{letra}2:{letra}5000")
    return hoja


def hoja_leeme(libro: Workbook, titulo: str, introduccion: list[str], columnas: list[tuple[str, str, str, str]]):
    """Primera hoja del libro: explica cada hoja y columna. La aplicación la ignora."""
    hoja = libro.create_sheet("LEEME", 0)
    hoja["A1"] = titulo
    hoja["A1"].font = Font(bold=True, size=14, color="1F5FBF")
    fila = 3
    for parrafo in introduccion:
        hoja.cell(row=fila, column=1, value=parrafo).alignment = Alignment(wrap_text=True, vertical="top")
        hoja.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=4)
        hoja.row_dimensions[fila].height = 30
        fila += 1

    fila += 1
    for col, texto in enumerate(["Hoja", "Columna", "Obligatoria", "Descripción / valores permitidos"], start=1):
        celda = hoja.cell(row=fila, column=col, value=texto)
        celda.font, celda.fill = BLANCO_NEGRITA, AZUL
    hoja_anterior = None
    for nombre_hoja, columna, obligatoria, descripcion in columnas:
        fila += 1
        hoja.cell(row=fila, column=1, value=nombre_hoja if nombre_hoja != hoja_anterior else "")
        hoja.cell(row=fila, column=2, value=columna).font = Font(bold=True)
        hoja.cell(row=fila, column=3, value=obligatoria)
        hoja.cell(row=fila, column=4, value=descripcion).alignment = Alignment(wrap_text=True, vertical="top")
        if nombre_hoja != hoja_anterior:
            for col in range(1, 5):
                hoja.cell(row=fila, column=col).fill = GRIS
        hoja_anterior = nombre_hoja

    for letra, ancho in zip("ABCD", (18, 22, 12, 95)):
        hoja.column_dimensions[letra].width = ancho
    hoja.sheet_properties.tabColor = "1F5FBF"


def resaltar_pendientes(hoja, columna_obs: str) -> None:
    """Pinta de amarillo las filas con observación (datos por confirmar)."""
    indice = [c.value for c in hoja[1]].index(columna_obs) + 1
    for fila in hoja.iter_rows(min_row=2):
        if fila[indice - 1].value:
            for celda in fila:
                celda.fill = AMARILLO


# ---------------------------------------------------------------------------
# Libros
# ---------------------------------------------------------------------------
def crear_usuarios(ruta: Path) -> None:
    hasher = BcryptHasher(rondas=10)
    libro = Workbook()
    libro.remove(libro.active)
    hoja_leeme(
        libro,
        "Usuarios del sistema de transición de mallas",
        [
            "Cada fila es una persona que puede iniciar sesión. Las contraseñas NUNCA se escriben en claro: "
            "solo su hash bcrypt (genérelo con 'python scripts/generar_hash.py' o cree el usuario desde la aplicación).",
            "Lo normal es administrar los usuarios desde la aplicación (menú Usuarios, rol admin). "
            "No agregue otras hojas con contraseñas a este archivo.",
        ],
        [
            ("usuarios", "username", "Sí", "Nombre de usuario para entrar (minúsculas). Para estudiantes se usa su código."),
            ("usuarios", "password_hash", "Sí", "Hash bcrypt de la contraseña (empieza por $2b$)."),
            ("usuarios", "nombre", "Sí", "Nombre de la persona, se muestra en la aplicación."),
            ("usuarios", "rol", "Sí", "admin = todo (CRUD, tickets, auditoría) · consultor = consulta y valida "
                                      "estudiantes · estudiante = solo ve su propio avance."),
            ("usuarios", "activo", "No", "si / no. Vacío = si. Un usuario inactivo no puede entrar."),
            ("usuarios", "codigo_estudiante", "Solo estudiantes", "Código del estudiante (hoja 'estudiantes' del Excel académico)."),
        ],
    )
    hoja_datos(
        libro, "usuarios",
        ["username", "password_hash", "nombre", "rol", "activo", "codigo_estudiante"],
        [(u, hasher.hashear(c), n, r, "si" if a else "no", e) for u, c, n, r, a, e in datos.USUARIOS],
        listas={"rol": "admin,consultor,estudiante", "activo": "si,no"},
    )
    libro.save(ruta)


def crear_academico(ruta: Path) -> None:
    libro = Workbook()
    libro.remove(libro.active)
    hoja_leeme(
        libro,
        "Datos académicos — Ingeniería Química (UNAL Manizales)",
        [
            "Este archivo alimenta la aplicación de transición de mallas. La aplicación lee todas las hojas; "
            "estudiantes e historial también los modifica (registro desde la aplicación). Las demás las "
            "mantiene la oficina académica.",
            "Los encabezados no distinguen mayúsculas ni tildes. No cambie el nombre de las hojas. "
            "Las filas en AMARILLO tienen datos por confirmar (códigos temporales, equivalencias propuestas).",
            "Reglas de transición: 1) mismo código = directa · 2) equivalencia (si varias filas apuntan al mismo "
            "código nuevo es una fusión y se exigen todas) · 3) materia del catálogo de optativas = cupo de "
            "optativa de su grupo · 4) materia eliminada o de libre elección = cupo de libre elección con "
            "créditos menores o iguales · 5) si no cabe en ningún cupo se abre un ticket de revisión.",
        ],
        [
            ("estudiantes", "codigo", "Sí", "Código único del estudiante. Es la llave del historial."),
            ("estudiantes", "nombre", "Sí", "Nombre completo."),
            ("estudiantes", "documento", "Sí", "Documento de identidad (único)."),
            ("estudiantes", "correo", "No", "Correo institucional."),
            ("estudiantes", "malla_version", "Sí", "Malla con la que ingresó: 2016 o 2026 (debe existir en la hoja 'mallas')."),
            ("estudiantes", "estado", "No", "activo / inactivo / graduado / retirado. Vacío = activo."),
            ("materias_vistas", "codigo_estudiante", "Sí", "Código del estudiante (hoja 'estudiantes'). Una fila por materia y periodo."),
            ("materias_vistas", "codigo_materia", "Sí", "Código de la materia tal como aparece en la historia académica."),
            ("materias_vistas", "nombre_materia", "Sí", "Nombre de la materia."),
            ("materias_vistas", "creditos", "Sí", "Créditos con los que la cursó."),
            ("materias_vistas", "nota", "No", "Nota de 0 a 5. Vacía si fue por suficiencia (SUF) o si la está cursando."),
            ("materias_vistas", "estado", "Sí", "aprobada / reprobada / cursando / cancelada. Si se deja vacío se deduce "
                                                "de la nota (sin nota = cursando)."),
            ("materias_vistas", "tipologia", "No", "Como la reporta la universidad: fund_obligatoria, disciplinar_obligatoria, "
                                                   "fund_optativa, disciplinar_optativa, libre_eleccion, nivelacion, "
                                                   "trabajo_de_grado (también acepta las letras B, C, O, T, L, E, P)."),
            ("materias_vistas", "periodo", "Sí", "Periodo académico, p. ej. 2025-1S. Si repitió la materia, una fila por intento."),
            ("mallas", "version", "Sí", "Versión de la malla (2016, 2026...). La vigente se define en MALLA_VIGENTE del .env."),
            ("mallas", "semestre", "Sí", "Semestre sugerido (1 a 10)."),
            ("mallas", "codigo", "Sí", "Código de la materia. Para cupos se usan códigos propios: LE-xx (libre elección), "
                                       "OPT-xx (optativas)."),
            ("mallas", "nombre", "Sí", "Nombre de la materia o del cupo."),
            ("mallas", "creditos", "Sí", "Créditos."),
            ("mallas", "tipo", "Sí", "obligatoria · optativa (cupo que se llena con el catálogo de su grupo) · electiva "
                                     "(cupo de libre elección) · nivelacion (Inglés)."),
            ("mallas", "grupo", "Solo optativas", "Grupo del catálogo que puede llenar el cupo: ciencias_sociales, fisica, disciplinar."),
            ("mallas", "observacion", "No", "Notas internas (p. ej. código temporal)."),
            ("equivalencias", "codigo_anterior", "Sí", "Código en la malla anterior."),
            ("equivalencias", "nombre_anterior", "No", "Solo informativo."),
            ("equivalencias", "codigo_nuevo", "Sí", "Código en la malla vigente. Varias filas con el mismo código nuevo = fusión."),
            ("equivalencias", "nombre_nuevo", "No", "Solo informativo."),
            ("equivalencias", "estado", "No", "confirmada / propuesta (pendiente de aval del comité). Ambas se aplican; "
                                              "las propuestas se señalan en el resultado."),
            ("equivalencias", "observacion", "No", "Notas internas."),
            ("optativas", "grupo", "Sí", "ciencias_sociales, fisica o disciplinar (debe coincidir con 'grupo' en mallas)."),
            ("optativas", "codigo", "Sí", "Código de la materia que puede tomarse como optativa."),
            ("optativas", "nombre", "Sí", "Nombre de la materia."),
        ],
    )

    mallas = [("2016", *f) for f in datos.MALLA_2016] + [("2026", *f) for f in datos.MALLA_2026]
    hoja = hoja_datos(
        libro, "mallas",
        ["version", "semestre", "codigo", "nombre", "creditos", "tipo", "grupo", "observacion"],
        mallas,
        listas={"tipo": "obligatoria,optativa,electiva,nivelacion", "grupo": "ciencias_sociales,fisica,disciplinar"},
    )
    resaltar_pendientes(hoja, "observacion")

    hoja = hoja_datos(
        libro, "equivalencias",
        ["codigo_anterior", "nombre_anterior", "codigo_nuevo", "nombre_nuevo", "estado", "observacion"],
        datos.EQUIVALENCIAS,
        listas={"estado": "confirmada,propuesta"},
    )
    resaltar_pendientes(hoja, "estado")

    hoja_datos(libro, "optativas", ["grupo", "codigo", "nombre"], datos.OPTATIVAS,
               listas={"grupo": "ciencias_sociales,fisica,disciplinar"})
    hoja_datos(
        libro, "estudiantes",
        ["codigo", "nombre", "documento", "correo", "malla_version", "estado"],
        datos.ESTUDIANTES,
        listas={"malla_version": "2016,2026", "estado": "activo,inactivo,graduado,retirado"},
    )
    hoja_datos(
        libro, "materias_vistas",
        ["codigo_estudiante", "codigo_materia", "nombre_materia", "creditos", "nota", "estado", "tipologia", "periodo"],
        datos.MATERIAS_VISTAS,
        listas={
            "estado": "aprobada,reprobada,cursando,cancelada",
            "tipologia": "fund_obligatoria,disciplinar_obligatoria,fund_optativa,disciplinar_optativa,"
                         "libre_eleccion,nivelacion,trabajo_de_grado",
        },
    )
    libro.save(ruta)


def generar(destino: Path) -> None:
    """Crea los dos Excel en `destino` (lo usan también las pruebas automáticas)."""
    destino.mkdir(parents=True, exist_ok=True)
    crear_usuarios(destino / "usuarios.xlsx")
    crear_academico(destino / "academico.xlsx")


def main() -> None:
    destino = RAIZ / "data"
    existentes = [p for p in (destino / "usuarios.xlsx", destino / "academico.xlsx") if p.exists()]
    if existentes and "--forzar" not in sys.argv:
        respuesta = input(f"Se van a reemplazar {', '.join(p.name for p in existentes)}. ¿Continuar? (s/n): ")
        if respuesta.strip().lower() not in {"s", "si", "sí"}:
            sys.exit("Cancelado: no se modificó nada.")
    generar(destino)
    print("Creados data/usuarios.xlsx y data/academico.xlsx")
    print("\nUsuarios de prueba:")
    for username, clave, nombre, rol, activo, _ in datos.USUARIOS:
        if activo:
            print(f"  {rol:<11} {username:<10} / {clave}   ({nombre})")


if __name__ == "__main__":
    main()
