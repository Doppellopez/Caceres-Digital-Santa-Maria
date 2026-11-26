"""Intervencion 10: medidas de la fachada suroeste sobre tres fotos propias.

Ajusta a la vez las camaras de 184905, 184908 y 184911 (posicion, orientacion y
focal comun) y las posiciones 3D de los puntos que se ven en varias, apoyandose en
el contorno municipal (planta y cotas) y en las cornisas de la torre del modelo.
Despues retroproyecta sobre los planos medidos los puntos que se ven en una sola.

Coordenadas de fachada: s a lo largo (desde la esquina oeste de la torre, DXF 82,
hacia el sur), d hacia fuera del paramento, z cota local.

Los pixeles se marcaron a ojo sobre las fotos giradas y reducidas a 1500 x 2000.
Escribe referencias/medidas_suroeste.json. Solo necesita numpy.

Uso (desde la raiz del proyecto):  python herramientas/i10_medir_suroeste.py
"""
import json
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
CX, CY = 750.0, 1000.0
FOCAL_EXIF = 29.0 * 2500.0 / 43.27      # 29 mm equivalentes

# --- puntos 3D: valor inicial y holgura (m) de cada coordenada; 0 = fija -------
PUNTOS = {
    # cornisas de la torre (vertices del modelo, intervencion 8)
    "c1_izq": ((-0.70, 0.03, 17.91), (0, 0, 0)),
    "c2_izq": ((-0.70, 0.03, 21.59), (0, 0, 0)),
    "c3_izq": ((-0.86, 0.02, 27.80), (0, 0, 0)),
    # contrafuerte derecho (B2), planta del levantamiento
    "b2_muro_pie": ((16.23, -0.27, 2.45), (0, 0, 0.5)),
    "b2_izq_pie": ((16.23, 0.42, 2.45), (0, 0, 0.5)),
    "b2_der_pie": ((17.60, 0.45, 2.50), (0, 0, 0.5)),
    "b2_izq_alto": ((16.23, 0.42, 18.45), (0, 0, 1.0)),
    "b2_der_alto": ((17.60, 0.45, 18.40), (0, 0, 1.0)),
    "muro_b2_izq": ((16.24, -0.27, 18.48), (0, 0, 0.4)),
    "fin_alto": ((24.5, -0.44, 15.6), (1.5, 0, 0.8)),
    "fin_pie": ((24.5, -0.44, 2.75), (1.5, 0, 0.4)),
    # puntos libres
    "roseton": ((12.2, -0.4, 12.5), (3, 0.3, 3)),
    "cornisa_izq": ((10.0, 0.2, 9.0), (3, 0.7, 3)),
    "cornisa_der": ((15.0, 0.2, 9.0), (3, 0.7, 3)),
    "puerta_clave": ((12.5, -0.2, 6.5), (3, 0.8, 3)),
    "puerta_arr_izq": ((11.5, -0.2, 5.0), (3, 0.8, 3)),
    "puerta_arr_der": ((13.5, -0.2, 5.0), (3, 0.8, 3)),
    "puerta_pie_izq": ((11.5, -0.2, 2.4), (3, 0.8, 0.5)),
    "puerta_pie_der": ((13.5, -0.2, 2.4), (3, 0.8, 0.5)),
    "cuerpo_pie_izq": ((10.0, 0.0, 2.35), (3, 0.6, 0.5)),
    "cuerpo_pie_der": ((15.2, 0.0, 2.45), (3, 0.6, 0.5)),
    "b1_rep_izq": ((7.6, 0.4, 13.0), (2, 0.8, 4)),
    "b1_rep_der": ((8.8, 0.4, 13.0), (2, 0.8, 4)),
    "b1_alto_izq": ((7.6, 0.3, 17.5), (2, 0.8, 3)),
    "b1_alto_der": ((8.8, 0.3, 17.5), (2, 0.8, 3)),
    "b1_pie_izq": ((7.6, 0.5, 2.15), (2, 0.8, 0.5)),
    "b1_pie_der": ((8.8, 0.5, 2.15), (2, 0.8, 0.5)),
}
# ventanas de la torre: marco en el paramento (d = 0)
for nombre, z, s in (("vs", 10.5, 3.5), ("vi", 5.0, 3.0)):
    for esquina, ds, dz in (("ai", -0.5, 0.6), ("ad", 0.5, 0.6), ("bi", -0.5, -0.6), ("bd", 0.5, -0.6)):
        PUNTOS[f"{nombre}_{esquina}"] = ((s + ds, 0.0, z + dz), (3, 0.04, 3))
