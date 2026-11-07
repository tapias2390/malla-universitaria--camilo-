"""Entidades del dominio académico.

Son clases de datos simples: no saben de Excel, de Drive ni de HTTP.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# ---------------------------------------------------------------------------
# Usuarios del sistema
# ---------------------------------------------------------------------------
class Rol(str, Enum):
    ADMIN = "admin"            # consulta estudiantes y gestiona tickets
    CONSULTOR = "consultor"    # solo consulta estudiantes


@dataclass(frozen=True)
class Usuario:
    username: str
    password_hash: str         # hash bcrypt; nunca se guarda la contraseña en claro
    nombre: str
    rol: Rol
    activo: bool = True


# ---------------------------------------------------------------------------
# Malla curricular
# ---------------------------------------------------------------------------
class TipoMateria(str, Enum):
    OBLIGATORIA = "obligatoria"
    # Una electiva en la malla es un "cupo" (p. ej. "Electiva profesional I")
    # que el estudiante llena con alguna materia. Esos cupos son los que se
    # usan para reemplazar materias eliminadas.
    ELECTIVA = "electiva"


@dataclass(frozen=True)
class Materia:
    codigo: str
    nombre: str
    creditos: int
    semestre: int
    tipo: TipoMateria

    @property
    def es_electiva(self) -> bool:
        return self.tipo is TipoMateria.ELECTIVA


@dataclass
class Malla:
    """Plan de estudios en una versión concreta (p. ej. "2020", "2025")."""

    version: str
    materias: list[Materia]

    def buscar(self, codigo: str) -> Materia | None:
        """Devuelve la materia con ese código o None si no pertenece a esta malla."""
        return next((m for m in self.materias if m.codigo == codigo), None)

    @property
    def electivas(self) -> list[Materia]:
        return [m for m in self.materias if m.es_electiva]

    @property
    def creditos_totales(self) -> int:
        return sum(m.creditos for m in self.materias)


# ---------------------------------------------------------------------------
# Estudiantes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MateriaVista:
    """Registro del historial académico: una materia que el estudiante cursó."""

    codigo: str
    nombre: str
    creditos: int
    nota: float
    periodo: str

    def aprobada(self, nota_minima: float) -> bool:
        return self.nota >= nota_minima


@dataclass
class Estudiante:
    codigo: str
    nombre: str
    documento: str
    malla_version: str        # malla con la que ingresó / con la que está inscrito
    estado: str
    materias_vistas: list[MateriaVista] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Resultado de la transición entre mallas
# ---------------------------------------------------------------------------
class TipoHomologacion(str, Enum):
    DIRECTA = "directa"                      # la materia existe igual en la malla nueva
    EQUIVALENCIA = "equivalencia"            # cambió de código, hay tabla de equivalencias
    REEMPLAZO_ELECTIVA = "reemplazo_electiva"  # la eliminaron y ocupa un cupo de electiva
    REQUIERE_REVISION = "requiere_revision"  # la eliminaron y no hay electiva -> ticket


@dataclass(frozen=True)
class Homologacion:
    """Qué pasó con una materia vista al pasarla a la malla nueva."""

    materia_vista: MateriaVista
    tipo: TipoHomologacion
    materia_destino: Materia | None   # None cuando requiere revisión
    observacion: str


@dataclass(frozen=True)
class ResultadoTransicion:
    """Resumen completo de cómo queda un estudiante en la malla vigente."""

    estudiante: Estudiante
    malla_destino: Malla
    requiere_transicion: bool               # False si ya está en la malla vigente
    homologaciones: list[Homologacion]
    materias_pendientes: list[Materia]      # lo que le falta ver en la malla nueva
    materias_no_aprobadas: list[MateriaVista]

    @property
    def creditos_reconocidos(self) -> int:
        """Créditos de la malla nueva que el estudiante ya tiene cubiertos."""
        return sum(h.materia_destino.creditos for h in self.homologaciones if h.materia_destino)

    @property
    def creditos_requeridos(self) -> int:
        return self.malla_destino.creditos_totales

    @property
    def creditos_pendientes(self) -> int:
        return max(self.creditos_requeridos - self.creditos_reconocidos, 0)

    @property
    def creditos_aprobados_origen(self) -> int:
        """Créditos que el estudiante aprobó según su historial (antes de homologar)."""
        return sum(h.materia_vista.creditos for h in self.homologaciones)

    @property
    def casos_revision(self) -> list[Homologacion]:
        return [h for h in self.homologaciones if h.tipo is TipoHomologacion.REQUIERE_REVISION]

    @property
    def cumple_creditos(self) -> bool:
        """True si ya completó todos los créditos de la malla vigente."""
        return self.creditos_reconocidos >= self.creditos_requeridos


# ---------------------------------------------------------------------------
# Tickets de revisión
# ---------------------------------------------------------------------------
class EstadoTicket(str, Enum):
    ABIERTO = "abierto"
    CERRADO = "cerrado"


@dataclass
class Ticket:
    """Caso que un humano debe revisar (p. ej. materia eliminada sin electiva libre)."""

    id: str
    codigo_estudiante: str
    codigo_materia: str
    nombre_materia: str
    creditos: int
    motivo: str
    fecha_creacion: datetime
    estado: EstadoTicket = EstadoTicket.ABIERTO
    resolucion: str = ""
    cerrado_por: str = ""
