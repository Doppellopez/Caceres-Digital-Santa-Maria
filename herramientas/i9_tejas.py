"""Intervencion 9: teja arabe curva en todas las cubiertas inclinadas.

Parte del .blend de la intervencion 8: lo copia a blender/copias/santa_maria_i8.blend
y siempre trabaja desde esa copia. Genera por codigo las texturas (color y normal)
en texturas/cubiertas/; no usa ninguna fotografia. No mueve vertices: asigna UV y
material a las caras de cubierta con pendiente entre PENDIENTE_MIN y PENDIENTE_MAX
y vuelve hacia arriba las de esas caras que miraban hacia abajo.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/i9_tejas.py
    ... -- --prueba        texturas y renders pequenos, sin guardar el maestro
    ... -- --sin-render
"""
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

RAIZ = Path(__file__).resolve().parents[1]
BLEND = RAIZ / "blender" / "santa_maria.blend"
COPIA = RAIZ / "blender" / "copias" / "santa_maria_i8.blend"
PRUEBA = "--prueba" in sys.argv
SIN_RENDER = "--sin-render" in sys.argv
TEXTURAS = (RAIZ / "renders" / "i9_prueba") if PRUEBA else (RAIZ / "texturas" / "cubiertas")
ANTES = RAIZ / "renders" / "i9_antes"
DESPUES = RAIZ / "renders" / ("i9_prueba" if PRUEBA else "i9_despues")

PENDIENTE_MIN, PENDIENTE_MAX = 5.0, 90.0    # grados; por debajo se considera azotea
GIRO_FALDON = 20.0                          # caras vecinas que comparten direccion de teja
COLUMNAS, HILERAS = 16, 10                  # tejas por repeticion de la textura
PASO, SOLAPE = 0.24, 0.36                   # m entre columnas y largo visible de cada teja
ANCHO_UV, ALTO_UV = COLUMNAS * PASO, HILERAS * SOLAPE
LADO = 2048
COBIJAS_V03 = ("Concatedral_nave", "Concatedral_ala_norte", "Concatedral_ala_sur",
               "Concatedral_abside")


# --- texturas -------------------------------------------------------------------
def ruido(rng, lado, celdas):
    """Ruido suave y repetible en [-1, 1]."""
    g = rng.uniform(-1.0, 1.0, (celdas, celdas))
    t = np.arange(lado) * celdas / lado
    i = t.astype(int)
    f = t - i
    f = f * f * (3 - 2 * f)
    j = (i + 1) % celdas
    filas = g[i] * (1 - f)[:, None] + g[j] * f[:, None]
    return filas[:, i] * (1 - f) + filas[:, j] * f