PUNTOS["saet1"] = ((1.0, 0.0, 12.0), (2, 0.04, 4))
PUNTOS["saet2"] = ((0.8, 0.0, 9.0), (2, 0.04, 4))

# --- observaciones: foto -> punto: (x, y, sigma en px) --------------------------
OBS = {
    "184905": {
        "c1_izq": (105, 645, 10), "c2_izq": (152, 411, 10),
        "c3_izq": (227, 100, 20),
        "roseton": (1164, 1080, 6), "cornisa_izq": (942, 1313, 8),
        "b1_alto_izq": (717, 667, 10), "b1_alto_der": (803, 673, 10),
        "b1_rep_izq": (706, 915, 8), "b1_rep_der": (809, 923, 8),
        "vs_ai": (430, 1088, 7), "vs_ad": (548, 1093, 7), "vs_bi": (415, 1231, 7), "vs_bd": (542, 1243, 7),
        "vi_ai": (290, 1780, 8), "vi_ad": (420, 1779, 8), "vi_bi": (265, 1916, 8), "vi_bd": (408, 1921, 8),
        "saet1": (208, 853, 6), "saet2": (157, 1120, 6),
    },
    "184908": {
        "c1_izq": None,
        "roseton": (1092, 536, 5), "cornisa_izq": (848, 779, 7), "cornisa_der": (1425, 794, 7),
        "puerta_clave": (1115, 1109, 7), "puerta_arr_izq": (1015, 1243, 9), "puerta_arr_der": (1219, 1243, 9),
        "puerta_pie_izq": (1029, 1559, 10), "puerta_pie_der": (1220, 1558, 10),
        "cuerpo_pie_izq": (880, 1604, 12), "cuerpo_pie_der": (1445, 1576, 12),
        "b1_alto_izq": (628, 30, 9), "b1_alto_der": (732, 40, 9),
        "b1_rep_izq": (619, 342, 7), "b1_rep_der": (730, 353, 7),
        "b1_pie_izq": (596, 1624, 10), "b1_pie_der": (706, 1622, 10),
        "vs_ai": (323, 525, 6), "vs_ad": (451, 533, 6), "vs_bi": (317, 683, 6), "vs_bd": (448, 693, 6),
        "vi_ai": (222, 1187, 8), "vi_ad": (348, 1189, 8), "vi_bi": (210, 1301, 8), "vi_bd": (343, 1306, 8),
        "saet1": (65, 246, 6), "saet2": (38, 550, 6),
    },
    "184911": {
        "b2_muro_pie": (877, 1605, 10), "b2_izq_pie": (929, 1609, 10), "b2_der_pie": (1010, 1605, 10),
        "b2_izq_alto": (921, 300, 10), "b2_der_alto": (979, 312, 10),
        "muro_b2_izq": (868, 293, 12),
        "fin_alto": (1354, 658, 15), "fin_pie": (1367, 1542, 15),
        "roseton": (528, 607, 5), "cornisa_izq": (265, 812, 7), "cornisa_der": (808, 887, 7),
        "puerta_clave": (515, 1165, 7), "puerta_arr_izq": (404, 1291, 9), "puerta_arr_der": (594, 1297, 9),
        "puerta_pie_izq": (392, 1622, 10), "puerta_pie_der": (580, 1612, 10),
        "cuerpo_pie_izq": (236, 1678, 14), "cuerpo_pie_der": (781, 1624, 12),
        "b1_alto_izq": (79, 18, 14), "b1_alto_der": (193, 52, 14),
        "b1_rep_izq": (40, 323, 12), "b1_rep_der": (167, 357, 12),
    },
}
for obs in OBS.values():
    for k in [k for k, v in obs.items() if v is None]:
        del obs[k]
