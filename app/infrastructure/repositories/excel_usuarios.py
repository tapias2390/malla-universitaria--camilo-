"""Repositorio de usuarios sobre el Excel de usuarios.

Hoja esperada: `usuarios`
    username | password_hash | nombre | rol | activo
"""
from __future__ import annotations

import logging

from app.domain.entities import Rol, Usuario
from app.infrastructure.data_sources.fuentes import FuenteExcel
from app.infrastructure.data_sources.lector_excel import (
    como_booleano,
    como_texto,
    exigir_hoja,
    leer_libro,
)

log = logging.getLogger(__name__)

COLUMNAS = {"username", "password_hash", "nombre", "rol"}


class ExcelRepositorioUsuarios:
    def __init__(self, fuente: FuenteExcel) -> None:
        self._fuente = fuente

    def obtener_por_username(self, username: str) -> Usuario | None:
        filas = exigir_hoja(leer_libro(self._fuente.obtener_bytes()), "usuarios", COLUMNAS)
        for fila in filas:
            if como_texto(fila.get("username")).lower() != username:
                continue
            try:
                rol = Rol(como_texto(fila.get("rol")).lower())
            except ValueError:
                log.warning("Usuario '%s' con rol desconocido; se ignora.", username)
                return None
            activo = fila.get("activo")
            return Usuario(
                username=username,
                password_hash=como_texto(fila.get("password_hash")),
                nombre=como_texto(fila.get("nombre")),
                rol=rol,
                # Si la columna 'activo' está vacía se asume activo.
                activo=True if activo in (None, "") else como_booleano(activo),
            )
        return None
