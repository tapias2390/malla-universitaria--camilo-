"""Casos de uso de autenticación: iniciar sesión y validar un token."""
from __future__ import annotations

from dataclasses import dataclass

from app.application.ports import HasherPassword, RepositorioUsuarios, ServicioTokens
from app.domain.entities import Rol
from app.domain.exceptions import CredencialesInvalidas, TokenInvalido


@dataclass(frozen=True)
class UsuarioAutenticado:
    """Identidad que viaja dentro del token (no incluye el hash de la contraseña)."""

    username: str
    nombre: str
    rol: Rol


class IniciarSesion:
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        hasher: HasherPassword,
        tokens: ServicioTokens,
    ) -> None:
        self._usuarios = usuarios
        self._hasher = hasher
        self._tokens = tokens

    def ejecutar(self, username: str, password: str) -> str:
        """Valida las credenciales y devuelve un token JWT."""
        usuario = self._usuarios.obtener_por_username(username.strip().lower())

        # Mismo error para "no existe", "inactivo" y "contraseña mala":
        # no le damos pistas a quien intenta adivinar usuarios.
        if usuario is None or not usuario.activo:
            raise CredencialesInvalidas()
        if not self._hasher.verificar(password, usuario.password_hash):
            raise CredencialesInvalidas()

        return self._tokens.emitir(usuario)


class ValidarToken:
    def __init__(self, tokens: ServicioTokens) -> None:
        self._tokens = tokens

    def ejecutar(self, token: str) -> UsuarioAutenticado:
        claims = self._tokens.decodificar(token)
        try:
            return UsuarioAutenticado(
                username=claims["sub"],
                nombre=claims.get("nombre", ""),
                rol=Rol(claims["rol"]),
            )
        except (KeyError, ValueError) as exc:
            raise TokenInvalido() from exc
