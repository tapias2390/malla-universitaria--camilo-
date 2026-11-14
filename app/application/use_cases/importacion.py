"""Importación masiva de estudiantes y su historial desde un Excel (solo admin).

Formato: el mismo del Excel académico, hojas `estudiantes` y `materias_vistas`
(se puede descargar una plantilla desde la aplicación).

Reglas:
- Un estudiante que ya existe (mismo código) se ACTUALIZA; si no existe se CREA.
- Si un estudiante aparece en `materias_vistas`, su historial se REEMPLAZA
  completo por las filas del archivo. Si no aparece, su historial no se toca.
- Primero se valida TODO el archivo. Si hay un solo error no se guarda nada
  (todo o nada), y se informa cada error con su hoja y fila.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Protocol

from app.application.ports import HasherPassword, RepositorioAcademico, RepositorioUsuarios
from app.application.use_cases.auditoria import Actor, Auditor
from app.application.use_cases.gestion_estudiantes import (
    DatosEstudiante,
    GestionEstudiantes,
    validar_materia_vista,
    validar_password,
)
from app.domain.entities import EstadoMateria, Estudiante, MateriaVista, Rol, Usuario
from app.domain.exceptions import DatosInvalidos


# ---------------------------------------------------------------------------
# Datos leídos del archivo (los produce la infraestructura)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ErrorImportacion:
    hoja: str
    fila: int          # número de fila en Excel (la 1 es el encabezado)
    mensaje: str


@dataclass(frozen=True)
class FilaEstudiante:
    fila: int
    datos: DatosEstudiante


@dataclass(frozen=True)
class FilaMateria:
    fila: int
    codigo_estudiante: str
    materia: MateriaVista


@dataclass
class LoteImportacion:
    estudiantes: list[FilaEstudiante] = field(default_factory=list)
    materias: list[FilaMateria] = field(default_factory=list)
    errores: list[ErrorImportacion] = field(default_factory=list)   # errores de lectura (formato)


class LectorImportacion(Protocol):
    def leer(self, contenido: bytes) -> LoteImportacion: ...


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class EstudianteImportado:
    codigo: str
    nombre: str
    accion: str                 # "nuevo", "actualizado" o "solo_historial"
    malla_version: str
    materias: int               # filas de historial en el archivo
    aprobadas: int
    cursando: int
    reemplaza_historial: bool
    crea_cuenta: bool


@dataclass(frozen=True)
class ResultadoImportacion:
    aplicado: bool
    estudiantes: list[EstudianteImportado]
    errores: list[ErrorImportacion]

    @property
    def nuevos(self) -> int:
        return sum(1 for e in self.estudiantes if e.accion == "nuevo")

    @property
    def actualizados(self) -> int:
        return len(self.estudiantes) - self.nuevos

    @property
    def total_materias(self) -> int:
        return sum(e.materias for e in self.estudiantes)


# ---------------------------------------------------------------------------
# Caso de uso
# ---------------------------------------------------------------------------
class ImportarEstudiantes:
    def __init__(
        self,
        academico: RepositorioAcademico,
        usuarios: RepositorioUsuarios,
        hasher: HasherPassword,
        auditor: Auditor,
        lector: LectorImportacion,
        gestion: GestionEstudiantes,
    ) -> None:
        self._academico = academico
        self._usuarios = usuarios
        self._hasher = hasher
        self._auditor = auditor
        self._lector = lector
        self._gestion = gestion

    def ejecutar(
        self, contenido: bytes, actor: Actor, aplicar: bool = False, password_cuentas: str = ""
    ) -> ResultadoImportacion:
        """Valida el archivo; si `aplicar` y no hay errores, guarda todo."""
        lote = self._lector.leer(contenido)
        errores = list(lote.errores)
        if not lote.estudiantes and not lote.materias and not errores:
            errores.append(ErrorImportacion("—", 0, "El archivo no tiene filas en 'estudiantes' ni en 'materias_vistas'."))
        if password_cuentas:
            try:
                validar_password(password_cuentas)
            except DatosInvalidos as exc:
                errores.append(ErrorImportacion("—", 0, f"Contraseña inicial: {exc}"))

        existentes = {e.codigo: e for e in self._academico.listar_estudiantes()}
        estudiantes = self._validar_estudiantes(lote.estudiantes, existentes, errores)
        historiales = self._validar_materias(lote.materias, estudiantes, existentes, errores)

        usernames = {u.username for u in self._usuarios.listar()} if password_cuentas else set()
        resumen = []
        for codigo in dict.fromkeys([*estudiantes, *historiales]):
            est = estudiantes.get(codigo) or existentes[codigo]
            materias = historiales.get(codigo, [])
            accion = "nuevo" if codigo not in existentes else ("actualizado" if codigo in estudiantes else "solo_historial")
            resumen.append(EstudianteImportado(
                codigo=codigo,
                nombre=est.nombre,
                accion=accion,
                malla_version=est.malla_version,
                materias=len(materias),
                aprobadas=sum(1 for m in materias if m.estado is EstadoMateria.APROBADA),
                cursando=sum(1 for m in materias if m.estado is EstadoMateria.CURSANDO),
                reemplaza_historial=codigo in historiales,
                crea_cuenta=bool(password_cuentas) and accion == "nuevo" and codigo.lower() not in usernames,
            ))

        if errores or not aplicar:
            errores.sort(key=lambda e: (e.hoja != "—", e.hoja, e.fila))
            return ResultadoImportacion(False, resumen, errores)

        self._academico.guardar_lote(list(estudiantes.values()), historiales)
        cuentas = [r for r in resumen if r.crea_cuenta]
        for r in cuentas:
            self._usuarios.guardar(Usuario(
                username=r.codigo.lower(),
                password_hash=self._hasher.hashear(password_cuentas),
                nombre=r.nombre, rol=Rol.ESTUDIANTE, activo=True, codigo_estudiante=r.codigo,
            ))
        resultado = ResultadoImportacion(True, resumen, [])
        self._auditor.registrar(
            actor, "importar_estudiantes", "estudiante", f"{len(resumen)} estudiantes",
            f"{resultado.nuevos} nuevos, {resultado.actualizados} actualizados, "
            f"{resultado.total_materias} materias, {len(cuentas)} cuentas creadas",
        )
        return resultado

    # ---------------------------------------------------------------- validación
    def _validar_estudiantes(
        self, filas: list[FilaEstudiante], existentes: dict[str, Estudiante], errores: list[ErrorImportacion]
    ) -> dict[str, Estudiante]:
        validos: dict[str, Estudiante] = {}
        documentos = {e.documento: e.codigo for e in existentes.values()}
        for fila in filas:
            try:
                est = self._gestion.validar_datos(fila.datos)
            except DatosInvalidos as exc:
                errores.append(ErrorImportacion("estudiantes", fila.fila, f"{fila.datos.codigo or 'sin código'}: {exc}"))
                continue
            if est.codigo in validos:
                errores.append(ErrorImportacion("estudiantes", fila.fila, f"El código {est.codigo} está repetido en el archivo."))
                continue
            dueno = documentos.get(est.documento)
            if dueno and dueno != est.codigo:
                errores.append(ErrorImportacion(
                    "estudiantes", fila.fila, f"El documento {est.documento} ya pertenece al estudiante {dueno}."))
                continue
            documentos[est.documento] = est.codigo
            validos[est.codigo] = est
        return validos

    @staticmethod
    def _validar_materias(
        filas: list[FilaMateria],
        estudiantes: dict[str, Estudiante],
        existentes: dict[str, Estudiante],
        errores: list[ErrorImportacion],
    ) -> dict[str, list[MateriaVista]]:
        historiales: dict[str, list[MateriaVista]] = defaultdict(list)
        vistas: set[tuple[str, str, str]] = set()
        for fila in filas:
            codigo = fila.codigo_estudiante
            if codigo not in estudiantes and codigo not in existentes:
                errores.append(ErrorImportacion(
                    "materias_vistas", fila.fila,
                    f"El estudiante {codigo or '(vacío)'} no existe ni está en la hoja 'estudiantes'."))
                continue
            try:
                materia = validar_materia_vista(fila.materia)
            except DatosInvalidos as exc:
                errores.append(ErrorImportacion("materias_vistas", fila.fila, str(exc)))
                continue
            clave = (codigo, materia.codigo, materia.periodo)
            if clave in vistas:
                errores.append(ErrorImportacion(
                    "materias_vistas", fila.fila,
                    f"{codigo}: la materia {materia.codigo} está repetida en el periodo '{materia.periodo}'."))
                continue
            vistas.add(clave)
            historiales[codigo].append(materia)
        return dict(historiales)
