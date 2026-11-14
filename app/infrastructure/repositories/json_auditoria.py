"""Registro de auditoría en un archivo local de "una línea JSON por evento" (.jsonl).

Solo se agregan líneas al final: nunca se modifica ni se borra un evento, así
el historial no se puede alterar desde la aplicación.
"""
from __future__ import annotations

import json
import threading
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from app.domain.entities import EventoAuditoria


class JsonlRepositorioAuditoria:
    def __init__(self, ruta: str | Path) -> None:
        self._ruta = Path(ruta)
        self._lock = threading.Lock()

    def registrar(self, evento: EventoAuditoria) -> None:
        datos = asdict(evento)
        datos["fecha"] = evento.fecha.isoformat(timespec="seconds")
        linea = json.dumps(datos, ensure_ascii=False)
        with self._lock:
            self._ruta.parent.mkdir(parents=True, exist_ok=True)
            with self._ruta.open("a", encoding="utf-8") as archivo:
                archivo.write(linea + "\n")

    def listar(
        self,
        usuario: str | None = None,
        accion: str | None = None,
        desde: datetime | None = None,
        limite: int = 500,
    ) -> list[EventoAuditoria]:
        with self._lock:
            if not self._ruta.exists():
                return []
            lineas = self._ruta.read_text(encoding="utf-8").splitlines()

        eventos: list[EventoAuditoria] = []
        for linea in reversed(lineas):                  # más recientes primero
            if not linea.strip():
                continue
            datos = json.loads(linea)
            evento = EventoAuditoria(**{**datos, "fecha": datetime.fromisoformat(datos["fecha"])})
            if usuario and usuario.lower() not in evento.usuario.lower():
                continue
            if accion and evento.accion != accion:
                continue
            if desde and evento.fecha < desde:
                continue
            eventos.append(evento)
            if len(eventos) >= limite:
                break
        return eventos