def teja():
    """Devuelve color (sRGB) y normal, ambos con la fila 0 ABAJO (alero)."""
    rng = np.random.default_rng(1229)
    x = (np.arange(LADO) + 0.5) / LADO * COLUMNAS       # en columnas
    y = (np.arange(LADO) + 0.5) / LADO * HILERAS        # en hileras, hacia la cumbrera
    X, Y = np.meshgrid(x, y)
    col = np.floor(X).astype(int)
    fx = X - col - 0.5                                  # -0.5..0.5 respecto al eje de la cobija

    # Cobija (teja que cubre): cada columna lleva un pequeno desfase propio.
    desfase = rng.uniform(-0.09, 0.09, COLUMNAS)
    yc = Y + desfase[col]
    t0 = yc - np.floor(yc)
    semi = 0.37 - 0.05 * t0                             # conica: mas ancha abajo
    arco = 0.11 * np.clip(1.0 - (fx / semi) ** 2, 0, 1)  # el canto visible es un arco
    yc = yc + arco
    fila_c = np.floor(yc).astype(int) % HILERAS
    t = yc - np.floor(yc)                               # 0 borde inferior, 1 bajo la siguiente
    q = fx / semi
    es_cobija = np.abs(q) < 1.0
    h_cobija = 0.025 + 0.062 * np.sqrt(np.clip(1.0 - 0.94 * q * q, 0, 1)) + 0.018 * (1.0 - t)

    # Canal: la columna intermedia, concava y con las juntas a media hilera.
    col_k = np.floor(X + 0.5).astype(int) % COLUMNAS
    fk = X - np.floor(X + 0.5)                          # -0.5..0.5 respecto al eje del canal
    yk = Y + 0.5 + desfase[col_k]
    fila_k = np.floor(yk).astype(int) % HILERAS
    tk = yk - np.floor(yk)
    h_canal = 0.045 * np.clip(fk / 0.22, -1, 1) ** 2 + 0.014 * (1.0 - tk)
    altura = np.where(es_cobija, h_cobija, h_canal)

    base = np.array([178, 106, 78], float) / 255.0
    tonos_c = (1.0 + rng.normal(0, 0.065, (HILERAS, COLUMNAS)))
    tonos_k = (1.0 + rng.normal(0, 0.055, (HILERAS, COLUMNAS)))
    calidez = rng.normal(0, 0.018, (HILERAS, COLUMNAS))
    tono = np.where(es_cobija, tonos_c[fila_c, col % COLUMNAS], tonos_k[fila_k, col_k] * 0.86)
    calor = np.where(es_cobija, calidez[fila_c, col % COLUMNAS], calidez[fila_k, col_k])
    color = base[None, None, :] * tono[..., None]
    color[..., 0] += calor
    color[..., 2] -= calor

    # Sombra propia, suave: bajo el labio de cada teja y junto a la cobija.
    labio_c = np.where(es_cobija, 1.0 - 0.42 * np.clip((t - 0.90) / 0.10, 0, 1), 1.0)
    labio_k = np.where(~es_cobija, 1.0 - 0.30 * np.clip((tk - 0.87) / 0.13, 0, 1), 1.0)
    junto = np.where(~es_cobija, 1.0 - 0.32 * np.clip((np.abs(fk) - 0.06) / 0.10, 0, 1), 1.0)
    canto = np.where(es_cobija, 1.0 + 0.10 * np.clip((0.035 - t) / 0.035, 0, 1), 1.0)
    # La curva de la teja: se oscurece hacia los flancos y brilla algo en el lomo.
    lomo = np.where(es_cobija, 1.09 - 0.40 * np.clip(np.abs(q), 0, 1) ** 2.2, 1.0)
    color *= (labio_c * labio_k * junto * canto * lomo)[..., None]
    grano = 0.045 * ruido(rng, LADO, 512) + 0.035 * ruido(rng, LADO, 128) + 0.04 * ruido(rng, LADO, 24)
    color = np.clip(color * (1.0 + grano)[..., None], 0, 1)

    # Normal (convencion OpenGL: X a la derecha, Y hacia la cumbrera).
    altura = altura + 0.0008 * ruido(rng, LADO, 384)
    dx = (np.roll(altura, -1, 1) - np.roll(altura, 1, 1)) / (2 * ANCHO_UV / LADO)
    dy = (np.roll(altura, -1, 0) - np.roll(altura, 1, 0)) / (2 * ALTO_UV / LADO)
    n = np.dstack((-np.clip(dx, -2.5, 2.5), -np.clip(dy, -2.5, 2.5), np.ones_like(altura)))
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return color.astype(np.float32), (0.5 + 0.5 * n).astype(np.float32)


def guardar(nombre, datos, es_color):
    img = bpy.data.images.new(nombre, LADO, LADO, alpha=False)
    if not es_color:
        img.colorspace_settings.name = "Non-Color"
    rgba = np.ones((LADO, LADO, 4), np.float32)
    rgba[..., :3] = datos
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = str(TEXTURAS / f"{nombre}.png")
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    img = bpy.data.images.load(str(TEXTURAS / f"{nombre}.png"))
    img.name = nombre
    if not es_color:
        img.colorspace_settings.name = "Non-Color"
    if not PRUEBA:
        img.filepath = f"//../texturas/cubiertas/{nombre}.png"
    return img


def material(color, normal):
    mat = bpy.data.materials.new("Teja_arabe_cubiertas")
    mat.use_nodes = True
    arbol = mat.node_tree
    bsdf = arbol.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.85
    uv = arbol.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    tex = arbol.nodes.new("ShaderNodeTexImage")
    tex.image = color
    tex_n = arbol.nodes.new("ShaderNodeTexImage")
    tex_n.image = normal
    mapa = arbol.nodes.new("ShaderNodeNormalMap")
    mapa.uv_map = "UVMap"
    arbol.links.new(uv.outputs[0], tex.inputs[0])
    arbol.links.new(uv.outputs[0], tex_n.inputs[0])
    arbol.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    arbol.links.new(tex_n.outputs["Color"], mapa.inputs["Color"])
    arbol.links.new(mapa.outputs["Normal"], bsdf.inputs["Normal"])
    mat["textura"] = "teja arabe generada por codigo (herramientas/i9_tejas.py)"
    return mat


