"""Modelos de entrada/salida de la API (DTOs).

Separan lo que se expone por HTTP de las entidades internas: por ejemplo, el
hash de la contraseña nunca sale en una respuesta.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.application.use_cases.autenticacion import UsuarioAutenticado
from app.application.use_cases.estudiantes import ResultadoValidacion
from app.domain.entities import Estudiante, Homologacion, Malla, Materia, MateriaVista, Ticket


# ----------------------------------------------------------------- auth
class UsuarioOut(BaseModel):
    username: str
    nombre: str
    rol: str

    @classmethod
    def desde(cls, u: UsuarioAutenticado) -> "UsuarioOut":
        return cls(username=u.username, nombre=u.nombre, rol=u.rol.value)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expira_en_minutos: int


# ----------------------------------------------------------------- académico
class MateriaOut(BaseModel):
    codigo: str
    nombre: str
    creditos: int
    semestre: int
    tipo: str

    @classmethod
    def desde(cls, m: Materia) -> "MateriaOut":
        return cls(codigo=m.codigo, nombre=m.nombre, creditos=m.creditos, semestre=m.semestre, tipo=m.tipo.value)


class MallaOut(BaseModel):
    version: str
    creditos_totales: int
    materias: list[MateriaOut]

    @classmethod
    def desde(cls, m: Malla) -> "MallaOut":
        materias = sorted(m.materias, key=lambda x: (x.semestre, x.codigo))
        return cls(version=m.version, creditos_totales=m.creditos_totales, materias=[MateriaOut.desde(x) for x in materias])


class MateriaVistaOut(BaseModel):
    codigo: str
    nombre: str
    creditos: int
    nota: float
    periodo: str

    @classmethod
    def desde(cls, v: MateriaVista) -> "MateriaVistaOut":
        return cls(codigo=v.codigo, nombre=v.nombre, creditos=v.creditos, nota=v.nota, periodo=v.periodo)


class EstudianteOut(BaseModel):
    codigo: str
    nombre: str
    documento: str
    malla_version: str
    estado: str

    @classmethod
    def desde(cls, e: Estudiante) -> "EstudianteOut":
        return cls(codigo=e.codigo, nombre=e.nombre, documento=e.documento, malla_version=e.malla_version, estado=e.estado)


class HomologacionOut(BaseModel):
    materia_vista: MateriaVistaOut
    tipo: str
    materia_destino: MateriaOut | None
    observacion: str

    @classmethod
    def desde(cls, h: Homologacion) -> "HomologacionOut":
        return cls(
            materia_vista=MateriaVistaOut.desde(h.materia_vista),
            tipo=h.tipo.value,
            materia_destino=MateriaOut.desde(h.materia_destino) if h.materia_destino else None,
            observacion=h.observacion,
        )


class TicketOut(BaseModel):
    id: str
    codigo_estudiante: str
    codigo_materia: str
    nombre_materia: str
    creditos: int
    motivo: str
    fecha_creacion: datetime
    estado: str
    resolucion: str
    cerrado_por: str

    @classmethod
    def desde(cls, t: Ticket) -> "TicketOut":
        return cls(
            id=t.id, codigo_estudiante=t.codigo_estudiante, codigo_materia=t.codigo_materia,
            nombre_materia=t.nombre_materia, creditos=t.creditos, motivo=t.motivo,
            fecha_creacion=t.fecha_creacion, estado=t.estado.value,
            resolucion=t.resolucion, cerrado_por=t.cerrado_por,
        )


class ResumenCreditosOut(BaseModel):
    aprobados_en_historial: int = Field(description="Créditos aprobados según el historial")
    reconocidos: int = Field(description="Créditos que cuentan en la malla vigente")
    requeridos: int
    pendientes: int
    cumple: bool


class ValidacionOut(BaseModel):
    estudiante: EstudianteOut
    malla_vigente: str
    requiere_transicion: bool
    creditos: ResumenCreditosOut
    homologaciones: list[HomologacionOut]
    materias_pendientes: list[MateriaOut]
    materias_no_aprobadas: list[MateriaVistaOut]
    tickets: list[TicketOut]
    tickets_nuevos: int

    @classmethod
    def desde(cls, r: ResultadoValidacion) -> "ValidacionOut":
        t = r.transicion
        return cls(
            estudiante=EstudianteOut.desde(t.estudiante),
            malla_vigente=t.malla_destino.version,
            requiere_transicion=t.requiere_transicion,
            creditos=ResumenCreditosOut(
                aprobados_en_historial=t.creditos_aprobados_origen,
                reconocidos=t.creditos_reconocidos,
                requeridos=t.creditos_requeridos,
                pendientes=t.creditos_pendientes,
                cumple=t.cumple_creditos,
            ),
            homologaciones=[HomologacionOut.desde(h) for h in t.homologaciones],
            materias_pendientes=[MateriaOut.desde(m) for m in t.materias_pendientes],
            materias_no_aprobadas=[MateriaVistaOut.desde(v) for v in t.materias_no_aprobadas],
            tickets=[TicketOut.desde(x) for x in r.tickets],
            tickets_nuevos=r.tickets_nuevos,
        )


class CerrarTicketIn(BaseModel):
    resolucion: str = Field(min_length=3, max_length=1000)
