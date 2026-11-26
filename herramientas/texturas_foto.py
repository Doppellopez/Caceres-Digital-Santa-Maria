"""Texturas construidas con las fotos propias de referencias/fotos_jorge (numpy + bpy).

- Silleria: despiece generado por codigo; el grano de la piedra son recortes del
  primer plano 20261125_184935.jpg, de donde sale tambien el color del mortero (su
  grano es ruido generado), y la variacion de tono entre sillares se muestrea
  en la fachada suroeste (20261125_184908.jpg). El tono medio se mantiene en el de
  la textura anterior, porque las fotos son nocturnas.
- Granito liso: el mismo grano, sin juntas.
- Puerta y medallon de la fachada noroeste: recortes de 20261125_184811.jpg.

Las matrices que se devuelven tienen la fila 0 arriba.
"""
from pathlib import Path

import bpy
import numpy as np

from silleria import ALTO_M, ANCHO_M, PALETAS, PX, ruido

FOTOS = Path(__file__).resolve().parents[1] / "referencias" / "fotos_jorge"
PIEDRA = np.array(PALETAS["dorada"]).mean(axis=0)

# Rectangulos (x0, y0, x1, y1) en pixeles de la foto derecha.
SILLARES = [(50, 440, 1000, 1475), (1225, 590, 2440, 1500), (2660, 660, 3840, 1590),
            (50, 1815, 1975, 2500), (2265, 1825, 3850, 2500)]
JUNTA_FOTO = (1085, 800, 1150, 1380)
CONTRASTE_GRANO = 0.8
# 184908: paramentos sin huecos, para la variacion de tono.
PARAMENTOS = [(150, 1550, 1150, 2200), (1500, 400, 1720, 1500), (2480, 400, 2860, 1500)]


def cargar(nombre):
    img = bpy.data.images.load(str(FOTOS / nombre))
    ancho, alto = img.size
    datos = np.empty(ancho * alto * 4, np.float32)
    img.pixels.foreach_get(datos)
    bpy.data.images.remove(img)
    return datos.reshape(alto, ancho, 4)[::-1, :, :3]


def derecha(foto, vertical):
    """Aplica el giro EXIF (orientacion 6) si la imagen llega apaisada."""
    if vertical and foto.shape[1] > foto.shape[0]:
        return np.rot90(foto, k=-1)
    return foto


def reducir(a, f):
    alto, ancho = a.shape[0] // f, a.shape[1] // f
    return a[:alto * f, :ancho * f].reshape(alto, f, ancho, f, -1).mean(axis=(1, 3))


def desenfocar(a, radio):
    """Media movil separable (tres pasadas, casi gaussiana), bordes reflejados."""
    r = a.astype(np.float64)
    for _ in range(3):
        for eje in (0, 1):
            n = r.shape[eje]
            k = min(radio, n - 1)
            relleno = [(0, 0)] * r.ndim
            relleno[eje] = (k + 1, k)
            s = np.cumsum(np.pad(r, relleno, mode="reflect"), axis=eje)
            alto = np.take(s, np.arange(2 * k + 1, 2 * k + 1 + n), axis=eje)
            bajo = np.take(s, np.arange(0, n), axis=eje)
            r = (alto - bajo) / (2 * k + 1)
    return r


def detalle(rect, foto, f, radio):
    """Grano de un recorte sin la iluminacion: cociente con su version desenfocada."""
    x0, y0, x1, y1 = rect
    p = reducir(foto[y0:y1, x0:x1], f)
    return np.clip(p / np.maximum(desenfocar(p, radio), 0.02), 0.45, 1.7)


def parche(rng, fuente, alto, ancho):
    if rng.random() < 0.5:
        fuente = fuente[::-1]
    if rng.random() < 0.5:
        fuente = fuente[:, ::-1]
    falta_y, falta_x = max(0, alto - fuente.shape[0]), max(0, ancho - fuente.shape[1])
    if falta_y or falta_x:
        fuente = np.pad(fuente, ((0, falta_y), (0, falta_x), (0, 0)), mode="symmetric")
    y = rng.integers(fuente.shape[0] - alto + 1)
    x = rng.integers(fuente.shape[1] - ancho + 1)
    return fuente[y:y + alto, x:x + ancho]


