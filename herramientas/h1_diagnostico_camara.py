"""H1: el desfase del pretil, es del modelo o del ajuste de camara?

Ajusta la camara de la misma foto con tres juegos de puntos y muestra el error de
cada punto. Con 7 puntos hay 14 ecuaciones para 6 o 7 incognitas, asi que un error
pequeno en todos indica que la geometria es coherente con la foto. No guarda nada.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/h1_diagnostico_camara.py
"""
import json
from pathlib import Path

import numpy as np

DXF = Path(__file__).resolve().parents[1] / "datos" / "locales" / "santa_maria_dxf_local.json"
P = np.array([p[:2] for p in json.loads(DXF.read_text(encoding="utf-8"))
              ["/mnt/data/work/trama urbana_2012_3D.dxf"][1688][2]])

ANCHO, ALTO = 2000, 1328
F_EXIF = 27 / 36.0 * ANCHO

TORRE = [("torre O arriba", (5.11, -7.17, 27.77), (1627, 117)),
         ("torre N arriba", (10.33, -2.19, 27.77), (1362, 108)),
         ("torre O pie", (5.11, -7.32, 1.74), (1748, 1270))]
A = P[67]                                        # mismo eje que la intervencion 2
T = (P[58] - A) / np.linalg.norm(P[58] - A)


def muro(s, d, z):
    n = np.array([-T[1], T[0]])
    return (*(A + T * s + n * d), z)


REMATES = [("pie remate B2", muro(18.60, 0.1, 15.18), (314, 534)),
           ("pie remate B3", muro(12.53, 0.1, 14.90), (613, 541)),
           ("pie remate B4", muro(6.69, 0.1, 14.70), (907, 552)),
           ("pie remate B5", muro(0.38, 0.1, 15.05), (1211, 566))]


def ejes(g, c, a):
    f = np.array([np.cos(c) * np.cos(g), np.cos(c) * np.sin(g), np.sin(c)])
    r0 = np.cross(f, [0, 0, 1.0])
    r0 /= np.linalg.norm(r0)
    u0 = np.cross(r0, f)
    return np.cos(a) * r0 + np.sin(a) * u0, -np.sin(a) * r0 + np.cos(a) * u0, f


def proyectar(par, pts):
    r, u, f = ejes(*par[3:6])
    fpx = par[6]
    v = np.asarray(pts, float) - par[:3]
    z = v @ f
    return np.stack([ANCHO / 2 + fpx * (v @ r) / z, ALTO / 2 - fpx * (v @ u) / z], axis=1)


def ajustar(puntos, focal_libre):
    def res(p):
        q = np.append(p, F_EXIF) if not focal_libre else p
        e = (proyectar(q, [x[1] for x in puntos]) - [x[2] for x in puntos]).ravel() / 8.0
        return np.concatenate([e, [(q[2] - 3.05) / 0.5, q[5] / np.radians(2.0)]])

    mejor = None
    for dist in (18.0, 25.0, 35.0):
        c = np.array([15.9 - 0.69 * dist, 3.0 + 0.72 * dist, 3.05])
        m = np.array([13.0, 0.0, 11.0]) - c
        p = np.array([*c, np.arctan2(m[1], m[0]), np.arctan2(m[2], np.hypot(*m[:2])), 0.0])
        if focal_libre:
            p = np.append(p, F_EXIF)
        lam = 1.0
        for _ in range(400):
            r = res(p)
            J = np.stack([(res(p + e) - r) / 1e-6 for e in np.eye(len(p)) * 1e-6], axis=1)
            paso = np.linalg.solve(J.T @ J + lam * np.eye(len(p)), -J.T @ r)
            if np.sum(res(p + paso) ** 2) < np.sum(r ** 2):
                p, lam = p + paso, lam / 3
            else:
                lam *= 5
        coste = np.sum(res(p) ** 2)
        if mejor is None or coste < mejor[0]:
            mejor = (coste, p if focal_libre else np.append(p, F_EXIF))
    return mejor[1]


for titulo, juego, libre in (("solo torre", TORRE, False),
                             ("torre + remates", TORRE + REMATES, False),
                             ("torre + remates, focal libre", TORRE + REMATES, True)):
    p = ajustar(juego, libre)
    todos = TORRE + REMATES
    err = np.linalg.norm(proyectar(p, [x[1] for x in todos]) - [x[2] for x in todos], axis=1)
    print(f"AJUSTE {titulo}: camara {np.round(p[:3], 2).tolist()} alabeo "
          f"{np.degrees(p[5]):.2f} focal_eq {p[6] * 36 / ANCHO:.1f}")
    for (nombre, *_), e in zip(todos, err):
        print(f"ERR {titulo} | {nombre}: {e:.1f} px")
