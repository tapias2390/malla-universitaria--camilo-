"""Convierte un .xlsx en listas de diccionarios (una por hoja).

La primera fila de cada hoja son los encabezados. Se normalizan para tolerar
mayúsculas, tildes y espacios: "Código Materia" -> "codigo_materia".
"""
from __future__ import annotations

import io
import unicodedata

from openpyxl import load_workbook

from app.domain.exceptions import ErrorFuenteDatos

Fila = dict[str, object]


def normalizar_encabezado(texto: object) -> str:
    texto = str(texto or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return "_".join(texto.split())


def leer_libro(contenido: bytes) -> dict[str, list[Fila]]:
    """Devuelve {nombre_hoja_normalizado: [fila, ...]} ignorando filas vacías."""
    try:
        libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    except Exception as exc:  # openpyxl lanza varios tipos según el problema
        raise ErrorFuenteDatos(f"El archivo no es un Excel válido: {exc}") from exc

    hojas: dict[str, list[Fila]] = {}
    for hoja in libro.worksheets:
        filas = hoja.iter_rows(values_only=True)
        encabezados = [normalizar_encabezado(c) for c in next(filas, [])]
        datos = []
        for fila in filas:
            if all(celda in (None, "") for celda in fila):
                continue
            datos.append({encabezados[i]: celda for i, celda in enumerate(fila) if i < len(encabezados)})
        hojas[normalizar_encabezado(hoja.title)] = datos
    libro.close()
    return hojas


def exigir_hoja(hojas: dict[str, list[Fila]], nombre: str, columnas: set[str]) -> list[Fila]:
    """Obtiene una hoja obligatoria y verifica que tenga las columnas esperadas."""
    if nombre not in hojas:
        raise ErrorFuenteDatos(f"Falta la hoja '{nombre}' en el Excel.")
    filas = hojas[nombre]
    if filas:
        faltantes = columnas - set(filas[0].keys())
        if faltantes:
            raise ErrorFuenteDatos(
                f"A la hoja '{nombre}' le faltan las columnas: {', '.join(sorted(faltantes))}."
            )
    return filas


# --- Conversores de celdas ---------------------------------------------------
def como_texto(valor: object) -> str:
    """Texto limpio. Evita que el código 2020 llegue como '2020.0'."""
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return str(valor).strip()


def como_entero(valor: object, por_defecto: int = 0) -> int:
    try:
        return int(float(str(valor).replace(",", ".")))
    except (TypeError, ValueError):
        return por_defecto


def como_decimal(valor: object, por_defecto: float = 0.0) -> float:
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return por_defecto


def como_decimal_opcional(valor: object) -> float | None:
    """Como `como_decimal`, pero una celda vacía (o sin número) da None en vez de 0."""
    if valor is None or como_texto(valor) == "":
        return None
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


def como_booleano(valor: object) -> bool:
    if isinstance(valor, bool):
        return valor
    return como_texto(valor).lower() in {"1", "si", "sí", "true", "verdadero", "x", "activo"}
