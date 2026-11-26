"""Intervencion 11: cristalera en la ventana en arco de la cara noroeste de la torre.

Pedida por Jorge. En su foto 184811 esa ventana se ve cegada, sin vidrio: es una
decision suya, no un dato. Solo cambia el material y las UV del fondo de la
ventana (Concatedral_torre_ventana_ciega_fondo); no mueve vertices. La imagen del
vidrio emplomado se genera por codigo.

Parte del .blend de la intervencion 10: lo copia a blender/copias/santa_maria_i10.blend
y siempre trabaja desde esa copia.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/i11_cristalera_torre.py
"""
import math
import shutil
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

RAIZ = Path(__file__).resolve().parents[1]
BLEND = RAIZ / "blender" / "santa_maria.blend"
COPIA = RAIZ / "blender" / "copias" / "santa_maria_i10.blend"
PNG = RAIZ / "texturas" / "concatedral" / "cristalera_torre_color.png"
RENDERS = RAIZ / "renders" / "i11_cristalera"
OBJETO = "Concatedral_torre_ventana_ciega_fondo"
PPM = 520                      # pixeles por metro de la imagen


def datos_ventana(o):
    """Eje horizontal del pano, extremos y normal exterior."""
    nm = o.matrix_world.to_3x3().inverted_safe().transposed()
    n = (nm @ o.data.polygons[0].normal).normalized()
    if n.xy.dot(Vector((-0.69, 0.72))) < 0:
        n = -n
    t = Vector((-n.y, n.x, 0)).normalized()      # derecha de quien mira de frente
    pts = [o.matrix_world @ v.co for v in o.data.vertices]
    s = [p.dot(t) for p in pts]
    z = [p.z for p in pts]
    centro = sum(pts, Vector()) / len(pts)
    return t, n, min(s), max(s), min(z), max(z), centro


def imagen(ancho_m, alto_m):
    """Vidrio emplomado azul, fila 0 abajo, en sRGB."""
    w, h = round(ancho_m * PPM), round(alto_m * PPM)
    x = (np.arange(w) + 0.5) / PPM - ancho_m / 2      # m desde el eje
    y = (np.arange(h) + 0.5) / PPM                     # m desde el antepecho
    X, Y = np.meshgrid(x, y)
    r = ancho_m / 2
    arranque = alto_m - r
    # Distancia hacia dentro desde el contorno (jambas, antepecho y medio punto).
    radial = np.hypot(X, Y - arranque)
    lado = np.where(Y > arranque, r - radial, r - np.abs(X))
    borde = np.minimum(lado, Y)
    marco, filete, plomo = 0.065, 0.011, 0.007
    rng = np.random.default_rng(1229)
    base = np.array([30, 66, 122]) / 255.0
    tonos = np.array([[24, 52, 104], [36, 80, 140], [30, 66, 122], [48, 96, 148],
                      [28, 74, 112]]) / 255.0

    # Paños interiores: tres columnas e hiladas de 0,17 m, alternadas a media altura.
    interior = ancho_m - 2 * marco
    col = np.clip(((X + interior / 2) / (interior / 3)).astype(int), 0, 2)
    desfase = np.where(col == 1, 0.085, 0.0)
    fila = ((Y - marco + desfase) / 0.17).astype(int)
    elegidos = rng.integers(0, len(tonos), (40, 3))
    color = tonos[elegidos[np.clip(fila, 0, 39), col]]
    en_plomo = np.zeros_like(X, bool)
    for borde_col in (-interior / 6, interior / 6):
        en_plomo |= np.abs(X - borde_col) < plomo
    resto = np.mod(Y - marco + desfase, 0.17)
    en_plomo |= (resto < plomo) | (resto > 0.17 - plomo)
    # Orla exterior de piezas ambar.
    orla = borde < marco
    tramo = np.where(Y > arranque, (np.arctan2(Y - arranque, X) * r / 0.14).astype(int),
                     (Y / 0.14).astype(int))
    ambar = np.array([[150, 96, 34], [128, 76, 30], [168, 118, 46]]) / 255.0
    color = np.where(orla[..., None], ambar[np.mod(tramo, 3)], color)
    paso = np.where(Y > arranque, np.mod(np.arctan2(Y - arranque, X) * r, 0.14), np.mod(Y, 0.14))
    en_plomo = np.where(orla, paso < 2 * plomo, en_plomo)
    en_plomo |= np.abs(borde - marco) < filete
    # Roseta en la cabeza del arco.
    d = np.hypot(X, Y - arranque)
    roseta = d < 0.12
    angulo = np.arctan2(Y - arranque, X)
    petalo = (np.floor(np.mod(angulo, 2 * math.pi) / (math.pi / 4)).astype(int)) % 2
    color = np.where(roseta[..., None], np.where(petalo[..., None] == 0, ambar[2], tonos[3]), color)
    giro = np.mod(angulo, math.pi / 4)
    en_plomo = np.where(roseta, (np.minimum(giro, math.pi / 4 - giro) * d < plomo) | (np.abs(d - 0.045) < plomo),
                        en_plomo)
    en_plomo |= np.abs(d - 0.12) < filete
    color = np.where((roseta & (d < 0.045))[..., None], np.array([140, 40, 32]) / 255.0, color)
    en_plomo |= borde < 0.012
    grano = 1.0 + 0.10 * rng.normal(0, 1, (h, w))
    suave = grano
    for eje in (0, 1):
        suave = (suave + np.roll(suave, 3, eje) + np.roll(suave, -3, eje)) / 3
    color = np.clip(color * suave[..., None], 0, 1)
    color = np.where(en_plomo[..., None], np.array([34, 31, 28]) / 255.0, color)
    return color.astype(np.float32)