def variaciones(foto):
    muestras = []
    for x0, y0, x1, y1 in PARAMENTOS:
        p = foto[y0:y1, x0:x1]
        base = desenfocar(reducir(p, 10), 12)
        pequeno = reducir(p, 10)
        cociente = pequeno / np.maximum(base, 0.02)
        for y in range(0, cociente.shape[0] - 6, 7):
            for x in range(0, cociente.shape[1] - 10, 11):
                muestras.append(np.median(cociente[y + 1:y + 6, x + 1:x + 9], axis=(0, 1)))
    return np.clip(np.array(muestras), 0.8, 1.2)


def silleria(semilla=11):
    """Color y relieve repetibles de ANCHO_M x ALTO_M, y datos del muestreo."""
    rng = np.random.default_rng(semilla)
    ancho, alto = int(ANCHO_M * PX), int(ALTO_M * PX)
    primer_plano = cargar("20261125_184935.jpg")
    piedras = [detalle(r, primer_plano, 5, 22) for r in SILLARES]
    media = lambda r: np.median(primer_plano[r[1]:r[3], r[0]:r[2]], axis=(0, 1))
    razon = media(JUNTA_FOTO) / np.mean([media(r) for r in SILLARES], axis=0)
    mortero = np.clip(PIEDRA * (1 + (razon - 1) * 0.45), 0, 1)
    tonos = variaciones(derecha(cargar("20261125_184908.jpg"), True))

    # Hiladas de altura desigual (0,28 a 0,46 m) que suman la repeticion.
    alturas = []
    while sum(alturas) < ALTO_M:
        alturas.append(rng.uniform(0.28, 0.46))
    cortes_y = np.round(np.cumsum([0] + alturas) * alto / sum(alturas)).astype(int)

    color = np.zeros((alto, ancho, 3))
    borde = np.zeros((alto, ancho))
    for y0, y1 in zip(cortes_y[:-1], cortes_y[1:]):
        anchos = []
        while sum(anchos) < ancho:
            anchos.append(rng.uniform(0.28, 0.95) * PX)
        cortes = np.round(np.cumsum([0] + anchos) * ancho / sum(anchos)).astype(int)
        giro = rng.integers(ancho)
        for x0, x1 in zip(cortes[:-1], cortes[1:]):
            columnas = (np.arange(x0, x1) + giro) % ancho
            grano = parche(rng, piedras[rng.integers(len(piedras))], y1 - y0, x1 - x0)
            tono = PIEDRA * tonos[rng.integers(len(tonos))]
            color[y0:y1, columnas] = tono * (1 + (grano - 1) * CONTRASTE_GRANO)
            dx = np.minimum(np.arange(x1 - x0), np.arange(x1 - x0)[::-1])
            dy = np.minimum(np.arange(y1 - y0), np.arange(y1 - y0)[::-1])
            borde[y0:y1, columnas] = np.minimum(dx[None, :], dy[:, None])

    # Juntas irregulares: se deforman las coordenadas de todo el despiece.
    yy, xx = np.mgrid[0:alto, 0:ancho]
    xx = (xx + 4.0 * ruido(rng, alto, ancho, 48) + 1.5 * ruido(rng, alto, ancho, 12)).astype(int) % ancho
    yy = (yy + 3.5 * ruido(rng, alto, ancho, 64) + 1.5 * ruido(rng, alto, ancho, 12)).astype(int) % alto
    color, borde = color[yy, xx], borde[yy, xx]
    semiancho = 2.8 + 1.8 * ruido(rng, alto, ancho, 40)
    junta = np.clip((semiancho + 1.0 - borde) / 2.0, 0, 1)
    pared = (1 + 0.07 * ruido(rng, alto, ancho, 3) + 0.06 * ruido(rng, alto, ancho, 20))[..., None]
    color = color * (1 - junta[..., None]) + mortero * pared * junta[..., None]
    manchas = ruido(rng, alto, ancho, 320) * 0.05 + ruido(rng, alto, ancho, 96) * 0.035
    color *= (1 + manchas)[..., None]

    lum = color @ np.array([0.2126, 0.7152, 0.0722])
    grano = np.clip(lum / np.maximum(desenfocar(lum, 4), 0.02) - 1, -0.4, 0.4)
    relieve = 0.3 + 0.45 * np.sqrt(np.clip(borde / 16.0, 0, 1)) + 0.1 * ruido(rng, alto, ancho, 80) + 0.15 * grano
    relieve = relieve * (1 - junta) + (0.28 + 0.1 * grano) * junta
    datos = {"mortero_sobre_piedra_en_foto": [round(float(v), 3) for v in razon],
             "muestras_de_tono": len(tonos), "hiladas": len(alturas)}
    return np.clip(color, 0, 1), np.clip(relieve, 0, 1), datos


