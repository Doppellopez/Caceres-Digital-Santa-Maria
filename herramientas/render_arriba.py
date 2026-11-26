"""Vista cenital (ortografica, norte arriba) centrada en la concatedral.

No guarda el .blend: la camara solo existe durante el render.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/render_arriba.py
"""
from pathlib import Path

import bpy
from mathutils import Vector

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "renders" / "cenital" / "CAM_cenital_iglesia.png"
LADO_PX = 2000
MUESTRAS = 64
ENTORNO = 1.7  # lado de la imagen respecto al lado mayor de la concatedral

bpy.ops.wm.open_mainfile(filepath=str(RAIZ / "blender" / "santa_maria.blend"))
escena = bpy.context.scene
visibles = [o for o in escena.objects if o.type == "MESH" and not o.hide_render]
pts = [o.matrix_world @ Vector(c) for o in visibles
       if o.name.startswith("Concatedral") for c in o.bound_box]
minimo = Vector([min(p[i] for p in pts) for i in range(3)])
maximo = Vector([max(p[i] for p in pts) for i in range(3)])
centro = (minimo + maximo) / 2.0

datos = bpy.data.cameras.new("CAM_cenital_iglesia")
datos.type = "ORTHO"
datos.ortho_scale = max(maximo.x - minimo.x, maximo.y - minimo.y) * ENTORNO
datos.clip_end = 1000.0
cam = bpy.data.objects.new(datos.name, datos)
escena.collection.objects.link(cam)
cam.location = (centro.x, centro.y, maximo.z + 200.0)
cam.rotation_euler = (0.0, 0.0, 0.0)  # mira hacia -Z, norte arriba, este a la derecha
escena.camera = cam

escena.render.resolution_x = escena.render.resolution_y = LADO_PX
escena.render.resolution_percentage = 100
escena.cycles.samples = MUESTRAS
escena.render.filepath = str(SALIDA)
SALIDA.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.render.render(write_still=True)
print("CENTRO", [round(v, 2) for v in centro], "LADO_M", round(datos.ortho_scale, 2))
print("RENDER", SALIDA)
