"""Rutas de autenticación."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.domain.exceptions import CredencialesInvalidas
from app.presentation.api.dependencies import ContenedorDep, UsuarioDep
from app.presentation.api.limitador import LimitadorIntentos
from app.presentation.api.schemas import TokenOut, UsuarioOut

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])
limitador = LimitadorIntentos(max_intentos=5, ventana_segundos=300)


@router.post("/login", response_model=TokenOut, summary="Iniciar sesión y obtener un JWT")
def login(
    request: Request,
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
    contenedor: ContenedorDep,
) -> TokenOut:
    ip = request.client.host if request.client else "desconocida"
    clave = f"{ip}:{formulario.username.strip().lower()}"

    if limitador.bloqueado(clave):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Demasiados intentos fallidos. Intente de nuevo en unos minutos.",
        )
    try:
        token = contenedor.iniciar_sesion.ejecutar(formulario.username, formulario.password)
    except CredencialesInvalidas:
        limitador.registrar_fallo(clave)
        raise

    limitador.reiniciar(clave)
    return TokenOut(access_token=token, expira_en_minutos=contenedor.settings.jwt_expiracion_minutos)


@router.get("/yo", response_model=UsuarioOut, summary="Datos del usuario autenticado")
def yo(usuario: UsuarioDep) -> UsuarioOut:
    return UsuarioOut.desde(usuario)
