"""H1, intervencion 7: texturas de las fotos de Jorge en la concatedral.

Parte del .blend de la intervencion 6: lo copia a blender/copias/santa_maria_i6.blend
y siempre trabaja desde esa copia. Escribe las texturas en texturas/concatedral/,
enlazadas con ruta relativa. No cambia ningun vertice.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/h1_i7_foto.py
    ... -- --prueba        solo texturas y renders pequenos, sin guardar el maestro
    ... -- --sin-render
"""
import json
import shutil
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import texturas_foto as tf  # noqa: E402
from silleria import normales  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
BLEND = RAIZ / "blender" / "santa_maria.blend"
COPIA = RAIZ / "blender" / "copias" / "santa_maria_i6.blend"
PRUEBA = "--prueba" in sys.argv
SIN_RENDER = "--sin-render" in sys.argv
TEXTURAS = (RAIZ / "renders" / "h1_i7_prueba") if PRUEBA else (RAIZ / "texturas" / "concatedral")
ANTES = RAIZ / "renders" / "h1_i7_antes"
DESPUES = RAIZ / "renders" / ("h1_i7_prueba" if PRUEBA else "h1_i7_despues")
CAMARAS = ("CAM_calle_NO", "CAM_portada", "CAM_torre", "CAM_foto")


def camara_calle():
    """La vista noroeste de render_calle.py, recreada desde su registro."""
    r = json.loads((RAIZ / "renders" / "calle" / "registro.json").read_text(encoding="utf-8"))
    v = r["vistas"]["NO"]
    datos = bpy.data.cameras.new("CAM_calle_NO")
    datos.lens, datos.sensor_width, datos.sensor_fit = v["focal_mm"], r["sensor_mm"], "HORIZONTAL"
    datos.shift_y = v["desplazamiento_y"]
    cam = bpy.data.objects.new("CAM_calle_NO", datos)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = v["posicion"]
    a = np.radians(v["rumbo_grados"])
    cam.rotation_euler = Vector((np.sin(a), np.cos(a), 0)).to_track_quat("-Z", "Y").to_euler()


def renderizar(carpeta):
    escena = bpy.context.scene
    camara_calle()
    carpeta.mkdir(parents=True, exist_ok=True)
    sol = escena.objects["Sol_base"]
    sol_base = sol.rotation_euler.copy()
    for nombre in CAMARAS:
        if nombre not in escena.objects:
            continue
        escena.camera = escena.objects[nombre]
        sol.rotation_euler = sol_base
        ancho, alto = {"CAM_foto": (2000, 1328), "CAM_calle_NO": (2000, 1500)}.get(nombre, (1600, 1000))
        if nombre == "CAM_calle_NO":
            mira = escena.camera.rotation_euler.to_matrix() @ Vector((0, 0, -1))
            rumbo = np.arctan2(-mira.x, -mira.y) + np.radians(35)
            desde = Vector((np.sin(rumbo), np.cos(rumbo), 1.0)).normalized()
            sol.rotation_euler = desde.to_track_quat("Z", "Y").to_euler()
        escena.render.resolution_x, escena.render.resolution_y = ancho, alto
        escena.render.resolution_percentage = 40 if PRUEBA else 100
        escena.cycles.samples = 16 if PRUEBA else 48
        escena.render.filepath = str(carpeta / f"{nombre}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", escena.render.filepath)


if not COPIA.exists():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    assert bpy.context.scene.get("intervencion") == 6, "el maestro no es el de la intervencion 6"
    shutil.copy2(BLEND, COPIA)
if not (PRUEBA or SIN_RENDER) and not ANTES.exists():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    assert bpy.context.scene.get("intervencion") == 6, "no se puede sacar el 'antes'"
    renderizar(ANTES)
bpy.ops.wm.open_mainfile(filepath=str(COPIA))
escena = bpy.context.scene
geometria_antes = {o.name: [tuple(v.co) for v in o.data.vertices]
                   for o in escena.objects if o.type == "MESH"}