def granito_liso(semilla=5):
    """Grano sin juntas, 3,2 x 3,2 m."""
    rng = np.random.default_rng(semilla)
    lado = int(3.2 * PX)
    foto = cargar("20261125_184935.jpg")
    piedras = [detalle(r, foto, 5, 22) for r in SILLARES]
    celda = 128
    color = np.zeros((lado, lado, 3))
    for y in range(0, lado, celda):
        for x in range(0, lado, celda):
            color[y:y + celda, x:x + celda] = parche(rng, piedras[rng.integers(len(piedras))], celda, celda)
    manchas = ruido(rng, lado, lado, 256) * 0.07 + ruido(rng, lado, lado, 64) * 0.04
    return np.clip(color * PIEDRA * (1 + manchas)[..., None], 0, 1)


def muestrear(foto, x, y):
    """Interpolacion bilineal en coordenadas de pixel."""
    x0 = np.clip(np.floor(x).astype(int), 0, foto.shape[1] - 2)
    y0 = np.clip(np.floor(y).astype(int), 0, foto.shape[0] - 2)
    fx, fy = (x - x0)[..., None], (y - y0)[..., None]
    return ((foto[y0, x0] * (1 - fx) + foto[y0, x0 + 1] * fx) * (1 - fy)
            + (foto[y0 + 1, x0] * (1 - fx) + foto[y0 + 1, x0 + 1] * fx) * fy)


def homografia(esquinas, ancho, alto):
    destino = [(0, 0), (ancho - 1, 0), (ancho - 1, alto - 1), (0, alto - 1)]
    a, b = [], []
    for (u, v), (x, y) in zip(destino, esquinas):
        a.append([u, v, 1, 0, 0, 0, -u * x, -v * x])
        a.append([0, 0, 0, u, v, 1, -u * y, -v * y])
        b += [x, y]
    h = np.append(np.linalg.solve(np.array(a, float), np.array(b, float)), 1).reshape(3, 3)
    v, u = np.mgrid[0:alto, 0:ancho]
    p = np.stack([u, v, np.ones_like(u)], axis=-1) @ h.T
    return p[..., 0] / p[..., 2], p[..., 1] / p[..., 2]


def puerta():
    """Una hoja de la puerta noroeste, rectificada y recoloreada a madera oscura."""
    foto = derecha(cargar("20261125_184811.jpg"), True)
    ancho, alto = 256, 840
    x, y = homografia([(945, 2517), (1104, 2519), (1070, 3108), (890, 3105)], ancho, alto)
    hoja = muestrear(foto, x, y)
    # Una persona tapa la esquina inferior derecha: se refleja el lado izquierdo.
    f, c = int(alto * 0.66), int(ancho * 0.76)
    hoja[f:, c:] = hoja[f:, :ancho - c][:, ::-1]
    lum = hoja @ np.array([0.2126, 0.7152, 0.0722])
    # La foto tiene velo en la parte baja: se iguala el contraste local.
    dif = lum - desenfocar(lum, 14)
    desv = np.sqrt(np.maximum(desenfocar(dif ** 2, 40), 0))
    razon = np.clip(1 + 0.38 * dif / (desv + 0.006), 0.45, 2.4)
    return np.clip(np.array((0.22, 0.155, 0.105)) * razon[..., None], 0, 1)


def medallon():
    """El escudo circular de la torre, cara noroeste, con el tono de la piedra."""
    foto = derecha(cargar("20261125_184811.jpg"), True)
    lado = 256
    v, u = np.mgrid[0:lado, 0:lado]
    s, t = u / (lado - 1) * 2 - 1, 1 - v / (lado - 1) * 2
    centro, der, arr = np.array((2415.0, 910.5)), np.array((96.5, -10.0)), np.array((-6.25, -82.5))
    p = centro + s[..., None] * der + t[..., None] * arr
    recorte = muestrear(foto, p[..., 0], p[..., 1])
    lum = recorte @ np.array([0.2126, 0.7152, 0.0722])
    razon = np.clip(lum / np.median(lum), 0.35, 1.45)
    return np.clip(PIEDRA * razon[..., None], 0, 1)
