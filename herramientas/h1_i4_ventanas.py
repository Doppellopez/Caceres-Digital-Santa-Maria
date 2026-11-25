"""H1, intervencion 4: las cuatro ventanas de la fachada noroeste.

Parte del .blend de la intervencion 3: lo copia a blender/copias/santa_maria_i3.blend
y siempre trabaja desde esa copia. Medidas en referencias/medidas_ventanas.json
(h1_medir_ventanas.py). Abre el hueco en los panos del muro principal y construye
el abocinado y el vidrio detras.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/h1_i4_ventanas.py
    ... -- --sin-render
"""
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

RAIZ = Path(__file__).resolve().parents[1]
BLEND = RAIZ / "blender" / "santa_maria.blend"
COPIA = RAIZ / "blender" / "copias" / "santa_maria_i3.blend"
ANTES = RAIZ / "renders" / "h1_i4_antes"
DESPUES = RAIZ / "renders" / "h1_i4_despues"
SIN_RENDER = "--sin-render" in sys.argv
PROF = 0.45          # fondo del vidrio respecto al paramento: supuesto
ORDENES = 3

V = json.loads((RAIZ / "referencias" / "medidas_ventanas.json").read_text(encoding="utf-8"))
P = [Vector((p[0], p[1], p[2] - 440.0)) for p in json.loads(
    (RAIZ / "datos" / "locales" / "santa_maria_dxf_local.json").read_text(encoding="utf-8"))
    ["/mnt/data/work/trama urbana_2012_3D.dxf"][1688][2]]
# Pano del muro principal que contiene cada ventana (puntos del contorno).
PANOS = {(59, 67): ["W1", "W2"], (67, 68): ["W3"], (54, 55): ["W4"]}

if not COPIA.exists():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    assert bpy.context.scene.get("intervencion") == 3, "el maestro no es el de la intervencion 3"
    shutil.copy2(BLEND, COPIA)
bpy.ops.wm.open_mainfile(filepath=str(COPIA))
escena = bpy.context.scene

A = P[67].xy
T = (P[58].xy - A).normalized()
N = Vector((-T.y, T.x))
if N.dot(Vector((-0.69, 0.72))) < 0:
    N = -N
EJE_D = Vector((N.x, N.y, 0))


def camara(nombre, desde, hacia, focal):
    datos = bpy.data.cameras.new(nombre)
    datos.lens, datos.sensor_width = focal, 36.0
    c = bpy.data.objects.new(nombre, datos)
    bpy.data.collections["Camaras_y_luz"].objects.link(c)
    c.location = desde
    c.rotation_euler = (hacia - desde).to_track_quat("-Z", "Y").to_euler()


def renderizar(carpeta, camaras):
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre in camaras:
        escena.camera = bpy.data.objects[nombre]
        escena.render.filepath = str(carpeta / f"{nombre}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", escena.render.filepath)


q = A + T * 12.0 + N * 21.0
camara("CAM_ventanas", Vector((q.x, q.y, 3.1)),
       Vector(((A + T * 10.0).x, (A + T * 10.0).y, 10.5)), 30.0)
def vistas_apuntada(ojo):
    """Fraccion del hueco apuntado visible desde un punto, con el edificio vecino."""
    dg = bpy.context.evaluated_depsgraph_get()
    v, n, libres = V["W4"], 0, 0
    for fs in (-0.8, -0.4, 0.0, 0.4, 0.8):
        for fz in (0.1, 0.3, 0.5, 0.7):
            q = A + T * (v["s"] + fs * v["semiancho"]) + N * 0.15
            z = v["antepecho_z"] + fz * (v["clave_z"] - v["antepecho_z"])
            d = Vector((q.x, q.y, z)) - ojo
            ok, *_ = escena.ray_cast(dg, ojo, d.normalized(), distance=d.length)
            n, libres = n + 1, libres + (not ok)
    return libres / n


