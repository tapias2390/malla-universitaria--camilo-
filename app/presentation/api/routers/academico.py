"""Rutas de estudiantes y mallas (requieren estar autenticado)."""
from __future__ import annotations

from fastapi import APIRouter

from app.presentation.api.dependencies import ContenedorDep, UsuarioDep
from app.presentation.api.schemas import EstudianteOut, MallaOut, ValidacionOut

router = APIRouter(prefix="/api", tags=["Académico"])


@router.get("/estudiantes", response_model=list[EstudianteOut], summary="Listar / buscar estudiantes")
def listar_estudiantes(contenedor: ContenedorDep, _: UsuarioDep, q: str = "") -> list[EstudianteOut]:
    return [EstudianteOut.desde(e) for e in contenedor.listar_estudiantes.ejecutar(q)]


@router.post(
    "/estudiantes/{codigo}/validar-malla",
    response_model=ValidacionOut,
    summary="Validar al estudiante contra la malla vigente (puede crear tickets)",
)
def validar_malla(codigo: str, contenedor: ContenedorDep, _: UsuarioDep) -> ValidacionOut:
    return ValidacionOut.desde(contenedor.validar_malla.ejecutar(codigo))


@router.get("/mallas/vigente", response_model=MallaOut, summary="Malla vigente")
def malla_vigente(contenedor: ContenedorDep, _: UsuarioDep) -> MallaOut:
    return MallaOut.desde(contenedor.consultar_malla.ejecutar(contenedor.settings.malla_vigente))


@router.get("/mallas/{version}", response_model=MallaOut, summary="Malla por versión")
def malla_por_version(version: str, contenedor: ContenedorDep, _: UsuarioDep) -> MallaOut:
    return MallaOut.desde(contenedor.consultar_malla.ejecutar(version))
