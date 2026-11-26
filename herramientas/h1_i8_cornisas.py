"""H1, intervencion 8: cornisas de la torre con vuelo constante.

Las de la intervencion 6 se trazaron entre las puntas de los resaltes de las
esquinas y no eran paralelas a los muros: el vuelo iba de 1 a 40 cm. Ahora
siguen el contorno de la torre (muros y resaltes) desplazado una distancia fija.

Parte del .blend de la intervencion 7: lo copia a blender/copias/santa_maria_i7.blend
y siempre trabaja desde esa copia. Solo rehace las mallas de las tres cornisas.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/h1_i8_cornisas.py
    ... -- --sin-render
"""
import json
import shutil
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.geometry import intersect_line_line_2d, tessellate_polygon

RAIZ = Path(__file__).resolve().parents[1]
BLEND = RAIZ / "blender" / "santa_maria.blend"
COPIA = RAIZ / "blender" / "copias" / "santa_maria_i7.blend"
DESPUES = RAIZ / "renders" / "h1_i8_despues"
SIN_RENDER = "--sin-render" in sys.argv
ANCHO_M, ALTO_M = 6.4, 3.2           # repeticion de la silleria
VUELOS = {1: 0.17, 2: 0.17, 3: 0.28}  # los previstos en la intervencion 6
EMPOTRE = 0.06
ARRIBA = Vector((0, 0, 1))

P = [Vector((p[0], p[1])) for p in json.loads(
    (RAIZ / "datos" / "locales" / "santa_maria_dxf_local.json").read_text(encoding="utf-8"))
    ["/mnt/data/work/trama urbana_2012_3D.dxf"][1688][2]]
ESTE = P[87] + (P[69] - P[79])        # esquina interior supuesta (intervencion 1)
# Contorno de la torre: P74-P79 y P82-P83 son los paramentos noroeste y suroeste.
CONTORNO = [P[i] for i in (69, 70, 71, 72, 73, 74, 79, 80, 81, 82, 83, 84, 85, 86, 87)] + [ESTE]
CARAS = {"NO": (P[74], P[79]), "SO": (P[82], P[83]), "NE": (P[69], ESTE), "SE": (ESTE, P[87])}


def area(poligono):
    return sum(a.x * b.y - b.x * a.y for a, b in zip(poligono, poligono[1:] + poligono[:1])) / 2


if area(CONTORNO) < 0:
    CONTORNO.reverse()


def fuera_de(a, b):
    """Normal exterior de la arista a-b de un contorno antihorario."""
    t = (b - a).normalized()
    return Vector((t.y, -t.x))


def desplazar(poligono, d):
    """Contorno paralelo a distancia d, suprimiendo las aristas que se invierten."""
    aristas = [(a, b) for a, b in zip(poligono, poligono[1:] + poligono[:1])]
    while True:
        puntos = []
        for (a, b), (c, e) in zip(aristas[-1:] + aristas[:-1], aristas):
            n1, n2 = fuera_de(a, b) * d, fuera_de(c, e) * d
            t1, t2 = b - a, e - c
            giro = t1.x * t2.y - t1.y * t2.x
            if abs(giro) < 1e-6:
                puntos.append(c + n2)
                continue
            r = (c + n2) - (a + n1)
            puntos.append(a + n1 + t1 * ((r.x * t2.y - r.y * t2.x) / giro))
        malas = [i for i, (a, b) in enumerate(aristas)
                 if (puntos[(i + 1) % len(puntos)] - puntos[i]).dot(b - a) <= 0]
        if not malas:
            break
        del aristas[malas[0]]
    n = len(puntos)
    for i in range(n):
        for j in range(i + 2, n - (i == 0)):
            assert intersect_line_line_2d(puntos[i], puntos[(i + 1) % n], puntos[j],
                                          puntos[(j + 1) % n]) is None, ("se cruza", d, i, j)
    return puntos


def anillo(fuera, dentro, z0, z1):
    vertices, caras = [], []

    def tri(a, b, c, mira):
        if (b - a).cross(c - a).length < 1e-7:
            return
        if (b - a).cross(c - a).dot(mira) < 0:
            b, c = c, b
        n = len(vertices)
        vertices.extend([a, b, c])
        caras.append([n, n + 1, n + 2])

    for a, b in zip(fuera, fuera[1:] + fuera[:1]):
        mira = fuera_de(a, b).to_3d()
        q = [a.to_3d() + ARRIBA * z0, b.to_3d() + ARRIBA * z0,
             b.to_3d() + ARRIBA * z1, a.to_3d() + ARRIBA * z1]
        tri(q[0], q[1], q[2], mira)
        tri(q[0], q[2], q[3], mira)
    for z, mira in ((z0, -ARRIBA), (z1, ARRIBA)):
        todos = [p.to_3d() + ARRIBA * z for p in fuera + dentro]
        triangulos = tessellate_polygon([[p.to_3d() for p in fuera], [p.to_3d() for p in dentro]])
        for t in triangulos:
            tri(*(todos[i] for i in t), mira)
        cubierto = sum(abs(area([todos[i].xy for i in t])) for t in triangulos)
        esperado = abs(area(fuera)) - abs(area(dentro))
        assert abs(cubierto - esperado) < 0.01, ("anillo mal cerrado", cubierto, esperado)
    return vertices, caras


def uv_metros(me, mw):
    capa = me.uv_layers.new(name="UVMap")
    for cara in me.polygons:
        pts = [mw @ me.vertices[me.loops[i].vertex_index].co for i in cara.loop_indices]
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0]).normalized()
        t = Vector((-n.y, n.x, 0.0))
        for li, p in zip(cara.loop_indices, pts):
            u, v = (p.dot(t.normalized()), p.z) if t.length > 0.3 else (p.x, p.y)
            capa.data[li].uv = (u / ANCHO_M, v / ALTO_M)


