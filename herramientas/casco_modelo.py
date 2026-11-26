"""Casco antiguo: amplia la maqueta con relieve y cubiertas LiDAR y la renderiza desde arriba.

Abre blender/santa_maria.blend (no lo modifica) y guarda blender/santa_maria_casco.blend.
Dentro del recorte de la maqueta se conserva la maqueta; fuera, volumetria medida sin fachadas.
Requiere datos/locales/casco_lidar.npz (herramientas/casco_datos.py).

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/casco_modelo.py
"""
import json
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

RAIZ = Path(__file__).resolve().parents[1]
MAESTRO = RAIZ / "blender" / "santa_maria.blend"
DESTINO = RAIZ / "blender" / "santa_maria_casco.blend"
DATOS = RAIZ / "datos" / "locales" / "casco_lidar.npz"
SALIDA = RAIZ / "renders" / "casco"
ORIGEN_E, ORIGEN_N = 726189.9868201963, 4372743.045037453
SALTO = 1.2        # m: mayor diferencia entre celdas vecinas que se considera la misma cubierta
PX_POR_M = 6

bpy.ops.wm.open_mainfile(filepath=str(MAESTRO))
escena = bpy.context.scene
d = np.load(DATOS)
cubierta, suelo = d["cubierta"].astype(float), d["suelo"].astype(float)
e0, n0, ancho, alto = d["ventana"]
celda, celda_s = d["celdas"]
x0, y1 = e0 - ORIGEN_E, n0 + alto - ORIGEN_N       # esquina noroeste en coordenadas de la maqueta


def cota_suelo(x, y):
    f = np.clip((y1 - y) / celda_s, 0, suelo.shape[0] - 1.000001)
    c = np.clip((x - x0) / celda_s, 0, suelo.shape[1] - 1.000001)
    i, j = int(f), int(c)
    u, v = c - j, f - i
    return float((suelo[i, j] * (1 - u) + suelo[i, j + 1] * u) * (1 - v)
                 + (suelo[i + 1, j] * (1 - u) + suelo[i + 1, j + 1] * u) * v)


# --- maqueta existente: recorte de edificios y terreno ------------------------
propios = [o for o in escena.objects if o.type == "MESH" and not o.hide_render
           and not o.name.startswith("Terreno")]
pts = [o.matrix_world @ Vector(c) for o in propios for c in o.bound_box]
caja = (min(p.x for p in pts), min(p.y for p in pts), max(p.x for p in pts), max(p.y for p in pts))
terreno = bpy.data.objects["Terreno_interpolado"]
inv = terreno.matrix_world.inverted()


def cota_maqueta(x, y):
    ok, p, _, _ = terreno.ray_cast(inv @ Vector((x, y, 300.0)),
                                   (inv.to_3x3() @ Vector((0, 0, -1))).normalized())
    return (terreno.matrix_world @ p).z if ok else None


# --- materiales con el color medio de la maqueta ------------------------------
def color_medio(obj):
    capa = obj.data.color_attributes[0]
    return np.mean([list(e.color)[:3] for e in capa.data], axis=0)


def material(nombre, rgb):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*[float(v) for v in rgb], 1.0)
    b.inputs["Roughness"].default_value = 0.92
    return m


edificios = [o for o in propios if o.name.startswith("Edificio") and o.data.color_attributes]
mat_cub = material("Casco_cubierta_LiDAR", np.mean([color_medio(o) for o in edificios], axis=0))
mat_muro = material("Casco_muro_LiDAR", np.mean([color_medio(o) for o in edificios], axis=0) * 0.7)
mat_suelo = material("Casco_suelo_MDT", color_medio(terreno))

col = bpy.data.collections.new("Casco_antiguo_LiDAR")
escena.collection.children.link(col)


def crear(nombre, verts, caras, mats, indices):
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(verts, [], caras)
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", np.array(indices, np.int32))
    me.update()
    o = bpy.data.objects.new(nombre, me)
    col.objects.link(o)
    return o


# --- terreno ------------------------------------------------------------------
nf, nc = suelo.shape
verts = [(x0 + j * celda_s, y1 - i * celda_s, float(suelo[i, j])) for i in range(nf) for j in range(nc)]
cubierto = np.zeros(suelo.shape, bool)
diferencias = []
for i in range(nf):
    for j in range(nc):
        x, y, z = verts[i * nc + j]
        if abs(x) < 85 and abs(y) < 85:
            zm = cota_maqueta(x, y)
            if zm is not None:
                cubierto[i, j] = True
                diferencias.append(zm - z)
caras = []
for i in range(nf - 1):
    for j in range(nc - 1):
        if cubierto[i:i + 2, j:j + 2].all():
            continue
        a = i * nc + j
        caras.append((a, a + nc, a + nc + 1, a + 1))
crear("Casco_terreno_MDT02", verts, caras, [mat_suelo], [0] * len(caras))

