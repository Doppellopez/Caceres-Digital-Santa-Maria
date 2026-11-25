"""H0: crea el .blend maestro inicial a partir de v0.3 y saca los renders base.

No altera la geometria de v0.3. Unica reparacion de importacion: el GLB contiene
10 mallas de contrafuerte pero solo 1 esta enlazada a un nodo (nombres de nodo
repetidos al exportar). Las 9 huerfanas se leen del propio GLB, sin tocar sus
coordenadas, y quedan en una coleccion aparte para poder ocultarlas.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/h0_baseline.py
    ... -- --forzar        sobrescribe blender/santa_maria.blend
    ... -- --solo-render   abre el .blend existente y solo vuelve a renderizar
"""
import json
import math
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Vector

RAIZ = Path(__file__).resolve().parents[1]
GLB = RAIZ / "modelos" / "v0.3" / "santa_maria_v0_3.glb"
BLEND = RAIZ / "blender" / "santa_maria.blend"
SALIDA = RAIZ / "renders" / "h0_baseline"

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SOLO_RENDER = "--solo-render" in ARGS

ALTURA_OJOS = 1.65
# nombre: (x, y, punto al que mira, focal mm). La Z de las peatonales sale del terreno.
CAMARAS = {
    "CAM_general": ((-75.0, 62.0, 78.0), (14.0, -6.0, 6.0), 40.0),
    "CAM_peaton_noroeste": ((-5.0, 16.0, None), (17.0, 1.0, 8.0), 20.0),
    "CAM_peaton_oeste_torre": ((-5.5, 2.0, None), (14.0, -13.0, 11.0), 20.0),
}
RESOLUCION = (1600, 1000)
MUESTRAS = 48


def leer_glb(ruta):
    datos = ruta.read_bytes()
    n = struct.unpack("<I", datos[12:16])[0]
    cabecera = json.loads(datos[20:20 + n])
    return cabecera, datos[20 + n + 8:]


def accesor(cab, binario, indice):
    a = cab["accessors"][indice]
    vista = cab["bufferViews"][a["bufferView"]]
    n_comp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
    letra = {5121: "B", 5123: "H", 5125: "I", 5126: "f"}[a["componentType"]]
    fmt = "<" + letra * n_comp
    paso = vista.get("byteStride", struct.calcsize(fmt))
    base = vista.get("byteOffset", 0) + a.get("byteOffset", 0)
    return [struct.unpack_from(fmt, binario, base + i * paso) for i in range(a["count"])]


def coleccion(nombre):
    c = bpy.data.collections.get(nombre)
    if c is None:
        c = bpy.data.collections.new(nombre)
        bpy.context.scene.collection.children.link(c)
    return c


def mover(obj, destino):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    destino.objects.link(obj)


def recuperar_huerfanas(modelo):
    """Crea objetos para las mallas del GLB que ningun nodo referencia."""
    cab, binario = leer_glb(GLB)
    usadas = {n["mesh"] for n in cab["nodes"] if "mesh" in n}
    destino = coleccion("Concatedral_recuperados_GLB")
    modelo_mat = modelo.data.materials[0]
    creadas = []
    for i, malla in enumerate(cab["meshes"]):
        if i in usadas:
            continue
        prim = malla["primitives"][0]
        # Los vertices del GLB estan en Z arriba (la rotacion va en el nodo raiz),
        # igual que el unico contrafuerte que si se importa.
        verts = accesor(cab, binario, prim["attributes"]["POSITION"])
        idx = [t[0] for t in accesor(cab, binario, prim["indices"])]
        caras = [idx[k:k + 3] for k in range(0, len(idx), 3)]
        nombre = malla["name"]
        if nombre == "Concatedral_contrafuerte":
            nombre += "_0"
        me = bpy.data.meshes.new(nombre)
        me.from_pydata(verts, [], caras)
        me.update()
        colores = accesor(cab, binario, prim["attributes"]["COLOR_0"])
        nombre_col = modelo.data.color_attributes[0].name
        capa = me.color_attributes.new(nombre_col, "BYTE_COLOR", "POINT")
        for k, c in enumerate(colores):
            rgba = [v / 255.0 for v in c] + [1.0] * (4 - len(c))
            capa.data[k].color = rgba[:4]
        me.materials.append(modelo_mat)
        o = bpy.data.objects.new(nombre, me)
        destino.objects.link(o)
        creadas.append(o.name)
    return creadas


def importar():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    escena = bpy.context.scene
    escena.unit_settings.system = "METRIC"
    escena.unit_settings.scale_length = 1.0
    mallas = [o for o in escena.objects if o.type == "MESH"]
    terreno = coleccion("Terreno")
    cate = coleccion("Concatedral")
    resto = coleccion("Edificios")
    for o in mallas:
        mundo = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mundo
        if o.name.startswith("Terreno"):
            mover(o, terreno)
        elif o.name.startswith("Concatedral"):
            mover(o, cate)
        else:
            mover(o, resto)
    for o in [o for o in escena.objects if o.type == "EMPTY"]:
        bpy.data.objects.remove(o)
    # El unico enlazado es la malla _9 pese a llamarse sin sufijo.
    modelo = bpy.data.objects["Concatedral_contrafuerte"]
    modelo.name = modelo.data.name = "Concatedral_contrafuerte_9"
    creadas = recuperar_huerfanas(modelo)
    print("IMPORTADAS", len(mallas), "RECUPERADAS", len(creadas), creadas)
    return len(mallas), creadas