candidatas = []
for s_cam in range(0, 19):
    for d_cam in range(5, 19):
        q = A + T * s_cam + N * d_cam
        dg = bpy.context.evaluated_depsgraph_get()
        ok, *_, quien, _ = escena.ray_cast(dg, Vector((q.x, q.y, 200.0)), Vector((0, 0, -1)))
        if ok and quien.name == "Terreno_interpolado":
            ojo = Vector((q.x, q.y, 3.1))
            distancia = (ojo.xy - (A + T * V["W4"]["s"])).length
            candidatas.append((vistas_apuntada(ojo), -distancia, s_cam, d_cam, ojo))
mejor = max(candidatas, key=lambda c: (c[0], c[1]))
assert mejor[0] > 0.5, "ningun punto de la plaza ve la ventana apuntada"
print("CAMARA_APUNTADA visible", mejor[0], "s", mejor[2], "d", mejor[3])
camara("CAM_ventana_apuntada", mejor[4],
       Vector(((A + T * V["W4"]["s"]).x, (A + T * V["W4"]["s"]).y, 8.4)), 45.0)
if not SIN_RENDER:
    renderizar(ANTES, ["CAM_ventanas", "CAM_ventana_apuntada"])


def contorno(v, k, n=14):
    """Lazo (s, z) del orden k: antepecho, jamba, arco y jamba."""
    f = k / ORDENES
    a0, av = v["semiancho"], v["semiancho_vidrio"]
    z0 = v["antepecho_z"] + (v["antepecho_vidrio_z"] - v["antepecho_z"]) * f
    if v["tipo"] == "medio_punto":
        # radios leidos de la foto: 1, 0,78, 0,55 y el del vidrio
        radio = [a0, a0 * 0.78, a0 * 0.555, av][k]
        arranque = v["clave_z"] - a0
        centro, fin = 0.0, math.pi / 2
    else:
        # apuntada equilatera y concentrica: la clave del vidrio medida lo confirma
        semi = a0 + (av - a0) * f
        centro, radio = a0, semi + a0
        arranque = v["clave_z"] - math.sqrt(3.0) * a0
        fin = math.acos(centro / radio)
    izq = [(centro - radio * math.cos(fin * i / n), arranque + radio * math.sin(fin * i / n))
           for i in range(n + 1)]
    pts = [(izq[0][0], z0)] + izq + [(-x, z) for x, z in reversed(izq[:-1])] + [(-izq[0][0], z0)]
    return [(v["s"] + x, z) for x, z in pts]


def en_mundo(s, d, z):
    p = A + T * s + N * d
    return Vector((p.x, p.y, z))


muro = bpy.data.objects["Concatedral_fachadas"]
piedra = muro.data.materials[0]
nombre_capa = muro.data.color_attributes[0].name
color = tuple(muro.data.color_attributes[0].data[0].color)
mundo = [muro.matrix_world @ v.co for v in muro.data.vertices]
caras = [list(f.vertices) for f in muro.data.polygons]

# --- 1. Huecos en los panos del muro -----------------------------------------
nuevas_v, nuevas_f = [], []


def anadir(destino_v, destino_f, tri, mira):
    a, b, c = tri
    if (b - a).cross(c - a).length < 1e-7:
        return
    if (b - a).cross(c - a).dot(mira) < 0:
        b, c = c, b
    n = len(destino_v)
    destino_v.extend([a, b, c])
    destino_f.append([n, n + 1, n + 2])


