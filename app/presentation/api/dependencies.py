"""Dependencias de FastAPI: acceso al contenedor y control de autenticación/roles."""
from __future__ import annotations

from typing import Annotated, Callable

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.application.use_cases.auditoria import Actor
from app.application.use_cases.autenticacion import UsuarioAutenticado
from app.bootstrap import Contenedor
from app.domain.entities import Rol
from app.domain.exceptions import AccesoDenegado

# Le dice a FastAPI/Swagger dónde se obtiene el token (botón "Authorize").
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def obtener_contenedor(request: Request) -> Contenedor:
    return request.app.state.contenedor


ContenedorDep = Annotated[Contenedor, Depends(obtener_contenedor)]


def ip_cliente(request: Request) -> str:
    return request.client.host if request.client else ""


def usuario_actual(token: Annotated[str, Depends(oauth2)], contenedor: ContenedorDep) -> UsuarioAutenticado:
    """Valida el JWT del encabezado `Authorization: Bearer <token>`."""
    return contenedor.validar_token.ejecutar(token)


UsuarioDep = Annotated[UsuarioAutenticado, Depends(usuario_actual)]


def requiere_rol(*roles: Rol) -> Callable[..., Actor]:
    """Exige uno de los `roles` y entrega el Actor (usuario + IP) para la auditoría."""

    def verificar(request: Request, usuario: UsuarioDep) -> Actor:
        if usuario.rol not in roles:
            raise AccesoDenegado("No tiene permisos para esta operación.")
        return usuario.como_actor(ip_cliente(request))

    return verificar


# Atajos para las rutas
AdminDep = Annotated[Actor, Depends(requiere_rol(Rol.ADMIN))]
PersonalDep = Annotated[Actor, Depends(requiere_rol(Rol.ADMIN, Rol.CONSULTOR))]
EstudianteDep = Annotated[Actor, Depends(requiere_rol(Rol.ESTUDIANTE))]
CualquieraDep = Annotated[Actor, Depends(requiere_rol(*Rol))]
