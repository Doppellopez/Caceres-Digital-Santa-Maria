"""Alzados sin perspectiva de las cuatro fachadas de la concatedral.

Solo se ven las piezas de la concatedral (sin edificios vecinos ni terreno), a la
misma escala en las cuatro. El sol se recoloca delante de cada fachada; no es el
real. No guarda el .blend. La lamina la monta componer_fachadas.py.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/render_fachadas.py
    ... -- --ventanas      ademas, primeros planos de las ventanas noroeste
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "renders" / "fachadas"
PX_ANCHO, PX_ALTO = 1600, 1200
NORMALES = {"NO": (-0.716, 0.698), "SO": (-0.698, -0.716), "SE": (0.716, -0.698), "NE": (0.698, 0.716)}

bpy.ops.wm.open_mainfile(filepath=str(RAIZ / "blender" / "santa_maria.blend"))
escena = bpy.context.scene
for o in escena.objects:
    if o.type == "MESH" and not o.name.startswith("Concatedral"):
        o.hide_render = True
iglesia = [o for o in escena.objects if o.type == "MESH" and not o.hide_render]
puntos = [o.matrix_world @ v.co for o in iglesia for v in o.data.vertices]
sol = escena.objects["Sol_base"]
SALIDA.mkdir(parents=True, exist_ok=True)


def poner_sol(n):
    t = Vector((-n.y, n.x, 0))
    sol.rotation_euler = (n + t * 0.7 + Vector((0, 0, 1.0))).normalized().to_track_quat("Z", "Y").to_euler()


def disparar(cam, ruta, ancho, alto):
    escena.camera = cam
    escena.render.resolution_x, escena.render.resolution_y = ancho, alto
    escena.render.resolution_percentage = 100
    escena.cycles.samples = 48
    escena.render.filepath = str(ruta)
    bpy.ops.render.render(write_still=True)
    print("RENDER", ruta)


def camara(nombre, ojo, mira):
    datos = bpy.data.cameras.new(nombre)
    datos.clip_end = 1000.0
    cam = bpy.data.objects.new(nombre, datos)
    escena.collection.objects.link(cam)
    cam.location = ojo
    cam.rotation_euler = (mira - ojo).to_track_quat("-Z", "Y").to_euler()
    return cam


# La misma escala para las cuatro: la que hace caber la mayor.
cajas = {}
for nombre, (nx, ny) in NORMALES.items():
    n = Vector((nx, ny, 0)).normalized()
    derecha = Vector((-n.y, n.x, 0))
    s = [p.dot(derecha) for p in puntos]
    cajas[nombre] = (n, derecha, min(s), max(s))
z0, z1 = min(p.z for p in puntos), max(p.z for p in puntos)
ancho_m = max(max(c[3] - c[2] for c in cajas.values()), (z1 - z0) * PX_ANCHO / PX_ALTO) * 1.04
centro = sum(puntos, Vector()) / len(puntos)
escena.render.film_transparent = True
for nombre, (n, derecha, s0, s1) in cajas.items():
    mira = centro + derecha * ((s0 + s1) / 2 - centro.dot(derecha))
    mira.z = (z0 + z1) / 2
    cam = camara(f"alzado_{nombre}", mira + n * 120.0, mira)
    cam.data.type, cam.data.ortho_scale = "ORTHO", ancho_m
    poner_sol(n)
    disparar(cam, SALIDA / f"alzado_{nombre}.png", PX_ANCHO, PX_ALTO)

if "--ventanas" in sys.argv:
    escena.render.film_transparent = False
    n = cajas["NO"][0]
    poner_sol(n)
    vidrio = {v: escena.objects[f"Concatedral_ventana_{v}_vidrio"] for v in ("W1", "W2", "W3", "W4")}
    centros = {v: sum((o.matrix_world @ p.co for p in o.data.vertices), Vector()) / len(o.data.vertices)
               for v, o in vidrio.items()}
    for v, centro_v in centros.items():
        cam = camara(v, centro_v + n * 9.0, centro_v)
        cam.data.type, cam.data.ortho_scale = "ORTHO", 4.6 if v == "W4" else 3.2
        disparar(cam, SALIDA / f"ventana_{v}.png", 800, 1100)