def renderizar(nombre):
    escena = bpy.context.scene
    t, n, s0, s1, z0, z1, centro = datos_ventana(escena.objects[OBJETO])
    RENDERS.mkdir(parents=True, exist_ok=True)
    sol = escena.objects["Sol_base"]
    sol.rotation_euler = (n + t * 0.5 + Vector((0, 0, 1.0))).normalized().to_track_quat("Z", "Y").to_euler()
    for sufijo, distancia, focal, subir in (("cerca", 9.0, 70.0, 0.0), ("torre", 30.0, 45.0, 5.0)):
        datos = bpy.data.cameras.new(sufijo)
        datos.lens, datos.sensor_width = focal, 36.0
        cam = bpy.data.objects.new(sufijo, datos)
        escena.collection.objects.link(cam)
        mira = centro + Vector((0, 0, subir))
        cam.location = centro + n * distancia + t * (distancia * 0.12) - Vector((0, 0, distancia * 0.28))
        cam.rotation_euler = (mira - cam.location).to_track_quat("-Z", "Y").to_euler()
        escena.camera = cam
        escena.render.resolution_x, escena.render.resolution_y = 1400, 1400
        escena.render.resolution_percentage = 100
        escena.cycles.samples = 48
        escena.render.filepath = str(RENDERS / f"{nombre}_{sufijo}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", escena.render.filepath)


if not COPIA.exists():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    assert bpy.context.scene.get("intervencion") == 10, "el maestro no es el de la intervencion 10"
    shutil.copy2(BLEND, COPIA)
if not (RENDERS / "antes_cerca.png").exists():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    assert bpy.context.scene.get("intervencion") == 10, "no se puede sacar el 'antes'"
    renderizar("antes")

# El maestro de partida es identico a la copia: se abre el maestro para que las
# rutas relativas de las texturas sigan siendo validas.
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
if bpy.context.scene.get("intervencion") != 10:
    shutil.copy2(COPIA, BLEND)
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
escena = bpy.context.scene
assert escena.get("intervencion") == 10


def geometria():
    return {o.name: [tuple(v.co) for v in o.data.vertices] for o in escena.objects if o.type == "MESH"}


antes = geometria()
o = escena.objects[OBJETO]
t, n, s0, s1, z0, z1, _ = datos_ventana(o)
datos = imagen(s1 - s0, z1 - z0)
alto, ancho = datos.shape[:2]
img = bpy.data.images.new("cristalera_torre_color", ancho, alto, alpha=False)
rgba = np.ones((alto, ancho, 4), np.float32)
rgba[..., :3] = datos
img.pixels.foreach_set(rgba.ravel())
img.filepath_raw = str(PNG)
img.file_format = "PNG"
img.save()
bpy.data.images.remove(img)
img = bpy.data.images.load(str(PNG))
img.name = "cristalera_torre_color"
img.filepath = "//../texturas/concatedral/cristalera_torre_color.png"

mat = bpy.data.materials.new("Cristalera_torre_NO")
mat.use_nodes = True
arbol = mat.node_tree
bsdf = arbol.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.6          # como los vidrios de la nave
bsdf.inputs["Specular IOR Level"].default_value = 0.15
uv = arbol.nodes.new("ShaderNodeUVMap")
uv.uv_map = "UVMap"
tex = arbol.nodes.new("ShaderNodeTexImage")
tex.image, tex.extension = img, "EXTEND"
arbol.links.new(uv.outputs[0], tex.inputs[0])
arbol.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
mat["textura"] = "vidrio emplomado generado por codigo (herramientas/i11_cristalera_torre.py)"

me = o.data
capa = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
capa = me.uv_layers["UVMap"]
for cara in me.polygons:
    for li in cara.loop_indices:
        p = o.matrix_world @ me.vertices[me.loops[li].vertex_index].co
        capa.data[li].uv = ((p.dot(t) - s0) / (s1 - s0), (p.z - z0) / (z1 - z0))
me.materials.clear()
me.materials.append(mat)
o["origen"] = o["origen"] + "; cristalera en la intervencion 11"
o["provisional"] = "cristalera inventada a peticion de Jorge: en la foto 184811 la ventana esta cegada"
assert antes == geometria(), "la intervencion no debe mover vertices"
print("VIDRIO ancho", round(s1 - s0, 3), "alto", round(z1 - z0, 3), "cota", round(z0, 2), round(z1, 2))

escena["intervencion"] = 11
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True, relative_remap=False)
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
for i in bpy.data.images:
    if i.filepath.startswith("//"):
        assert Path(bpy.path.abspath(i.filepath)).exists(), i.filepath
renderizar("despues")
