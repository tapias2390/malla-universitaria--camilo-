"""Genera empaquetado/icono.ico a partir del escudo (imagen en escala de grises) coloreándolo.

- Recorta el escudo (quita el texto inferior), vuelve transparente el fondo blanco,
  colorea en dos tonos (azul en las líneas oscuras, dorado en los tonos medios)
  y lo pone sobre una placa blanca redondeada para que se vea en fondos oscuros.

Uso:  python empaquetado/icono_escudo.py <imagen_del_escudo.png> [alto_recorte]
Requiere Pillow (solo para construir; la aplicación no lo usa).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

AZUL = (24, 48, 120)
DORADO = (196, 146, 32)
CARPETA = Path(__file__).resolve().parent


def mezclar(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def colorear(escudo: Image.Image) -> Image.Image:
    gris = escudo.convert("L")
    alfa_original = escudo.getchannel("A") if escudo.mode == "RGBA" else None
    salida = Image.new("RGBA", gris.size)
    pix_g, pix_s = gris.load(), salida.load()
    for y in range(gris.height):
        for x in range(gris.width):
            l = pix_g[x, y]
            a = 255 if alfa_original is None else alfa_original.getpixel((x, y))
            if l >= 232:                                   # fondo blanco -> transparente
                pix_s[x, y] = (255, 255, 255, 0)
                continue
            # oscuro (0) = azul · medio (~150) = dorado · claro = dorado que se desvanece
            if l < 150:
                color = mezclar(AZUL, DORADO, (l / 150) ** 1.6)
            else:
                color = DORADO
            opacidad = 255 if l < 200 else round(255 * (232 - l) / 32)
            pix_s[x, y] = (*color, min(a, opacidad))
    return salida


def placa(escudo: Image.Image, tamano: int = 256) -> Image.Image:
    lienzo = Image.new("RGBA", (tamano, tamano), (0, 0, 0, 0))
    mascara = Image.new("L", (tamano, tamano), 0)
    ImageDraw.Draw(mascara).rounded_rectangle([4, 4, tamano - 5, tamano - 5], radius=tamano * 0.2, fill=255)
    fondo = Image.new("RGBA", (tamano, tamano), (255, 255, 255, 255))
    lienzo.paste(fondo, (0, 0), mascara)
    ImageDraw.Draw(lienzo).rounded_rectangle(
        [4, 4, tamano - 5, tamano - 5], radius=tamano * 0.2, outline=(*DORADO, 255), width=max(2, tamano // 40))

    margen = int(tamano * 0.13)
    caja = tamano - 2 * margen
    escala = min(caja / escudo.width, caja / escudo.height)
    grande = escudo.resize((round(escudo.width * escala), round(escudo.height * escala)), Image.LANCZOS)
    grande = grande.filter(ImageFilter.UnsharpMask(radius=2, percent=80, threshold=2))
    lienzo.alpha_composite(grande, ((tamano - grande.width) // 2, (tamano - grande.height) // 2))
    return lienzo


def main() -> None:
    origen = Image.open(sys.argv[1]).convert("RGBA")
    alto = int(sys.argv[2]) if len(sys.argv) > 2 else round(origen.height * 0.86)
    escudo = origen.crop((0, 0, origen.width, alto))
    caja = escudo.convert("L").point(lambda v: 255 if v < 232 else 0).getbbox()   # ajustar a lo dibujado
    escudo = colorear(escudo.crop(caja) if caja else escudo)
    icono = placa(escudo)
    icono.save(CARPETA / "icono_vista_previa.png")
    icono.save(CARPETA / "icono.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Creados {CARPETA / 'icono.ico'} y icono_vista_previa.png")


if __name__ == "__main__":
    main()
