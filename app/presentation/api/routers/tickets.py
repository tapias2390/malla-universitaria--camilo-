"""Rutas de tickets de revisión (solo administradores)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter

from app.presentation.api.dependencies import AdminDep, ContenedorDep
from app.presentation.api.schemas import CerrarTicketIn, TicketOut

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])


@router.get("", response_model=list[TicketOut], summary="Listar tickets")
def listar(
    contenedor: ContenedorDep,
    _: AdminDep,
    estado: Literal["abierto", "cerrado"] | None = None,
) -> list[TicketOut]:
    return [TicketOut.desde(t) for t in contenedor.listar_tickets.ejecutar(estado)]


@router.post("/{ticket_id}/cerrar", response_model=TicketOut, summary="Cerrar un ticket con su resolución")
def cerrar(ticket_id: str, datos: CerrarTicketIn, contenedor: ContenedorDep, actor: AdminDep) -> TicketOut:
    return TicketOut.desde(contenedor.cerrar_ticket.ejecutar(ticket_id, datos.resolucion, actor))
