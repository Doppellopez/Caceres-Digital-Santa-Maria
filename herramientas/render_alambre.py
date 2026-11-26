"""Vista cenital del casco antiguo con las aristas de la malla dibujadas.

Abre blender/santa_maria_casco.blend y no lo guarda.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/render_alambre.py
"""
from pathlib import Path

import bpy

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "renders" / "casco" / "CAM_casco_cenital_alambre.png"
PX_POR_M = 8
GROSOR = 0.13      # m: algo mas de un pixel

bpy.ops.wm.open_mainfile(filepath=str(RAIZ / "blender" / "santa_maria_casco.blend"))
escena = bpy.context.scene

linea = bpy.data.materials.new("Arista_alambre")
linea.use_nodes = True
nodos = linea.node_tree.nodes
negro = nodos.new("ShaderNodeEmission")
negro.inputs["Color"].default_value = (0.012, 0.016, 0.022, 1.0)
linea.node_tree.links.new(negro.outputs[0], nodos["Material Output"].inputs["Surface"])

mallas = [o for o in escena.objects if o.type == "MESH" and not o.hide_render]
aristas = 0
for o in mallas:
    aristas += len(o.data.edges)
    alambre = o.copy()
    alambre.data = o.data.copy()
    alambre.name = o.name + "_alambre"
    escena.collection.objects.link(alambre)
    alambre.data.materials.clear()
    alambre.data.materials.append(linea)
    alambre.data.polygons.foreach_set("material_index", [0] * len(alambre.data.polygons))
    mod = alambre.modifiers.new("alambre", "WIREFRAME")
    mod.thickness = GROSOR
    mod.use_replace = True
    mod.use_even_offset = False
    alambre.visible_shadow = False
    alambre.visible_diffuse = False

cam = bpy.data.objects["CAM_casco_cenital"]
escena.camera = cam
ancho_m, alto_m = 512, 576
escena.render.resolution_x, escena.render.resolution_y = ancho_m * PX_POR_M, alto_m * PX_POR_M
escena.cycles.samples = 24
escena.cycles.use_denoising = False   # el filtrado emborrona las lineas
escena.render.filepath = str(SALIDA)
bpy.ops.render.render(write_still=True)
print("MALLAS", len(mallas), "ARISTAS", aristas, "RENDER", SALIDA)
