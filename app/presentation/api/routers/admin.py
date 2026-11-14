"""Rutas de administración: CRUD de estudiantes, historial, usuarios y auditoría (solo admin)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, File, Form, Query, Response, UploadFile, status

from app.domain.exceptions import DatosInvalidos
from app.presentation.api.dependencies import AdminDep, ContenedorDep
from app.presentation.api.schemas import (
    EstudianteCrearIn,
    EstudianteDetalleOut,
    EstudianteIn,
    EventoAuditoriaOut,
    HistorialIn,
    ImportacionOut,
    UsuarioAdminOut,
    UsuarioCrearIn,
    UsuarioIn,
)

router = APIRouter(prefix="/api/admin", tags=["Administración"])
MAX_BYTES_IMPORTACION = 5 * 1024 * 1024
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ----------------------------------------------------------------- importación desde Excel
async def _leer_archivo(archivo: UploadFile) -> bytes:
    if not (archivo.filename or "").lower().endswith(".xlsx"):
        raise DatosInvalidos("Suba un archivo de Excel .xlsx (puede partir de la plantilla).")
    contenido = await archivo.read(MAX_BYTES_IMPORTACION + 1)
    if len(contenido) > MAX_BYTES_IMPORTACION:
        raise DatosInvalidos("El archivo supera 5 MB.")
    return contenido


@router.get("/importacion/plantilla", response_class=Response, summary="Descargar plantilla de importación")
def plantilla(contenedor: ContenedorDep, _: AdminDep) -> Response:
    return Response(
        content=contenedor.generar_plantilla(),
        media_type=MIME_XLSX,
        headers={"Content-Disposition": 'attachment; filename="plantilla_importar_estudiantes.xlsx"'},
    )


@router.post("/importacion/validar", response_model=ImportacionOut,
             summary="Validar un Excel de estudiantes (no guarda nada)")
async def validar_importacion(
    contenedor: ContenedorDep, actor: AdminDep, archivo: UploadFile = File(...), password_cuentas: str = Form("")
) -> ImportacionOut:
    contenido = await _leer_archivo(archivo)
    return ImportacionOut.desde(contenedor.importar_estudiantes.ejecutar(contenido, actor, False, password_cuentas))


@router.post("/importacion/aplicar", response_model=ImportacionOut,
             summary="Importar un Excel de estudiantes (todo o nada)")
async def aplicar_importacion(
    contenedor: ContenedorDep, actor: AdminDep, archivo: UploadFile = File(...), password_cuentas: str = Form("")
) -> ImportacionOut:
    contenido = await _leer_archivo(archivo)
    return ImportacionOut.desde(contenedor.importar_estudiantes.ejecutar(contenido, actor, True, password_cuentas))


# ----------------------------------------------------------------- estudiantes
@router.post("/estudiantes", response_model=EstudianteDetalleOut, status_code=status.HTTP_201_CREATED,
             summary="Registrar estudiante (y opcionalmente su cuenta de acceso)")
def crear_estudiante(datos: EstudianteCrearIn, contenedor: ContenedorDep, actor: AdminDep) -> EstudianteDetalleOut:
    estudiante = contenedor.gestion_estudiantes.crear(datos.a_datos(datos.codigo), actor, datos.password_cuenta)
    return EstudianteDetalleOut.desde(estudiante)


@router.get("/estudiantes/{codigo}", response_model=EstudianteDetalleOut, summary="Estudiante con su historial")
def obtener_estudiante(codigo: str, contenedor: ContenedorDep, _: AdminDep) -> EstudianteDetalleOut:
    return EstudianteDetalleOut.desde(contenedor.gestion_estudiantes.obtener(codigo))


@router.put("/estudiantes/{codigo}", response_model=EstudianteDetalleOut, summary="Actualizar datos del estudiante")
def actualizar_estudiante(codigo: str, datos: EstudianteIn, contenedor: ContenedorDep, actor: AdminDep) -> EstudianteDetalleOut:
    return EstudianteDetalleOut.desde(contenedor.gestion_estudiantes.actualizar(codigo, datos.a_datos(codigo), actor))


@router.delete("/estudiantes/{codigo}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None, summary="Eliminar estudiante y su historial")
def eliminar_estudiante(codigo: str, contenedor: ContenedorDep, actor: AdminDep) -> None:
    contenedor.gestion_estudiantes.eliminar(codigo, actor)


@router.put("/estudiantes/{codigo}/historial", response_model=EstudianteDetalleOut,
            summary="Reemplazar el historial académico completo")
def guardar_historial(codigo: str, datos: HistorialIn, contenedor: ContenedorDep, actor: AdminDep) -> EstudianteDetalleOut:
    materias = [m.a_entidad() for m in datos.materias]
    return EstudianteDetalleOut.desde(contenedor.gestion_estudiantes.guardar_historial(codigo, materias, actor))


# ----------------------------------------------------------------- usuarios
@router.get("/usuarios", response_model=list[UsuarioAdminOut], summary="Listar usuarios")
def listar_usuarios(contenedor: ContenedorDep, _: AdminDep) -> list[UsuarioAdminOut]:
    return [UsuarioAdminOut.desde(u) for u in contenedor.gestion_usuarios.listar()]


@router.post("/usuarios", response_model=UsuarioAdminOut, status_code=status.HTTP_201_CREATED, summary="Crear usuario")
def crear_usuario(datos: UsuarioCrearIn, contenedor: ContenedorDep, actor: AdminDep) -> UsuarioAdminOut:
    return UsuarioAdminOut.desde(contenedor.gestion_usuarios.crear(datos.a_datos(datos.username), actor))


@router.put("/usuarios/{username}", response_model=UsuarioAdminOut, summary="Actualizar usuario")
def actualizar_usuario(username: str, datos: UsuarioIn, contenedor: ContenedorDep, actor: AdminDep) -> UsuarioAdminOut:
    return UsuarioAdminOut.desde(contenedor.gestion_usuarios.actualizar(username, datos.a_datos(username), actor))


@router.delete("/usuarios/{username}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None, summary="Eliminar usuario")
def eliminar_usuario(username: str, contenedor: ContenedorDep, actor: AdminDep) -> None:
    contenedor.gestion_usuarios.eliminar(username, actor)


# ----------------------------------------------------------------- auditoría
@router.get("/auditoria", response_model=list[EventoAuditoriaOut], summary="Registro de auditoría")
def auditoria(
    contenedor: ContenedorDep,
    _: AdminDep,
    usuario: str = "",
    accion: str = "",
    desde: datetime | None = None,
    limite: int = Query(300, ge=1, le=2000),
) -> list[EventoAuditoriaOut]:
    eventos = contenedor.listar_auditoria.ejecutar(usuario, accion, desde, limite)
    return [EventoAuditoriaOut.desde(e) for e in eventos]