# --- texturas -----------------------------------------------------------------
TEXTURAS.mkdir(parents=True, exist_ok=True)


def guardar(nombre, datos, es_color=True):
    """datos con la fila 0 arriba."""
    alto, ancho = datos.shape[:2]
    img = bpy.data.images.new(nombre, ancho, alto, alpha=False)
    if not es_color:
        img.colorspace_settings.name = "Non-Color"
    rgba = np.ones((alto, ancho, 4), np.float32)
    rgba[..., :3] = datos[::-1]
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = str(TEXTURAS / f"{nombre}.png")
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    img = bpy.data.images.load(str(TEXTURAS / f"{nombre}.png"))
    img.name = nombre
    if not es_color:
        img.colorspace_settings.name = "Non-Color"
    if not PRUEBA:
        img.filepath = f"//../texturas/concatedral/{nombre}.png"
    return img


color, relieve, muestreo = tf.silleria()
img_color = guardar("silleria_foto_color", color)
# normales() espera la fila 0 abajo.
img_normal = guardar("silleria_foto_normal", normales(relieve[::-1])[::-1], False)
img_liso = guardar("granito_foto_color", tf.granito_liso())
img_puerta = guardar("puerta_NO_foto", tf.puerta())
img_medallon = guardar("medallon_NO_foto", tf.medallon())

# --- silleria: mismas UV, solo cambian las imagenes ----------------------------
silleria = bpy.data.materials["Granito_silleria_concatedral"]
for nodo in silleria.node_tree.nodes:
    if nodo.type == "TEX_IMAGE":
        nodo.image = img_normal if nodo.image.name.endswith("_normal") else img_color
silleria["textura"] = "despiece generado; grano y tonos de fotos de referencias/fotos_jorge"
for nombre in ("silleria_dorada_color", "silleria_dorada_normal"):
    bpy.data.images.remove(bpy.data.images[nombre])


def material(nombre, imagen, rugosidad, origen):
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    arbol = mat.node_tree
    bsdf = arbol.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rugosidad
    uv = arbol.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    tex = arbol.nodes.new("ShaderNodeTexImage")
    tex.image = imagen
    if nombre != "Granito_liso_concatedral":
        tex.extension = "EXTEND"
    arbol.links.new(uv.outputs[0], tex.inputs[0])
    arbol.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    mat["textura"] = origen
    return mat


def poner(o, mat, uv_de):
    """uv_de(cara, puntos en mundo) -> lista de (u, v)."""
    me = o.data
    if "UVMap" not in me.uv_layers:
        me.uv_layers.new(name="UVMap")
    capa = me.uv_layers["UVMap"]
    for cara in me.polygons:
        pts = [o.matrix_world @ me.vertices[me.loops[i].vertex_index].co for i in cara.loop_indices]
        for li, uv in zip(cara.loop_indices, uv_de(cara, pts)):
            capa.data[li].uv = uv
    me.uv_layers.active = capa
    me.materials.clear()
    me.materials.append(mat)


def caja(cara, pts):
    n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
    n = n.normalized() if n.length > 1e-12 else Vector((0, 0, 1))
    t = Vector((-n.y, n.x, 0.0))
    if t.length > 0.3:
        return [(p.dot(t.normalized()) / 3.2, p.z / 3.2) for p in pts]
    return [(p.x / 3.2, p.y / 3.2) for p in pts]


liso = material("Granito_liso_concatedral", img_liso, 0.9, "grano de foto propia")
lisos = [o for o in escena.objects if o.type == "MESH" and o.name != "Concatedral_torre_medallon"
         and any(m and m.name == "Granito_liso_provisional" for m in o.data.materials)]
for o in lisos:
    assert len(o.data.materials) == 1, o.name
    poner(o, liso, caja)

