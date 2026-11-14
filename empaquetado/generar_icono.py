"""Genera empaquetado/icono.ico (cuadro morado con una cuadrícula: la "malla") sin librerías externas.

Uso:  python empaquetado/generar_icono.py
"""
import struct
import zlib
from pathlib import Path

MORADO, BLANCO, CLARO = (59, 45, 145, 255), (255, 255, 255, 255), (201, 195, 242, 255)


def pixel(x: int, y: int, n: int) -> tuple:
    radio = n * 0.18
    # esquinas redondeadas (transparente fuera del cuadro)
    for cx, cy in ((radio, radio), (n - radio, radio), (radio, n - radio), (n - radio, n - radio)):
        if (x < radio or x > n - radio) and (y < radio or y > n - radio):
            if (x - cx) ** 2 + (y - cy) ** 2 > radio ** 2 and abs(x - cx) <= radio and abs(y - cy) <= radio:
                return (0, 0, 0, 0)
    margen, celda, espacio = n * 0.2, n * 0.27, n * 0.06
    for fila in range(2):
        for col in range(2):
            x0 = margen + col * (celda + espacio)
            y0 = margen + fila * (celda + espacio)
            if x0 <= x < x0 + celda and y0 <= y < y0 + celda:
                return CLARO if (fila, col) == (1, 1) else BLANCO
    return MORADO


def png(n: int) -> bytes:
    filas = b"".join(b"\x00" + b"".join(bytes(pixel(x, y, n)) for x in range(n)) for y in range(n))

    def bloque(tipo: bytes, datos: bytes) -> bytes:
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos))

    return (b"\x89PNG\r\n\x1a\n" + bloque(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 6, 0, 0, 0))
            + bloque(b"IDAT", zlib.compress(filas, 9)) + bloque(b"IEND", b""))


def main() -> None:
    tamanos = [16, 32, 48, 256]
    imagenes = [png(n) for n in tamanos]
    cabecera = struct.pack("<HHH", 0, 1, len(tamanos))
    desplazamiento = 6 + 16 * len(tamanos)
    entradas = b""
    for n, datos in zip(tamanos, imagenes):
        entradas += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(datos), desplazamiento)
        desplazamiento += len(datos)
    destino = Path(__file__).resolve().parent / "icono.ico"
    destino.write_bytes(cabecera + entradas + b"".join(imagenes))
    print(f"Creado {destino}")


if __name__ == "__main__":
    main()
