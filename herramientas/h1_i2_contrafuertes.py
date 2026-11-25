"""H1, intervencion 2: contrafuertes y remates de la fachada noroeste.

Parte del .blend de la intervencion 1: lo copia a blender/copias/santa_maria_i1.blend
y siempre trabaja desde esa copia. Posiciones del levantamiento (registro 1688);
anchos, alturas de remate y repisas medidos sobre la foto con
h1_medir_contrafuertes.py. Ver referencias/medidas_fachada_noroeste.md.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/h1_i2_contrafuertes.py
    ... -- --sin-render
"""
import json
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector

RAIZ = Path(__file__).resolve().parents[1]
BLEND = RAIZ / "blender" / "santa_maria.blend"
COPIA = RAIZ / "blender" / "copias" / "santa_maria_i1.blend"
DESPUES = RAIZ / "renders" / "h1_i2_despues"
SIN_RENDER = "--sin-render" in sys.argv

registro = json.loads((RAIZ / "datos" / "locales" / "santa_maria_dxf_local.json")
                      .read_text(encoding="utf-8"))["/mnt/data/work/trama urbana_2012_3D.dxf"][1688]
P = [Vector((p[0], p[1], p[2] - 440.0)) for p in registro[2]]

if not COPIA.exists():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    assert bpy.context.scene.get("intervencion") == 1, "el maestro no es el de la intervencion 1"
    shutil.copy2(BLEND, COPIA)
bpy.ops.wm.open_mainfile(filepath=str(COPIA))
escena = bpy.context.scene

# Eje del muro: s crece desde la torre (punto 67) hacia la cabecera; d sale a la plaza.
A = P[67].xy
T = (P[58].xy - A).normalized()
N = Vector((-T.y, T.x))
if N.dot(Vector((-0.69, 0.72))) < 0:
    N = -N

col = bpy.data.collections["Concatedral"]
muro = bpy.data.objects["Concatedral_fachadas"]
material = muro.data.materials[0]
nombre_capa = muro.data.color_attributes[0].name
color = tuple(muro.data.color_attributes[0].data[0].color)
terreno = bpy.data.objects["Terreno_interpolado"]


def en_mundo(s, d, z):
    q = A + T * s + N * d
    return Vector((q.x, q.y, z))


def suelo(s, d):
    q = en_mundo(s, d, 200.0)
    inv = terreno.matrix_world.inverted()
    abajo = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
    ok, golpe, *_ = terreno.ray_cast(inv @ q, abajo)
    assert ok, (s, d)
    return (terreno.matrix_world @ golpe).z


def caja(nombre, s0, s1, d0, d1, z0, z1, origen, supuesto):
    """Prisma cerrado alineado con el muro, con las normales hacia fuera."""
    v = [en_mundo(s, d, z) for z in (z0, z1) for s, d in ((s0, d0), (s1, d0), (s1, d1), (s0, d1))]
    centro = sum(v, Vector()) / 8.0
    caras = []
    for f in ([0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]):
        a, b, c = v[f[0]], v[f[1]], v[f[2]]
        medio = sum((v[i] for i in f), Vector()) / 4.0
        if (b - a).cross(c - a).dot(medio - centro) < 0:
            f = f[::-1]
        caras.append(f)
    me = bpy.data.meshes.new("Concatedral_" + nombre)
    # Vertices propios por cara, como el resto del modelo.
    verts, tris = [], []
    for f in caras:
        n = len(verts)
        verts.extend(v[i] for i in f)
        tris.extend([[n, n + 1, n + 2], [n, n + 2, n + 3]])
    me.from_pydata(verts, [], tris)
    me.update()
    capa = me.color_attributes.new(nombre_capa, "BYTE_COLOR", "POINT")
    for dato in capa.data:
        dato.color = color
    me.materials.append(material)
    o = bpy.data.objects.new(me.name, me)
    col.objects.link(o)
    o["origen"] = "H1 intervencion 2; " + origen
    o["provisional"] = supuesto
    return o


nuevos = []
ANCHO = 0.90          # contrafuertes y remates: 0,84 a 0,99 m en la foto
ALTO_REMATE = 1.65    # sobre el pretil: 1,58 a 1,70 m en la foto
LOSA = 0.18

# --- B2: cuerpo bajo algo mas saliente y repisa (el alto ya esta en los muros) -------
repisa_b2 = suelo(18.6, 1.2) + 0.321 * (15.10 - suelo(18.6, 1.2))
base = min(suelo(18.0, 1.0), suelo(19.25, 1.0)) - 0.1
nuevos.append(caja("contrafuerte_B2_pie", 18.0, 19.25, 0.0, 1.00, base, repisa_b2 - 0.20,
                   "planta del DXF; altura de repisa de la foto", "saliente extra 0,12 m a ojo"))
