"""Casos de uso de tickets de revisión."""
from __future__ import annotations

from app.application.ports import RepositorioTickets
from app.application.use_cases.auditoria import Actor, Auditor
from app.domain.entities import EstadoTicket, Ticket
from app.domain.exceptions import DatosInvalidos, TicketNoEncontrado


class ListarTickets:
    def __init__(self, tickets: RepositorioTickets) -> None:
        self._tickets = tickets

    def ejecutar(self, estado: str | None = None) -> list[Ticket]:
        return sorted(self._tickets.listar(estado), key=lambda t: t.fecha_creacion, reverse=True)


class CerrarTicket:
    def __init__(self, tickets: RepositorioTickets, auditor: Auditor) -> None:
        self._tickets = tickets
        self._auditor = auditor

    def ejecutar(self, ticket_id: str, resolucion: str, actor: Actor) -> Ticket:
        ticket = self._tickets.obtener(ticket_id)
        if ticket is None:
            raise TicketNoEncontrado(f"No existe el ticket '{ticket_id}'.")
        if ticket.estado is EstadoTicket.CERRADO:
            raise DatosInvalidos("El ticket ya estaba cerrado.")
        ticket.estado = EstadoTicket.CERRADO
        ticket.resolucion = resolucion.strip()
        ticket.cerrado_por = actor.username
        self._tickets.guardar(ticket)
        self._auditor.registrar(
            actor, "cerrar_ticket", "ticket", ticket.id,
            f"{ticket.codigo_estudiante} / {ticket.codigo_materia}: {ticket.resolucion}",
        )
        return ticket
