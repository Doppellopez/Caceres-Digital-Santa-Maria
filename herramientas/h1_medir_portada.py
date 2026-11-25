"""H1: mide la portada sobre la foto y guarda las medidas para la intervencion 3.

La camara se ajusta con la torre y los cuatro remates visibles (ningun punto de la
portada, salvo las dos anclas que se declaran abajo). Foto "Santa Maria,
Caceres.JPG", Jesusccastillo, CC BY-SA 3.0 ES. Pixeles marcados a ojo sobre la
foto reducida a 2000 px de ancho.

Anclas: el eje de las escaleras del DXF (capa 'Escalera') fija la posicion a lo
largo del muro, suponiendo que el arco esta centrado con ellas como se ve en la
foto; el suelo y la cornisa (cota 12,54 del DXF) fijan las alturas.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/h1_medir_portada.py
"""
import json
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
TRAMA = json.loads((RAIZ / "datos" / "locales" / "santa_maria_dxf_local.json")
                   .read_text(encoding="utf-8"))["/mnt/data/work/trama urbana_2012_3D.dxf"]
P = np.array([[p[0], p[1], p[2] - 440.0] for p in TRAMA[1688][2]])
SALIDA = RAIZ / "referencias" / "medidas_portada.json"

ANCHO, ALTO, FPX = 2000, 1328, 27 / 36.0 * 2000
A = P[67, :2]
T = (P[58, :2] - A) / np.linalg.norm(P[58, :2] - A)
N = np.array([-T[1], T[0]])
SUELO_MODELO = 1.5


def en_mundo(s, d, z):
    return np.array([*(A + T * s + N * d), z])


def a_muro(p):
    r = p[:2] - A
    return float(r @ T), float(r @ N)


AJUSTE = [((5.11, -7.17, 27.77), (1627, 117)), ((10.33, -2.19, 27.77), (1362, 108)),
          ((5.11, -7.32, 1.74), (1748, 1270)),
          (en_mundo(18.60, 0.1, 15.18), (314, 534)), (en_mundo(12.53, 0.1, 14.90), (613, 541)),
          (en_mundo(6.69, 0.1, 14.70), (907, 552)), (en_mundo(0.38, 0.1, 15.05), (1211, 566))]


def ejes(g, c, a):
    f = np.array([np.cos(c) * np.cos(g), np.cos(c) * np.sin(g), np.sin(c)])
    r0 = np.cross(f, [0, 0, 1.0])
    r0 /= np.linalg.norm(r0)
    u0 = np.cross(r0, f)
    return np.cos(a) * r0 + np.sin(a) * u0, -np.sin(a) * r0 + np.cos(a) * u0, f


def proyectar(par, pts):
    r, u, f = ejes(*par[3:6])
    v = np.asarray(pts, float) - par[:3]
    z = v @ f
    return np.stack([ANCHO / 2 + FPX * (v @ r) / z, ALTO / 2 - FPX * (v @ u) / z], axis=-1)


def residuos(p):
    e = (proyectar(p, [x[0] for x in AJUSTE]) - [x[1] for x in AJUSTE]).ravel() / 8.0
    return np.concatenate([e, [(p[2] - 3.05) / 0.5, p[5] / np.radians(2.0)]])


def ajustar():
    mejor = None
    for dist in (18.0, 25.0, 35.0):
        c = np.array([15.9 - 0.69 * dist, 3.0 + 0.72 * dist, 3.05])
        m = np.array([13.0, 0.0, 11.0]) - c
        p = np.array([*c, np.arctan2(m[1], m[0]), np.arctan2(m[2], np.hypot(*m[:2])), 0.0])
        lam = 1.0
        for _ in range(400):
            r = residuos(p)
            J = np.stack([(residuos(p + e) - r) / 1e-6 for e in np.eye(6) * 1e-6], axis=1)
            paso = np.linalg.solve(J.T @ J + lam * np.eye(6), -J.T @ r)
            if np.sum(residuos(p + paso) ** 2) < np.sum(r ** 2):
                p, lam = p + paso, lam / 3
            else:
                lam *= 5
        coste = np.sum(residuos(p) ** 2)
        if mejor is None or coste < mejor[0]:
            mejor = (coste, p)
    return mejor[1]


PAR = ajustar()


def retro(px, py, d):
    r, u, f = ejes(*PAR[3:6])
    rayo = f + (px - ANCHO / 2) / FPX * r - (py - ALTO / 2) / FPX * u
    t = (d - (PAR[:2] - A) @ N) / (rayo[:2] @ N)
    q = PAR[:3] + t * rayo
    return a_muro(q)[0], float(q[2])