# --- UV por faldones ------------------------------------------------------------
def es_cubierta(o):
    return (o.type == "MESH" and not o.hide_render
            and (o.name.endswith("_cubierta") or o.name in COBIJAS_V03
                 or o.name == "Concatedral_cubierta_cierre_provisional"))


def tejar(o, mat):
    me = o.data
    normal_m = o.matrix_world.to_3x3().inverted_safe().transposed()
    areas = {"teja": 0.0, "plana": 0.0, "empinada": 0.0}
    normal = {}                                     # cara -> normal hacia arriba
    voltear = []
    for p in me.polygons:
        n = (normal_m @ p.normal).normalized()
        arriba = -n if n.z < 0 else n
        pendiente = math.degrees(math.acos(min(1.0, arriba.z)))
        puntos = [o.matrix_world @ me.vertices[i].co for i in p.vertices]
        area = sum(((puntos[k] - puntos[0]).cross(puntos[k + 1] - puntos[0])).length / 2
                   for k in range(1, len(puntos) - 1))
        if pendiente < PENDIENTE_MIN:
            areas["plana"] += area
        elif pendiente > PENDIENTE_MAX:
            areas["empinada"] += area
        else:
            areas["teja"] += area
            normal[p.index] = (arriba, area)
            if n.z < 0:
                voltear.append(p.index)
    if not normal:
        return areas, 0, 0
    for i in voltear:
        me.polygons[i].flip()
    me.update()

    # Faldones: caras unidas por una arista (por posicion) y de orientacion parecida.
    def clave(i):
        return tuple(round(c, 3) for c in me.vertices[i].co)

    aristas = {}
    for i in normal:
        for a, b in me.polygons[i].edge_keys:
            aristas.setdefault(frozenset((clave(a), clave(b))), []).append(i)
    vecinas = {i: set() for i in normal}
    for caras in aristas.values():
        for i in caras:
            vecinas[i].update(c for c in caras if c != i)
    limite = math.cos(math.radians(GIRO_FALDON))
    faldones, hechas = [], set()
    for semilla in sorted(normal, key=lambda i: -normal[i][1]):  # primero las grandes
        if semilla in hechas:
            continue
        grupo, pila = [semilla], [semilla]
        hechas.add(semilla)
        while pila:
            for v in vecinas[pila.pop()]:
                if v not in hechas and normal[v][0].dot(normal[semilla][0]) >= limite:
                    hechas.add(v)
                    grupo.append(v)
                    pila.append(v)
        faldones.append(grupo)

    if "UVMap" not in me.uv_layers:
        me.uv_layers.new(name="UVMap")
    capa = me.uv_layers["UVMap"]
    for grupo in faldones:
        n = sum((normal[i][0] * normal[i][1] for i in grupo), Vector()).normalized()
        u = Vector((0, 0, 1)).cross(n).normalized()   # horizontal: alero
        v = n.cross(u).normalized()                   # pendiente arriba: canales
        for i in grupo:
            for li in me.polygons[i].loop_indices:
                p = o.matrix_world @ me.vertices[me.loops[li].vertex_index].co
                capa.data[li].uv = (p.dot(u) / ANCHO_UV, p.dot(v) / ALTO_UV)
    capa = me.uv_layers["UVMap"]
    me.uv_layers.active = capa
    capa.active_render = True

    if len(normal) == len(me.polygons):
        me.materials.clear()
        me.materials.append(mat)
        for p in me.polygons:
            p.material_index = 0
    else:
        assert len(me.materials) == 1, o.name
        me.materials.append(mat)
        for p in me.polygons:
            p.material_index = 1 if p.index in normal else 0
    return areas, len(faldones), len(voltear)


# --- renders --------------------------------------------------------------------
def camara(nombre, ojo, mira, focal=35.0, orto=None):
    datos = bpy.data.cameras.new(nombre)
    datos.lens, datos.sensor_width, datos.clip_end = focal, 36.0, 2000.0
    if orto:
        datos.type, datos.ortho_scale = "ORTHO", orto
    cam = bpy.data.objects.new(nombre, datos)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = ojo
    cam.rotation_euler = (Vector(mira) - Vector(ojo)).to_track_quat("-Z", "Y").to_euler()
    return cam


def sobre_faldon():
    """Ojo y punto de mira a unos metros del mayor faldon de Edificio_34."""
    o = bpy.data.objects["Edificio_34_cubierta"]
    nm = o.matrix_world.to_3x3().inverted_safe().transposed()
    validas = [p for p in o.data.polygons
               if 0.80 < abs((nm @ p.normal).normalized().z) < 0.96]
    cara = max(validas, key=lambda p: p.area)
    n = (nm @ cara.normal).normalized()
    n = -n if n.z < 0 else n
    mira = o.matrix_world @ cara.center
    desde = (Vector((n.x, n.y, 0)).normalized() + Vector((0, 0, 0.75))).normalized()
    return mira + desde * 13.0, mira


