"""Casos de uso sobre estudiantes y mallas."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.application.ports import RepositorioAcademico, RepositorioTickets
from app.domain.entities import Estudiante, Malla, ResultadoTransicion, Ticket
from app.domain.exceptions import EstudianteNoEncontrado, MallaNoEncontrada
from app.domain.services.motor_transicion import MotorTransicion


class ListarEstudiantes:
    def __init__(self, academico: RepositorioAcademico) -> None:
        self._academico = academico

    def ejecutar(self, texto: str = "") -> list[Estudiante]:
        """Lista estudiantes; filtra por código, nombre o documento si se pasa `texto`."""
        texto = texto.strip().lower()
        estudiantes = self._academico.listar_estudiantes()
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


@dataclass(frozen=True)
class ResultadoValidacion:
    transicion: ResultadoTransicion
    tickets: list[Ticket]          # tickets abiertos para este estudiante (nuevos o previos)
    tickets_nuevos: int


class ValidarMallaEstudiante:
    """Calcula cómo queda un estudiante en la malla vigente y abre tickets si hace falta.

    - Estudiante nuevo (ya inscrito en la malla vigente): solo ve su avance.
    - Estudiante antiguo: se homologan sus materias vistas contra la malla
      vigente; cada materia eliminada sin electiva disponible genera un ticket
      (uno solo por materia aunque se valide varias veces).
    """

    def __init__(
        self,
        academico: RepositorioAcademico,
        tickets: RepositorioTickets,
        motor: MotorTransicion,
        version_vigente: str,
    ) -> None:
        self._academico = academico
        self._tickets = tickets
        self._motor = motor
        self._version_vigente = version_vigente

    def ejecutar(self, codigo_estudiante: str) -> ResultadoValidacion:
        estudiante = self._academico.obtener_estudiante(codigo_estudiante)
        if estudiante is None:
            raise EstudianteNoEncontrado(f"No existe el estudiante '{codigo_estudiante}'.")

        malla = self._academico.obtener_malla(self._version_vigente)
        if malla is None:
            raise MallaNoEncontrada(f"La malla vigente '{self._version_vigente}' no está cargada.")

        transicion = self._motor.evaluar(estudiante, malla, self._academico.obtener_equivalencias())

        tickets: list[Ticket] = []
        nuevos = 0
        for caso in transicion.casos_revision:
            vista = caso.materia_vista
            existente = self._tickets.buscar_abierto(estudiante.codigo, vista.codigo)
            if existente:
                tickets.append(existente)
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

        return ResultadoValidacion(transicion=transicion, tickets=tickets, tickets_nuevos=nuevos)
