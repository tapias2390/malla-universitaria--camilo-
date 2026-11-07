"""Creación de la aplicación FastAPI."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.bootstrap import construir_contenedor
from app.domain.exceptions import (
    AccesoDenegado,
    CredencialesInvalidas,
    ErrorDominio,
    ErrorFuenteDatos,
    EstudianteNoEncontrado,
    MallaNoEncontrada,
    TicketNoEncontrado,
    TokenInvalido,
)
from app.infrastructure.config import Settings, obtener_settings
from app.presentation.api.routers import academico, auth, tickets

log = logging.getLogger(__name__)
CARPETA_WEB = Path(__file__).resolve().parent.parent / "web"

# Traducción de errores de negocio -> (código HTTP, mensaje por defecto)
MAPA_ERRORES: dict[type[ErrorDominio], tuple[int, str]] = {
    CredencialesInvalidas: (status.HTTP_401_UNAUTHORIZED, "Usuario o contraseña incorrectos."),
    TokenInvalido: (status.HTTP_401_UNAUTHORIZED, "Sesión inválida o vencida. Inicie sesión de nuevo."),
    AccesoDenegado: (status.HTTP_403_FORBIDDEN, "No tiene permisos para esta operación."),
    EstudianteNoEncontrado: (status.HTTP_404_NOT_FOUND, "Estudiante no encontrado."),
    MallaNoEncontrada: (status.HTTP_404_NOT_FOUND, "Malla no encontrada."),
    TicketNoEncontrado: (status.HTTP_404_NOT_FOUND, "Ticket no encontrado."),
    ErrorFuenteDatos: (status.HTTP_503_SERVICE_UNAVAILABLE, "No se pudieron leer los datos."),
}


def crear_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or obtener_settings()

    app = FastAPI(
        title="Transición de Mallas Curriculares",
        description="Login con JWT, consulta de estudiantes y homologación contra la malla vigente.",
        version="1.0.0",
    )
    app.state.contenedor = construir_contenedor(settings)

    @app.exception_handler(ErrorDominio)
    async def manejar_error_dominio(_: Request, exc: ErrorDominio) -> JSONResponse:
        codigo, mensaje = MAPA_ERRORES.get(type(exc), (status.HTTP_400_BAD_REQUEST, "Solicitud inválida."))
        # Para credenciales/token se usa SIEMPRE el mensaje genérico (no filtrar detalles).
        if not isinstance(exc, (CredencialesInvalidas, TokenInvalido)) and str(exc):
            mensaje = str(exc)
        if isinstance(exc, ErrorFuenteDatos):
            log.error("Error en la fuente de datos: %s", exc)
        cabeceras = {"WWW-Authenticate": "Bearer"} if codigo == status.HTTP_401_UNAUTHORIZED else None
        return JSONResponse(status_code=codigo, content={"detail": mensaje}, headers=cabeceras)

    @app.exception_handler(Exception)
    async def manejar_error_inesperado(_: Request, exc: Exception) -> JSONResponse:
        # Cualquier fallo no previsto: se registra completo en la consola del
        # servidor y al usuario se le da un mensaje claro (sin detalles internos).
        log.exception("Error inesperado", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Ocurrió un error inesperado en el servidor. Revise la consola."},
        )

    app.include_router(auth.router)
    app.include_router(academico.router)
    app.include_router(tickets.router)

    # El frontend se monta al final para no tapar las rutas /api.
    app.mount("/", StaticFiles(directory=CARPETA_WEB, html=True), name="web")
    return app
