"""Puertos: contratos que la infraestructura debe cumplir.

Los casos de uso dependen de estas interfaces, nunca de Excel, Drive o PyJWT
directamente. Así se puede cambiar el origen de datos (p. ej. pasar de Excel a
una base de datos) sin tocar las reglas de negocio, y en las pruebas se usan
implementaciones falsas en memoria.
"""
from __future__ import annotations

from typing import Protocol

from app.domain.entities import Estudiante, Malla, Ticket, Usuario


class RepositorioUsuarios(Protocol):
    def obtener_por_username(self, username: str) -> Usuario | None: ...


class RepositorioAcademico(Protocol):
    def listar_estudiantes(self) -> list[Estudiante]: ...

    def obtener_estudiante(self, codigo: str) -> Estudiante | None:
        """Devuelve el estudiante con su historial de materias vistas."""
        ...

    def obtener_malla(self, version: str) -> Malla | None: ...

    def obtener_equivalencias(self) -> dict[str, str]:
        """{codigo_anterior: codigo_nuevo}. Vacío si no hay tabla de equivalencias."""
        ...


class RepositorioTickets(Protocol):
    def guardar(self, ticket: Ticket) -> None:
        """Crea o actualiza el ticket (según su id)."""
        ...

    def obtener(self, ticket_id: str) -> Ticket | None: ...

    def listar(self, estado: str | None = None) -> list[Ticket]: ...

    def buscar_abierto(self, codigo_estudiante: str, codigo_materia: str) -> Ticket | None: ...


class HasherPassword(Protocol):
    def hashear(self, password: str) -> str: ...

    def verificar(self, password: str, password_hash: str) -> bool: ...


class ServicioTokens(Protocol):
    def emitir(self, usuario: Usuario) -> str: ...

    def decodificar(self, token: str) -> dict:
        """Devuelve los claims. Lanza TokenInvalido si no es válido."""
        ...
