"""Corte horizontal de toda la concatedral en el maestro, para dibujar su planta.

No modifica ni guarda el .blend. Escribe renders/planta_iglesia/cortes.json.
planta_iglesia_dibujo.py lo dibuja.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/planta_iglesia_datos.py
"""
import json
from pathlib import Path

import bpy

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "renders" / "planta_iglesia"
COTA = 5.5  # m locales: por encima del suelo en todo el perimetro y bajo las cubiertas

bpy.ops.wm.open_mainfile(filepath=str(RAIZ / "blender" / "santa_maria.blend"))
objetos = {}
for o in bpy.context.scene.objects:
    if o.type != "MESH" or o.hide_render or not o.name.startswith("Concatedral"):
        continue
    mundo = [o.matrix_world @ v.co for v in o.data.vertices]
    segmentos = []
    for cara in o.data.polygons:
        pts = [mundo[i] for i in cara.vertices]
        cruces = []
        for a, b in zip(pts, pts[1:] + pts[:1]):
            if (a.z > COTA) != (b.z > COTA):
                p = a.lerp(b, (COTA - a.z) / (b.z - a.z))
                cruces.append((round(p.x, 4), round(p.y, 4)))
        for i in range(0, len(cruces) - 1, 2):
            segmentos.append([cruces[i], cruces[i + 1]])
    if segmentos:
        objetos[o.name] = segmentos

contorno = [[p[0], p[1]] for p in json.loads(
    (RAIZ / "datos" / "locales" / "santa_maria_dxf_local.json").read_text(encoding="utf-8"))
    ["/mnt/data/work/trama urbana_2012_3D.dxf"][1688][2]]
SALIDA.mkdir(parents=True, exist_ok=True)
(SALIDA / "cortes.json").write_text(json.dumps(
    {"cota": COTA, "objetos": objetos, "contorno": contorno}), encoding="utf-8")
print("CORTE", COTA, {k: len(v) for k, v in objetos.items()})
