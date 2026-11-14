"""Lee el Excel que sube el administrador para importar estudiantes.

Conserva el número de fila de cada registro para poder decir exactamente dónde
está cada error ("materias_vistas, fila 14: créditos inválidos").
"""
from __future__ import annotations

import io

from openpyxl import load_workbook

from app.application.use_cases.gestion_estudiantes import DatosEstudiante
from app.application.use_cases.importacion import (
    ErrorImportacion,
    FilaEstudiante,
    FilaMateria,
    LoteImportacion,
)
from app.domain.entities import MateriaVista
from app.domain.exceptions import ErrorFuenteDatos
from app.infrastructure.data_sources.lector_excel import (
    como_decimal_opcional,
    como_texto,
    normalizar_encabezado,
)
from app.infrastructure.repositories.excel_academico import interpretar_estado, interpretar_tipologia

COLUMNAS_ESTUDIANTES = {"codigo", "nombre", "documento", "malla_version"}
COLUMNAS_MATERIAS = {"codigo_estudiante", "codigo_materia", "creditos", "estado"}
MAX_FILAS = 20_000


class ExcelLectorImportacion:
    def __init__(self, nota_minima: float = 3.0) -> None:
        self._nota_minima = nota_minima

    def leer(self, contenido: bytes) -> LoteImportacion:
        lote = LoteImportacion()
        try:
            libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
        except Exception:
            lote.errores.append(ErrorImportacion("—", 0, "El archivo no es un Excel válido (.xlsx)."))
            return lote

        hojas = {normalizar_encabezado(h.title): h for h in libro.worksheets}
        if "estudiantes" not in hojas and "materias_vistas" not in hojas:
            lote.errores.append(ErrorImportacion(
                "—", 0, "El archivo debe tener una hoja 'estudiantes' y/o una hoja 'materias_vistas' (use la plantilla)."))
            libro.close()
            return lote

        if "estudiantes" in hojas:
            for fila, datos in self._filas(hojas["estudiantes"], "estudiantes", COLUMNAS_ESTUDIANTES, lote):
                lote.estudiantes.append(FilaEstudiante(fila, DatosEstudiante(
                    codigo=como_texto(datos.get("codigo")),
                    nombre=como_texto(datos.get("nombre")),
                    documento=como_texto(datos.get("documento")),
                    malla_version=como_texto(datos.get("malla_version")),
                    estado=como_texto(datos.get("estado")) or "activo",
                    correo=como_texto(datos.get("correo")),
                )))

        if "materias_vistas" in hojas:
            for fila, datos in self._filas(hojas["materias_vistas"], "materias_vistas", COLUMNAS_MATERIAS, lote):
                materia = self._a_materia(fila, datos, lote)
                if materia:
                    lote.materias.append(FilaMateria(fila, como_texto(datos.get("codigo_estudiante")), materia))
        libro.close()
        return lote

    # ------------------------------------------------------------------ internos
    @staticmethod
    def _filas(hoja, nombre: str, obligatorias: set[str], lote: LoteImportacion):
        filas = hoja.iter_rows(values_only=True)
        encabezados = [normalizar_encabezado(c) for c in next(filas, [])]
        faltantes = obligatorias - set(encabezados)
        if faltantes:
            lote.errores.append(ErrorImportacion(nombre, 1, f"Faltan las columnas: {', '.join(sorted(faltantes))}."))
            return
        for numero, valores in enumerate(filas, start=2):
            if numero > MAX_FILAS:
                lote.errores.append(ErrorImportacion(nombre, numero, f"Máximo {MAX_FILAS} filas por hoja."))
                return
            if all(v in (None, "") for v in valores):
                continue
            yield numero, {encabezados[i]: v for i, v in enumerate(valores) if i < len(encabezados)}

    def _a_materia(self, fila: int, datos: dict, lote: LoteImportacion) -> MateriaVista | None:
        nota_cruda = datos.get("nota")
        nota = como_decimal_opcional(nota_cruda)
        if nota is None and como_texto(nota_cruda):
            lote.errores.append(ErrorImportacion("materias_vistas", fila, f"La nota '{nota_cruda}' no es un número."))
            return None
        creditos_texto = como_texto(datos.get("creditos"))
        try:
            creditos = int(float(creditos_texto.replace(",", ".")))
        except ValueError:
            lote.errores.append(ErrorImportacion("materias_vistas", fila, f"Los créditos '{creditos_texto}' no son un número."))
            return None
        try:
            estado = interpretar_estado(datos.get("estado"), nota, self._nota_minima)
        except ErrorFuenteDatos as exc:
            lote.errores.append(ErrorImportacion("materias_vistas", fila, str(exc)))
            return None
        return MateriaVista(
            codigo=como_texto(datos.get("codigo_materia")),
            nombre=como_texto(datos.get("nombre_materia")),
            creditos=creditos,
            nota=nota,
            periodo=como_texto(datos.get("periodo")),
            estado=estado,
            tipologia=interpretar_tipologia(datos.get("tipologia")),
        )
