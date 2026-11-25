"""Silleria de granito generada por codigo (numpy). Sin fotografias ni terceros.

Modulo comun de prueba_piedra.py y h1_i5_piedra.py. Las matrices van con la fila 0
abajo (v = 0), que es como Blender guarda los pixeles.
"""
import numpy as np

ANCHO_M, ALTO_M = 6.4, 3.2          # tamano real de una repeticion
PX = 320                            # pixeles por metro
HILADAS = 8                         # hiladas de 0,40 m

PALETAS = {
    # Tonos claros, como la imagen de muestra de Jorge.
    "clara": [(0.82, 0.73, 0.63), (0.78, 0.72, 0.66), (0.85, 0.74, 0.60),
              (0.74, 0.69, 0.63), (0.83, 0.70, 0.60)],
    # Granito dorado, ajustado a ojo a las fotos de la concatedral.
    "dorada": [(0.71, 0.60, 0.46), (0.66, 0.57, 0.46), (0.73, 0.61, 0.45),
               (0.63, 0.56, 0.47), (0.69, 0.56, 0.43)],
}


def ruido(rng, alto, ancho, celda):
    """Ruido de valor repetible en ambos ejes, en [-1, 1]."""
    gy, gx = max(1, alto // celda), max(1, ancho // celda)
    g = rng.uniform(-1, 1, (gy, gx))
    y = np.arange(alto) * gy / alto
    x = np.arange(ancho) * gx / ancho
    y0, x0 = y.astype(int), x.astype(int)
    fy, fx = (y - y0)[:, None], (x - x0)[None, :]
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    y1, x1 = (y0 + 1) % gy, (x0 + 1) % gx
    arriba = g[np.ix_(y0, x0)] * (1 - fx) + g[np.ix_(y0, x1)] * fx
    abajo = g[np.ix_(y1, x0)] * (1 - fx) + g[np.ix_(y1, x1)] * fx
    return arriba * (1 - fy) + abajo * fy


def generar(paleta, semilla=7):
    rng = np.random.default_rng(semilla)
    ancho, alto = int(ANCHO_M * PX), int(ALTO_M * PX)
    h = alto // HILADAS
    color = np.zeros((alto, ancho, 3))
    relieve = np.zeros((alto, ancho))
    # Coordenadas deformadas para que las juntas no sean rectas perfectas.
    yy, xx = np.mgrid[0:alto, 0:ancho]
    xx = (xx + 3.0 * ruido(rng, alto, ancho, 40)).astype(int) % ancho
    yy = (yy + 2.5 * ruido(rng, alto, ancho, 64)).astype(int) % alto
    ids = np.zeros((alto, ancho), int)
    borde = np.zeros((alto, ancho))
    tonos, n = [], 0
    for fila in range(HILADAS):
        anchos = []
        while sum(anchos) < ancho:
            anchos.append(int(rng.uniform(0.45, 1.25) * PX))
        anchos = np.array(anchos) * ancho / sum(anchos)
        cortes = (np.cumsum(anchos) + rng.uniform(0, ancho)) % ancho
        cortes = np.sort(cortes)
        banda = (yy >= fila * h) & (yy < (fila + 1) * h)
        x = xx[banda]
        pos = np.searchsorted(cortes, x) % len(cortes)
        ids[banda] = n + pos
        dx = np.min(np.abs((x[:, None] - cortes[None, :] + ancho / 2) % ancho - ancho / 2), axis=1)
        dy = np.minimum(yy[banda] - fila * h, (fila + 1) * h - 1 - yy[banda])
        borde[banda] = np.minimum(dx, dy)
        for _ in cortes:
            base = np.array(paleta[rng.integers(len(paleta))])
            tonos.append(base * rng.uniform(0.9, 1.07))
        n += len(cortes)
    color = np.array(tonos)[ids]
    manchas = ruido(rng, alto, ancho, 160) * 0.06 + ruido(rng, alto, ancho, 48) * 0.045
    grano = ruido(rng, alto, ancho, 3)
    fino = rng.uniform(-1, 1, (alto, ancho))
    color = color * (1 + manchas + grano * 0.05 + fino * 0.035)[..., None]
    motas = (fino > 0.93) & (grano < 0.1)
    color[motas] *= 0.78
    junta = np.clip((4.0 - borde) / 2.0, 0, 1)
    mortero = np.array(paleta[3]) * 0.52
    color = color * (1 - junta[..., None]) + mortero * junta[..., None]
    arista = np.clip(borde / 14.0, 0, 1)
    relieve = 0.25 + 0.55 * np.sqrt(arista) + 0.12 * ruido(rng, alto, ancho, 90) + 0.05 * grano
    relieve[junta > 0.5] = 0.1
    return np.clip(color, 0, 1), np.clip(relieve, 0, 1)


def normales(relieve, amplitud_m=0.0245):
    """Mapa de normales (convencion OpenGL, la de glTF) a partir del relieve."""
    paso = 1.0 / PX
    dx = (np.roll(relieve, -1, 1) - np.roll(relieve, 1, 1)) * amplitud_m / (2 * paso)
    dy = (np.roll(relieve, -1, 0) - np.roll(relieve, 1, 0)) * amplitud_m / (2 * paso)
    n = np.dstack([-dx, -dy, np.ones_like(dx)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return 0.5 + 0.5 * n
