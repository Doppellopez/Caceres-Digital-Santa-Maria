"""Cortes horizontales de la torre en el maestro, para dibujar su planta.

No modifica ni guarda el .blend. Escribe renders/planta_torre/cortes.json:
segmentos de cada corte, contorno de la tapa de la torre y vertices del contorno
municipal cercanos. planta_torre_dibujo.py los dibuja.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/planta_torre_datos.py
"""
import json
from collections import Counter
from pathlib import Path

import bpy

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "renders" / "planta_torre"
CORTES = {"baja": 7.0, "media": 13.0, "campanas": 24.2}  # cota local en metros

bpy.ops.wm.open_mainfile(filepath=str(RAIZ / "blender" / "santa_maria.blend"))
escena = bpy.context.scene
objetos = [o for o in escena.objects
           if o.type == "MESH" and not o.hide_render and o.name.startswith("Concatedral")]


def cortar(o, z):
    mundo = [o.matrix_world @ v.co for v in o.data.vertices]
    segmentos = []
    for cara in o.data.polygons:
        pts = [mundo[i] for i in cara.vertices]
        cruces = []
        for a, b in zip(pts, pts[1:] + pts[:1]):
            if (a.z > z) != (b.z > z):
                p = a.lerp(b, (z - a.z) / (b.z - a.z))
                cruces.append((round(p.x, 4), round(p.y, 4)))
        for i in range(0, len(cruces) - 1, 2):
            segmentos.append([cruces[i], cruces[i + 1]])
    return segmentos


cortes = {}
for nombre, z in CORTES.items():
    cortes[nombre] = {"z": z, "objetos": {o.name: s for o in objetos if (s := cortar(o, z))}}

# Contorno de la tapa: aristas que pertenecen a una sola cara.
tapa = escena.objects["Concatedral_torre_cubierta"]
mundo = [tapa.matrix_world @ v.co for v in tapa.data.vertices]
clave = lambda i: (round(mundo[i].x, 3), round(mundo[i].y, 3))
aristas = Counter()
for cara in tapa.data.polygons:
    ids = list(cara.vertices)
    for a, b in zip(ids, ids[1:] + ids[:1]):
        aristas[tuple(sorted((clave(a), clave(b))))] += 1
contorno = [list(k) for k, n in aristas.items() if n == 1]

dxf = json.loads((RAIZ / "datos" / "locales" / "santa_maria_dxf_local.json")
                 .read_text(encoding="utf-8"))["/mnt/data/work/trama urbana_2012_3D.dxf"][1688][2]
puntos = [{"i": i, "x": p[0], "y": p[1], "z": p[2] - 440.0} for i, p in enumerate(dxf)
          if p[0] < 19 and p[1] < 0]

SALIDA.mkdir(parents=True, exist_ok=True)
(SALIDA / "cortes.json").write_text(json.dumps(
    {"cortes": cortes, "contorno_tapa": contorno, "puntos_dxf": puntos}, indent=1), encoding="utf-8")
for nombre, c in cortes.items():
    print("CORTE", nombre, c["z"], {k: len(v) for k, v in c["objetos"].items()})
print("TAPA", contorno)
print("DXF", [(p["i"], round(p["x"], 2), round(p["y"], 2), round(p["z"], 2)) for p in puntos])
