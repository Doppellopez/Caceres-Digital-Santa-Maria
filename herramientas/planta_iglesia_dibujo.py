"""Dibuja la planta de la concatedral a partir de renders/planta_iglesia/cortes.json.

Necesita matplotlib (vale el Python de QGIS). Antes: planta_iglesia_datos.py.

Uso (desde la raiz del proyecto):
    python herramientas/planta_iglesia_dibujo.py
"""
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

CARPETA = Path(__file__).resolve().parents[1] / "renders" / "planta_iglesia"
D = json.loads((CARPETA / "cortes.json").read_text(encoding="utf-8"))
P = D["contorno"]

# Ejes de la iglesia: a lo largo de la fachada noroeste (T, hacia la cabecera) y hacia fuera (N).
T = (P[58][0] - P[67][0], P[58][1] - P[67][1])
largo_t = math.hypot(*T)
T = (T[0] / largo_t, T[1] / largo_t)
N = (-T[1], T[0])
if N[0] * -0.69 + N[1] * 0.72 < 0:
    N = (-N[0], -N[1])


def st(p):
    return p[0] * T[0] + p[1] * T[1], p[0] * N[0] + p[1] * N[1]


def xy(s, d):
    return s * T[0] + d * N[0], s * T[1] + d * N[1]


proyectado = [st(p) for p in P]
s0, s1 = min(p[0] for p in proyectado), max(p[0] for p in proyectado)
d0, d1 = min(p[1] for p in proyectado), max(p[1] for p in proyectado)

fig, ax = plt.subplots(figsize=(14, 14), dpi=150)
cx, cy = zip(*(P + P[:1]))
ax.fill(cx, cy, facecolor="#f3efe7", edgecolor="#1d4f91", lw=0.8, ls="--", zorder=1)
for nombre, segmentos in D["objetos"].items():
    provisional = "provisional" in nombre or nombre.endswith("fondo")
    for a, b in segmentos:
        ax.plot([a[0], b[0]], [a[1], b[1]], color="#999999" if provisional else "black",
                lw=1.0 if provisional else 1.8, ls="--" if provisional else "-",
                solid_capstyle="round", zorder=2)


def cota(a, b, texto, hacia, sep):
    p0, p1 = [(q[0] + hacia[0] * sep, q[1] + hacia[1] * sep) for q in (a, b)]
    ax.annotate("", xy=p1, xytext=p0, arrowprops={"arrowstyle": "<->", "color": "#b4551d", "lw": 1.2})
    for q, p in ((a, p0), (b, p1)):
        ax.plot([q[0], p[0]], [q[1], p[1]], color="#b4551d", lw=0.6, ls=":")
    giro = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    giro = giro - 180 if giro > 90 else giro + 180 if giro < -90 else giro
    m = ((p0[0] + p1[0]) / 2 + hacia[0] * 1.3, (p0[1] + p1[1]) / 2 + hacia[1] * 1.3)
    ax.text(*m, texto, color="#b4551d", rotation=giro, rotation_mode="anchor", ha="center",
            va="center", fontsize=13)


def metros(v):
    return f"{v:.1f} m".replace(".", ",")


cota(xy(s0, d0), xy(s1, d0), "Largo máximo " + metros(s1 - s0), (-N[0], -N[1]), 4.0)
cota(xy(s1, d0), xy(s1, d1), "Ancho máximo " + metros(d1 - d0), T, 4.0)

giro = math.degrees(math.atan2(T[1], T[0]))


def rotulo(s, d, texto, angulo=0.0, **kw):
    ax.text(*xy(s, d), texto, rotation=angulo, rotation_mode="anchor", ha="center", va="center",
            fontsize=13, **kw)


s_med, d_med = (s0 + s1) / 2, (d0 + d1) / 2
rotulo(s_med - 3, d1 + 4.5, "Fachada noroeste (Puerta del Evangelio)", giro)
rotulo(s1 - 6, d_med, "Cabecera", giro - 90)
rotulo(s0 - 3.5, d_med - 3, "Fachada suroeste\n(sin modelar)", giro - 90, color="#7a3b10")
torre = (10.8, -7.6)
ax.text(*torre, "Torre", ha="center", va="center", fontsize=14, fontweight="bold")

xmin, xmax = min(cx) - 9, max(cx) + 9
ymin, ymax = min(cy) - 9, max(cy) + 9
ax.annotate("N", xy=(xmax - 3, ymax - 1), xytext=(xmax - 3, ymax - 8), ha="center", fontsize=18,
            arrowprops={"arrowstyle": "-|>", "color": "black", "lw": 1.6})
ax.plot([xmin + 2, xmin + 12], [ymin + 2, ymin + 2], color="black", lw=5, solid_capstyle="butt")
ax.text(xmin + 7, ymin + 3.2, "10 m", ha="center", fontsize=13)
ax.set_title("Concatedral de Santa María: planta del modelo (corte a cota "
             + metros(D["cota"]) + ")", fontsize=16)
ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)
ax.set_aspect("equal")
ax.axis("off")
fig.text(0.02, 0.015, "Negro: muros del modelo. Gris discontinuo: cierres provisionales. Azul discontinuo "
         "y relleno claro: contorno del levantamiento municipal.\nEl modelo es solo exterior: no hay "
         "grosor de muros, pilares ni interior. Las medidas son del contorno municipal.", fontsize=11)
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(CARPETA / "planta_iglesia.png")
print("RENDER", CARPETA / "planta_iglesia.png", "LARGO", round(s1 - s0, 2), "ANCHO", round(d1 - d0, 2))
