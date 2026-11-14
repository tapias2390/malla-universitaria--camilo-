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
    ADMIN = "admin"            # todo: consulta, CRUD de estudiantes/usuarios, tickets y auditoría
    CONSULTOR = "consultor"    # consulta estudiantes y valida su transición
    ESTUDIANTE = "estudiante"  # solo ve SU avance en la malla vigente


@dataclass(frozen=True)
class Usuario:
    username: str
    password_hash: str         # hash bcrypt; nunca se guarda la contraseña en claro
    nombre: str
    rol: Rol
    activo: bool = True
    # Solo para rol ESTUDIANTE: código del estudiante al que pertenece la cuenta.
    codigo_estudiante: str = ""


# ---------------------------------------------------------------------------
# Malla curricular
# ---------------------------------------------------------------------------
class TipoMateria(str, Enum):
    OBLIGATORIA = "obligatoria"
    # Cupo de LIBRE ELECCIÓN ("electiva"): el estudiante lo llena con cualquier
    # materia. Son los cupos que reciben las materias eliminadas de la malla.
    ELECTIVA = "electiva"
    # Cupo de OPTATIVA: solo lo llenan materias del catálogo de su `grupo`
    # (p. ej. "ciencias_sociales", "disciplinar"). Hoja `optativas` del Excel.
    OPTATIVA = "optativa"
    # Nivelación (p. ej. Inglés I-IV): se homologa por código como una obligatoria.
    NIVELACION = "nivelacion"


@dataclass(frozen=True)
class Materia:
    codigo: str
    nombre: str
    creditos: int
    semestre: int
    tipo: TipoMateria
    grupo: str = ""            # solo para optativas: grupo del catálogo que la puede llenar
    observacion: str = ""

    @property
    def es_cupo(self) -> bool:
        """True si es un cupo (electiva u optativa) y no una materia concreta."""
        return self.tipo in (TipoMateria.ELECTIVA, TipoMateria.OPTATIVA)


@dataclass
class Malla:
    """Plan de estudios en una versión concreta (p. ej. "2016", "2026")."""

    version: str
    materias: list[Materia]

    def buscar(self, codigo: str) -> Materia | None:
        """Materia concreta (no cupo) con ese código, o None si no pertenece a esta malla."""
        return next((m for m in self.materias if m.codigo == codigo and not m.es_cupo), None)

    @property
    def electivas(self) -> list[Materia]:
        return [m for m in self.materias if m.tipo is TipoMateria.ELECTIVA]

    def optativas(self, grupo: str | None = None) -> list[Materia]:
        return [
            m for m in self.materias
            if m.tipo is TipoMateria.OPTATIVA and (grupo is None or m.grupo == grupo)
        ]

    @property
    def creditos_totales(self) -> int:
        return sum(m.creditos for m in self.materias)

    def creditos_por_tipo(self, tipo: TipoMateria) -> int:
        return sum(m.creditos for m in self.materias if m.tipo is tipo)


@dataclass(frozen=True)
class Equivalencia:
    """Una materia de la malla anterior que se reconoce como otra de la malla nueva.

    Si varias equivalencias apuntan al MISMO `codigo_nuevo` es una FUSIÓN: el
    estudiante debe haber aprobado TODAS las materias anteriores para que se le
    reconozca la nueva (p. ej. Química General I + II -> Química General).
    """

    codigo_anterior: str
    codigo_nuevo: str
    estado: str = "confirmada"   # "confirmada" o "propuesta" (pendiente de aval del comité)
    observacion: str = ""


@dataclass(frozen=True)
class MateriaCatalogo:
    """Materia que puede llenar un cupo de optativa de su grupo."""

    grupo: str
    codigo: str
    nombre: str


# ---------------------------------------------------------------------------
# Estudiantes
# ---------------------------------------------------------------------------
class EstadoMateria(str, Enum):
    APROBADA = "aprobada"
    REPROBADA = "reprobada"
    CURSANDO = "cursando"      # inscrita en el periodo actual, aún sin nota
    CANCELADA = "cancelada"


@dataclass(frozen=True)
class MateriaVista:
    """Registro del historial académico: una materia que el estudiante cursó."""

    codigo: str
    nombre: str
    creditos: int
    nota: float | None         # None si no tiene nota (validación por suficiencia, cursando...)
    periodo: str
    estado: EstadoMateria
    tipologia: str = ""        # como la reporta la universidad: fund_obligatoria, libre_eleccion...

    @property
    def aprobada(self) -> bool:
        return self.estado is EstadoMateria.APROBADA

    @property
    def nota_texto(self) -> str:
        return "—" if self.nota is None else f"{self.nota:.1f}"


@dataclass
class Estudiante:
    codigo: str
    nombre: str
    documento: str
    malla_version: str        # malla con la que ingresó / con la que está inscrito
    estado: str
    correo: str = ""
    materias_vistas: list[MateriaVista] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Resultado de la transición entre mallas
