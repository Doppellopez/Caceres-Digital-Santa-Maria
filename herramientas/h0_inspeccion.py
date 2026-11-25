"""H0: importa modelos/v0.3 en una escena vacia y comprueba escala, ejes y objetos.

No guarda ningun .blend ni modifica geometria.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/h0_inspeccion.py
"""
import json
from pathlib import Path

import bpy
from mathutils import Vector

RAIZ = Path(__file__).resolve().parents[1]
GLB = RAIZ / "modelos" / "v0.3" / "santa_maria_v0_3.glb"
OBJ = RAIZ / "modelos" / "v0.3" / "santa_maria_v0_3.obj"


def caja(objetos):
    pts = [o.matrix_world @ v.co for o in objetos for v in o.data.vertices]
    mn = [round(min(p[i] for p in pts), 3) for i in range(3)]
    mx = [round(max(p[i] for p in pts), 3) for i in range(3)]
    return mn, mx


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(GLB))
mallas = [o for o in bpy.context.scene.objects if o.type == "MESH"]

print("VERSION", bpy.app.version_string)
print("OBJETOS", len(bpy.context.scene.objects), "MALLAS", len(mallas))
print("CAJA_GLB", caja(mallas))
for o in sorted(mallas, key=lambda o: o.name):
    mn, mx = caja([o])
    mats = [m.name for m in o.data.materials if m]
    print("OBJ", json.dumps([o.name, len(o.data.vertices), len(o.data.polygons),
                             mn, mx, mats, len(o.data.uv_layers)]))

# Caja del OBJ (declarado Z arriba) leida como texto, para contrastar ejes.
vs = []
with open(OBJ, encoding="utf-8", errors="replace") as f:
    for linea in f:
        if linea.startswith("v "):
            vs.append(Vector(tuple(map(float, linea.split()[1:4]))))
print("CAJA_OBJ_TEXTO",
      [round(min(v[i] for v in vs), 3) for i in range(3)],
      [round(max(v[i] for v in vs), 3) for i in range(3)])

# Dispositivos de render disponibles para Cycles.
bpy.context.scene.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
for tipo in ("CUDA", "OPTIX", "HIP", "ONEAPI"):
    try:
        disp = [(d.name, d.type) for d in prefs.get_devices_for_type(tipo)]
    except Exception as e:  # el backend puede no existir en esta compilacion
        disp = str(e)
    print("CYCLES", tipo, disp)
