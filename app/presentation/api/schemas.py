"""Modelos de entrada/salida de la API (DTOs).

Separan lo que se expone por HTTP de las entidades internas: por ejemplo, el
hash de la contraseña nunca sale en una respuesta.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.application.use_cases.autenticacion import UsuarioAutenticado
from app.application.use_cases.estudiantes import ResultadoValidacion
from app.application.use_cases.gestion_estudiantes import DatosEstudiante
from app.application.use_cases.gestion_usuarios import DatosUsuario
from app.application.use_cases.importacion import ResultadoImportacion
from app.domain.entities import (
    ComparacionMallas,
    Equivalencia,
    EstadoMateria,
    Estudiante,
    EventoAuditoria,
    Homologacion,
    Malla,
    Materia,
    MateriaVista,
    ResumenTipo,
    Ticket,
    Usuario,
)


# ================================================================= sesión
class UsuarioOut(BaseModel):
    username: str
    nombre: str
    rol: str
    codigo_estudiante: str = ""

    @classmethod
    def desde(cls, u: UsuarioAutenticado) -> "UsuarioOut":
        return cls(username=u.username, nombre=u.nombre, rol=u.rol.value, codigo_estudiante=u.codigo_estudiante)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expira_en_minutos: int


# ================================================================= mallas
class MateriaOut(BaseModel):
    codigo: str
    nombre: str
    creditos: int
    semestre: int
    tipo: str
    grupo: str = ""
    observacion: str = ""

    @classmethod
    def desde(cls, m: Materia) -> "MateriaOut":
        return cls(
            codigo=m.codigo, nombre=m.nombre, creditos=m.creditos, semestre=m.semestre,
            tipo=m.tipo.value, grupo=m.grupo, observacion=m.observacion,
        )


class MallaOut(BaseModel):
    version: str
    creditos_totales: int
    materias: list[MateriaOut]

    @classmethod
    def desde(cls, m: Malla) -> "MallaOut":
        materias = sorted(m.materias, key=lambda x: (x.semestre, x.tipo.value, x.codigo))
        return cls(version=m.version, creditos_totales=m.creditos_totales, materias=[MateriaOut.desde(x) for x in materias])


class EquivalenciaOut(BaseModel):
    codigo_anterior: str
    codigo_nuevo: str
    estado: str
    observacion: str

    @classmethod
    def desde(cls, e: Equivalencia) -> "EquivalenciaOut":
        return cls(codigo_anterior=e.codigo_anterior, codigo_nuevo=e.codigo_nuevo, estado=e.estado, observacion=e.observacion)


# ================================================================= estudiantes
class MateriaVistaOut(BaseModel):
    codigo: str
    nombre: str
    creditos: int
    nota: float | None
    periodo: str
    estado: str
    tipologia: str

    @classmethod
    def desde(cls, v: MateriaVista) -> "MateriaVistaOut":
        return cls(
            codigo=v.codigo, nombre=v.nombre, creditos=v.creditos, nota=v.nota,
            periodo=v.periodo, estado=v.estado.value, tipologia=v.tipologia,
        )


class EstudianteOut(BaseModel):
    codigo: str
    nombre: str
    documento: str
    correo: str
    malla_version: str
    estado: str

    @classmethod
    def desde(cls, e: Estudiante) -> "EstudianteOut":
        return cls(
            codigo=e.codigo, nombre=e.nombre, documento=e.documento, correo=e.correo,
            malla_version=e.malla_version, estado=e.estado,
        )


class EstudianteDetalleOut(EstudianteOut):
    historial: list[MateriaVistaOut]

    @classmethod
    def desde(cls, e: Estudiante) -> "EstudianteDetalleOut":
        historial = sorted(e.materias_vistas, key=lambda v: (v.periodo, v.codigo))
        return cls(**EstudianteOut.desde(e).model_dump(), historial=[MateriaVistaOut.desde(v) for v in historial])


class EstudianteIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=120)
    documento: str = Field(min_length=4, max_length=20)
    correo: str = Field(default="", max_length=120)
    malla_version: str = Field(min_length=1, max_length=20)
    estado: Literal["activo", "inactivo", "graduado", "retirado"] = "activo"

    def a_datos(self, codigo: str) -> DatosEstudiante:
        return DatosEstudiante(codigo, self.nombre, self.documento, self.malla_version, self.estado, self.correo)


class EstudianteCrearIn(EstudianteIn):
    codigo: str = Field(min_length=2, max_length=30)
    password_cuenta: str = Field(
        default="", max_length=100,
        description="Si se envía, se crea el usuario del estudiante (usuario = código) con esta contraseña.",
    )


class MateriaVistaIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=30)
    nombre: str = Field(default="", max_length=150)
    creditos: int = Field(ge=1, le=20)
    nota: float | None = Field(default=None, ge=0, le=5)
    periodo: str = Field(default="", max_length=20)
    estado: Literal["aprobada", "reprobada", "cursando", "cancelada"]
    tipologia: str = Field(default="", max_length=40)

    def a_entidad(self) -> MateriaVista:
        return MateriaVista(
            self.codigo, self.nombre, self.creditos, self.nota, self.periodo,
            EstadoMateria(self.estado), self.tipologia,
        )


class HistorialIn(BaseModel):
    materias: list[MateriaVistaIn] = Field(max_length=300)


# ================================================================= validación
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


class ResumenTipoOut(BaseModel):
    tipo: str
    requeridos: int
    reconocidos: int
    pendientes: int

    @classmethod
    def desde(cls, r: ResumenTipo) -> "ResumenTipoOut":
        return cls(tipo=r.tipo.value, requeridos=r.requeridos, reconocidos=r.reconocidos, pendientes=r.pendientes)


class ResumenCreditosOut(BaseModel):
    aprobados_en_historial: int = Field(description="Créditos aprobados según el historial")
    reconocidos: int = Field(description="Créditos que cuentan en la malla vigente")
    requeridos: int
    pendientes: int
    cursando: int
    porcentaje_avance: float
    cumple: bool
    por_tipo: list[ResumenTipoOut]


class ComparacionOut(BaseModel):
    malla_origen: str
    malla_destino: str
    pendientes_origen: int
    pendientes_destino: int
    pendientes_origen_proyectado: int
    pendientes_destino_proyectado: int
    conviene_transicion: bool
    recomendacion: str

    @classmethod
    def desde(cls, c: ComparacionMallas) -> "ComparacionOut":
        return cls(
            malla_origen=c.malla_origen, malla_destino=c.malla_destino,
            pendientes_origen=c.pendientes_origen, pendientes_destino=c.pendientes_destino,
            pendientes_origen_proyectado=c.pendientes_origen_proyectado,
            pendientes_destino_proyectado=c.pendientes_destino_proyectado,
            conviene_transicion=c.conviene_transicion, recomendacion=c.recomendacion,
        )


class ValidacionOut(BaseModel):
    estudiante: EstudianteOut
    malla_vigente: str
    requiere_transicion: bool
    creditos: ResumenCreditosOut
    comparacion: ComparacionOut | None
    homologaciones: list[HomologacionOut]
    materias_cubiertas: list[MateriaOut]
    materias_pendientes: list[MateriaOut]
    materias_no_aprobadas: list[MateriaVistaOut]
    materias_cursando: list[MateriaVistaOut]
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
                cursando=t.creditos_cursando,
                porcentaje_avance=t.porcentaje_avance,
                cumple=t.cumple_creditos,
                por_tipo=[ResumenTipoOut.desde(x) for x in t.resumen_por_tipo()],
            ),
            comparacion=ComparacionOut.desde(r.comparacion) if r.comparacion else None,
            homologaciones=[HomologacionOut.desde(h) for h in t.homologaciones],
            materias_cubiertas=[MateriaOut.desde(m) for m in t.materias_cubiertas],
            materias_pendientes=[MateriaOut.desde(m) for m in t.materias_pendientes],
            materias_no_aprobadas=[MateriaVistaOut.desde(v) for v in t.materias_no_aprobadas],
            materias_cursando=[MateriaVistaOut.desde(v) for v in t.materias_cursando],
            tickets=[TicketOut.desde(x) for x in r.tickets],
            tickets_nuevos=r.tickets_nuevos,
        )


class CerrarTicketIn(BaseModel):
    resolucion: str = Field(min_length=3, max_length=1000)


# ================================================================= usuarios
class UsuarioAdminOut(BaseModel):
    username: str
    nombre: str
    rol: str
    activo: bool
    codigo_estudiante: str

    @classmethod
    def desde(cls, u: Usuario) -> "UsuarioAdminOut":
        return cls(username=u.username, nombre=u.nombre, rol=u.rol.value, activo=u.activo, codigo_estudiante=u.codigo_estudiante)


class UsuarioIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=120)
    rol: Literal["admin", "consultor", "estudiante"]
    activo: bool = True
    codigo_estudiante: str = Field(default="", max_length=30)
    password: str = Field(default="", max_length=100, description="Vacía al editar = no cambiarla")

    def a_datos(self, username: str) -> DatosUsuario:
        return DatosUsuario(username, self.nombre, self.rol, self.activo, self.codigo_estudiante, self.password)


class UsuarioCrearIn(UsuarioIn):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=8, max_length=100)


# ================================================================= importación
class ErrorImportacionOut(BaseModel):
    hoja: str
    fila: int
    mensaje: str


class EstudianteImportadoOut(BaseModel):
    codigo: str
    nombre: str
    accion: str
    malla_version: str
    materias: int
    aprobadas: int
    cursando: int
    reemplaza_historial: bool
    crea_cuenta: bool


class ImportacionOut(BaseModel):
    aplicado: bool
    nuevos: int
    actualizados: int
    total_materias: int
    estudiantes: list[EstudianteImportadoOut]
    errores: list[ErrorImportacionOut]

    @classmethod
    def desde(cls, r: ResultadoImportacion) -> "ImportacionOut":
        return cls(
            aplicado=r.aplicado, nuevos=r.nuevos, actualizados=r.actualizados, total_materias=r.total_materias,
            estudiantes=[EstudianteImportadoOut(**e.__dict__) for e in r.estudiantes],
            errores=[ErrorImportacionOut(**e.__dict__) for e in r.errores],
        )


# ================================================================= auditoría
class EventoAuditoriaOut(BaseModel):
    id: str
    fecha: datetime
    usuario: str
    rol: str
    accion: str
    entidad: str
    entidad_id: str
    detalle: str
    ip: str
    exito: bool

    @classmethod
    def desde(cls, e: EventoAuditoria) -> "EventoAuditoriaOut":
        return cls(**e.__dict__)