# ---------------------------------------------------------------------------
class TipoHomologacion(str, Enum):
    DIRECTA = "directa"                        # la materia existe igual en la malla nueva
    EQUIVALENCIA = "equivalencia"              # cambió de código o se fusionó con otra
    OPTATIVA = "optativa"                      # está en el catálogo y llena un cupo de optativa
    REEMPLAZO_ELECTIVA = "reemplazo_electiva"  # ya no existe y llena un cupo de libre elección
    REQUIERE_REVISION = "requiere_revision"    # no se pudo ubicar -> ticket


@dataclass(frozen=True)
class Homologacion:
    """Qué pasó con una materia vista al pasarla a la malla nueva."""

    materia_vista: MateriaVista
    tipo: TipoHomologacion
    materia_destino: Materia | None   # None cuando requiere revisión
    observacion: str


@dataclass(frozen=True)
class ResumenTipo:
    """Créditos de un tipo de materia (obligatoria, optativa...) en la malla destino."""

    tipo: TipoMateria
    requeridos: int
    reconocidos: int

    @property
    def pendientes(self) -> int:
        return max(self.requeridos - self.reconocidos, 0)


@dataclass(frozen=True)
class ResultadoTransicion:
    """Resumen completo de cómo queda un estudiante en la malla destino."""

    estudiante: Estudiante
    malla_destino: Malla
    requiere_transicion: bool               # False si ya está en la malla vigente
    homologaciones: list[Homologacion]
    materias_pendientes: list[Materia]      # lo que le falta ver en la malla nueva
    materias_no_aprobadas: list[MateriaVista]
    materias_cursando: list[MateriaVista] = field(default_factory=list)

    @property
    def materias_cubiertas(self) -> list[Materia]:
        """Materias/cupos de la malla destino ya cubiertos (sin repetir: una fusión cuenta una vez)."""
        unicas: dict[str, Materia] = {}
        for h in self.homologaciones:
            if h.materia_destino:
                unicas[h.materia_destino.codigo] = h.materia_destino
        return list(unicas.values())

    @property
    def creditos_reconocidos(self) -> int:
        return sum(m.creditos for m in self.materias_cubiertas)

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
    def creditos_cursando(self) -> int:
        return sum(v.creditos for v in self.materias_cursando)

    @property
    def porcentaje_avance(self) -> float:
        if not self.creditos_requeridos:
            return 0.0
        return round(100 * self.creditos_reconocidos / self.creditos_requeridos, 1)

    def resumen_por_tipo(self) -> list[ResumenTipo]:
        cubiertas = self.materias_cubiertas
        resumen = []
        for tipo in TipoMateria:
            requeridos = self.malla_destino.creditos_por_tipo(tipo)
            if requeridos:
                reconocidos = sum(m.creditos for m in cubiertas if m.tipo is tipo)
                resumen.append(ResumenTipo(tipo, requeridos, reconocidos))
        return resumen

    @property
    def casos_revision(self) -> list[Homologacion]:
        return [h for h in self.homologaciones if h.tipo is TipoHomologacion.REQUIERE_REVISION]

    @property
    def cumple_creditos(self) -> bool:
        """True si ya completó todos los créditos de la malla destino."""
        return self.creditos_reconocidos >= self.creditos_requeridos


@dataclass(frozen=True)
class ComparacionMallas:
    """Cuánto le falta al estudiante si se queda en su malla o si pasa a la vigente.

    Sirve para decidir si la transición le conviene (a un estudiante muy
    avanzado puede salirle más largo pasarse a la malla nueva).
    """

    malla_origen: str
    malla_destino: str
    pendientes_origen: int
    pendientes_destino: int
    # Lo mismo, suponiendo que aprueba todo lo que está cursando:
    pendientes_origen_proyectado: int
    pendientes_destino_proyectado: int

    @property
    def conviene_transicion(self) -> bool:
        return self.pendientes_destino_proyectado <= self.pendientes_origen_proyectado

    @property
    def recomendacion(self) -> str:
        diferencia = self.pendientes_destino_proyectado - self.pendientes_origen_proyectado
        if diferencia < 0:
            return f"Le conviene la malla {self.malla_destino}: termina con {-diferencia} créditos menos."
        if diferencia == 0:
            return "Le faltan los mismos créditos en ambas mallas."
        return (
            f"Le conviene terminar en la malla {self.malla_origen}: en la {self.malla_destino} "
            f"le faltarían {diferencia} créditos más."
        )


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


# ---------------------------------------------------------------------------
# Auditoría
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class EventoAuditoria:
    """Quién hizo qué y cuándo. Nunca se modifica ni se borra."""

    id: str
    fecha: datetime
    usuario: str
    rol: str
    accion: str                # p. ej. "login", "crear_estudiante", "cerrar_ticket"
    entidad: str               # "estudiante", "usuario", "ticket", "sesion"...
    entidad_id: str
    detalle: str
    ip: str = ""
    exito: bool = True
