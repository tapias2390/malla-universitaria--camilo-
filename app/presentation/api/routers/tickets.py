"""Rutas de tickets de revisión (solo administradores)."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends

from app.application.use_cases.autenticacion import UsuarioAutenticado
from app.domain.entities import Rol
from app.presentation.api.dependencies import ContenedorDep, requiere_rol
from app.presentation.api.schemas import CerrarTicketIn, TicketOut

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])
AdminDep = Annotated[UsuarioAutenticado, Depends(requiere_rol(Rol.ADMIN))]


@router.get("", response_model=list[TicketOut], summary="Listar tickets")
def listar(
    contenedor: ContenedorDep,
    _: AdminDep,
    estado: Literal["abierto", "cerrado"] | None = None,
) -> list[TicketOut]:
    return [TicketOut.desde(t) for t in contenedor.listar_tickets.ejecutar(estado)]


@router.post("/{ticket_id}/cerrar", response_model=TicketOut, summary="Cerrar un ticket con su resolución")
def cerrar(ticket_id: str, datos: CerrarTicketIn, contenedor: ContenedorDep, admin: AdminDep) -> TicketOut:
    return TicketOut.desde(contenedor.cerrar_ticket.ejecutar(ticket_id, datos.resolucion, admin.username))
