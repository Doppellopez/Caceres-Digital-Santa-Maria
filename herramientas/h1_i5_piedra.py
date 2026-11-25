"""H1, intervencion 5: aplica al maestro la silleria generada (elegida por Jorge).

Parte del .blend de la intervencion 4: lo copia a blender/copias/santa_maria_i4.blend
y siempre trabaja desde esa copia. Escribe las texturas en texturas/concatedral/,
enlazadas con ruta relativa. No cambia ningun vertice.

UV en metros (una repeticion = 6,4 x 3,2 m): paramentos con hiladas horizontales;
en arquivoltas, juntas radiales como dovelas.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/h1_i5_piedra.py
    ... -- --sin-render
"""
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from silleria import ALTO_M, ANCHO_M, PALETAS, generar, normales  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
BLEND = RAIZ / "blender" / "santa_maria.blend"
COPIA = RAIZ / "blender" / "copias" / "santa_maria_i4.blend"
TEXTURAS = RAIZ / "texturas" / "concatedral"
REF = RAIZ / "referencias"
DESPUES = RAIZ / "renders" / "h1_i5_despues"
SIN_RENDER = "--sin-render" in sys.argv
PIEZAS = ("fachadas", "torre_interior", "contrafuerte", "cuerpo", "remate", "ventana",
          "portada_rebaje", "portada_cornisa", "portada_canecillos", "portada_peldanos")

if not COPIA.exists():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    assert bpy.context.scene.get("intervencion") == 4, "el maestro no es el de la intervencion 4"
    shutil.copy2(BLEND, COPIA)
bpy.ops.wm.open_mainfile(filepath=str(COPIA))
escena = bpy.context.scene
geometria_antes = {o.name: [tuple(v.co) for v in o.data.vertices]
                   for o in escena.objects if o.type == "MESH"}

# --- texturas -----------------------------------------------------------------
TEXTURAS.mkdir(parents=True, exist_ok=True)
color, relieve = generar(PALETAS["dorada"])


def guardar(nombre, datos, es_color):
    alto, ancho = datos.shape[:2]
    img = bpy.data.images.new(nombre, ancho, alto, alpha=False)
    if not es_color:
        img.colorspace_settings.name = "Non-Color"
    rgba = np.ones((alto, ancho, 4), np.float32)
    rgba[..., :3] = datos
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = str(TEXTURAS / f"{nombre}.png")
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    img = bpy.data.images.load(str(TEXTURAS / f"{nombre}.png"))
    img.name = nombre
    if not es_color:
        img.colorspace_settings.name = "Non-Color"
    img.filepath = f"//../texturas/concatedral/{nombre}.png"
    return img


img_color = guardar("silleria_dorada_color", color, True)
img_normal = guardar("silleria_dorada_normal", normales(relieve), False)

# --- material -------------------------------------------------------------------
mat = bpy.data.materials.new("Granito_silleria_concatedral")
mat.use_nodes = True
arbol = mat.node_tree
bsdf = arbol.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.92
uv = arbol.nodes.new("ShaderNodeUVMap")
uv.uv_map = "UVMap"
tc = arbol.nodes.new("ShaderNodeTexImage")
tc.image = img_color
tn = arbol.nodes.new("ShaderNodeTexImage")
tn.image = img_normal
mapa = arbol.nodes.new("ShaderNodeNormalMap")
mapa.uv_map = "UVMap"
arbol.links.new(uv.outputs[0], tc.inputs[0])
arbol.links.new(uv.outputs[0], tn.inputs[0])
arbol.links.new(tn.outputs["Color"], mapa.inputs["Color"])
arbol.links.new(mapa.outputs[0], bsdf.inputs["Normal"])
arbol.links.new(tc.outputs["Color"], bsdf.inputs["Base Color"])
mat["textura"] = "generada por herramientas/silleria.py; no es la piedra real"

