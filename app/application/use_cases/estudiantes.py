"""Casos de uso de consulta: estudiantes, mallas y validación de la transición."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.application.ports import RepositorioAcademico, RepositorioTickets
from app.application.use_cases.auditoria import Actor, Auditor
from app.domain.entities import ComparacionMallas, Equivalencia, Estudiante, Malla, ResultadoTransicion, Ticket
from app.domain.exceptions import AccesoDenegado, EstudianteNoEncontrado, MallaNoEncontrada
from app.domain.services.comparador_mallas import comparar_mallas
from app.domain.services.motor_transicion import MotorTransicion


class ListarEstudiantes:
    def __init__(self, academico: RepositorioAcademico) -> None:
        self._academico = academico

    def ejecutar(self, texto: str = "") -> list[Estudiante]:
        """Lista estudiantes; filtra por código, nombre o documento si se pasa `texto`."""
        texto = texto.strip().lower()
        estudiantes = sorted(self._academico.listar_estudiantes(), key=lambda e: e.nombre.lower())
        if not texto:
            return estudiantes
        return [
            e for e in estudiantes
            if texto in e.codigo.lower() or texto in e.nombre.lower() or texto in e.documento.lower()
        ]


class ConsultarMalla:
    def __init__(self, academico: RepositorioAcademico) -> None:
        self._academico = academico

    def ejecutar(self, version: str) -> Malla:
        malla = self._academico.obtener_malla(version)
        if malla is None:
            raise MallaNoEncontrada(f"No existe la malla '{version}'.")
        return malla

    def versiones(self) -> list[str]:
        return self._academico.versiones_malla()

    def equivalencias(self) -> list[Equivalencia]:
        return self._academico.obtener_equivalencias()


@dataclass(frozen=True)
class ResultadoValidacion:
    transicion: ResultadoTransicion
    comparacion: ComparacionMallas | None   # None si ya está en la malla vigente
    tickets: list[Ticket]                   # tickets abiertos para este estudiante (nuevos o previos)
    tickets_nuevos: int


class ValidarMallaEstudiante:
    """Calcula cómo queda un estudiante en la malla vigente y abre tickets si hace falta.

    - Estudiante nuevo (ya inscrito en la malla vigente): solo ve su avance.
    - Estudiante antiguo: se homologan sus materias vistas contra la malla
      vigente; cada caso sin solución automática genera UN ticket (aunque se
      valide varias veces).
    """

    def __init__(
        self,
        academico: RepositorioAcademico,
        tickets: RepositorioTickets,
        motor: MotorTransicion,
        auditor: Auditor,
        version_vigente: str,
    ) -> None:
        self._academico = academico
        self._tickets = tickets
        self._motor = motor
        self._auditor = auditor
        self._version_vigente = version_vigente

    def ejecutar(self, codigo_estudiante: str, actor: Actor, crear_tickets: bool = True) -> ResultadoValidacion:
        estudiante = self._academico.obtener_estudiante(codigo_estudiante)
        if estudiante is None:
            raise EstudianteNoEncontrado(f"No existe el estudiante '{codigo_estudiante}'.")

        malla = self._academico.obtener_malla(self._version_vigente)
        if malla is None:
            raise MallaNoEncontrada(f"La malla vigente '{self._version_vigente}' no está cargada.")

        equivalencias = self._academico.obtener_equivalencias()
        catalogo = self._academico.obtener_catalogo_optativas()
        transicion = self._motor.evaluar(estudiante, malla, equivalencias, catalogo)

        comparacion = None
        origen = self._academico.obtener_malla(estudiante.malla_version)
        if transicion.requiere_transicion and origen is not None:
            comparacion = comparar_mallas(estudiante, origen, malla, self._motor, equivalencias, catalogo)

        tickets, nuevos = self._tickets_de(estudiante, transicion, crear_tickets)
        if crear_tickets:
            self._auditor.registrar(
                actor, "validar_malla", "estudiante", estudiante.codigo,
                f"{transicion.creditos_reconocidos}/{transicion.creditos_requeridos} créditos; "
                f"{nuevos} tickets nuevos",
            )
        return ResultadoValidacion(transicion, comparacion, tickets, nuevos)

    def _tickets_de(
        self, estudiante: Estudiante, transicion: ResultadoTransicion, crear: bool
    ) -> tuple[list[Ticket], int]:
        tickets: list[Ticket] = []
        nuevos = 0
        for caso in transicion.casos_revision:
            vista = caso.materia_vista
            existente = self._tickets.buscar_abierto(estudiante.codigo, vista.codigo)
            if existente:
                tickets.append(existente)
                continue
            if not crear:
                continue
            ticket = Ticket(
                id=uuid.uuid4().hex[:10],
                codigo_estudiante=estudiante.codigo,
                codigo_materia=vista.codigo,
                nombre_materia=vista.nombre,
                creditos=vista.creditos,
                motivo=caso.observacion,
                fecha_creacion=datetime.now(),
            )
            self._tickets.guardar(ticket)
            tickets.append(ticket)
            nuevos += 1
        return tickets, nuevos


class ConsultarMiAvance:
    """Lo que ve un ESTUDIANTE al iniciar sesión: su avance en la malla vigente.

    Es solo lectura: no abre tickets (eso lo hace el personal académico).
    """

    def __init__(self, validar: ValidarMallaEstudiante) -> None:
        self._validar = validar

    def ejecutar(self, actor: Actor) -> ResultadoValidacion:
        if not actor.codigo_estudiante:
            raise AccesoDenegado("Su cuenta no está asociada a ningún estudiante.")
        return self._validar.ejecutar(actor.codigo_estudiante, actor, crear_tickets=False)
