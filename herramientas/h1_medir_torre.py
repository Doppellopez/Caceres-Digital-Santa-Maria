"""H1: mide los elementos de la torre sobre la foto.

Alturas: retroproyeccion sobre el plano de la cara noroeste (camara de
medidas_portada.json), calibrada con la coronacion (Z 27,77) y el pie (Z 1,74)
medidos en la propia foto. Posiciones horizontales: distancia, sobre ese mismo
plano, al canto derecho de la torre (esquina oeste, punto 80 del DXF), que es el
que la camara reproduce bien a todas las alturas. Foto "Santa Maria, Caceres.JPG", Jesusccastillo,
CC BY-SA 3.0 ES. Pixeles marcados a ojo en la foto reducida a 2000 px.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/h1_medir_torre.py
"""
import json
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
REF = RAIZ / "referencias"
PAR = np.array(json.loads((REF / "medidas_portada.json").read_text(encoding="utf-8"))["camara_par"])
P = np.array([p[:2] for p in json.loads(
    (RAIZ / "datos" / "locales" / "santa_maria_dxf_local.json").read_text(encoding="utf-8"))
    ["/mnt/data/work/trama urbana_2012_3D.dxf"][1688][2]])
ANCHO, ALTO, FPX = 2000, 1328, 27 / 36.0 * 2000
NORTE, OESTE = P[70], P[80]                      # extremos de la cara noroeste
LARGO = float(np.linalg.norm(OESTE - NORTE))
T = (OESTE - NORTE) / LARGO
N = np.array([T[1], -T[0]])
if N @ np.array([-0.69, 0.72]) < 0:
    N = -N
CIMA, PIE = 27.77, 1.74


def ejes(g, c, a):
    f = np.array([np.cos(c) * np.cos(g), np.cos(c) * np.sin(g), np.sin(c)])
    r0 = np.cross(f, [0, 0, 1.0])
    r0 /= np.linalg.norm(r0)
    u0 = np.cross(r0, f)
    return np.cos(a) * r0 + np.sin(a) * u0, -np.sin(a) * r0 + np.cos(a) * u0, f


def z_plano(px, py, d=0.0):
    r, u, f = ejes(*PAR[3:6])
    rayo = f + (px - ANCHO / 2) / FPX * r - (py - ALTO / 2) / FPX * u
    t = (d - (PAR[:2] - NORTE) @ N) / (rayo[:2] @ N)
    return float(PAR[2] + t * rayo[2])


Z0, Z1 = z_plano(1748, 1270), z_plano(1634, 117)


def cota(px, py):
    return PIE + (z_plano(px, py) - Z0) / (Z1 - Z0) * (CIMA - PIE)


def canto_oeste(y):
    """Pixel x del canto derecho de la torre a la fila y."""
    return 1634 + (y - 122) * 0.148


def u_plano(px, py, d=0.0):
    r, u, f = ejes(*PAR[3:6])
    rayo = f + (px - ANCHO / 2) / FPX * r - (py - ALTO / 2) / FPX * u
    t = (d - (PAR[:2] - NORTE) @ N) / (rayo[:2] @ N)
    return float((PAR[:2] + t * rayo[:2] - NORTE) @ T)


def fraccion(px, py):
    """Posicion a lo largo de la cara: 0 en el canto norte, 1 en la esquina oeste."""
    return 1.0 - (u_plano(canto_oeste(py), py) - u_plano(px, py)) / LARGO


def hueco(x0, x1, y0, y1):
    """Hueco rectangular o de arco: x de las jambas, fila de la clave y del antepecho."""
    xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    return {"f": fraccion(xc, yc), "ancho": (fraccion(x1, yc) - fraccion(x0, yc)) * LARGO,
            "z_alto": cota(xc, y0), "z_bajo": cota(xc, y1)}


m = {"largo_cara": LARGO, "z_calibracion": [Z0, Z1],
     "cornisas_z": [cota(1503, 337), cota(1525, 485)],
     "campanario": hueco(1459, 1537, 160, 280),
     "balaustrada": hueco(1476, 1545, 285, 327),
     "medallon": hueco(1490, 1561, 360, 430),
     "ventanuco_medallon": hueco(1456, 1483, 391, 424),
     "ventanuco_alto": hueco(1534, 1573, 518, 575),
     "ciega": hueco(1522, 1597, 624, 746),
     "ventanuco_bajo": hueco(1528, 1574, 956, 1015),
     "campana": hueco(1470, 1515, 226, 270)}
# Pinaculo del canto norte: pie, tope del pedestal, base del plato, tope del plato y remate.
filas = {"pie": 102, "pedestal": 74, "plato_bajo": 42, "plato_alto": 22, "remate": 9}
zp = {k: z_plano(1380, v, -0.45) for k, v in filas.items()}
escala = (CIMA - PIE) / (Z1 - Z0)
m["pinaculo"] = {k: (v - zp["pie"]) * escala for k, v in zp.items()}


def redondear(v):
    if isinstance(v, dict):
        return {k: redondear(x) for k, x in v.items()}
    if isinstance(v, list):
        return [redondear(x) for x in v]
    return round(float(v), 3)


m = redondear(m)
(REF / "medidas_torre.json").write_text(json.dumps(m, indent=2), encoding="utf-8")
for k, v in m.items():
    print("TORRE", k, v)
# Contraste del contrafuerte de la torre (DXF 74-78) con la foto: cantos de su frente.
for y in (700, 900):
    print("CONTRAFUERTE_FOTO", y, [round(fraccion(x, y) * LARGO, 2)
          for x in (1443 + (y - 800) * 0.06, 1498 + (y - 800) * 0.06)],
          "modelo u", [round(float((P[i] - NORTE) @ T), 2) for i in (74, 77)])
