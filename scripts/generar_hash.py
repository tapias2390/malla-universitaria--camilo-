"""Genera el hash bcrypt de una contraseña para pegarlo en la columna
`password_hash` del Excel de usuarios.

Uso:  python scripts/generar_hash.py
(la contraseña se pide sin mostrarse en pantalla)
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.infrastructure.security.bcrypt_hasher import BcryptHasher  # noqa: E402


def main() -> None:
    clave = getpass.getpass("Contraseña: ")
    if clave != getpass.getpass("Repita la contraseña: "):
        sys.exit("Las contraseñas no coinciden.")
    if len(clave) < 8:
        sys.exit("Use al menos 8 caracteres.")
    print("\nCopie este valor en la columna password_hash:\n")
    print(BcryptHasher().hashear(clave))


if __name__ == "__main__":
    main()