def vuelos_medidos(o, z):
    """Distancia entre el paramento y el canto de la cornisa en cinco puntos de cada cara."""
    inv = o.matrix_world.inverted()
    salida = {}
    for nombre, (a, b) in CARAS.items():
        n = fuera_de(a, b)
        if n.dot((a + b) / 2 - sum(CONTORNO, Vector((0, 0))) / len(CONTORNO)) < 0:
            n = -n
        fila = []
        for f in (0.08, 0.3, 0.5, 0.7, 0.92):
            origen = (a.lerp(b, f) + n * 3.0).to_3d() + ARRIBA * z
            ok, p, _, _ = o.ray_cast(inv @ origen, (inv.to_3x3() @ -n.to_3d()).normalized())
            fila.append(round(3.0 - (o.matrix_world @ p - origen).length, 3) if ok else None)
        salida[nombre] = fila
    return salida


if not COPIA.exists():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    assert bpy.context.scene.get("intervencion") == 7, "el maestro no es el de la intervencion 7"
    shutil.copy2(BLEND, COPIA)
bpy.ops.wm.open_mainfile(filepath=str(COPIA))
escena = bpy.context.scene
geometria = lambda: {o.name: [tuple(v.co) for v in o.data.vertices]
                     for o in escena.objects if o.type == "MESH"}
antes = geometria()
informe = {"cornisas": {}}
for n, vuelo in VUELOS.items():
    o = escena.objects[f"Concatedral_torre_cornisa_{n}"]
    zs = [(o.matrix_world @ v.co).z for v in o.data.vertices]
    z0, z1 = min(zs), max(zs)
    medio = (z0 + z1) / 2
    previo = vuelos_medidos(o, medio)
    vertices, caras = anillo(desplazar(CONTORNO, vuelo), desplazar(CONTORNO, -EMPOTRE), z0, z1)
    me = bpy.data.meshes.new(o.name + "_i8")
    inv = o.matrix_world.inverted()
    me.from_pydata([inv @ v for v in vertices], [], caras)
    me.update()
    for m in o.data.materials:
        me.materials.append(m)
    uv_metros(me, o.matrix_world)
    viejo, o.data = o.data, me
    nombre_malla = viejo.name
    bpy.data.meshes.remove(viejo)
    me.name = nombre_malla
    o["origen"] = o["origen"] + "; contorno rehecho en la intervencion 8"
    bpy.context.view_layer.update()
    medido = vuelos_medidos(o, medio)
    for cara, fila in medido.items():
        assert all(v is not None and abs(v - vuelo) < 0.003 for v in fila), (n, cara, fila)
    informe["cornisas"][o.name] = {"vuelo_previsto_m": vuelo, "cota": [round(z0, 3), round(z1, 3)],
                                   "antes": previo, "despues": medido}
    print("CORNISA", n, "antes", previo, "despues", medido)

despues = geometria()
cambiados = sorted(k for k in despues if despues[k] != antes.get(k))
assert cambiados == [f"Concatedral_torre_cornisa_{n}" for n in VUELOS], cambiados
assert set(despues) == set(antes)
informe["objetos_modificados"] = cambiados

escena["intervencion"] = 8
# Sin remapeo: las rutas "//../texturas" ya estan escritas respecto a blender/.
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True, relative_remap=False)
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
escena = bpy.context.scene
for img in bpy.data.images:
    if img.filepath.startswith("//"):
        assert Path(bpy.path.abspath(img.filepath)).exists(), img.filepath
DESPUES.mkdir(parents=True, exist_ok=True)
(DESPUES / "informe.json").write_text(json.dumps(informe, indent=2), encoding="utf-8")

if not SIN_RENDER:
    registro = json.loads((RAIZ / "renders" / "calle_i7" / "registro.json").read_text(encoding="utf-8"))
    sol = escena.objects["Sol_base"]
    sol_base = sol.rotation_euler.copy()
    for nombre in ("CAM_foto", "CAM_torre", "CAM_calle_S"):
        sol.rotation_euler = sol_base
        ancho, alto = {"CAM_foto": (2000, 1328), "CAM_torre": (1600, 1000)}.get(nombre, (2000, 1500))
        if nombre == "CAM_calle_S":
            v = registro["vistas"]["S"]
            datos = bpy.data.cameras.new(nombre)
            datos.lens, datos.sensor_width = v["focal_mm"], registro["sensor_mm"]
            datos.sensor_fit, datos.shift_y = "HORIZONTAL", v["desplazamiento_y"]
            cam = bpy.data.objects.new(nombre, datos)
            escena.collection.objects.link(cam)
            cam.location = v["posicion"]
            a = np.radians(v["rumbo_grados"])
            mira = Vector((np.sin(a), np.cos(a), 0))
            cam.rotation_euler = mira.to_track_quat("-Z", "Y").to_euler()
            rumbo = np.arctan2(-mira.x, -mira.y) + np.radians(35)
            sol.rotation_euler = Vector((np.sin(rumbo), np.cos(rumbo), 1.0)).normalized() \
                .to_track_quat("Z", "Y").to_euler()
        escena.camera = escena.objects[nombre]
        escena.render.resolution_x, escena.render.resolution_y = ancho, alto
        escena.render.resolution_percentage = 100
        escena.cycles.samples = 48
        escena.render.filepath = str(DESPUES / f"{nombre}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", escena.render.filepath)