# --- cubiertas y muros --------------------------------------------------------
filas, cols = cubierta.shape
hay = ~np.isnan(cubierta)
for i, j in zip(*np.nonzero(hay)):
    x, y = x0 + (j + 0.5) * celda, y1 - (i + 0.5) * celda
    if caja[0] <= x <= caja[2] and caja[1] <= y <= caja[3]:
        hay[i, j] = False

verts, caras, indices = [], [], []
esquina = {}      # (fila, col de la celda, fila, col de la esquina) -> vertice


def vertice(p):
    verts.append(p)
    return len(verts) - 1


# En cada esquina las celdas vecinas de altura parecida comparten vertice (faldon continuo).
for ci in range(filas + 1):
    for cj in range(cols + 1):
        vec = [(float(cubierta[i, j]), i, j) for i in (ci - 1, ci) for j in (cj - 1, cj)
               if 0 <= i < filas and 0 <= j < cols and hay[i, j]]
        if not vec:
            continue
        vec.sort()
        grupos = [[vec[0]]]
        for v in vec[1:]:
            if v[0] - grupos[-1][-1][0] > SALTO:
                grupos.append([])
            grupos[-1].append(v)
        for g in grupos:
            n = vertice((x0 + cj * celda, y1 - ci * celda, sum(v[0] for v in g) / len(g)))
            for _, i, j in g:
                esquina[i, j, ci, cj] = n

bases = {}


def base(ci, cj):
    if (ci, cj) not in bases:
        x, y = x0 + cj * celda, y1 - ci * celda
        bases[ci, cj] = vertice((x, y, cota_suelo(x, y) - 0.4))
    return bases[ci, cj]


def muro(a, b, c, e):
    cara = []
    for v in (a, b, c, e):
        if v not in cara:
            cara.append(v)
    if len(cara) > 2:
        caras.append(tuple(cara))
        indices.append(1)


for i, j in zip(*np.nonzero(hay)):
    i, j = int(i), int(j)
    nw, sw = esquina[i, j, i, j], esquina[i, j, i + 1, j]
    se, ne = esquina[i, j, i + 1, j + 1], esquina[i, j, i, j + 1]
    caras.append((nw, sw, se, ne))
    indices.append(0)
    # (celda vecina, extremos de la arista en sentido antihorario visto desde arriba)
    for (vi, vj), p, q in (((i, j - 1), (i, j), (i + 1, j)), ((i + 1, j), (i + 1, j), (i + 1, j + 1)),
                           ((i, j + 1), (i + 1, j + 1), (i, j + 1)), ((i - 1, j), (i, j + 1), (i, j))):
        a, b = esquina[i, j, p[0], p[1]], esquina[i, j, q[0], q[1]]
        if 0 <= vi < filas and 0 <= vj < cols and hay[vi, vj]:
            c, e = esquina[vi, vj, p[0], p[1]], esquina[vi, vj, q[0], q[1]]
            # solo la celda mas alta levanta el muro compartido
            if verts[a][2] + verts[b][2] > verts[c][2] + verts[e][2]:
                muro(a, c, e, b)
        else:
            muro(a, base(*p), base(*q), b)
crear("Casco_edificios_LiDAR", verts, caras, [mat_cub, mat_muro], indices)

# --- guardar y renderizar -----------------------------------------------------
cam_d = bpy.data.cameras.new("CAM_casco_cenital")
cam_d.type, cam_d.ortho_scale, cam_d.clip_end = "ORTHO", float(max(ancho, alto)), 2000.0
cam = bpy.data.objects.new("CAM_casco_cenital", cam_d)
bpy.data.collections["Camaras_y_luz"].objects.link(cam)
cam.location = (x0 + ancho / 2, y1 - alto / 2, 400.0)
escena.camera = cam
escena.render.resolution_x, escena.render.resolution_y = int(ancho * PX_POR_M), int(alto * PX_POR_M)
escena.render.resolution_percentage = 100
bpy.ops.wm.save_as_mainfile(filepath=str(DESTINO), compress=True, relative_remap=False)

SALIDA.mkdir(parents=True, exist_ok=True)
dif = np.array(diferencias)
informe = {
    "ventana_epsg25829": [e0, n0, e0 + ancho, n0 + alto],
    "recorte_maqueta_xy": [round(v, 2) for v in caja],
    "celdas_edificio_fuera_de_la_maqueta": int(hay.sum()),
    "cota_maqueta_menos_MDT02_m": {"mediana": round(float(np.median(dif)), 2),
                                   "p10": round(float(np.percentile(dif, 10)), 2),
                                   "p90": round(float(np.percentile(dif, 90)), 2),
                                   "muestras": int(dif.size)},
}
(SALIDA / "informe.json").write_text(json.dumps(informe, indent=2), encoding="utf-8")
print("INFORME", json.dumps(informe))
escena.render.filepath = str(SALIDA / "CAM_casco_cenital.png")
bpy.ops.render.render(write_still=True)
print("RENDER", escena.render.filepath)