def renderizar(carpeta):
    """Solo con camaras creadas al vuelo; se llama sin guardar despues el .blend."""
    escena = bpy.context.scene
    carpeta.mkdir(parents=True, exist_ok=True)
    c = Vector((28.0, -2.0, 15.0))                   # concatedral
    vistas = [
        (camara("CAM_aerea_SO", c + Vector((-85, -85, 85)), c, 40.0), 2000, 1400),
        (camara("CAM_aerea_NE", c + Vector((85, 85, 85)), c, 40.0), 2000, 1400),
        (camara("CAM_tejado_cerca", *sobre_faldon(), 45.0), 1600, 1000),
        (camara("CAM_cenital_tejas", (0, 0, 300), (0, 0, 0), orto=170.0), 2000, 2000),
    ]
    for cam, ancho, alto in vistas:
        escena.camera = cam
        escena.render.resolution_x, escena.render.resolution_y = ancho, alto
        escena.render.resolution_percentage = 40 if PRUEBA else 100
        escena.cycles.samples = 16 if PRUEBA else 48
        escena.render.filepath = str(carpeta / f"{cam.name}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", escena.render.filepath)


# --- ejecucion ------------------------------------------------------------------
if not COPIA.exists():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    assert bpy.context.scene.get("intervencion") == 8, "el maestro no es el de la intervencion 8"
    shutil.copy2(BLEND, COPIA)
if not (SIN_RENDER or ANTES.exists()):
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    assert bpy.context.scene.get("intervencion") == 8, "no se puede sacar el 'antes'"
    renderizar(ANTES)
bpy.ops.wm.open_mainfile(filepath=str(COPIA))
assert bpy.context.scene.get("intervencion") == 8
escena = bpy.context.scene
if PRUEBA:
    # La copia esta una carpeta mas abajo: solo en memoria, para ver las texturas.
    for img in bpy.data.images:
        if img.filepath.startswith("//../"):
            img.filepath = "//../../" + img.filepath[5:]


def vertices():
    return {o.name: [tuple(v.co) for v in o.data.vertices]
            for o in escena.objects if o.type == "MESH"}


antes = vertices()
TEXTURAS.mkdir(parents=True, exist_ok=True)
color, normales = teja()
mat = material(guardar("teja_arabe_color", color, True),
               guardar("teja_arabe_normal", normales, False))
informe = {"pendiente_grados": [PENDIENTE_MIN, PENDIENTE_MAX],
           "textura_m": [ANCHO_UV, ALTO_UV], "textura_px": LADO, "objetos": {}}
for o in sorted((o for o in escena.objects if es_cubierta(o)), key=lambda o: o.name):
    areas, faldones, volteadas = tejar(o, mat)
    informe["objetos"][o.name] = {"m2": {k: round(v, 1) for k, v in areas.items()},
                                  "faldones": faldones, "caras_volteadas": volteadas}
assert antes == vertices(), "la intervencion no debe mover vertices"
objetos = informe["objetos"].values()
informe["total_m2"] = {k: round(sum(d["m2"][k] for d in objetos), 1)
                       for k in ("teja", "plana", "empinada")}
informe["cubiertas_con_teja"] = sum(d["m2"]["teja"] > 0 for d in objetos)
informe["cubiertas_sin_teja"] = sorted(n for n, d in informe["objetos"].items()
                                       if d["m2"]["teja"] == 0)
informe["vertices_modificados"] = 0
print("INFORME", json.dumps({k: v for k, v in informe.items() if k != "objetos"}))

escena["intervencion"] = 9
if not PRUEBA:
    escena.camera = bpy.data.objects["CAM_general"]
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True, relative_remap=False)
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    escena = bpy.context.scene
    for nombre in ("teja_arabe_color", "teja_arabe_normal"):
        img = bpy.data.images[nombre]
        assert (img.filepath.startswith("//") and Path(bpy.path.abspath(img.filepath)).exists()
                and img.size[0] == LADO), (nombre, img.filepath)
DESPUES.mkdir(parents=True, exist_ok=True)
(DESPUES / "informe.json").write_text(json.dumps(informe, indent=2), encoding="utf-8")
if not SIN_RENDER:
    renderizar(DESPUES)   # no se guarda el .blend despues
