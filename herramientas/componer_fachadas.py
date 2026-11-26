"""Monta en una lamina los alzados de render_fachadas.py. Necesita Pillow.

Uso (desde la raiz del proyecto):  python herramientas/componer_fachadas.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CARPETA = Path(__file__).resolve().parents[1] / "renders" / "fachadas"
PANELES = (("NO", "Noroeste: Puerta del Evangelio"), ("SO", "Suroeste: portada y rosetón"),
           ("SE", "Sureste: sin detallar"), ("NE", "Noreste: cabecera, sin detallar"))
ANCHO, ALTO, CABECERA, PIE, HUECO = 1600, 1200, 70, 70, 24


def letra(tamano):
    for nombre in ("segoeui.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(nombre, tamano)
        except OSError:
            pass
    return ImageFont.load_default(tamano)


lamina = Image.new("RGB", (ANCHO * 2 + HUECO * 3, (ALTO + CABECERA) * 2 + HUECO * 3 + PIE), (196, 204, 214))
dibujo = ImageDraw.Draw(lamina)
for i, (clave, titulo) in enumerate(PANELES):
    x = HUECO + (i % 2) * (ANCHO + HUECO)
    y = HUECO + (i // 2) * (ALTO + CABECERA + HUECO)
    dibujo.rectangle([x, y, x + ANCHO, y + ALTO + CABECERA], fill=(232, 234, 238))
    dibujo.text((x + 30, y + 10), titulo, font=letra(44), fill=(30, 30, 30))
    panel = Image.open(CARPETA / f"alzado_{clave}.png").convert("RGBA")
    lamina.paste(panel, (x, y + CABECERA), panel)
dibujo.text((HUECO + 30, lamina.height - PIE),
            "Concatedral de Santa María (maqueta). Alzados sin perspectiva y a la misma escala, "
            "sin edificios vecinos ni terreno.", font=letra(36), fill=(30, 30, 30))
destino = CARPETA / "fachadas_concatedral.png"
lamina.save(destino)
print(destino, lamina.size)
