"""Intervencion 12: las cuatro ventanas de la nave noroeste, con la cristalera de la torre.

Pedida por Jorge: el mismo diseno de la intervencion 11 (emplomado azul, orla
ambar y roseta), adaptado al contorno de cada vidrio (W1 a W3 de medio punto, W4
apuntada). El diseno es inventado: en la realidad no se ha comprobado. Solo cambian
material y UV de los cuatro vidrios; no mueve vertices.

Parte del .blend de la intervencion 11: lo copia a blender/copias/santa_maria_i11.blend.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/i12_cristaleras_nave.py
"""
import math
import shutil
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

RAIZ = Path(__file__).resolve().parents[1]
BLEND = RAIZ / "blender" / "santa_maria.blend"
COPIA = RAIZ / "blender" / "copias" / "santa_maria_i11.blend"
TEXTURAS = RAIZ / "texturas" / "concatedral"
RENDERS = RAIZ / "renders" / "i12_cristaleras"
VENTANAS = ("W1", "W2", "W3", "W4")
PPM = 520
ANCHO_TORRE = 0.495            # las medidas del dibujo se escalan desde esta ventana
EXTERIOR = Vector((-0.69, 0.72))


def pano(o):
    """Ejes del vidrio y su contorno ordenado en coordenadas (x, y) de pano."""
    nm = o.matrix_world.to_3x3().inverted_safe().transposed()
    n = sum((nm @ p.normal * p.area for p in o.data.polygons), Vector()).normalized()
    if n.xy.dot(EXTERIOR) < 0:
        n = -n
    t = Vector((-n.y, n.x, 0)).normalized()
    mundo = [o.matrix_world @ v.co for v in o.data.vertices]
    clave = [(round(p.dot(t), 3), round(p.z, 3)) for p in mundo]
    usos = {}
    for cara in o.data.polygons:
        for a, b in cara.edge_keys:
            k = frozenset((clave[a], clave[b]))
            if len(k) == 2:
                usos[k] = usos.get(k, 0) + 1
    vecinos = {}
    for k, veces in usos.items():
        if veces == 1:
            a, b = tuple(k)
            vecinos.setdefault(a, []).append(b)
            vecinos.setdefault(b, []).append(a)
    assert vecinos and all(len(v) == 2 for v in vecinos.values()), (o.name, "contorno abierto")
    lazo = [min(vecinos, key=lambda q: (q[1], q[0]))]
    previo = None
    while True:
        siguiente = next(q for q in vecinos[lazo[-1]] if q != previo)
        if siguiente == lazo[0]:
            break
        previo = lazo[-1]
        lazo.append(siguiente)
    assert len(lazo) == len(vecinos), (o.name, "varios contornos")
    x0, x1 = min(q[0] for q in lazo), max(q[0] for q in lazo)
    y0, y1 = min(q[1] for q in lazo), max(q[1] for q in lazo)
    eje = (x0 + x1) / 2
    contorno = np.array([(q[0] - eje, q[1] - y0) for q in lazo])
    centro = sum(mundo, Vector()) / len(mundo)
    return t, n, eje, x1 - x0, y0, y1 - y0, contorno, centro


def al_contorno(X, Y, contorno):
    """Distancia de cada punto al contorno y posicion a lo largo de el."""
    mejor = np.full(X.shape, np.inf)
    recorrido = np.zeros(X.shape)
    acumulado = 0.0
    for a, b in zip(contorno, np.roll(contorno, -1, axis=0)):
        d = b - a
        largo = float(np.hypot(*d))
        if largo < 1e-6:
            continue
        f = np.clip(((X - a[0]) * d[0] + (Y - a[1]) * d[1]) / largo**2, 0, 1)
        r = np.hypot(X - a[0] - f * d[0], Y - a[1] - f * d[1])
        cerca = r < mejor
        mejor = np.where(cerca, r, mejor)
        recorrido = np.where(cerca, acumulado + f * largo, recorrido)
        acumulado += largo
    return mejor, recorrido, acumulado


