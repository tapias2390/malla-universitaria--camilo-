"""Rutas de consulta: estudiantes (personal académico), mallas (todos) y avance propio (estudiante)."""
from __future__ import annotations

from fastapi import APIRouter

from app.presentation.api.dependencies import ContenedorDep, CualquieraDep, EstudianteDep, PersonalDep
from app.presentation.api.schemas import EquivalenciaOut, EstudianteOut, MallaOut, ValidacionOut

router = APIRouter(prefix="/api", tags=["Consulta"])


# ----------------------------------------------------------------- personal (admin / consultor)
@router.get("/estudiantes", response_model=list[EstudianteOut], summary="Listar / buscar estudiantes")
def listar_estudiantes(contenedor: ContenedorDep, _: PersonalDep, q: str = "") -> list[EstudianteOut]:
    return [EstudianteOut.desde(e) for e in contenedor.listar_estudiantes.ejecutar(q)]


@router.post(
    "/estudiantes/{codigo}/validar-malla",
    response_model=ValidacionOut,
    summary="Validar al estudiante contra la malla vigente (puede crear tickets)",
)
def validar_malla(codigo: str, contenedor: ContenedorDep, actor: PersonalDep) -> ValidacionOut:
    return ValidacionOut.desde(contenedor.validar_malla.ejecutar(codigo, actor))


# ----------------------------------------------------------------- estudiante
@router.get("/mi-avance", response_model=ValidacionOut, summary="Avance del estudiante que inició sesión")
def mi_avance(contenedor: ContenedorDep, actor: EstudianteDep) -> ValidacionOut:
    return ValidacionOut.desde(contenedor.mi_avance.ejecutar(actor))


# ----------------------------------------------------------------- mallas (cualquier usuario)
@router.get("/mallas", response_model=list[str], summary="Versiones de malla cargadas")
def versiones(contenedor: ContenedorDep, _: CualquieraDep) -> list[str]:
    return contenedor.consultar_malla.versiones()


@router.get("/equivalencias", response_model=list[EquivalenciaOut], summary="Equivalencias entre mallas")
def equivalencias(contenedor: ContenedorDep, _: CualquieraDep) -> list[EquivalenciaOut]:
    return [EquivalenciaOut.desde(e) for e in contenedor.consultar_malla.equivalencias()]


@router.get("/mallas/vigente", response_model=MallaOut, summary="Malla vigente")
def malla_vigente(contenedor: ContenedorDep, _: CualquieraDep) -> MallaOut:
    return MallaOut.desde(contenedor.consultar_malla.ejecutar(contenedor.settings.malla_vigente))


@router.get("/mallas/{version}", response_model=MallaOut, summary="Malla por versión")
def malla_por_version(version: str, contenedor: ContenedorDep, _: CualquieraDep) -> MallaOut:
    return MallaOut.desde(contenedor.consultar_malla.ejecutar(version))
