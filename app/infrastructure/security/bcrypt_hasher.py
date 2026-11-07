"""Hash de contraseñas con bcrypt (implementa el puerto HasherPassword)."""
from __future__ import annotations

import bcrypt


class BcryptHasher:
    def __init__(self, rondas: int = 12) -> None:
        self._rondas = rondas

    def hashear(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(self._rondas)).decode("utf-8")

    def verificar(self, password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except ValueError:
            # El hash guardado en el Excel no es un hash bcrypt válido.
            return False