def imagen(ancho, alto, contorno, semilla):
    """Mismo dibujo que la intervencion 11 para un contorno cualquiera; fila 0 abajo."""
    k = ancho / ANCHO_TORRE
    w, h = round(ancho * PPM), round(alto * PPM)
    X, Y = np.meshgrid((np.arange(w) + 0.5) / PPM - ancho / 2, (np.arange(h) + 0.5) / PPM)
    borde, recorrido, perimetro = al_contorno(X, Y, contorno)
    marco, filete, plomo, hilada = 0.065 * k, 0.011, 0.007, 0.17 * k
    rng = np.random.default_rng(semilla)
    tonos = np.array([[24, 52, 104], [36, 80, 140], [30, 66, 122], [48, 96, 148],
                      [28, 74, 112]]) / 255.0
    ambar = np.array([[150, 96, 34], [128, 76, 30], [168, 118, 46]]) / 255.0

    interior = ancho - 2 * marco
    col = np.clip(((X + interior / 2) / (interior / 3)).astype(int), 0, 2)
    alterna = Y - marco + np.where(col == 1, hilada / 2, 0.0)
    elegidos = rng.integers(0, len(tonos), (60, 3))
    color = tonos[elegidos[np.clip((alterna / hilada).astype(int), 0, 59), col]]
    en_plomo = (np.abs(X + interior / 6) < plomo) | (np.abs(X - interior / 6) < plomo)
    resto = np.mod(alterna, hilada)
    en_plomo |= (resto < plomo) | (resto > hilada - plomo)

    orla = borde < marco
    piezas = max(3, round(perimetro / 0.14))
    tramo = recorrido / (perimetro / piezas)
    color = np.where(orla[..., None], ambar[tramo.astype(int) % 3], color)
    en_plomo = np.where(orla, np.mod(tramo, 1.0) * perimetro / piezas < 2 * plomo, en_plomo)
    en_plomo |= np.abs(borde - marco) < filete

    # Roseta: lo mas alto del eje donde todavia cabe como en la torre.
    ys = np.linspace(0, alto, 600)
    holgura = al_contorno(np.zeros_like(ys), ys, contorno)[0]
    yc = ys[holgura >= 0.47 * ancho].max()
    radio, boton = 0.12 * k, 0.045 * k
    d = np.hypot(X, Y - yc)
    angulo = np.arctan2(Y - yc, X)
    roseta = d < radio
    petalo = np.floor(np.mod(angulo, 2 * math.pi) / (math.pi / 4)).astype(int) % 2
    color = np.where(roseta[..., None], np.where(petalo[..., None] == 0, ambar[2], tonos[3]), color)
    giro = np.mod(angulo, math.pi / 4)
    en_plomo = np.where(roseta, (np.minimum(giro, math.pi / 4 - giro) * d < plomo)
                        | (np.abs(d - boton) < plomo), en_plomo)
    en_plomo |= np.abs(d - radio) < filete
    color = np.where((roseta & (d < boton))[..., None], np.array([140, 40, 32]) / 255.0, color)
    en_plomo |= borde < 0.012

    grano = 1.0 + 0.10 * rng.normal(0, 1, (h, w))
    for eje in (0, 1):
        grano = (grano + np.roll(grano, 3, eje) + np.roll(grano, -3, eje)) / 3
    color = np.clip(color * grano[..., None], 0, 1)
    return np.where(en_plomo[..., None], np.array([34, 31, 28]) / 255.0, color).astype(np.float32)


def material(nombre, datos):
    archivo = f"cristalera_{nombre}_color"
    alto, ancho = datos.shape[:2]
    img = bpy.data.images.new(archivo, ancho, alto, alpha=False)
    rgba = np.ones((alto, ancho, 4), np.float32)
    rgba[..., :3] = datos
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = str(TEXTURAS / f"{archivo}.png")
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    img = bpy.data.images.load(str(TEXTURAS / f"{archivo}.png"))
    img.name = archivo
    img.filepath = f"//../texturas/concatedral/{archivo}.png"
    mat = bpy.data.materials.new(f"Cristalera_{nombre}_NO")
    mat.use_nodes = True
    arbol = mat.node_tree
    bsdf = arbol.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.6
    bsdf.inputs["Specular IOR Level"].default_value = 0.15
    uv = arbol.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    tex = arbol.nodes.new("ShaderNodeTexImage")
    tex.image, tex.extension = img, "EXTEND"
    arbol.links.new(uv.outputs[0], tex.inputs[0])
    arbol.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    mat["textura"] = "vidrio emplomado generado por codigo (herramientas/i12_cristaleras_nave.py)"
    return mat