nuevos.append(caja("contrafuerte_B2_repisa", 17.93, 19.32, 0.0, 1.10, repisa_b2 - 0.20, repisa_b2,
                   "foto", "grueso y vuelo estimados; sin las dos cabezas talladas"))

# --- B3: del remate del escalon al pretil, con una repisa intermedia -----------------
escalon = P[60].z
s1_b3 = 12.98
repisa_b3 = suelo(12.5, 1.1) + 0.774 * (14.90 - suelo(12.5, 1.1))
assert escalon < repisa_b3 < 14.9
nuevos.append(caja("contrafuerte_B3_bajo", s1_b3 - ANCHO, s1_b3, 0.0, 0.96, escalon - 0.6,
                   repisa_b3, "extremo del escalon (DXF 59-60); foto",
                   "se supone enrasado con el frente del escalon"))
nuevos.append(caja("contrafuerte_B3_alto", s1_b3 - ANCHO, s1_b3, 0.0, 0.80, repisa_b3, 14.90,
                   "foto", "retranqueo de 0,16 m a ojo"))

# --- B4: sobre la cornisa de la portada ----------------------------------------------
s1_b4, d_b4 = 7.14, 1.25
nuevos.append(caja("contrafuerte_B4", s1_b4 - ANCHO, s1_b4, 0.0, d_b4, P[63].z - 0.05, P[62].z,
                   "punto 62 del DXF (esquina y cota); ancho de la foto",
                   "fondo apoyado en el muro principal"))

# --- Remates --------------------------------------------------------------------------
REMATES = {  # nombre: (centro s, cota del pretil, nota)
    "B1": (22.75, P[51].z, "no se ve en la foto medida; visto en Concatedral 02"),
    "B2": (18.60, P[55].z, "centro del contrafuerte del DXF"),
    "B3": (s1_b3 - ANCHO / 2, 14.90, "sobre B3"),
    "B4": (s1_b4 - ANCHO / 2, P[62].z, "sobre B4"),
    "B5": (0.38, P[65].z, "centro del contrafuerte del DXF"),
}
d1 = 0.10
for nombre, (s, pretil, nota) in REMATES.items():
    s0, s1 = s - ANCHO / 2, s + ANCHO / 2
    cima = pretil + ALTO_REMATE
    nuevos.append(caja(f"remate_{nombre}", s0, s1, d1 - ANCHO, d1, pretil - 1.0, cima - LOSA,
                       nota, "planta cuadrada y posicion en profundidad supuestas"))
    nuevos.append(caja(f"remate_{nombre}_losa", s0 - 0.09, s1 + 0.09, d1 - ANCHO - 0.09,
                       d1 + 0.09, cima - LOSA, cima, "foto",
                       "losa plana; sin la inclinacion ni la figura que la corona"))

# --- Contrafuertes inventados de v0.3 en esta fachada ---------------------------------
ocultos = bpy.data.collections["Concatedral_v03_ocultos"]
for n in (0, 1):
    o = bpy.data.objects[f"Concatedral_contrafuerte_{n}"]
    for c in list(o.users_collection):
        c.objects.unlink(o)
    ocultos.objects.link(o)
    o.hide_viewport = o.hide_render = True
    o["motivo_oculto"] = "no coincide con ningun contrafuerte del levantamiento ni de las fotos"

escena["intervencion"] = 2
escena.camera = bpy.data.objects["CAM_general"]
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)

DESPUES.mkdir(parents=True, exist_ok=True)
informe = {
    "objetos_nuevos": [o.name for o in nuevos],
    "ocultos": ["Concatedral_contrafuerte_0", "Concatedral_contrafuerte_1"],
    "repisa_B2_z": round(repisa_b2, 2), "repisa_B3_z": round(repisa_b3, 2),
    "caras_degeneradas": [o.name for o in nuevos if any(f.area < 1e-6 for f in o.data.polygons)],
}
(DESPUES / "informe.json").write_text(json.dumps(informe, indent=2), encoding="utf-8")
print("INFORME", json.dumps(informe))
if not SIN_RENDER:
    for nombre in ("CAM_general", "CAM_peaton_noroeste", "CAM_peaton_oeste_torre",
                   "CAM_inspeccion_suroeste"):
        escena.camera = bpy.data.objects[nombre]
        escena.render.filepath = str(DESPUES / f"{nombre}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", escena.render.filepath)
