"""Repositorio académico sobre el Excel de estudiantes.

Hojas esperadas:

  estudiantes      codigo | nombre | documento | malla_version | estado
  materias_vistas  codigo_estudiante | codigo_materia | nombre_materia | creditos | nota | periodo
  mallas           version | codigo | nombre | creditos | semestre | tipo (obligatoria/electiva)
  equivalencias    codigo_anterior | codigo_nuevo        (opcional)
"""
from __future__ import annotations

import threading
from collections import defaultdict

from app.domain.entities import Estudiante, Malla, Materia, MateriaVista, TipoMateria
from app.domain.exceptions import ErrorFuenteDatos
from app.infrastructure.data_sources.fuentes import FuenteExcel
from app.infrastructure.data_sources.lector_excel import (
    Fila,
    como_decimal,
    como_entero,
    como_texto,
    exigir_hoja,
    leer_libro,
)

COLUMNAS_ESTUDIANTES = {"codigo", "nombre", "documento", "malla_version"}
COLUMNAS_VISTAS = {"codigo_estudiante", "codigo_materia", "nombre_materia", "creditos", "nota"}
COLUMNAS_MALLAS = {"version", "codigo", "nombre", "creditos", "semestre", "tipo"}


class ExcelRepositorioAcademico:
    def __init__(self, fuente: FuenteExcel) -> None:
        self._fuente = fuente
        # El libro se parsea una sola vez por cada versión descargada del archivo.
        self._lock = threading.Lock()
        self._contenido_previo: bytes | None = None
        self._hojas: dict[str, list[Fila]] = {}

    # ------------------------------------------------------------- lectura base
    def _libro(self) -> dict[str, list[Fila]]:
        contenido = self._fuente.obtener_bytes()
        with self._lock:
            if contenido != self._contenido_previo:
                self._hojas = leer_libro(contenido)
                self._contenido_previo = contenido
            return self._hojas

    # ------------------------------------------------------------- estudiantes
    def listar_estudiantes(self) -> list[Estudiante]:
        filas = exigir_hoja(self._libro(), "estudiantes", COLUMNAS_ESTUDIANTES)
        return [self._a_estudiante(f) for f in filas]

    def obtener_estudiante(self, codigo: str) -> Estudiante | None:
        libro = self._libro()
        filas = exigir_hoja(libro, "estudiantes", COLUMNAS_ESTUDIANTES)
        fila = next((f for f in filas if como_texto(f.get("codigo")) == codigo), None)
        if fila is None:
            return None

        estudiante = self._a_estudiante(fila)
        vistas = exigir_hoja(libro, "materias_vistas", COLUMNAS_VISTAS)
        estudiante.materias_vistas = [
            MateriaVista(
                codigo=como_texto(v.get("codigo_materia")),
                nombre=como_texto(v.get("nombre_materia")),
                creditos=como_entero(v.get("creditos")),
                nota=como_decimal(v.get("nota")),
                periodo=como_texto(v.get("periodo")),
            )
            for v in vistas
            if como_texto(v.get("codigo_estudiante")) == codigo
        ]
        return estudiante

    @staticmethod
    def _a_estudiante(fila: Fila) -> Estudiante:
        return Estudiante(
            codigo=como_texto(fila.get("codigo")),
            nombre=como_texto(fila.get("nombre")),
            documento=como_texto(fila.get("documento")),
            malla_version=como_texto(fila.get("malla_version")),
            estado=como_texto(fila.get("estado")) or "activo",
        )

    # ------------------------------------------------------------- mallas
    def obtener_malla(self, version: str) -> Malla | None:
        filas = exigir_hoja(self._libro(), "mallas", COLUMNAS_MALLAS)
        por_version: dict[str, list[Materia]] = defaultdict(list)
        for f in filas:
            por_version[como_texto(f.get("version"))].append(self._a_materia(f))
        materias = por_version.get(version)
        return Malla(version=version, materias=materias) if materias else None

    @staticmethod
    def _a_materia(fila: Fila) -> Materia:
        tipo_texto = como_texto(fila.get("tipo")).lower()
        try:
            tipo = TipoMateria(tipo_texto)
        except ValueError as exc:
            raise ErrorFuenteDatos(
                f"Tipo de materia inválido '{tipo_texto}' en la hoja 'mallas' "
                "(use 'obligatoria' o 'electiva')."
            ) from exc
        return Materia(
            codigo=como_texto(fila.get("codigo")),
            nombre=como_texto(fila.get("nombre")),
            creditos=como_entero(fila.get("creditos")),
            semestre=como_entero(fila.get("semestre")),
            tipo=tipo,
        )

    # ------------------------------------------------------------- equivalencias
    def obtener_equivalencias(self) -> dict[str, str]:
        filas = self._libro().get("equivalencias", [])  # hoja opcional
        return {
            como_texto(f.get("codigo_anterior")): como_texto(f.get("codigo_nuevo"))
            for f in filas
            if f.get("codigo_anterior") and f.get("codigo_nuevo")
        }