# El vidrio liso reflejaba el sol y desde algunos angulos parecia un hueco.
for nombre in ("Vidrio_azul_provisional", "Vidrio_oscuro_provisional"):
    vidrio = bpy.data.materials[nombre].node_tree.nodes["Principled BSDF"]
    vidrio.inputs["Roughness"].default_value = 0.6
    vidrio.inputs["Specular IOR Level"].default_value = 0.15

# --- arcos: donde las juntas deben ser radiales ---------------------------------
P = [Vector((p[0], p[1], p[2] - 440.0)) for p in json.loads(
    (RAIZ / "datos" / "locales" / "santa_maria_dxf_local.json").read_text(encoding="utf-8"))
    ["/mnt/data/work/trama urbana_2012_3D.dxf"][1688][2]]
A = P[67].xy
T = (P[58].xy - A).normalized()
N = Vector((-T.y, T.x))
if N.dot(Vector((-0.69, 0.72))) < 0:
    N = -N
M = json.loads((REF / "medidas_portada.json").read_text(encoding="utf-8"))
V = json.loads((REF / "medidas_ventanas.json").read_text(encoding="utf-8"))
ext, inte = M["arco_exterior"], M["arco_interior"]
a_ext = (ext["s_izq"] - ext["s_der"]) / 2.0
a_int = (inte["s_izq"] - inte["s_der"]) / 2.0
arranque = (inte["z_arranque"] + M["puertas"]["z_dintel"]) / 2.0
centro = (a_ext ** 2 + (ext["z_clave"] - arranque) ** 2) / (2 * a_ext) - a_ext

# objeto: (eje s, arranque, desplazamiento de los centros, radio menor, radio mayor,
#          d a partir de la cual es paramento y no arco)
ARCOS = {"Concatedral_cuerpo_portada": (M["eje_escalera"], arranque, centro,
                                        a_int + centro, a_ext + centro, M["frente_d"] - 0.005)}
for nombre, v in V.items():
    a0, av = v["semiancho"], v["semiancho_vidrio"]
    if v["tipo"] == "medio_punto":
        datos = (v["s"], v["clave_z"] - a0, 0.0, av, a0)
    else:
        datos = (v["s"], v["clave_z"] - math.sqrt(3.0) * a0, a0, av + a0, 2 * a0)
    ARCOS[f"Concatedral_ventana_{nombre}"] = (*datos, None)


def polar(punto, arco, lado=None):
    """(radio, angulo desde el arranque) respecto al centro del lado indicado.

    El lado se decide por cara, no por vertice, para no deformar las de la clave.
    """
    eje, z0, c, *_ = arco
    r = punto.xy - A
    x, z = r.dot(T) - eje, punto.z - z0
    if lado is None:
        lado = 1 if x > 0 else -1
    dx = c + lado * x
    angulo = math.atan2(z, dx)
    if lado > 0:
        angulo = math.pi - angulo          # el arco sigue hacia el otro arranque
    return math.hypot(dx, z), angulo


def uv_objeto(o):
    me = o.data
    capa = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    capa = me.uv_layers["UVMap"]
    mw = o.matrix_world
    arco = ARCOS.get(o.name)
    dovelas = 0
    for cara in me.polygons:
        pts = [mw @ me.vertices[me.loops[i].vertex_index].co for i in cara.loop_indices]
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        n = n.normalized() if n.length > 1e-12 else Vector((0, 0, 1))
        es_arco = False
        if arco:
            _, z0, c, r_min, r_max, d_frente = arco
            medio = sum(pts, Vector()) / len(pts)
            rel = medio.xy - A
            radio, _ = polar(medio, arco)
            es_arco = (medio.z > z0 + 0.01 and r_min - 0.03 <= radio <= r_max + 0.03
                       and (d_frente is None or rel.dot(N) < d_frente))
        if es_arco:
            dovelas += 1
            lado = 1 if (medio.xy - A).dot(T) > arco[0] else -1
            for li, p in zip(cara.loop_indices, pts):
                radio, angulo = polar(p, arco, lado)
                # Hiladas de la textura siguiendo el arco = juntas radiales. En u se
                # suma el fondo: en las coronas varia el radio y en los intrados, d.
                fondo = (p.xy - A).dot(N)
                capa.data[li].uv = ((radio + fondo) / ANCHO_M, angulo * arco[4] / ALTO_M)
            continue
        t = Vector((-n.y, n.x, 0.0))
        for li, p in zip(cara.loop_indices, pts):
            if t.length > 0.3:
                u, v = p.dot(t.normalized()), p.z
            else:
                u, v = p.x, p.y
            capa.data[li].uv = (u / ANCHO_M, v / ALTO_M)
    me.uv_layers.active = capa
    return dovelas