frente = [a_muro(P[i])[1] for i in (62, 63, 64)]
D_FRENTE = float(np.mean(frente))
COTA_CORNISA = float(P[63, 2])

# Puntos de las escaleras situados ante la portada.
ESCALERA = []
for registro in TRAMA:
    if registro[1] != "Escalera":
        continue
    for p in registro[2]:
        s, d = a_muro(np.array(p[:2]))
        if -1.0 <= s <= 9.0 and 0.5 <= d <= 2.0:
            ESCALERA.append((round(s, 2), round(d, 2), round(p[2] - 440.0, 2)))
ESCALERA = sorted(set(ESCALERA))
assert len(ESCALERA) >= 6
EJE_ESCALERA = float(np.mean([e[0] for e in ESCALERA]))
centro_foto = np.mean([retro(862, 995, D_FRENTE)[0], retro(1255, 998, D_FRENTE)[0]])
corr_s = EJE_ESCALERA - centro_foto
_, z_suelo = retro(1060, 1295, D_FRENTE)
_, z_cornisa = retro(1070, 660, D_FRENTE)


def medir(px, py, d=D_FRENTE):
    s, z = retro(px, py, d)
    zm = SUELO_MODELO + (z - z_suelo) / (z_cornisa - z_suelo) * (COTA_CORNISA - SUELO_MODELO)
    return s + corr_s, zm


# Profundidad del abocinado: el centro del arco interior y el del exterior, a la
# altura del arranque, deben caer en la misma s.
s_ext = medir(1058.5, 995)[0]
profundidades = np.arange(0.0, 2.01, 0.01)
errores = [abs(medir(1053, 1015, D_FRENTE - k)[0] - s_ext) for k in profundidades]
prof_foto = float(profundidades[int(np.argmin(errores))])
# Esa estimacion es muy debil (unos 10 px por metro: +-0,5 m). Se toma 1,0 m como
# supuesto, compatible con seis arquivoltas y sin atravesar el muro principal.
prof = 1.0
d_fondo = D_FRENTE - prof

medidas = {
    "frente_d": D_FRENTE, "frente_d_puntos": frente, "s_izquierda": medir(851, 900)[0],
    "s_derecha": medir(1288, 900)[0], "cornisa_z": COTA_CORNISA,
    "eje_escalera": EJE_ESCALERA, "escalera_dxf": [list(e) for e in ESCALERA],
    "profundidad_estimada_foto": prof_foto, "profundidad_usada": prof,
    "arco_exterior": {"s_izq": medir(862, 995)[0], "s_der": medir(1255, 998)[0],
                      "z_arranque": medir(1058.5, 996)[1], "z_clave": medir(1065, 773)[1]},
    "arco_interior": {"s_izq": medir(959, 1015, d_fondo)[0], "s_der": medir(1147, 1017, d_fondo)[0],
                      "z_arranque": medir(1053, 1014, d_fondo)[1],
                      "z_clave": medir(1054, 886, d_fondo)[1]},
    "puertas": {"s": [medir(x, 1140, d_fondo)[0] for x in (956, 1039, 1066, 1146)],
                "z_suelo": medir(1050, 1268, d_fondo)[1], "z_dintel": medir(1050, 1017, d_fondo)[1]},
    "peldanos": {"s_izq": medir(872, 1285)[0], "s_der": medir(1256, 1285)[0],
                 "z_alto": medir(1060, 1270)[1]},
    "cornisa_grueso": medir(1070, 660)[1] - medir(1070, 670)[1],
    "canecillos_s": [medir(x, 678)[0] for x in
                     (858, 890, 942, 992, 1038, 1078, 1127, 1179, 1210, 1245, 1277)],
    "camara_par": PAR.tolist(),
    "camara_error_px": np.linalg.norm(
        proyectar(PAR, [x[0] for x in AJUSTE]) - [x[1] for x in AJUSTE], axis=1).round(1).tolist(),
    "correccion_s": corr_s,
}


def redondear(v):
    if isinstance(v, dict):
        return {k: redondear(x) for k, x in v.items()}
    if isinstance(v, list):
        return [redondear(x) for x in v]
    return round(v, 4)


SALIDA.write_text(json.dumps(redondear(medidas), indent=2), encoding="utf-8")
for k, v in redondear(medidas).items():
    print("MEDIDA", k, v)
