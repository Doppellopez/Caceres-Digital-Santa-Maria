"""H1: mide las cuatro ventanas de la fachada noroeste sobre la foto.

Usa la camara de referencias/medidas_portada.json y corrige su error local con los
pies de los cuatro remates (posicion a lo largo del muro y cota del pretil
conocidas). Foto "Santa Maria, Caceres.JPG", Jesusccastillo, CC BY-SA 3.0 ES.
Pixeles marcados a ojo en la foto reducida a 2000 px.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/h1_medir_ventanas.py
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
A = P[67]
T = (P[58] - A) / np.linalg.norm(P[58] - A)
N = np.array([-T[1], T[0]])


def ejes(g, c, a):
    f = np.array([np.cos(c) * np.cos(g), np.cos(c) * np.sin(g), np.sin(c)])
    r0 = np.cross(f, [0, 0, 1.0])
    r0 /= np.linalg.norm(r0)
    u0 = np.cross(r0, f)
    return np.cos(a) * r0 + np.sin(a) * u0, -np.sin(a) * r0 + np.cos(a) * u0, f


def retro(px, py, d=0.0):
    r, u, f = ejes(*PAR[3:6])
    rayo = f + (px - ANCHO / 2) / FPX * r - (py - ALTO / 2) / FPX * u
    t = (d - (PAR[:2] - A) @ N) / (rayo[:2] @ N)
    q = PAR[:3] + t * rayo
    return float((q[:2] - A) @ T), float(q[2])


# (pixel del pie del remate, s en el modelo, cota del pretil)
ANCLAS = [((314, 534), 18.60, 15.18), ((613, 541), 12.53, 14.90),
          ((907, 552), 6.69, 14.70), ((1211, 566), 0.38, 15.05)]
XS = [a[0][0] for a in ANCLAS]
CS = [a[1] - retro(*a[0], 0.1)[0] for a in ANCLAS]
CZ = [a[2] - retro(*a[0], 0.1)[1] for a in ANCLAS]
print("CORRECCION s", np.round(CS, 2).tolist(), "z", np.round(CZ, 2).tolist())


def medir(px, py):
    s, z = retro(px, py)
    return s + float(np.interp(px, XS, CS)), z + float(np.interp(px, XS, CZ))


def medio_ancho(xc, dx, y):
    return abs(medir(xc - dx, y)[0] - medir(xc + dx, y)[0]) / 2.0


# Ventanas altas, de medio punto: eje x, semiancho exterior y del vidrio (px), filas.
ALTAS = {
    "W1": dict(x=745.8, ext=45.8, vid=13.0, clave=577, clave_vid=613, antepecho=689, antepecho_vid=677),
    "W2": dict(x=1055.8, ext=43.8, vid=12.4, clave=590, clave_vid=623.6),
    "W3": dict(x=1317.0, clave=601.6, antepecho=712, antepecho_vid=699),
}
medidas = {}
semi_ext = float(np.mean([medio_ancho(v["x"], v["ext"], 625) for v in ALTAS.values() if "ext" in v]))
semi_vid = float(np.mean([medio_ancho(v["x"], v["vid"], 630) for v in ALTAS.values() if "vid" in v]))
caida = float(np.mean([medir(v["x"], v["clave"])[1] - medir(v["x"], v["antepecho"])[1]
                       for v in ALTAS.values() if "antepecho" in v]))
repisa = float(np.mean([medir(v["x"], v["antepecho_vid"])[1] - medir(v["x"], v["antepecho"])[1]
                        for v in ALTAS.values() if "antepecho" in v]))
for nombre, v in ALTAS.items():
    s, clave = medir(v["x"], v["clave"])
    medidas[nombre] = {"tipo": "medio_punto", "s": s, "semiancho": semi_ext, "semiancho_vidrio": semi_vid,
                       "clave_z": clave, "antepecho_z": clave - caida,
                       "antepecho_vidrio_z": clave - caida + repisa}

# Ventana apuntada de la izquierda: medio oculta; se mide desde su clave y su canto derecho.
s_clave, z_clave = medir(166, 733)
_, z_clave_vid = medir(171.7, 798)
s_der = medir(213, 830)[0]
s_der_vid = medir(181.7, 830)[0]
s_izq_vid = medir(156.7, 830)[0]
medidas["W4"] = {"tipo": "apuntada", "s": s_clave, "semiancho": abs(s_clave - s_der),
                 "semiancho_vidrio": abs(s_izq_vid - s_der_vid) / 2.0, "clave_z": z_clave,
                 "clave_vidrio_z": z_clave_vid, "antepecho_z": medir(160, 990)[1],
                 "antepecho_vidrio_z": medir(160, 970)[1]}
medidas = {k: {c: (x if isinstance(x, str) else round(float(x), 3)) for c, x in v.items()}
           for k, v in medidas.items()}
(REF / "medidas_ventanas.json").write_text(json.dumps(medidas, indent=2), encoding="utf-8")
for k, v in medidas.items():
    print("VENTANA", k, v)