texturizados, dovelas = [], {}
for o in escena.objects:
    if (o.type != "MESH" or o.hide_render or not o.name.startswith("Concatedral")
            or "vidrio" in o.name or not any(p in o.name for p in PIEZAS)):
        continue
    n = uv_objeto(o)
    if n:
        dovelas[o.name] = n
    o.data.materials.clear()
    o.data.materials.append(mat)
    texturizados.append(o.name)

# --- camara de la foto, fija en el maestro --------------------------------------
ajuste = json.loads((RAIZ / "renders" / "h1_i4_comparacion" / "ajuste.json")
                    .read_text(encoding="utf-8"))
datos = bpy.data.cameras.new("CAM_foto")
datos.lens, datos.sensor_width = ajuste["exif_focal"]["eq"], 36.0
datos.sensor_fit = "HORIZONTAL"
cam_foto = bpy.data.objects.new("CAM_foto", datos)
bpy.data.collections["Camaras_y_luz"].objects.link(cam_foto)
cam_foto.matrix_world = Matrix(ajuste["matriz_camara"])

geometria_despues = {o.name: [tuple(v.co) for v in o.data.vertices]
                     for o in escena.objects if o.type == "MESH"}
assert geometria_antes == geometria_despues, "la intervencion no debe mover vertices"

escena["intervencion"] = 5
escena.camera = bpy.data.objects["CAM_general"]
# Sin remapeo: las rutas "//../texturas" ya estan escritas respecto a blender/, no
# respecto a blender/copias/, que es desde donde se abrio el archivo.
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True, relative_remap=False)

# Se reabre el maestro para comprobar que las texturas se encuentran por ruta relativa.
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
escena = bpy.context.scene
imagenes = {}
for nombre in ("silleria_dorada_color", "silleria_dorada_normal"):
    img = bpy.data.images[nombre]
    imagenes[nombre] = {"ruta": img.filepath, "tamano": list(img.size),
                        "existe": Path(bpy.path.abspath(img.filepath)).exists()}
    assert (img.filepath.startswith("//") and imagenes[nombre]["existe"]
            and img.size[0] > 0), imagenes[nombre]
DESPUES.mkdir(parents=True, exist_ok=True)
informe = {"objetos_texturizados": sorted(texturizados), "caras_con_dovelas": dovelas,
           "texturas": imagenes, "vertices_modificados": 0}
(DESPUES / "informe.json").write_text(json.dumps(informe, indent=2), encoding="utf-8")
print("INFORME", len(texturizados), json.dumps(dovelas), json.dumps(imagenes))
if not SIN_RENDER:
    for nombre in ("CAM_foto", "CAM_peaton_noroeste", "CAM_portada", "CAM_ventanas",
                   "CAM_ventana_apuntada", "CAM_peaton_oeste_torre", "CAM_general"):
        escena.camera = bpy.data.objects[nombre]
        escena.render.resolution_x, escena.render.resolution_y = (
            (2000, 1328) if nombre == "CAM_foto" else (1600, 1000))
        escena.render.filepath = str(DESPUES / f"{nombre}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", escena.render.filepath)
