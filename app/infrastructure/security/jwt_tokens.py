"""Emisión y validación de tokens JWT (implementa el puerto ServicioTokens)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from app.domain.entities import Usuario
from app.domain.exceptions import TokenInvalido


class JwtServicioTokens:
    def __init__(self, secreto: str, algoritmo: str = "HS256", expiracion_minutos: int = 60) -> None:
        self._secreto = secreto
        self._algoritmo = algoritmo
        self._expiracion = timedelta(minutes=expiracion_minutos)

    def emitir(self, usuario: Usuario) -> str:
        ahora = datetime.now(timezone.utc)
        claims = {
            "sub": usuario.username,
            "nombre": usuario.nombre,
            "rol": usuario.rol.value,
            "iat": ahora,
            "exp": ahora + self._expiracion,
        }
        return jwt.encode(claims, self._secreto, algorithm=self._algoritmo)

    def decodificar(self, token: str) -> dict:
        try:
            # `algorithms` explícito: evita el ataque de cambiar el algoritmo a "none".
            return jwt.decode(
                token,
                self._secreto,
                algorithms=[self._algoritmo],
                options={"require": ["sub", "exp", "iat"]},
            )
        except jwt.PyJWTError as exc:
            raise TokenInvalido(str(exc)) from exc
