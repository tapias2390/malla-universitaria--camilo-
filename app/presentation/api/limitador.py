"""Limitador simple de intentos de login fallidos (en memoria).

Protege contra ataques de fuerza bruta: tras `max_intentos` fallos en la
ventana de tiempo, se bloquean nuevos intentos de ese usuario desde esa IP.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class LimitadorIntentos:
    def __init__(self, max_intentos: int = 5, ventana_segundos: int = 300) -> None:
        self._max = max_intentos
        self._ventana = ventana_segundos
        self._fallos: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _limpiar(self, clave: str, ahora: float) -> deque[float]:
        fallos = self._fallos[clave]
        while fallos and ahora - fallos[0] > self._ventana:
            fallos.popleft()
        return fallos

    def bloqueado(self, clave: str) -> bool:
        with self._lock:
            return len(self._limpiar(clave, time.monotonic())) >= self._max

    def registrar_fallo(self, clave: str) -> None:
        with self._lock:
            ahora = time.monotonic()
            self._limpiar(clave, ahora).append(ahora)

    def reiniciar(self, clave: str) -> None:
        with self._lock:
            self._fallos.pop(clave, None)
