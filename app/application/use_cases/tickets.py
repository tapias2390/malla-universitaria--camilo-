"""Casos de uso de tickets de revisión."""
from __future__ import annotations

from app.application.ports import RepositorioTickets
from app.domain.entities import EstadoTicket, Ticket
from app.domain.exceptions import TicketNoEncontrado


class ListarTickets:
    def __init__(self, tickets: RepositorioTickets) -> None:
        self._tickets = tickets

    def ejecutar(self, estado: str | None = None) -> list[Ticket]:
        return sorted(self._tickets.listar(estado), key=lambda t: t.fecha_creacion, reverse=True)


class CerrarTicket:
    def __init__(self, tickets: RepositorioTickets) -> None:
        self._tickets = tickets

    def ejecutar(self, ticket_id: str, resolucion: str, cerrado_por: str) -> Ticket:
        ticket = self._tickets.obtener(ticket_id)
        if ticket is None:
            raise TicketNoEncontrado(f"No existe el ticket '{ticket_id}'.")
        ticket.estado = EstadoTicket.CERRADO
        ticket.resolucion = resolucion.strip()
        ticket.cerrado_por = cerrado_por
        self._tickets.guardar(ticket)
        return ticket
