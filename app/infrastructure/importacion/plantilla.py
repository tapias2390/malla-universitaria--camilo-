"""Genera la plantilla de Excel para importar estudiantes (se descarga desde la aplicación)."""
from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

AZUL = PatternFill("solid", fgColor="1F5FBF")
GRIS = PatternFill("solid", fgColor="EEF2F7")
BLANCO = Font(bold=True, color="FFFFFF")

ESTUDIANTES = ["codigo", "nombre", "documento", "correo", "malla_version", "estado"]
MATERIAS = ["codigo_estudiante", "codigo_materia", "nombre_materia", "creditos", "nota", "estado", "tipologia", "periodo"]
TIPOLOGIAS = ("fund_obligatoria,disciplinar_obligatoria,fund_optativa,disciplinar_optativa,"
              "libre_eleccion,nivelacion,trabajo_de_grado")

INSTRUCCIONES = [
    ("Cómo funciona", ""),
    ("1", "Llene la hoja 'estudiantes' (una fila por estudiante) y la hoja 'materias_vistas' (una fila por materia "
          "cursada y por periodo). Borre las filas de ejemplo."),
    ("2", "En la aplicación: Importar → suba el archivo → 'Validar'. Verá cada error con su hoja y fila. "
          "No se guarda nada hasta que el archivo esté sin errores y usted confirme."),
    ("3", "Si el código del estudiante ya existe, sus datos se ACTUALIZAN; si no existe, se CREA."),
    ("4", "Si un estudiante aparece en 'materias_vistas', su historial se REEMPLAZA COMPLETO por las filas del archivo. "
          "Si solo aparece en 'estudiantes', su historial no se toca."),
    ("5", "Puede importar solo una de las dos hojas: por ejemplo, solo 'materias_vistas' para actualizar el "
          "historial de estudiantes que ya existen."),
    ("", ""),
    ("Hoja estudiantes", ""),
    ("codigo *", "Código único del estudiante."),
    ("nombre *", "Nombre completo."),
    ("documento *", "Documento de identidad (único)."),
    ("correo", "Correo institucional."),
    ("malla_version *", "Malla con la que ingresó (p. ej. 2016 o 2026). Debe existir en el sistema."),
    ("estado", "activo / inactivo / graduado / retirado. Vacío = activo."),
    ("", ""),
    ("Hoja materias_vistas", ""),
    ("codigo_estudiante *", "Código del estudiante (de este archivo o ya registrado)."),
    ("codigo_materia *", "Código de la materia como aparece en la historia académica."),
    ("nombre_materia", "Nombre de la materia."),
    ("creditos *", "Créditos con los que la cursó (1 a 20)."),
    ("nota", "0 a 5. Vacía si fue por suficiencia (SUF) o si la está cursando."),
    ("estado *", "aprobada / reprobada / cursando / cancelada (también acepta 'Aprobada (SUF)')."),
    ("tipologia", "Como la reporta la universidad: " + TIPOLOGIAS.replace(",", ", ") + " (o las letras B, C, O, T, L, E, P)."),
    ("periodo", "Periodo académico, p. ej. 2025-1S. Si repitió la materia, una fila por intento."),
    ("", ""),
    ("* = obligatoria", ""),
]


def generar_plantilla() -> bytes:
    libro = Workbook()
    leeme = libro.active
    leeme.title = "LEEME"
    leeme["A1"] = "Plantilla de importación de estudiantes — Transición de mallas"
    leeme["A1"].font = Font(bold=True, size=14, color="1F5FBF")
    for i, (a, b) in enumerate(INSTRUCCIONES, start=3):
        leeme.cell(row=i, column=1, value=a).font = Font(bold=True)
        leeme.cell(row=i, column=2, value=b).alignment = Alignment(wrap_text=True, vertical="top")
        if a and not b:
            leeme.cell(row=i, column=1).fill = GRIS
    leeme.column_dimensions["A"].width = 22
    leeme.column_dimensions["B"].width = 110

    _hoja(libro, "estudiantes", ESTUDIANTES, [
        ["20262050", "Nombre Apellido Ejemplo", "1000000050", "ejemplo@unal.edu.co", "2016", "activo"],
    ], {"estado": "activo,inactivo,graduado,retirado"})
    _hoja(libro, "materias_vistas", MATERIAS, [
        ["20262050", "1000004", "Cálculo Diferencial", 4, 3.8, "aprobada", "fund_obligatoria", "2025-1S"],
        ["20262050", "1000044", "Inglés I", 3, None, "aprobada", "nivelacion", "2025-1S"],
        ["20262050", "1000005", "Cálculo Integral", 4, None, "cursando", "fund_obligatoria", "2025-2S"],
    ], {"estado": "aprobada,reprobada,cursando,cancelada", "tipologia": TIPOLOGIAS})

    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


def _hoja(libro: Workbook, nombre: str, columnas: list[str], ejemplos: list[list], listas: dict[str, str]) -> None:
    hoja = libro.create_sheet(nombre)
    hoja.append(columnas)
    for fila in ejemplos:
        hoja.append(fila)
    for celda in hoja[1]:
        celda.font, celda.fill = BLANCO, AZUL
    hoja.freeze_panes = "A2"
    for i, columna in enumerate(columnas):
        hoja.column_dimensions[chr(65 + i)].width = max(len(columna) + 4, 14 if columna != "nombre_materia" else 30)
    hoja.column_dimensions["B"].width = max(hoja.column_dimensions["B"].width, 26)
    for columna, opciones in listas.items():
        letra = chr(65 + columnas.index(columna))
        validacion = DataValidation(type="list", formula1=f'"{opciones}"', allow_blank=True)
        hoja.add_data_validation(validacion)
        validacion.add(f"{letra}2:{letra}5000")