INICIO = {"184905": (4.0, 11.0, 3.8, 0.0, 0.65, 0.0),
          "184908": (9.0, 13.0, 3.8, 0.0, 0.35, 0.0),
          "184911": (6.0, 14.0, 3.9, 0.45, 0.35, 0.0)}
FOTOS = list(OBS)
NOMBRES = list(PUNTOS)
LIBRES = [(i, k) for i, n in enumerate(NOMBRES) for k in range(3) if PUNTOS[n][1][k] > 0]
BASE = np.array([PUNTOS[n][0] for n in NOMBRES], float)


def ejes(giro, cabeceo, alabeo):
    f = np.array([np.sin(giro) * np.cos(cabeceo), -np.cos(giro) * np.cos(cabeceo), np.sin(cabeceo)])
    r0 = np.array([np.cos(giro), np.sin(giro), 0.0])
    u0 = np.array([-np.sin(giro) * np.sin(cabeceo), np.cos(giro) * np.sin(cabeceo), np.cos(cabeceo)])
    return (np.cos(alabeo) * r0 + np.sin(alabeo) * u0,
            -np.sin(alabeo) * r0 + np.cos(alabeo) * u0, f)


def proyectar(cam, puntos, focal):
    r, u, f = ejes(*cam[3:6])
    v = np.atleast_2d(puntos) - cam[:3]
    z = v @ f
    return np.stack([CX + focal * (v @ r) / z, CY - focal * (v @ u) / z], axis=1)


def separar(x):
    focal = x[0]
    camaras = x[1:1 + 6 * len(FOTOS)].reshape(-1, 6)
    puntos = BASE.copy()
    for (i, k), val in zip(LIBRES, x[1 + 6 * len(FOTOS):]):
        puntos[i, k] = val
    return focal, camaras, puntos


def residuos(x):
    focal, camaras, puntos = separar(x)
    r = [(focal - FOCAL_EXIF) / 40.0]
    for j, foto in enumerate(FOTOS):
        nombres = list(OBS[foto])
        datos = np.array([OBS[foto][n] for n in nombres], float)
        px = proyectar(camaras[j], puntos[[NOMBRES.index(n) for n in nombres]], focal)
        r.extend(((px - datos[:, :2]) / datos[:, 2:3]).ravel())
        r.append((camaras[j, 2] - 3.9) / 0.6)            # camara a la altura de la mano
        r.append(camaras[j, 5] / np.radians(3.0))        # casi nivelada
    for (i, k) in LIBRES:
        r.append((puntos[i, k] - BASE[i, k]) / PUNTOS[NOMBRES[i]][1][k])

    def p(n):
        return puntos[NOMBRES.index(n)]

    # piezas que deben compartir plano o cota
    for a, b, eje, sigma in (
            ("cornisa_izq", "cornisa_der", 1, 0.05), ("cornisa_izq", "cornisa_der", 2, 0.06),
            ("puerta_arr_izq", "puerta_arr_der", 1, 0.05), ("puerta_arr_izq", "puerta_arr_der", 2, 0.05),
            ("puerta_pie_izq", "puerta_pie_der", 1, 0.05), ("puerta_arr_izq", "puerta_pie_izq", 1, 0.05),
            ("puerta_arr_izq", "puerta_pie_izq", 0, 0.06), ("puerta_arr_der", "puerta_pie_der", 0, 0.06),
            ("puerta_clave", "puerta_arr_izq", 1, 0.08), ("cuerpo_pie_izq", "cuerpo_pie_der", 1, 0.08),
            ("b1_rep_izq", "b1_rep_der", 1, 0.08), ("b1_rep_izq", "b1_rep_der", 2, 0.06),
            ("b1_alto_izq", "b1_alto_der", 1, 0.08), ("b1_alto_izq", "b1_alto_der", 2, 0.06),
            ("b1_pie_izq", "b1_pie_der", 1, 0.08), ("b1_pie_izq", "b1_rep_izq", 0, 0.25),
            ("b1_pie_der", "b1_rep_der", 0, 0.25), ("b1_alto_izq", "b1_rep_izq", 0, 0.15),
            ("fin_pie", "fin_alto", 0, 0.3)):
        r.append((p(a)[eje] - p(b)[eje]) / sigma)
    r.append(((p("puerta_clave")[0]) - (p("puerta_arr_izq")[0] + p("puerta_arr_der")[0]) / 2) / 0.12)
    for v in ("vs", "vi"):
        for a, b, eje in (("ai", "ad", 2), ("bi", "bd", 2), ("ai", "bi", 0), ("ad", "bd", 0)):
            r.append((p(f"{v}_{a}")[eje] - p(f"{v}_{b}")[eje]) / 0.06)
    return np.array(r)