# Normal exterior de la fachada noroeste (la misma que usan las intervenciones).
P = [Vector((p[0], p[1], p[2] - 440.0)) for p in json.loads(
    (RAIZ / "datos" / "locales" / "santa_maria_dxf_local.json").read_text(encoding="utf-8"))
    ["/mnt/data/work/trama urbana_2012_3D.dxf"][1688][2]]
T = (P[58].xy - P[67].xy).normalized()
N = Vector((-T.y, T.x))
if N.dot(Vector((-0.69, 0.72))) < 0:
    N = -N
DERECHA = Vector((-N.y, N.x, 0.0))  # derecha de quien mira la fachada de frente

# Puertas: cada hoja (un cuadrilatero) recibe la imagen completa.
puertas = escena.objects["Concatedral_portada_puertas"]
mundo = [puertas.matrix_world @ v.co for v in puertas.data.vertices]
s = [p.dot(DERECHA) for p in mundo]
medio = (min(s) + max(s)) / 2.0
hojas = {}
for lado in (False, True):
    pts = [p for p in mundo if (p.dot(DERECHA) > medio) == lado]
    hs = [p.dot(DERECHA) for p in pts]
    hojas[lado] = (min(hs), max(hs), min(p.z for p in pts), max(p.z for p in pts))


def uv_puerta(cara, pts):
    lado = sum(p.dot(DERECHA) for p in pts) / len(pts) > medio
    s0, s1, z0, z1 = hojas[lado]
    return [((p.dot(DERECHA) - s0) / (s1 - s0), (p.z - z0) / (z1 - z0)) for p in pts]


poner(puertas, material("Puerta_foto_NO", img_puerta, 0.75, "foto propia 20261125_184811"), uv_puerta)

med = escena.objects["Concatedral_torre_medallon"]
mundo = [med.matrix_world @ v.co for v in med.data.vertices]
z0, z1 = min(p.z for p in mundo), max(p.z for p in mundo)
s0, s1 = min(p.dot(DERECHA) for p in mundo), max(p.dot(DERECHA) for p in mundo)
radio = (z1 - z0) / 2.0
sc = (s0 + s1) / 2.0
poner(med, material("Medallon_foto_NO", img_medallon, 0.9, "foto propia 20261125_184811"),
      lambda cara, pts: [(0.5 + (p.dot(DERECHA) - sc) / (2 * radio),
                          0.5 + (p.z - (z0 + z1) / 2) / (2 * radio)) for p in pts])

geometria_despues = {o.name: [tuple(v.co) for v in o.data.vertices]
                     for o in escena.objects if o.type == "MESH"}
assert geometria_antes == geometria_despues, "la intervencion no debe mover vertices"
informe = {"muestreo": muestreo, "objetos_granito_liso": sorted(o.name for o in lisos),
           "puertas_ancho_alto_m": [[round(h[1] - h[0], 2), round(h[3] - h[2], 2)] for h in hojas.values()],
           "medallon_diametro_m": round(2 * radio, 2), "vertices_modificados": 0}
print("INFORME", json.dumps(informe))

escena["intervencion"] = 7
escena.camera = bpy.data.objects["CAM_general"]
if not PRUEBA:
    # Sin remapeo: las rutas "//../texturas" ya estan escritas respecto a blender/.
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True, relative_remap=False)
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    escena = bpy.context.scene
    imagenes = {}
    for nombre in ("silleria_foto_color", "silleria_foto_normal", "granito_foto_color",
                   "puerta_NO_foto", "medallon_NO_foto"):
        img = bpy.data.images[nombre]
        imagenes[nombre] = {"ruta": img.filepath, "tamano": list(img.size),
                            "existe": Path(bpy.path.abspath(img.filepath)).exists()}
        assert (img.filepath.startswith("//") and imagenes[nombre]["existe"]
                and img.size[0] > 0), imagenes[nombre]
    informe["texturas"] = imagenes
    DESPUES.mkdir(parents=True, exist_ok=True)
    (DESPUES / "informe.json").write_text(json.dumps(informe, indent=2), encoding="utf-8")
if not SIN_RENDER:
    renderizar(DESPUES)