def altura_terreno(x, y):
    t = bpy.data.objects["Terreno_interpolado"]
    inv = t.matrix_world.inverted()
    origen = inv @ Vector((x, y, 200.0))
    direccion = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
    ok, punto, _, _ = t.ray_cast(origen, direccion)
    if not ok:
        raise RuntimeError(f"Sin terreno bajo ({x}, {y})")
    return (t.matrix_world @ punto).z


def preparar_escena():
    escena = bpy.context.scene
    camaras = coleccion("Camaras_y_luz")
    registro = {}
    for nombre, ((x, y, z), objetivo, focal) in CAMARAS.items():
        suelo = None
        if z is None:
            suelo = altura_terreno(x, y)
            z = suelo + ALTURA_OJOS
            dg = bpy.context.evaluated_depsgraph_get()
            ok, _, _, _, primero, _ = escena.ray_cast(dg, (x, y, 200.0), (0, 0, -1))
            if not ok or primero.name != "Terreno_interpolado":
                raise RuntimeError(f"{nombre}: ({x}, {y}) no es suelo a cielo abierto")
        datos = bpy.data.cameras.new(nombre)
        datos.lens = focal
        datos.sensor_width = 36.0
        cam = bpy.data.objects.new(nombre, datos)
        camaras.objects.link(cam)
        cam.location = (x, y, z)
        mira = Vector(objetivo) - Vector((x, y, z))
        cam.rotation_euler = mira.to_track_quat("-Z", "Y").to_euler()
        registro[nombre] = {
            "posicion": [round(x, 3), round(y, 3), round(z, 3)],
            "mira_a": list(objetivo),
            "rotacion_xyz_grados": [round(math.degrees(a), 3) for a in cam.rotation_euler],
            "focal_mm": focal,
            "sensor_mm": 36.0,
            "cota_suelo": None if suelo is None else round(suelo, 3),
        }
    sol_datos = bpy.data.lights.new("Sol_base", "SUN")
    sol_datos.energy = 2.0
    sol_datos.angle = math.radians(0.5)
    sol_datos.color = (1.0, 0.96, 0.9)
    sol = bpy.data.objects.new("Sol_base", sol_datos)
    camaras.objects.link(sol)
    # Luz de tarde desde el oeste, para que las fachadas de la plaza se lean.
    desde = Vector((-0.75, 0.15, 0.65)).normalized()
    sol.rotation_euler = desde.to_track_quat("Z", "Y").to_euler()

    mundo = bpy.data.worlds.new("Cielo_base")
    escena.world = mundo
    fondo = mundo.node_tree.nodes["Background"]
    fondo.inputs["Color"].default_value = (0.55, 0.68, 0.85, 1.0)
    fondo.inputs["Strength"].default_value = 0.45

    escena.render.engine = "CYCLES"
    escena.cycles.device = "CPU"
    escena.cycles.samples = MUESTRAS
    escena.cycles.use_denoising = True
    escena.cycles.seed = 0
    escena.render.resolution_x, escena.render.resolution_y = RESOLUCION
    escena.render.image_settings.file_format = "PNG"
    escena.view_settings.view_transform = "Standard"
    escena.camera = bpy.data.objects["CAM_general"]
    return registro


def renderizar():
    escena = bpy.context.scene
    SALIDA.mkdir(parents=True, exist_ok=True)
    for nombre in CAMARAS:
        escena.camera = bpy.data.objects[nombre]
        escena.render.filepath = str(SALIDA / f"{nombre}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", escena.render.filepath)
    escena.camera = bpy.data.objects["CAM_general"]


if SOLO_RENDER:
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    renderizar()
else:
    if BLEND.exists() and "--forzar" not in ARGS:
        raise SystemExit(f"{BLEND} ya existe; usa --forzar o --solo-render")
    n_importadas, creadas = importar()
    registro = preparar_escena()
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)
    renderizar()
    mallas = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    (SALIDA / "registro.json").write_text(json.dumps({
        "blender": bpy.app.version_string,
        "origen_modelo": str(GLB.relative_to(RAIZ).as_posix()),
        "motor": "Cycles CPU",
        "muestras": MUESTRAS,
        "denoise": True,
        "transformacion_de_vista": "Standard",
        "resolucion": list(RESOLUCION),
        "mallas_importadas": n_importadas,
        "mallas_recuperadas": creadas,
        "mallas_total": len(mallas),
        "camaras": registro,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print("TOTAL_MALLAS", len(mallas))
