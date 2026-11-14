"""Repositorio de usuarios sobre el Excel de usuarios.

Hoja `usuarios`:
    username | password_hash | nombre | rol | activo | codigo_estudiante

- rol: admin, consultor o estudiante.
- codigo_estudiante: solo para rol estudiante (código en el Excel académico).
- Las contraseñas se guardan SOLO como hash bcrypt.
"""
from __future__ import annotations

import logging

from app.domain.entities import Rol, Usuario
from app.infrastructure.data_sources.editor_excel import EditorExcel, HojaEditable
from app.infrastructure.data_sources.fuentes import FuenteExcel
from app.infrastructure.data_sources.lector_excel import (
    Fila,
    como_booleano,
    como_texto,
    exigir_hoja,
    leer_libro,
)

log = logging.getLogger(__name__)

COLUMNAS = {"username", "password_hash", "nombre", "rol"}
ESCRITURA = ["username", "password_hash", "nombre", "rol", "activo", "codigo_estudiante"]


class ExcelRepositorioUsuarios:
    def __init__(self, fuente: FuenteExcel) -> None:
        self._fuente = fuente
        self._editor = EditorExcel(fuente)

    def _filas(self) -> list[Fila]:
        return exigir_hoja(leer_libro(self._fuente.obtener_bytes()), "usuarios", COLUMNAS)

    def listar(self) -> list[Usuario]:
        usuarios = (self._a_usuario(f) for f in self._filas())
        return [u for u in usuarios if u is not None]

    def obtener_por_username(self, username: str) -> Usuario | None:
        username = username.strip().lower()
        for fila in self._filas():
            if como_texto(fila.get("username")).lower() == username:
                return self._a_usuario(fila)
        return None

    def guardar(self, usuario: Usuario) -> None:
        with self._editor.editar() as libro:
            HojaEditable(libro, "usuarios", ESCRITURA).reemplazar_o_agregar(
                {"username": usuario.username},
                {
                    "password_hash": usuario.password_hash,
                    "nombre": usuario.nombre,
                    "rol": usuario.rol.value,
                    "activo": "si" if usuario.activo else "no",
                    "codigo_estudiante": usuario.codigo_estudiante,
                },
            )

    def eliminar(self, username: str) -> None:
        with self._editor.editar() as libro:
            HojaEditable(libro, "usuarios", ESCRITURA).eliminar_donde(
                lambda leer: como_texto(leer("username")).lower() == username.lower()
            )

    @staticmethod
    def _a_usuario(fila: Fila) -> Usuario | None:
        username = como_texto(fila.get("username")).lower()
        if not username:
            return None
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
            codigo_estudiante=como_texto(fila.get("codigo_estudiante")),
        )