quitar = set()
for (i, j), ventanas in PANOS.items():
    a, b = P[i].xy, P[j].xy
    eje = (b - a).normalized()
    largo = (b - a).length
    del_pano = []
    for n_cara, f in enumerate(caras):
        r = [mundo[k].xy - a for k in f]
        if all(abs(eje.x * w.y - eje.y * w.x) < 0.02 and -0.02 <= w.dot(eje) <= largo + 0.02 for w in r):
            del_pano.append(n_cara)
    assert len(del_pano) == 2, (i, j, len(del_pano))
    quitar.update(del_pano)
    pts = {}
    for n_cara in del_pano:
        for k in caras[n_cara]:
            w = mundo[k]
            lado = 0 if (w.xy - a).length < largo / 2 else 1
            pts.setdefault(lado, []).append(w)
    ext = [min(pts[0], key=lambda w: w.z), min(pts[1], key=lambda w: w.z),
           max(pts[1], key=lambda w: w.z), max(pts[0], key=lambda w: w.z)]
    # Coordenadas del pano: s del eje de la portada y cota. d se interpola en la recta.
    s_de = [(w.xy - A).dot(T) for w in ext]
    d_de = [(w.xy - A).dot(N) for w in ext]

    def d_pano(s, s0=s_de[0], s1=s_de[1], d0=d_de[0], d1=d_de[1]):
        return d0 + (d1 - d0) * (s - s0) / (s1 - s0)

    lazos = [[Vector((s, w.z, 0)) for s, w in zip(s_de, ext)]]
    for nombre in ventanas:
        V[nombre]["d"] = d_pano(V[nombre]["s"])
        V[nombre]["d_pano"] = d_pano     # el muro no es exactamente paralelo al eje
        lazos.append([Vector((s, z, 0)) for s, z in contorno(V[nombre], 0)])
        zs = [p.y for p in lazos[-1]]
        assert min(s_de[:2]) < min(p.x for p in lazos[-1]) and max(p.x for p in lazos[-1]) < max(s_de[:2])
        assert max(zs) < min(ext[2].z, ext[3].z) and min(zs) > max(ext[0].z, ext[1].z)
    plano = [p for lazo in lazos for p in lazo]
    for tri in tessellate_polygon(lazos):
        anadir(nuevas_v, nuevas_f,
               [en_mundo(plano[k].x, d_pano(plano[k].x), plano[k].y) for k in tri], EJE_D)

for n_cara, f in enumerate(caras):
    if n_cara not in quitar:
        n = len(nuevas_v)
        nuevas_v.extend(mundo[k] for k in f)
        nuevas_f.append(list(range(n, n + len(f))))


def volcar(nombre, verts, tris, material, tono, origen, supuesto):
    completo = "Concatedral_" + nombre
    o = bpy.data.objects.get(completo)
    if o is not None:
        o.data.name = completo + "_anterior"
    me = bpy.data.meshes.new(completo)
    if o is None:
        o = bpy.data.objects.new(completo, me)
        bpy.data.collections["Concatedral"].objects.link(o)
        o["origen"] = "H1 intervencion 4; " + origen
        o["provisional"] = supuesto
        o["dibujar_aristas"] = True
    else:
        viejo, o.data = o.data, me
        bpy.data.meshes.remove(viejo)
    inv = o.matrix_world.inverted()
    me.from_pydata([inv @ v for v in verts], [], tris)
    me.update()
    capa = me.color_attributes.new(nombre_capa, "BYTE_COLOR", "POINT")
    for dato in capa.data:
        dato.color = tono
    me.materials.append(material)
    return o


volcar("fachadas", nuevas_v, nuevas_f, piedra, color, "", "")


def vidrio(nombre, tono):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = tono
    p.inputs["Roughness"].default_value = 0.25
    return m


azul = (0.012, 0.030, 0.085, 1.0)
oscuro = (0.006, 0.007, 0.009, 1.0)
vidrios = {"medio_punto": (vidrio("Vidrio_azul_provisional", azul), azul),
           "apuntada": (vidrio("Vidrio_oscuro_provisional", oscuro), oscuro)}

