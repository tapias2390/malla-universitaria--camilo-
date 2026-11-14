"""CRUD de usuarios del sistema (solo administradores)."""
from __future__ import annotations

import re
from dataclasses import dataclass, replace

from app.application.ports import HasherPassword, RepositorioAcademico, RepositorioUsuarios
from app.application.use_cases.auditoria import Actor, Auditor
from app.application.use_cases.gestion_estudiantes import validar_password
from app.domain.entities import Rol, Usuario
from app.domain.exceptions import DatosInvalidos, RegistroDuplicado, UsuarioNoEncontrado

USERNAME_VALIDO = re.compile(r"^[a-z0-9._-]{3,40}$")


@dataclass(frozen=True)
class DatosUsuario:
    username: str
    nombre: str
    rol: str
    activo: bool = True
    codigo_estudiante: str = ""
    password: str = ""        # obligatoria al crear; al actualizar, vacía = no cambiarla


class GestionUsuarios:
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        academico: RepositorioAcademico,
        hasher: HasherPassword,
        auditor: Auditor,
    ) -> None:
        self._usuarios = usuarios
        self._academico = academico
        self._hasher = hasher
        self._auditor = auditor

    def listar(self) -> list[Usuario]:
        return sorted(self._usuarios.listar(), key=lambda u: (u.rol.value, u.username))

    def crear(self, datos: DatosUsuario, actor: Actor) -> Usuario:
        username = datos.username.strip().lower()
        if not USERNAME_VALIDO.match(username):
            raise DatosInvalidos("El usuario debe tener de 3 a 40 caracteres: minúsculas, números, '.', '_' o '-'.")
        if self._usuarios.obtener_por_username(username):
            raise RegistroDuplicado(f"Ya existe el usuario '{username}'.")
        validar_password(datos.password)

        usuario = self._armar(username, datos, self._hasher.hashear(datos.password))
        self._usuarios.guardar(usuario)
        self._auditor.registrar(actor, "crear_usuario", "usuario", username, f"rol {usuario.rol.value}")
        return usuario

    def actualizar(self, username: str, datos: DatosUsuario, actor: Actor) -> Usuario:
        actual = self._obtener(username)
        password_hash = actual.password_hash
        if datos.password:
            validar_password(datos.password)
            password_hash = self._hasher.hashear(datos.password)

        nuevo = self._armar(actual.username, datos, password_hash)
        if actual.username == actor.username and (nuevo.rol is not Rol.ADMIN or not nuevo.activo):
            raise DatosInvalidos("No puede quitarse a sí mismo el rol de administrador ni desactivarse.")
        self._proteger_ultimo_admin(actual, nuevo)

        self._usuarios.guardar(nuevo)
        cambios = [
            f"{campo}: '{getattr(actual, campo)}' -> '{getattr(nuevo, campo)}'"
            for campo in ("nombre", "rol", "activo", "codigo_estudiante")
            if getattr(actual, campo) != getattr(nuevo, campo)
        ]
        if datos.password:
            cambios.append("contraseña cambiada")
        self._auditor.registrar(actor, "actualizar_usuario", "usuario", username, "; ".join(cambios) or "sin cambios")
        return nuevo

    def eliminar(self, username: str, actor: Actor) -> None:
        usuario = self._obtener(username)
        if usuario.username == actor.username:
            raise DatosInvalidos("No puede eliminar su propio usuario.")
        self._proteger_ultimo_admin(usuario, replace(usuario, activo=False))
        self._usuarios.eliminar(usuario.username)
        self._auditor.registrar(actor, "eliminar_usuario", "usuario", usuario.username, f"rol {usuario.rol.value}")

    # ---------------------------------------------------------------- privados
    def _obtener(self, username: str) -> Usuario:
        usuario = self._usuarios.obtener_por_username(username.strip().lower())
        if usuario is None:
            raise UsuarioNoEncontrado(f"No existe el usuario '{username}'.")
        return usuario

    def _armar(self, username: str, datos: DatosUsuario, password_hash: str) -> Usuario:
        try:
            rol = Rol(datos.rol.strip().lower())
        except ValueError as exc:
            raise DatosInvalidos("Rol inválido. Use admin, consultor o estudiante.") from exc
        nombre = " ".join(datos.nombre.split())
        if len(nombre) < 3:
            raise DatosInvalidos("Escriba el nombre de la persona.")

        codigo = datos.codigo_estudiante.strip() if rol is Rol.ESTUDIANTE else ""
        if rol is Rol.ESTUDIANTE:
            if not codigo:
                raise DatosInvalidos("Una cuenta de estudiante debe indicar el código del estudiante.")
            if self._academico.obtener_estudiante(codigo) is None:
                raise DatosInvalidos(f"No existe el estudiante '{codigo}'.")
        return Usuario(username, password_hash, nombre, rol, datos.activo, codigo)

    def _proteger_ultimo_admin(self, antes: Usuario, despues: Usuario) -> None:
        deja_de_ser_admin = antes.rol is Rol.ADMIN and antes.activo and (despues.rol is not Rol.ADMIN or not despues.activo)
        if not deja_de_ser_admin:
            return
        otros = [u for u in self._usuarios.listar() if u.rol is Rol.ADMIN and u.activo and u.username != antes.username]
        if not otros:
            raise DatosInvalidos("Debe quedar al menos un administrador activo.")
