"""CRUD de estudiantes y de su historial académico (solo administradores).

Cada operación valida los datos, guarda y deja un evento de auditoría.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.application.ports import HasherPassword, RepositorioAcademico, RepositorioUsuarios
from app.application.use_cases.auditoria import Actor, Auditor
from app.domain.entities import EstadoMateria, Estudiante, MateriaVista, Rol, Usuario
from app.domain.exceptions import DatosInvalidos, EstudianteNoEncontrado, RegistroDuplicado

ESTADOS_ESTUDIANTE = {"activo", "inactivo", "graduado", "retirado"}
CODIGO_VALIDO = re.compile(r"^[A-Za-z0-9_-]{2,30}$")


@dataclass(frozen=True)
class DatosEstudiante:
    codigo: str
    nombre: str
    documento: str
    malla_version: str
    estado: str = "activo"
    correo: str = ""


class GestionEstudiantes:
    def __init__(
        self,
        academico: RepositorioAcademico,
        usuarios: RepositorioUsuarios,
        hasher: HasherPassword,
        auditor: Auditor,
    ) -> None:
        self._academico = academico
        self._usuarios = usuarios
        self._hasher = hasher
        self._auditor = auditor

    # ---------------------------------------------------------------- consultar
    def obtener(self, codigo: str) -> Estudiante:
        estudiante = self._academico.obtener_estudiante(codigo)
        if estudiante is None:
            raise EstudianteNoEncontrado(f"No existe el estudiante '{codigo}'.")
        return estudiante

    # ---------------------------------------------------------------- crear
    def crear(self, datos: DatosEstudiante, actor: Actor, password_cuenta: str = "") -> Estudiante:
        """Registra al estudiante. Si se da `password_cuenta`, le crea su usuario para entrar."""
        estudiante = self.validar_datos(datos)
        if self._academico.obtener_estudiante(estudiante.codigo):
            raise RegistroDuplicado(f"Ya existe un estudiante con el código '{estudiante.codigo}'.")
        if any(e.documento == estudiante.documento for e in self._academico.listar_estudiantes()):
            raise RegistroDuplicado(f"Ya existe un estudiante con el documento '{estudiante.documento}'.")

        username = estudiante.codigo.lower()
        if password_cuenta:
            validar_password(password_cuenta)
            if self._usuarios.obtener_por_username(username):
                raise RegistroDuplicado(f"Ya existe el usuario '{username}'.")

        self._academico.guardar_estudiante(estudiante)
        self._auditor.registrar(actor, "crear_estudiante", "estudiante", estudiante.codigo, estudiante.nombre)

        if password_cuenta:
            self._usuarios.guardar(Usuario(
                username=username,
                password_hash=self._hasher.hashear(password_cuenta),
                nombre=estudiante.nombre,
                rol=Rol.ESTUDIANTE,
                activo=True,
                codigo_estudiante=estudiante.codigo,
            ))
            self._auditor.registrar(actor, "crear_usuario", "usuario", username, "cuenta de estudiante")
        return estudiante

    # ---------------------------------------------------------------- actualizar
    def actualizar(self, codigo: str, datos: DatosEstudiante, actor: Actor) -> Estudiante:
        actual = self.obtener(codigo)
        nuevo = self.validar_datos(DatosEstudiante(
            codigo=actual.codigo,              # el código no se cambia: es la llave del historial
            nombre=datos.nombre,
            documento=datos.documento,
            malla_version=datos.malla_version,
            estado=datos.estado,
            correo=datos.correo,
        ))
        otro = next(
            (e for e in self._academico.listar_estudiantes()
             if e.documento == nuevo.documento and e.codigo != codigo),
            None,
        )
        if otro:
            raise RegistroDuplicado(f"El documento '{nuevo.documento}' ya pertenece a {otro.codigo}.")

        self._academico.guardar_estudiante(nuevo)
        self._auditor.registrar(
            actor, "actualizar_estudiante", "estudiante", codigo, _diferencias(actual, nuevo) or "sin cambios"
        )
        nuevo.materias_vistas = actual.materias_vistas
        return nuevo

    # ---------------------------------------------------------------- eliminar
    def eliminar(self, codigo: str, actor: Actor) -> None:
        estudiante = self.obtener(codigo)
        self._academico.eliminar_estudiante(codigo)
        # Sus cuentas de acceso dejan de tener sentido.
        for usuario in self._usuarios.listar():
            if usuario.rol is Rol.ESTUDIANTE and usuario.codigo_estudiante == codigo:
                self._usuarios.eliminar(usuario.username)
                self._auditor.registrar(actor, "eliminar_usuario", "usuario", usuario.username, "cuenta del estudiante eliminado")
        self._auditor.registrar(
            actor, "eliminar_estudiante", "estudiante", codigo,
            f"{estudiante.nombre} ({len(estudiante.materias_vistas)} materias en el historial)",
        )

    # ---------------------------------------------------------------- historial
    def guardar_historial(self, codigo: str, materias: list[MateriaVista], actor: Actor) -> Estudiante:
        estudiante = self.obtener(codigo)
        limpias = [validar_materia_vista(m) for m in materias]
        claves = [(m.codigo, m.periodo) for m in limpias]
        repetida = next((c for c in claves if claves.count(c) > 1), None)
        if repetida:
            raise DatosInvalidos(f"La materia {repetida[0]} está dos veces en el periodo '{repetida[1]}'.")

        self._academico.guardar_historial(codigo, limpias)
        self._auditor.registrar(
            actor, "actualizar_historial", "estudiante", codigo,
            f"{len(estudiante.materias_vistas)} -> {len(limpias)} materias",
        )
        estudiante.materias_vistas = limpias
        return estudiante

    # ---------------------------------------------------------------- validación
    def validar_datos(self, datos: DatosEstudiante) -> Estudiante:
        """Limpia y valida los datos básicos (lo usa también la importación desde Excel)."""
        codigo = datos.codigo.strip()
        if not CODIGO_VALIDO.match(codigo):
            raise DatosInvalidos("El código debe tener de 2 a 30 caracteres: letras, números, '-' o '_'.")
        nombre = " ".join(datos.nombre.split())
        if len(nombre) < 3:
            raise DatosInvalidos("Escriba el nombre completo del estudiante.")
        documento = datos.documento.strip()
        if not re.fullmatch(r"[0-9A-Za-z-]{4,20}", documento):
            raise DatosInvalidos("El documento debe tener de 4 a 20 caracteres, sin espacios.")
        estado = datos.estado.strip().lower() or "activo"
        if estado not in ESTADOS_ESTUDIANTE:
            raise DatosInvalidos(f"Estado inválido. Use: {', '.join(sorted(ESTADOS_ESTUDIANTE))}.")
        version = datos.malla_version.strip()
        if version not in self._academico.versiones_malla():
            raise DatosInvalidos(f"La malla '{version}' no existe en el archivo académico.")
        correo = datos.correo.strip().lower()
        if correo and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo):
            raise DatosInvalidos("El correo no es válido.")
        return Estudiante(codigo, nombre, documento, version, estado, correo)


# ---------------------------------------------------------------------------
# Reglas compartidas
# ---------------------------------------------------------------------------
def validar_materia_vista(m: MateriaVista) -> MateriaVista:
    codigo = m.codigo.strip()
    if not codigo:
        raise DatosInvalidos("Cada materia del historial necesita su código.")
    if not 0 < m.creditos <= 20:
        raise DatosInvalidos(f"Créditos inválidos en {codigo}: deben estar entre 1 y 20.")
    if m.nota is not None and not 0 <= m.nota <= 5:
        raise DatosInvalidos(f"Nota inválida en {codigo}: debe estar entre 0 y 5.")
    if m.estado is EstadoMateria.REPROBADA and m.nota is None:
        raise DatosInvalidos(f"La materia {codigo} está reprobada pero no tiene nota.")
    return MateriaVista(
        codigo=codigo,
        nombre=" ".join(m.nombre.split()) or codigo,
        creditos=m.creditos,
        nota=m.nota,
        periodo=m.periodo.strip(),
        estado=m.estado,
        tipologia=m.tipologia.strip().lower(),
    )


def validar_password(password: str) -> None:
    if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise DatosInvalidos("La contraseña debe tener al menos 8 caracteres, con letras y números.")


def _diferencias(antes: Estudiante, despues: Estudiante) -> str:
    cambios = []
    for campo in ("nombre", "documento", "malla_version", "estado", "correo"):
        a, d = getattr(antes, campo), getattr(despues, campo)
        if a != d:
            cambios.append(f"{campo}: '{a}' -> '{d}'")
    return "; ".join(cambios)
