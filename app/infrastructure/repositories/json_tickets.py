"""Repositorio de tickets en un archivo JSON local.

Los Excel de Drive se tratan como solo lectura; los tickets se guardan en
local. Si más adelante se quieren en una hoja de Drive o en una base de
datos, basta con crear otra clase que cumpla el puerto RepositorioTickets.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from app.domain.entities import EstadoTicket, Ticket


class JsonRepositorioTickets:
    def __init__(self, ruta: str | Path) -> None:
        self._ruta = Path(ruta)
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- públicos
    def guardar(self, ticket: Ticket) -> None:
        with self._lock:
            tickets = self._leer()
            tickets[ticket.id] = ticket
            self._escribir(tickets)

    def obtener(self, ticket_id: str) -> Ticket | None:
        with self._lock:
            return self._leer().get(ticket_id)

    def listar(self, estado: str | None = None) -> list[Ticket]:
        with self._lock:
            tickets = list(self._leer().values())
        if estado:
            tickets = [t for t in tickets if t.estado.value == estado]
        return tickets

    def buscar_abierto(self, codigo_estudiante: str, codigo_materia: str) -> Ticket | None:
        return next(
            (
                t for t in self.listar(EstadoTicket.ABIERTO.value)
                if t.codigo_estudiante == codigo_estudiante and t.codigo_materia == codigo_materia
            ),
            None,
        )

    # ---------------------------------------------------------------- privados
    def _leer(self) -> dict[str, Ticket]:
        if not self._ruta.exists():
            return {}
        datos = json.loads(self._ruta.read_text(encoding="utf-8") or "[]")
        return {d["id"]: self._desde_dict(d) for d in datos}

    def _escribir(self, tickets: dict[str, Ticket]) -> None:
        self._ruta.parent.mkdir(parents=True, exist_ok=True)
        datos = [self._a_dict(t) for t in tickets.values()]
        # Escritura atómica: primero a un temporal y luego se reemplaza, para
        # no dejar el archivo corrupto si el proceso se corta a mitad.
        temporal = self._ruta.with_suffix(".tmp")
        temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporal, self._ruta)

    @staticmethod
    def _a_dict(ticket: Ticket) -> dict:
        datos = asdict(ticket)
        datos["estado"] = ticket.estado.value
        datos["fecha_creacion"] = ticket.fecha_creacion.isoformat()
        return datos

    @staticmethod
    def _desde_dict(datos: dict) -> Ticket:
        return Ticket(
            **{
                **datos,
                "estado": EstadoTicket(datos["estado"]),
                "fecha_creacion": datetime.fromisoformat(datos["fecha_creacion"]),
            }
        )
