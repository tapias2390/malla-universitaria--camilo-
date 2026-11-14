"""Puertos: contratos que la infraestructura debe cumplir.

Los casos de uso dependen de estas interfaces, nunca de Excel, Drive o PyJWT
directamente. Así se puede cambiar el origen de datos (p. ej. pasar de Excel a
una base de datos) sin tocar las reglas de negocio, y en las pruebas se usan
implementaciones falsas en memoria.
"""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.domain.entities import (
    Equivalencia,
    Estudiante,
    EventoAuditoria,
    Malla,
    MateriaCatalogo,
    MateriaVista,
    Ticket,
    Usuario,
)


class RepositorioUsuarios(Protocol):
    def obtener_por_username(self, username: str) -> Usuario | None: ...

    def listar(self) -> list[Usuario]: ...

    def guardar(self, usuario: Usuario) -> None:
        """Crea o actualiza el usuario (según su username)."""
        ...

    def eliminar(self, username: str) -> None: ...


class RepositorioAcademico(Protocol):
    # --- estudiantes ---
    def listar_estudiantes(self) -> list[Estudiante]: ...

    def obtener_estudiante(self, codigo: str) -> Estudiante | None:
        """Devuelve el estudiante con su historial de materias vistas."""
        ...

    def guardar_estudiante(self, estudiante: Estudiante) -> None:
        """Crea o actualiza los datos básicos del estudiante (no toca su historial)."""
        ...

    def eliminar_estudiante(self, codigo: str) -> None:
        """Elimina al estudiante y todo su historial."""
        ...

    def guardar_historial(self, codigo: str, materias: list[MateriaVista]) -> None:
        """Reemplaza el historial completo del estudiante."""
        ...

    def guardar_lote(self, estudiantes: list[Estudiante], historiales: dict[str, list[MateriaVista]]) -> None:
        """Crea/actualiza varios estudiantes y reemplaza los historiales dados, en una sola escritura."""
        ...

    # --- mallas (solo lectura: las mantiene la oficina académica en el Excel) ---
    def versiones_malla(self) -> list[str]: ...

    def obtener_malla(self, version: str) -> Malla | None: ...

    def obtener_equivalencias(self) -> list[Equivalencia]: ...

    def obtener_catalogo_optativas(self) -> list[MateriaCatalogo]: ...


class RepositorioTickets(Protocol):
    def guardar(self, ticket: Ticket) -> None:
        """Crea o actualiza el ticket (según su id)."""
        ...

    def obtener(self, ticket_id: str) -> Ticket | None: ...

    def listar(self, estado: str | None = None) -> list[Ticket]: ...

    def buscar_abierto(self, codigo_estudiante: str, codigo_materia: str) -> Ticket | None: ...


class RepositorioAuditoria(Protocol):
    def registrar(self, evento: EventoAuditoria) -> None: ...

    def listar(
        self,
        usuario: str | None = None,
        accion: str | None = None,
        desde: datetime | None = None,
        limite: int = 500,
    ) -> list[EventoAuditoria]:
        """Eventos más recientes primero."""
        ...


class HasherPassword(Protocol):
    def hashear(self, password: str) -> str: ...

    def verificar(self, password: str, password_hash: str) -> bool: ...


class ServicioTokens(Protocol):
    def emitir(self, usuario: Usuario) -> str: ...

    def decodificar(self, token: str) -> dict:
        """Devuelve los claims. Lanza TokenInvalido si no es válido."""
        ...
