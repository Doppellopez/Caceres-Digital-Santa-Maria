"""Dibuja la planta de la torre a partir de renders/planta_torre/cortes.json.

Necesita matplotlib (vale el Python de QGIS). Antes: planta_torre_datos.py.

Uso (desde la raiz del proyecto):
    python herramientas/planta_torre_dibujo.py
"""
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

CARPETA = Path(__file__).resolve().parents[1] / "renders" / "planta_torre"
D = json.loads((CARPETA / "cortes.json").read_text(encoding="utf-8"))
P = {p["i"]: (p["x"], p["y"]) for p in D["puntos_dxf"]}


def media(*ids):
    return tuple(sum(P[i][k] for i in ids) / len(ids) for k in (0, 1))


# Esquinas medias: los resaltes de coronacion se promedian.
OESTE = media(79, 81)
NORTE = media(70, 72)
SUR = media(83, 85)
ESTE = (16.393, -7.915)  # cierre en paralelogramo de la intervencion 1: supuesto
CARAS = [("Noroeste", OESTE, NORTE, False), ("Suroeste", SUR, OESTE, False),
         ("Noreste", NORTE, ESTE, True), ("Sudeste", ESTE, SUR, True)]
CENTRO = tuple(sum(p[k] for p in (OESTE, NORTE, SUR, ESTE)) / 4 for k in (0, 1))

fig = plt.figure(figsize=(16, 10), dpi=150)
rejilla = fig.add_gridspec(3, 2, width_ratios=[2.1, 1])
ax = fig.add_subplot(rejilla[:, 0])
for a, b in D["contorno_tapa"]:
    ax.plot([a[0], b[0]], [a[1], b[1]], color="black", lw=2.2, solid_capstyle="round")
for nombre, a, b, supuesta in CARAS:
    largo = math.dist(a, b)
    m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    d = (b[0] - a[0], b[1] - a[1])
    n = (-d[1] / largo, d[0] / largo)
    if (m[0] - CENTRO[0]) * n[0] + (m[1] - CENTRO[1]) * n[1] < 0:
        n = (-n[0], -n[1])
    sep = 1.35
    p0, p1 = [(q[0] + n[0] * sep, q[1] + n[1] * sep) for q in (a, b)]
    color = "#b4551d" if supuesta else "#1d4f91"
    ax.annotate("", xy=p1, xytext=p0, arrowprops={"arrowstyle": "<->", "color": color, "lw": 1.2})
    for q, p in ((a, p0), (b, p1)):
        ax.plot([q[0], p[0]], [q[1], p[1]], color=color, lw=0.6, ls=":")
    giro = math.degrees(math.atan2(d[1], d[0]))
    giro = giro - 180 if giro > 90 else giro + 180 if giro < -90 else giro
    texto = f"Cara {nombre.lower()}  {largo:.1f} m".replace(".", ",") + ("  (supuesta)" if supuesta else "")
    ax.text(m[0] + n[0] * (sep + 0.45), m[1] + n[1] * (sep + 0.45), texto, color=color,
            rotation=giro, rotation_mode="anchor", ha="center", va="center", fontsize=12)

contrafuerte = [P[i] for i in (74, 75, 76, 77, 74)]
ax.fill(*zip(*contrafuerte), facecolor="#d9d2c5", edgecolor="black", lw=1.4)
ax.annotate("Contrafuerte\n(hasta 14,8 m de cota)", xy=media(75, 76), xytext=(3.0, -0.2), fontsize=11,
            arrowprops={"arrowstyle": "-", "lw": 0.8})
ax.plot(*ESTE, "o", color="#b4551d", ms=7)
ax.text(ESTE[0] - 0.35, ESTE[1], "esquina interior\nsupuesta", color="#b4551d", ha="right",
        va="center", fontsize=11)
ax.annotate("N", xy=(18.0, 1.0), xytext=(18.0, -1.6), ha="center", fontsize=16,
            arrowprops={"arrowstyle": "-|>", "color": "black", "lw": 1.5})
ax.plot([2.5, 7.5], [-15.4, -15.4], color="black", lw=4, solid_capstyle="butt")
ax.text(5.0, -15.0, "5 m", ha="center", fontsize=11)
ax.set_title("Torre de la concatedral: planta (contorno de la coronación, cota 27,8 m)", fontsize=14)
ax.set_xlim(1.5, 19.5)
ax.set_ylim(-16.2, 1.8)
ax.set_aspect("equal")
ax.axis("off")

TITULOS = {"baja": "Corte a cota 7 m", "media": "Corte a cota 13 m",
           "campanas": "Corte a cota 24,2 m (campanas)"}
for fila, (nombre, corte) in enumerate(D["cortes"].items()):
    s = fig.add_subplot(rejilla[fila, 1])
    for objeto, segmentos in corte["objetos"].items():
        interior = "interior" in objeto or objeto.endswith("fondo")
        color = "#8a6d3b" if "campana" == objeto.split("_")[-1] else "#999999" if interior else "black"
        for a, b in segmentos:
            s.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=0.9 if interior else 1.3,
                   ls="--" if interior else "-")
    s.set_title(TITULOS[nombre], fontsize=12)
    s.set_xlim(3.5, 18.0)
    s.set_ylim(-14.5, 0.0)
    s.set_aspect("equal")
    s.axis("off")

fig.text(0.01, 0.012, "Cotas locales (el suelo junto a la torre está en torno a 1,5 m). Azul: contorno del "
         "levantamiento municipal. Naranja: supuesto.\n"
         "Gris discontinuo: cierres interiores provisionales; "
         "el modelo no tiene muros con grosor real ni interior.", fontsize=10)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(CARPETA / "planta_torre.png")
print("RENDER", CARPETA / "planta_torre.png")
for nombre, a, b, supuesta in CARAS:
    print(nombre, round(math.dist(a, b), 2), "supuesta" if supuesta else "")
