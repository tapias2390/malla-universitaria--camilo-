"""Dependencias de FastAPI: acceso al contenedor y control de autenticación/roles."""
from __future__ import annotations

from typing import Annotated, Callable

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.application.use_cases.autenticacion import UsuarioAutenticado
from app.bootstrap import Contenedor
from app.domain.entities import Rol
from app.domain.exceptions import AccesoDenegado

# Le dice a FastAPI/Swagger dónde se obtiene el token (botón "Authorize").
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def obtener_contenedor(request: Request) -> Contenedor:
    return request.app.state.contenedor


ContenedorDep = Annotated[Contenedor, Depends(obtener_contenedor)]


def usuario_actual(token: Annotated[str, Depends(oauth2)], contenedor: ContenedorDep) -> UsuarioAutenticado:
    """Valida el JWT del encabezado `Authorization: Bearer <token>`."""
    return contenedor.validar_token.ejecutar(token)


UsuarioDep = Annotated[UsuarioAutenticado, Depends(usuario_actual)]


def requiere_rol(*roles: Rol) -> Callable[[UsuarioAutenticado], UsuarioAutenticado]:
    """Uso: `Depends(requiere_rol(Rol.ADMIN))`."""

    def verificar(usuario: UsuarioDep) -> UsuarioAutenticado:
        if usuario.rol not in roles:
            raise AccesoDenegado("No tiene permisos para esta operación.")
        return usuario

    return verificar