def renderizar(nombre):
    escena = bpy.context.scene
    datos = {v: pano(escena.objects[f"Concatedral_ventana_{v}_vidrio"]) for v in VENTANAS}
    n = datos["W1"][1]
    t = datos["W1"][0]
    sol = escena.objects["Sol_base"]
    sol.rotation_euler = (n + t * 0.5 + Vector((0, 0, 1.0))).normalized().to_track_quat("Z", "Y").to_euler()
    RENDERS.mkdir(parents=True, exist_ok=True)
    altas = sum((datos[v][7] for v in VENTANAS[:3]), Vector()) / 3
    vistas = [("altas", altas, 30.0, 55.0, 9.0), ("W4", datos["W4"][7], 11.0, 60.0, 2.5),
              ("W1", datos["W1"][7], 8.0, 70.0, 1.5)]
    for sufijo, mira, distancia, focal, bajar in vistas:
        cd = bpy.data.cameras.new(sufijo)
        cd.lens, cd.sensor_width = focal, 36.0
        cam = bpy.data.objects.new(sufijo, cd)
        escena.collection.objects.link(cam)
        cam.location = mira + n * distancia - Vector((0, 0, bajar))
        cam.rotation_euler = (mira - cam.location).to_track_quat("-Z", "Y").to_euler()
        escena.camera = cam
        escena.render.resolution_x, escena.render.resolution_y = 1600, 1100
        escena.render.resolution_percentage = 100
        escena.cycles.samples = 48
        escena.render.filepath = str(RENDERS / f"{nombre}_{sufijo}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", escena.render.filepath)


bpy.ops.wm.open_mainfile(filepath=str(BLEND))
assert bpy.context.scene.get("intervencion") == 11, "el maestro no es el de la intervencion 11"
if not COPIA.exists():
    shutil.copy2(BLEND, COPIA)
renderizar("antes")
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
escena = bpy.context.scene


def geometria():
    return {o.name: [tuple(v.co) for v in o.data.vertices] for o in escena.objects if o.type == "MESH"}


antes = geometria()
for numero, v in enumerate(VENTANAS, 1):
    o = escena.objects[f"Concatedral_ventana_{v}_vidrio"]
    t, n, eje, ancho, y0, alto, contorno, _ = pano(o)
    print("VIDRIO", v, "ancho", round(ancho, 3), "alto", round(alto, 3), "cota", round(y0, 2))
    mat = material(v, imagen(ancho, alto, contorno, 1229 + numero))
    me = o.data
    if "UVMap" not in me.uv_layers:
        me.uv_layers.new(name="UVMap")
    capa = me.uv_layers["UVMap"]
    for cara in me.polygons:
        for li in cara.loop_indices:
            p = o.matrix_world @ me.vertices[me.loops[li].vertex_index].co
            capa.data[li].uv = ((p.dot(t) - eje) / ancho + 0.5, (p.z - y0) / alto)
    me.uv_layers.active = capa
    me.materials.clear()
    me.materials.append(mat)
    o["origen"] = o.get("origen", "") + "; cristalera en la intervencion 12"
    o["provisional"] = "cristalera de diseno inventado, a peticion de Jorge"
assert antes == geometria(), "la intervencion no debe mover vertices"
escena["intervencion"] = 12
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True, relative_remap=False)
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
for i in bpy.data.images:
    if i.filepath.startswith("//"):
        assert Path(bpy.path.abspath(i.filepath)).exists(), i.filepath
renderizar("despues")
