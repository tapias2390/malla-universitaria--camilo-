"""Casos de uso de autenticación: iniciar sesión y validar un token."""
from __future__ import annotations

from dataclasses import dataclass

from app.application.ports import HasherPassword, RepositorioUsuarios, ServicioTokens
from app.application.use_cases.auditoria import Actor, Auditor
from app.domain.entities import Rol
from app.domain.exceptions import CredencialesInvalidas, TokenInvalido


@dataclass(frozen=True)
class UsuarioAutenticado:
    """Identidad que viaja dentro del token (no incluye el hash de la contraseña)."""

    username: str
    nombre: str
    rol: Rol
    codigo_estudiante: str = ""

    def como_actor(self, ip: str = "") -> Actor:
        return Actor(self.username, self.rol.value, ip, self.codigo_estudiante)


class IniciarSesion:
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        hasher: HasherPassword,
        tokens: ServicioTokens,
        auditor: Auditor,
    ) -> None:
        self._usuarios = usuarios
        self._hasher = hasher
        self._tokens = tokens
        self._auditor = auditor

    def ejecutar(self, username: str, password: str, ip: str = "") -> str:
        """Valida las credenciales y devuelve un token JWT."""
        username = username.strip().lower()
        usuario = self._usuarios.obtener_por_username(username)

        # Mismo error para "no existe", "inactivo" y "contraseña mala":
        # no le damos pistas a quien intenta adivinar usuarios.
        if (
            usuario is None
            or not usuario.activo
            or not self._hasher.verificar(password, usuario.password_hash)
        ):
            self._auditor.registrar(
                Actor(username or "(vacío)", "", ip), "login_fallido", "sesion", username, exito=False
            )
            raise CredencialesInvalidas()

        self._auditor.registrar(Actor(usuario.username, usuario.rol.value, ip), "login", "sesion", usuario.username)
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
                codigo_estudiante=claims.get("est", ""),
            )
        except (KeyError, ValueError) as exc:
            raise TokenInvalido() from exc
