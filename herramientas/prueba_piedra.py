"""Prueba visual: silleria de granito generada por codigo sobre la concatedral.

Abre el .blend, pone el material en memoria, renderiza y NO guarda el .blend.
La textura es propia (numpy); no usa ninguna fotografia ni imagen de terceros.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/prueba_piedra.py

Tras la intervencion 1 solo saca el tono dorado, en renders/prueba_piedra_i1, y
usa tambien la camara ajustada a la foto (ejecutar antes h1_comparar_foto.py).
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from silleria import ALTO_M, ANCHO_M, PALETAS, generar  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
BLEND = RAIZ / "blender" / "santa_maria.blend"
SALIDA = RAIZ / "renders" / "prueba_piedra"

SUELO_Z = 1.4                       # cota aproximada del suelo ante la fachada

def imagen(nombre, datos, es_color):
    alto, ancho = datos.shape[:2]
    img = bpy.data.images.new(nombre, ancho, alto, alpha=True)
    rgba = np.ones((alto, ancho, 4), np.float32)
    rgba[..., :3] = datos if datos.ndim == 3 else datos[..., None]
    img.pixels.foreach_set(rgba.ravel())
    if not es_color:
        img.colorspace_settings.name = "Non-Color"
    img.filepath_raw = str(SALIDA / f"{nombre}.png")
    img.file_format = "PNG"
    img.save()
    return img


def material(nombre, img_color, img_relieve, verdin):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    a = m.node_tree
    bsdf = a.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.92
    uv = a.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "piedra"
    tc = a.nodes.new("ShaderNodeTexImage")
    tc.image = img_color
    th = a.nodes.new("ShaderNodeTexImage")
    th.image = img_relieve
    bump = a.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.7
    bump.inputs["Distance"].default_value = 0.035
    a.links.new(uv.outputs[0], tc.inputs[0])
    a.links.new(uv.outputs[0], th.inputs[0])
    a.links.new(th.outputs["Color"], bump.inputs["Height"])
    a.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    salida = tc.outputs["Color"]
    if verdin:
        alt = a.nodes.new("ShaderNodeUVMap")
        alt.uv_map = "altura"
        sep = a.nodes.new("ShaderNodeSeparateXYZ")
        a.links.new(alt.outputs[0], sep.inputs[0])
        ruidoso = a.nodes.new("ShaderNodeTexNoise")
        ruidoso.inputs["Scale"].default_value = 3.0
        ruidoso.inputs["Detail"].default_value = 8.0
        geo = a.nodes.new("ShaderNodeNewGeometry")
        a.links.new(geo.outputs["Position"], ruidoso.inputs["Vector"])
        suma = a.nodes.new("ShaderNodeMath")
        suma.operation = "MULTIPLY_ADD"
        suma.inputs[1].default_value = 0.9
        a.links.new(ruidoso.outputs["Fac"], suma.inputs[0])
        a.links.new(sep.outputs["Y"], suma.inputs[2])
        rango = a.nodes.new("ShaderNodeMapRange")
        rango.inputs["From Min"].default_value = 0.85
        rango.inputs["From Max"].default_value = 1.15
        rango.inputs["To Min"].default_value = 1.0
        rango.inputs["To Max"].default_value = 0.0
        a.links.new(suma.outputs[0], rango.inputs["Value"])
        mezcla = a.nodes.new("ShaderNodeMix")
        mezcla.data_type = "RGBA"
        mezcla.blend_type = "MULTIPLY"
        mezcla.inputs[7].default_value = (0.16, 0.24, 0.07, 1.0)
        a.links.new(rango.outputs[0], mezcla.inputs[0])
        a.links.new(salida, mezcla.inputs[6])
        salida = mezcla.outputs[2]
    a.links.new(salida, bsdf.inputs["Base Color"])
    return m


def uv_en_metros(o):
    me = o.data
    uv = me.uv_layers.get("piedra") or me.uv_layers.new(name="piedra")
    alt = me.uv_layers.get("altura") or me.uv_layers.new(name="altura")
    uv, alt = me.uv_layers["piedra"], me.uv_layers["altura"]
    mw = o.matrix_world
    giro = mw.to_3x3()
    for cara in me.polygons:
        n = (giro @ cara.normal).normalized()
        t = Vector((-n.y, n.x, 0.0))
        for li in cara.loop_indices:
            p = mw @ me.vertices[me.loops[li].vertex_index].co
            if t.length > 0.3:
                u, v = p.dot(t.normalized()), p.z
            else:
                u, v = p.x, p.y
            uv.data[li].uv = (u / ANCHO_M, v / ALTO_M)
            alt.data[li].uv = (0.0, 0.0 if p.z < 5.0 else p.z - SUELO_Z)


bpy.ops.wm.open_mainfile(filepath=str(BLEND))
escena = bpy.context.scene
intervenido = "intervencion" in escena
if escena.get("intervencion", 0) >= 5:
    raise SystemExit("La silleria ya esta en el maestro (intervencion 5); no hay nada que probar.")
if intervenido:
    SALIDA = RAIZ / "renders" / f"prueba_piedra_i{escena['intervencion']}"
SALIDA.mkdir(parents=True, exist_ok=True)
muros = [o for o in escena.objects if o.type == "MESH" and o.name.startswith("Concatedral")
         and any(c in o.name for c in ("fachadas", "contrafuerte", "torre_interior", "cuerpo", "remate", "rebaje", "cornisa",
                                            "canecillos", "peldanos", "ventana"))
         and "vidrio" not in o.name and not o.hide_render]
for o in muros:
    uv_en_metros(o)

cerca = bpy.data.cameras.new("CAM_prueba_cerca")
cerca.lens = 30.0
cam = bpy.data.objects.new("CAM_prueba_cerca", cerca)
escena.collection.objects.link(cam)
cam.location = (7.5, 9.5, 3.0)
cam.rotation_euler = (Vector((14.5, 2.8, 3.4)) - cam.location).to_track_quat("-Z", "Y").to_euler()

tomas = {"clara": ["CAM_peaton_noroeste", "CAM_prueba_cerca"], "dorada": ["CAM_peaton_noroeste"]}
if intervenido:
    ajuste = json.loads((RAIZ / "renders" / f"h1_i{escena['intervencion']}_comparacion"
                         / "ajuste.json")
                        .read_text(encoding="utf-8"))
    foto = bpy.data.cameras.new("CAM_foto")
    foto.lens, foto.sensor_width = ajuste["exif_focal"]["eq"], 36.0
    foto.sensor_fit = "HORIZONTAL"
    cf = bpy.data.objects.new("CAM_foto", foto)
    escena.collection.objects.link(cf)
    cf.matrix_world = Matrix(ajuste["matriz_camara"])
    tomas = {"dorada": ["CAM_foto", "CAM_peaton_noroeste"]}

for nombre, camaras in tomas.items():
    color, relieve = generar(PALETAS[nombre])
    m = material(f"PRUEBA_silleria_{nombre}",
                 imagen(f"silleria_{nombre}_color", color, True),
                 imagen(f"silleria_{nombre}_relieve", relieve, False),
                 verdin=nombre == "clara")
    for o in muros:
        o.data.materials.clear()
        o.data.materials.append(m)
    for c in camaras:
        escena.camera = escena.objects[c]
        escena.render.resolution_x, escena.render.resolution_y = (
            (2000, 1328) if c == "CAM_foto" else (1600, 1000))
        escena.render.filepath = str(SALIDA / f"{nombre}_{c}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", escena.render.filepath)
print("MUROS", len(muros))