# --- 2. Abocinados y vidrios --------------------------------------------------
paso = PROF / ORDENES
for nombre in ("W1", "W2", "W3", "W4"):
    v = V[nombre]
    verts, tris = [], []
    for k in range(ORDENES):
        fuera, dentro = v["d"] - paso * k, v["d"] - paso * (k + 1)
        p, q_ = contorno(v, k), contorno(v, k + 1)
        zc = (v["antepecho_z"] + v["clave_z"]) / 2
        for i in range(len(p)):
            j = (i + 1) % len(p)
            (sa, za), (sb, zb) = p[i], p[j]
            # normal del intrados: perpendicular al tramo, hacia dentro del hueco
            normal = Vector((-(zb - za), sb - sa))
            if normal.dot(Vector((v["s"] - (sa + sb) / 2, zc - (za + zb) / 2))) < 0:
                normal = -normal
            mira = Vector((T.x * normal.x, T.y * normal.x, normal.y))
            # El primer orden arranca justo en el canto del hueco del muro.
            da, db = (v["d_pano"](sa), v["d_pano"](sb)) if k == 0 else (fuera, fuera)
            cuad = [en_mundo(sa, da, za), en_mundo(sb, db, zb),
                    en_mundo(sb, dentro, zb), en_mundo(sa, dentro, za)]
            anadir(verts, tris, cuad[:3], mira)
            anadir(verts, tris, [cuad[0], cuad[2], cuad[3]], mira)
            corona = [en_mundo(sa, dentro, za), en_mundo(sb, dentro, zb),
                      en_mundo(q_[j][0], dentro, q_[j][1]), en_mundo(q_[i][0], dentro, q_[i][1])]
            anadir(verts, tris, corona[:3], EJE_D)
            anadir(verts, tris, [corona[0], corona[2], corona[3]], EJE_D)
    volcar(f"ventana_{nombre}", verts, tris, piedra, color,
           "posicion y tamano de la foto", "fondo, numero de ordenes y moldurado supuestos")
    lazo = contorno(v, ORDENES)
    verts, tris = [], []
    for tri in tessellate_polygon([[Vector((s, z, 0)) for s, z in lazo]]):
        anadir(verts, tris, [en_mundo(lazo[k][0], v["d"] - PROF, lazo[k][1]) for k in tri], EJE_D)
    material, tono = vidrios[v["tipo"]]
    volcar(f"ventana_{nombre}_vidrio", verts, tris, material, tono, "foto",
           "plano liso, sin plomos ni reja")
bpy.context.view_layer.update()

# Comprobacion: cada vertice del hueco del muro coincide con uno del abocinado.
for nombre in ("W1", "W2", "W3", "W4"):
    o = bpy.data.objects[f"Concatedral_ventana_{nombre}"]
    propios = [o.matrix_world @ x.co for x in o.data.vertices]
    for sa, za in contorno(V[nombre], 0):
        borde = en_mundo(sa, V[nombre]["d_pano"](sa), za)
        assert min((borde - x).length for x in propios) < 1e-3, (nombre, sa, za)

# --- 3. Comprobacion: por ningun hueco se ve el interior -----------------------
dg = bpy.context.evaluated_depsgraph_get()
informe = {"profundidad_supuesta": PROF, "ventanas": {}}
for nombre in ("W1", "W2", "W3", "W4"):
    v = V[nombre]
    lazo = contorno(v, 0)
    rayos = fugas = vistos = 0
    s = v["s"] - v["semiancho"] + 0.013
    while s < v["s"] + v["semiancho"]:
        z = v["antepecho_z"] + 0.017
        while z < v["clave_z"]:
            dentro = False
            for (x1, y1), (x2, y2) in zip(lazo, lazo[1:] + lazo[:1]):
                if (y1 > z) != (y2 > z) and s < x1 + (z - y1) / (y2 - y1) * (x2 - x1):
                    dentro = not dentro
            if dentro:
                ok, golpe, _, _, quien, _ = escena.ray_cast(dg, en_mundo(s, 4.0, z), -EJE_D, distance=12.0)
                rayos += 1
                fugas += not ok or (golpe.xy - A).dot(N) < v["d"] - PROF - 0.02
                vistos += ok and f"ventana_{nombre}" in quien.name
            z += 0.05
        s += 0.05
    informe["ventanas"][nombre] = {
        "s": v["s"], "ancho": round(2 * v["semiancho"], 2), "antepecho_z": v["antepecho_z"],
        "clave_z": v["clave_z"], "rayos": rayos, "fugas": fugas,
        "visible_desde_el_frente_pct": round(100 * vistos / rayos, 1)}

escena["intervencion"] = 4
escena.camera = bpy.data.objects["CAM_general"]
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)
DESPUES.mkdir(parents=True, exist_ok=True)
(DESPUES / "informe.json").write_text(json.dumps(informe, indent=2), encoding="utf-8")
print("INFORME", json.dumps(informe))
if not SIN_RENDER:
    renderizar(DESPUES, ["CAM_ventanas", "CAM_ventana_apuntada", "CAM_peaton_noroeste",
                         "CAM_general"])
