"""Auditoría: registro de quién hizo qué, y consulta de ese registro (solo admin)."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

from app.application.ports import RepositorioAuditoria
from app.domain.entities import EventoAuditoria

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Actor:
    """Quién ejecuta una acción. Lo arma la capa de presentación a partir del token."""

    username: str
    rol: str
    ip: str = ""
    codigo_estudiante: str = ""


ANONIMO = Actor(username="anonimo", rol="")


class Auditor:
    """Servicio que usan los casos de uso para dejar rastro de cada operación."""

    def __init__(self, repositorio: RepositorioAuditoria) -> None:
        self._repo = repositorio

    def registrar(
        self,
        actor: Actor,
        accion: str,
        entidad: str,
        entidad_id: str = "",
        detalle: str = "",
        exito: bool = True,
    ) -> None:
        evento = EventoAuditoria(
            id=uuid.uuid4().hex[:12],
            fecha=datetime.now(),
            usuario=actor.username,
            rol=actor.rol,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            detalle=detalle,
            ip=actor.ip,
            exito=exito,
        )
        try:
            self._repo.registrar(evento)
        except Exception:  # la auditoría nunca debe tumbar la operación principal
            log.exception("No se pudo registrar el evento de auditoría: %s", evento)


class ListarAuditoria:
    def __init__(self, repositorio: RepositorioAuditoria) -> None:
        self._repo = repositorio

    def ejecutar(
        self,
        usuario: str | None = None,
        accion: str | None = None,
        desde: datetime | None = None,
        limite: int = 500,
    ) -> list[EventoAuditoria]:
        return self._repo.listar(usuario=usuario or None, accion=accion or None, desde=desde, limite=limite)
