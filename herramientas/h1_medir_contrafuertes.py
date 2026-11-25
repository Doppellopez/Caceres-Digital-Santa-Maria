"""H1: mide contrafuertes y remates de la fachada noroeste sobre la foto ajustada.

Retroproyecta pixeles marcados a ojo (foto reducida a 2000 px de ancho) sobre
planos paralelos al muro principal, con la camara de h1_comparar_foto.py.
Foto: "Santa Maria, Caceres.JPG", Jesusccastillo, CC BY-SA 3.0 ES.

Uso (desde la raiz del proyecto; requiere renders/h1_i1_comparacion/ajuste.json):
    blender -b --factory-startup -P herramientas/h1_medir_contrafuertes.py
"""
import json
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
ajuste = json.loads((RAIZ / "renders" / "h1_i1_comparacion" / "ajuste.json")
                    .read_text(encoding="utf-8"))
dxf = json.loads((RAIZ / "datos" / "locales" / "santa_maria_dxf_local.json")
                 .read_text(encoding="utf-8"))
P = np.array([[p[0], p[1], p[2] - 440.0]
              for p in dxf["/mnt/data/work/trama urbana_2012_3D.dxf"][1688][2]])

ANCHO, ALTO = ajuste["imagen_px"]
FPX = ajuste["exif_focal"]["eq"] / 36.0 * ANCHO
M = np.array(ajuste["matriz_camara"])
OJO, DER, ARR, FRENTE = M[:3, 3], M[:3, 0], M[:3, 1], -M[:3, 2]

# Eje del muro principal: s crece desde la torre (punto 67) hacia la cabecera.
A = P[67, :2]
T = (P[58, :2] - A) / np.linalg.norm(P[58, :2] - A)
N = np.array([-T[1], T[0]])
if N @ np.array([-0.69, 0.72]) < 0:
    N = -N
SUELO = 1.4


def a_muro(p):
    """(s, d) de un punto en planta: a lo largo del muro y saliente respecto a el."""
    r = np.asarray(p[:2]) - A
    return float(r @ T), float(r @ N)


def punto(s, d, z):
    return np.array([*(A + T * s + N * d), z])


def proyectar(p):
    v = p - OJO
    z = v @ FRENTE
    return np.array([ANCHO / 2 + FPX * (v @ DER) / z, ALTO / 2 - FPX * (v @ ARR) / z])


def retro(px, py, d):
    """Corte del rayo del pixel con el plano vertical situado a d metros del muro."""
    r = FRENTE + (px - ANCHO / 2) / FPX * DER - (py - ALTO / 2) / FPX * ARR
    t = (d - (OJO[:2] - A) @ N) / (r[:2] @ N)
    q = OJO + t * r
    return a_muro(q)[0], float(q[2])


def saliente_por_costado(frente_der, costado, y):
    """Saliente cuyo costado visible mide en la foto lo marcado."""
    mejor = None
    for d in np.arange(0.1, 2.01, 0.01):
        s, z = retro(frente_der, y, d)
        e = abs(proyectar(punto(s, 0.0, z))[0] - costado)
        if mejor is None or e < mejor[0]:
            mejor = (e, d)
    return round(float(mejor[1]), 2)


print("CAMARA s, d, z:", [round(v, 2) for v in (*a_muro(OJO), OJO[2])])
for nombre, ids in {"B1": (51, 52, 53, 54), "B2": (55, 56, 57, 58), "B3": (59, 60),
                    "B4": (62,), "B5": (65, 66)}.items():
    print("DXF", nombre, [(i, *[round(v, 2) for v in a_muro(P[i])], round(P[i, 2], 2)) for i in ids])

# Costados: (frente izq, frente der, borde del costado, y)
costados = {"B2 alto": (256, 308, 322, 600), "B2 bajo": (177, 235, 254, 1037),
            "B3 alto": (562, 602, 618, 600), "B3 medio": (557, 600, 612, 733)}
for nombre, (xi, xd, xc, y) in costados.items():
    d = saliente_por_costado(xd, xc, y)
    s1, z = retro(xi, y, d)
    s0, _ = retro(xd, y, d)
    print(f"COSTADO {nombre}: saliente {d:.2f}  s {s0:.2f}..{s1:.2f}  ancho {s1 - s0:.2f}  z {z:.2f}")

for nombre, (xi, xd, y, d) in {"B4": (880, 928, 600, 0.9), "B5": (1204, 1250, 600, 1.05)}.items():
    s1, z = retro(xi, y, d)
    s0, _ = retro(xd, y, d)
    print(f"FRENTE {nombre}: s {s0:.2f}..{s1:.2f}  ancho {s1 - s0:.2f}  z {z:.2f}  (saliente supuesto {d})")

for d in (0.9, 1.1):
    s, z = retro(215, 1013, d)
    print(f"REPISA B2 con saliente {d}: z {z:.2f} (altura {z - SUELO:.2f})")
for d in (0.9, 1.2):
    s, z = retro(580, 690, d)
    print(f"REPISA B3 con saliente {d}: z {z:.2f}")

# Alturas de repisa como fraccion entre el suelo y el pretil en la misma vertical:
# asi no dependen del error de altura del ajuste de camara.
for nombre, (suelo_px, repisa_px, pretil_px) in {
        "B2": ((215, 1278), (215, 1013), (314, 534)),
        "B3": ((545, 1285), (580, 690), (600, 541))}.items():
    _, zs = retro(*suelo_px, 1.0)
    _, zr = retro(*repisa_px, 1.0)
    _, zp = retro(*pretil_px, 1.0)
    print(f"FRACCION repisa {nombre}: {(zr - zs) / (zp - zs):.3f}  (suelo {zs:.2f}, pretil {zp:.2f})")

# Remates: (pie izq, pie der, coronacion) de la cara delantera.
remates = {"B2": ((291, 534), (337, 535), (324, 460)),
           "B3": ((590, 541), (636, 542), (618, 468)),
           "B4": ((884, 551), (930, 553), (909, 478)),
           "B5": ((1190, 565), (1232, 568), (1208, 494))}
for nombre, (pi, pd, c) in remates.items():
    for d in (0.0, 0.4):
        s1, z1 = retro(*pi, d)
        s0, z0 = retro(*pd, d)
        _, zc = retro(*c, d)
        base = (z0 + z1) / 2
        print(f"REMATE {nombre} d={d}: s centro {(s0 + s1) / 2:.2f}  ancho {s1 - s0:.2f}  "
              f"pie z {base:.2f}  alto {zc - base:.2f}")