def robusto(x):
    """Perdida de Cauchy: un punto mal marcado no arrastra al resto."""
    r = residuos(x)
    return np.sign(r) * np.sqrt(4.0 * np.log1p(r * r / 4.0))


def ajustar(x):
    lam = 1e-2
    r = robusto(x)
    for _ in range(300):
        J = np.empty((len(r), len(x)))
        for k in range(len(x)):
            h = np.zeros_like(x)
            h[k] = 1e-6 * max(1.0, abs(x[k]))
            J[:, k] = (robusto(x + h) - r) / h[k]
        A, g = J.T @ J, J.T @ r
        while True:
            paso = np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), -g)
            r2 = robusto(x + paso)
            if r2 @ r2 < r @ r:
                break
            lam *= 4
            if lam > 1e10:
                return x
        mejora = r @ r - r2 @ r2
        x, r, lam = x + paso, r2, max(lam / 3, 1e-6)
        if mejora < 1e-7:
            break
    return x


x0 = np.concatenate([[FOCAL_EXIF], np.ravel([INICIO[f] for f in FOTOS]),
                     [BASE[i, k] for i, k in LIBRES]])
x = ajustar(x0)
focal, camaras, puntos = separar(x)

print(f"focal {focal:.0f} px (EXIF {FOCAL_EXIF:.0f})")
salida = {"focal_px": round(float(focal), 1), "camaras": {}, "puntos": {}, "error_px": {}}
for j, foto in enumerate(FOTOS):
    salida["camaras"][foto] = [round(float(v), 4) for v in camaras[j]]
    errores = {}
    for n, (px, py, _) in OBS[foto].items():
        q = proyectar(camaras[j], puntos[NOMBRES.index(n)], focal)[0]
        errores[n] = (round(float(q[0] - px)), round(float(q[1] - py)))
    mods = np.hypot(*np.array(list(errores.values())).T)
    salida["error_px"][foto] = {"mediana": round(float(np.median(mods)), 1),
                               "maximo": round(float(mods.max()), 1), "puntos": errores}
    print(foto, "camara", np.round(camaras[j], 2), "error mediano", salida["error_px"][foto]["mediana"],
          "max", salida["error_px"][foto]["maximo"])
    for n, e in errores.items():
        if np.hypot(*e) > 18:
            print("   ", n, e)
for n, p in zip(NOMBRES, puntos):
    salida["puntos"][n] = [round(float(v), 3) for v in p]
    print(f"{n:16s}", np.round(p, 2))


def sobre_plano(foto, pixel, d):
    """Punto (s, z) donde el rayo de un pixel corta el plano a distancia d."""
    j = FOTOS.index(foto)
    r, u, f = ejes(*camaras[j, 3:6])
    v = f + r * (pixel[0] - CX) / focal - u * (pixel[1] - CY) / focal
    t = (d - camaras[j, 1]) / v[1]
    q = camaras[j, :3] + v * t
    return [round(float(q[0]), 3), round(float(q[2]), 3)]


def P(n):
    return np.array(salida["puntos"][n])


# --- medidas por retroproyeccion sobre los planos ajustados ---------------------
d_cuerpo = float((P("cornisa_izq")[1] + P("cornisa_der")[1]) / 2)
d_puerta = float(P("puerta_clave")[1])
d_ros = float(P("roseton")[1])
d_frente = float((P("cuerpo_pie_izq")[1] + P("cuerpo_pie_der")[1]) / 2)
M = {"planos_d": {"cornisa_canto": round(d_cuerpo, 3), "puerta": round(d_puerta, 3),
                  "roseton": round(d_ros, 3), "frente_cuerpo": round(d_frente, 3)}}
