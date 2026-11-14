"""Modifica filas de un .xlsx conservando el resto del libro (formato, otras hojas, hoja LEEME).

Uso típico desde un repositorio:

    with editor.editar() as libro:
        hoja = HojaEditable(libro, "estudiantes", ["codigo", "nombre", ...])
        hoja.reemplazar_o_agregar({"codigo": "123"}, {...})

`editar()` descarga la versión más reciente (sin caché), aplica los cambios y
la vuelve a guardar. Un candado evita que dos peticiones simultáneas se pisen.
"""
from __future__ import annotations

import io
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.worksheet import Worksheet

from app.domain.exceptions import ErrorFuenteDatos
from app.infrastructure.data_sources.fuentes import FuenteExcel
from app.infrastructure.data_sources.lector_excel import normalizar_encabezado

Valores = dict[str, object]

ESTILO_ENCABEZADO = {
    "font": Font(bold=True, color="FFFFFF"),
    "fill": PatternFill("solid", fgColor="1F5FBF"),
}


class EditorExcel:
    def __init__(self, fuente: FuenteExcel) -> None:
        self._fuente = fuente
        self._lock = threading.Lock()

    @contextmanager
    def editar(self) -> Iterator[Workbook]:
        with self._lock:
            try:
                libro = load_workbook(io.BytesIO(self._fuente.obtener_bytes_frescos()))
            except ErrorFuenteDatos:
                raise
            except Exception as exc:
                raise ErrorFuenteDatos(f"El archivo no es un Excel válido: {exc}") from exc
            yield libro                      # si el bloque falla, no se guarda nada
            buffer = io.BytesIO()
            libro.save(buffer)
            self._fuente.guardar_bytes(buffer.getvalue())


class HojaEditable:
    """Acceso por nombre de columna a una hoja (encabezados en la fila 1)."""

    def __init__(self, libro: Workbook, nombre: str, columnas: list[str]) -> None:
        self._hoja = self._buscar_o_crear(libro, nombre)
        self._columnas = self._asegurar_columnas(columnas)

    # ---------------------------------------------------------------- consultas
    def _valor(self, fila: int, columna: str) -> object:
        return self._hoja.cell(row=fila, column=self._columnas[columna]).value

    def _coincide(self, fila: int, clave: Valores) -> bool:
        return all(_texto(self._valor(fila, c)) == _texto(v) for c, v in clave.items())

    def _filas_datos(self) -> range:
        return range(2, self._hoja.max_row + 1)

    # ---------------------------------------------------------------- cambios
    def reemplazar_o_agregar(self, clave: Valores, valores: Valores) -> None:
        """Actualiza la primera fila que coincide con `clave`; si no hay, agrega una al final."""
        fila = next((f for f in self._filas_datos() if self._coincide(f, clave)), None)
        if fila is None:
            fila = self._primera_fila_libre()
        for columna, valor in {**clave, **valores}.items():
            self._hoja.cell(row=fila, column=self._columnas[columna], value=valor)

    def eliminar_donde(self, predicado: Callable[[Callable[[str], object]], bool]) -> int:
        """Borra las filas para las que `predicado(leer)` es True. `leer(col)` da el valor de la celda."""
        borradas = 0
        for fila in reversed(self._filas_datos()):   # de abajo hacia arriba: no se corren los índices
            if predicado(lambda col, f=fila: self._valor(f, col)):
                self._hoja.delete_rows(fila)
                borradas += 1
        return borradas

    def agregar(self, valores: Valores) -> None:
        fila = self._primera_fila_libre()
        for columna, valor in valores.items():
            self._hoja.cell(row=fila, column=self._columnas[columna], value=valor)

    # ---------------------------------------------------------------- internos
    def _primera_fila_libre(self) -> int:
        fila = self._hoja.max_row
        while fila > 1 and all(c.value in (None, "") for c in self._hoja[fila]):
            fila -= 1
        return fila + 1

    @staticmethod
    def _buscar_o_crear(libro: Workbook, nombre: str) -> Worksheet:
        for hoja in libro.worksheets:
            if normalizar_encabezado(hoja.title) == nombre:
                return hoja
        return libro.create_sheet(nombre)

    def _asegurar_columnas(self, columnas: list[str]) -> dict[str, int]:
        """Ubica cada columna por su encabezado normalizado; agrega al final las que falten."""
        posiciones: dict[str, int] = {}
        for celda in self._hoja[1]:
            nombre = normalizar_encabezado(celda.value)
            if nombre and nombre not in posiciones:
                posiciones[nombre] = celda.column
        siguiente = max(posiciones.values(), default=0) + 1
        for columna in columnas:
            if columna not in posiciones:
                celda = self._hoja.cell(row=1, column=siguiente, value=columna)
                celda.font, celda.fill = ESTILO_ENCABEZADO["font"], ESTILO_ENCABEZADO["fill"]
                posiciones[columna] = siguiente
                siguiente += 1
        return posiciones


def _texto(valor: object) -> str:
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return "" if valor is None else str(valor).strip().lower()
