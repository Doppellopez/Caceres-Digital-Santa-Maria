"""H1: contrasta la concatedral v0.3 con el contorno 3D del levantamiento municipal.

Solo lectura: abre el .blend, mide, dibuja una planta y NO guarda el .blend.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/h1_medicion_noroeste.py
"""
import json
from pathlib import Path

import bpy
from mathutils import Vector

RAIZ = Path(__file__).resolve().parents[1]
BLEND = RAIZ / "blender" / "santa_maria.blend"
DXF = RAIZ / "datos" / "locales" / "santa_maria_dxf_local.json"
SALIDA = RAIZ / "renders" / "h1_medicion"
COTA_REF = 440.0
CONTORNO = 1688  # POLYLINE 'Edificio singular' de la concatedral
# Eje de la fachada noroeste: de la esquina de la torre hacia la cabecera.
A = Vector((5.3, -7.3))
B = Vector((31.14, 17.32))

registros = json.loads(DXF.read_text(encoding="utf-8"))
registro = registros["/mnt/data/work/trama urbana_2012_3D.dxf"][CONTORNO]
puntos = [(p[0], p[1], p[2] - COTA_REF) for p in registro[2]]
assert registro[1] == "Edificio singular" and max(p[2] for p in puntos) > 27

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
escena = bpy.context.scene
terreno = bpy.data.objects["Terreno_interpolado"]
eje = (B - A).normalized()
fuera = Vector((-eje.y, eje.x))


def suelo(x, y):
    # ray_cast trabaja en coordenadas locales y el objeto importado esta rotado.
    inv = terreno.matrix_world.inverted()
    direccion = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
    ok, p, _, _ = terreno.ray_cast(inv @ Vector((x, y, 200.0)), direccion)
    return (terreno.matrix_world @ p).z if ok else None


print("EJE largo", round((B - A).length, 2))
for i, (x, y, z) in enumerate(puntos):
    r = Vector((x, y)) - A
    u, v = r.dot(eje), r.dot(fuera)
    if -1.0 <= u <= (B - A).length + 0.5 and v > -2.0:
        q = Vector((x, y)) + fuera * 1.0
        s = suelo(q.x, q.y)
        alto = "sin terreno" if s is None else f"suelo={s:5.2f} altura={z - s:6.2f}"
        print(f"PTO {i:3d} u={u:6.2f} saliente={v:5.2f} cota={z:6.2f} {alto}")

torre = bpy.data.objects["Concatedral_torre_cubierta"]
vs = [torre.matrix_world @ v.co for v in torre.data.vertices]
centro = sum(vs, Vector()) / len(vs)
rel = Vector((centro.x, centro.y)) - A
print("TORRE_v03 centro", [round(c, 2) for c in centro], "u", round(rel.dot(eje), 2),
      "saliente", round(rel.dot(fuera), 2), "vertices",
      [[round(c, 2) for c in v] for v in vs])


def emisor(nombre, color):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    arbol = m.node_tree
    arbol.nodes.clear()
    e = arbol.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1.0)
    s = arbol.nodes.new("ShaderNodeOutputMaterial")
    arbol.links.new(e.outputs[0], s.inputs[0])
    return m


def linea(nombre, pts, material, grosor, z):
    c = bpy.data.curves.new(nombre, "CURVE")
    c.dimensions = "3D"
    c.bevel_depth = grosor
    t = c.splines.new("POLY")
    t.points.add(len(pts) - 1)
    for k, (x, y, _) in enumerate(pts):
        t.points[k].co = (x, y, z, 1.0)
    c.materials.append(material)
    o = bpy.data.objects.new(nombre, c)
    escena.collection.objects.link(o)


for o in list(escena.objects):
    if o.type == "MESH" and not o.name.startswith("Concatedral"):
        o.hide_render = True
gris = emisor("m_modelo", (0.45, 0.45, 0.45))
azul = emisor("m_torre_modelo", (0.02, 0.18, 0.8))
for o in escena.objects:
    if o.type == "MESH" and o.name.startswith("Concatedral"):
        o.data.materials.clear()
        o.data.materials.append(azul if "torre" in o.name else gris)
negro = emisor("m_contorno", (0.0, 0.0, 0.0))
rojo = emisor("m_torre_dato", (0.8, 0.02, 0.01))
linea("contorno", puntos + [puntos[0]], negro, 0.09, 40.0)
altos = [i for i, p in enumerate(puntos) if p[2] > 27]
linea("torre_dato", puntos[altos[0]:altos[-1] + 1], rojo, 0.28, 41.0)

escena.world.node_tree.nodes["Background"].inputs["Color"].default_value = (1, 1, 1, 1)
escena.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
datos = bpy.data.cameras.new("CAM_planta")
datos.type = "ORTHO"
datos.ortho_scale = 52.0
cam = bpy.data.objects.new("CAM_planta", datos)
escena.collection.objects.link(cam)
cam.location = (26.0, -2.0, 120.0)
escena.camera = cam
escena.render.resolution_x, escena.render.resolution_y = 1100, 1250
escena.cycles.samples = 8
SALIDA.mkdir(parents=True, exist_ok=True)
escena.render.filepath = str(SALIDA / "planta_torre.png")
bpy.ops.render.render(write_still=True)