muro = -0.37
M["roseton"] = {
    "centro": sobre_plano("184908", (1092, 536), muro),
    "vidrio_izq": sobre_plano("184908", (1031, 536), muro), "vidrio_der": sobre_plano("184908", (1155, 536), muro),
    "vidrio_alto": sobre_plano("184908", (1092, 477), muro), "vidrio_bajo": sobre_plano("184908", (1092, 594), muro),
    "orla_izq": sobre_plano("184908", (992, 530), muro), "orla_der": sobre_plano("184908", (1217, 530), muro),
    "orla_alto": sobre_plano("184908", (1102, 411), muro), "orla_bajo": sobre_plano("184908", (1108, 627), muro),
}
M["portada"] = {
    "cuerpo_izq": sobre_plano("184908", (878, 1000), d_frente),
    "cuerpo_der": sobre_plano("184908", (1396, 1000), d_frente),
    "cornisa_izq": sobre_plano("184908", (848, 779), d_cuerpo),
    "cornisa_der": sobre_plano("184908", (1425, 794), d_cuerpo),
    "cornisa_bajo": sobre_plano("184908", (1140, 806), d_cuerpo),
    "arco_ext_izq": sobre_plano("184908", (908, 1215), d_frente),
    "arco_ext_der": sobre_plano("184908", (1400, 1215), d_frente),
    "arco_ext_clave": sobre_plano("184908", (1150, 962), d_frente),
    "puerta_izq": sobre_plano("184908", (1015, 1400), d_puerta),
    "puerta_der": sobre_plano("184908", (1220, 1400), d_puerta),
    "puerta_arranque": sobre_plano("184908", (1015, 1243), d_puerta),
    "puerta_clave": sobre_plano("184908", (1115, 1109), d_puerta),
    "puerta_pie": sobre_plano("184908", (1125, 1559), d_puerta),
    "canecillos_x": [sobre_plano("184908", (x, 812), d_cuerpo)[0]
                     for x in (873, 896, 978, 1067, 1155, 1232, 1305, 1380)],
}
d_b1 = float((P("b1_rep_izq")[1] + P("b1_rep_der")[1]) / 2)
M["b1"] = {
    "repisa_izq": sobre_plano("184908", (622, 350), d_b1), "repisa_der": sobre_plano("184908", (727, 360), d_b1),
    "alto": sobre_plano("184908", (680, 34), d_b1),
    "pie_izq": sobre_plano("184908", (596, 1624), float(P("b1_pie_izq")[1])),
    "pie_der": sobre_plano("184908", (706, 1622), float(P("b1_pie_der")[1])),
    "medio_izq": sobre_plano("184908", (612, 900), d_b1), "medio_der": sobre_plano("184908", (718, 900), d_b1),
}


def caja(foto, x0, y0, x1, y1, d=0.0):
    a, b = sobre_plano(foto, (x0, y0), d), sobre_plano(foto, (x1, y1), d)
    return {"s0": a[0], "s1": b[0], "z0": b[1], "z1": a[1]}


M["torre"] = {
    "ventana_alta_marco": caja("184908", 320, 529, 449, 688),
    "ventana_alta_vano": caja("184908", 358, 589, 417, 667),
    "ventana_baja_marco": caja("184908", 214, 1188, 345, 1303),
    "ventana_baja_vano": caja("184908", 250, 1222, 296, 1280),
    "saetera1": caja("184908", 55, 227, 76, 266),
    "saetera2": caja("184908", 27, 531, 49, 571),
    "moldura_zocalo": sobre_plano("184908", (300, 1140), 0.05),
    "saetera3": caja("184905", 289, 345, 301, 361),
    "saetera4": caja("184905", 267, 489, 280, 507),
    "saetera5": caja("184905", 241, 635, 258, 655),
    "campanario": caja("184905", 441, 203, 586, 373),
    "balaustrada": caja("184905", 433, 389, 576, 445),
    "medallon": caja("184905", 396, 496, 522, 592),
}
M["muro"] = {
    "alero_junto_b1": sobre_plano("184908", (762, 52), -0.41),
    "alero_junto_b2": sobre_plano("184908", (1440, 112), -0.28),
}
salida["medidas"] = M
(RAIZ / "referencias" / "medidas_suroeste.json").write_text(
    json.dumps(salida, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps(M, indent=1))
