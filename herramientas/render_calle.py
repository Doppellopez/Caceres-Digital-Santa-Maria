"""Vistas desde la calle (1,65 m sobre el suelo) alrededor de la concatedral.

Una camara por cada octante. La posicion se elige sola: suelo a cielo abierto,
sin paredes a menos de 1,2 m y con la mayor parte posible de la iglesia a la
vista. La camara queda horizontal y encuadra con desplazamiento de objetivo
(verticales paralelas). El sol se recoloca en cada vista a espaldas de la
camara. No guarda el .blend.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/render_calle.py
    ... -- --prueba         renders pequenos y rapidos en renders/calle/prueba
    ... -- --solo N,SO      renderiza solo esas vistas
    ... -- --salida calle_i7   guarda en renders/calle_i7 en vez de renders/calle
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

RAIZ = Path(__file__).resolve().parents[1]
BLEND = RAIZ / "blender" / "santa_maria.blend"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PRUEBA = "--prueba" in ARGS
SOLO = ARGS[ARGS.index("--solo") + 1].split(",") if "--solo" in ARGS else None
CARPETA = ARGS[ARGS.index("--salida") + 1] if "--salida" in ARGS else "calle"
SALIDA = RAIZ / "renders" / CARPETA / ("prueba" if PRUEBA else "")

ALTURA_OJOS = 1.65
SENSOR = 36.0
FOCAL_MIN, FOCAL_MAX = 14.0, 35.0
ANCHO, ALTO = (480, 360) if PRUEBA else (2000, 1500)
MUESTRAS = 8 if PRUEBA else 64
MARGEN = 1.07
SEPARACION = 12.0  # m minimos entre dos camaras
# acimut en grados desde el norte, hacia el este
OCTANTES = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SO": 225, "O": 270, "NO": 315}

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
escena = bpy.context.scene
for o in escena.objects:
    if o.hide_render:
        o.hide_viewport = True  # que los rayos vean lo mismo que el render
dg = bpy.context.evaluated_depsgraph_get()

iglesia = [o for o in escena.objects
           if o.type == "MESH" and not o.hide_render and o.name.startswith("Concatedral")]
vertices = [o.matrix_world @ v.co for o in iglesia for v in o.data.vertices]
minimo = Vector([min(p[i] for p in vertices) for i in range(3)])
maximo = Vector([max(p[i] for p in vertices) for i in range(3)])
centro = (minimo + maximo) / 2.0

# Muestra de puntos repartidos por la superficie, para medir lo visible.
caras = []
for o in iglesia:
    m = o.matrix_world
    normal_m = m.to_3x3().inverted_safe().transposed()
    for p in o.data.polygons:
        n = (normal_m @ p.normal).normalized()
        if abs(n.z) < 0.5:
            caras.append((m @ p.center, p.area * m.median_scale ** 2))
total_area = sum(a for _, a in caras)
muestra, acumulado, paso = [], 0.0, total_area / 500.0
for c, a in caras:
    acumulado += a
    while acumulado >= paso:
        muestra.append(c)
        acumulado -= paso


def rayo(origen, direccion, distancia=1000.0):
    ok, punto, _, _, objeto, _ = escena.ray_cast(dg, origen, direccion, distance=distancia)
    return (punto, objeto) if ok else (None, None)


def posicion_valida(x, y):
    punto, objeto = rayo(Vector((x, y, 200.0)), Vector((0, 0, -1)))
    if objeto is None or not (objeto.name.startswith("Terreno") or "peldano" in objeto.name.lower()):
        return None
    ojo = Vector((x, y, punto.z + ALTURA_OJOS))
    for k in range(24):
        a = k * math.tau / 24
        if rayo(ojo, Vector((math.sin(a), math.cos(a), 0)), 1.2)[1] is not None:
            return None
    return ojo


def cielo(ojo):
    """Fraccion de cielo libre (o iglesia) mirando hacia arriba: evita rincones."""
    libres = total = 0
    for elevacion in (35, 55, 75):
        for k in range(16):
            a, e = k * math.tau / 16, math.radians(elevacion)
            d = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
            objeto = rayo(ojo, d)[1]
            libres += objeto is None or objeto.name.startswith("Concatedral")
            total += 1
    return libres / total


def visibles(ojo):
    n = 0
    for p in muestra:
        d = p - ojo
        largo = d.length
        punto, objeto = rayo(ojo, d / largo, largo + 0.5)
        if objeto is not None and objeto.name.startswith("Concatedral") and (punto - p).length < 0.4:
            n += 1
    return n / len(muestra)


def encuadre(ojo):
    """Focal y desplazamiento para que quepa la iglesia con la camara horizontal."""
    mira = Vector((centro.x - ojo.x, centro.y - ojo.y, 0)).normalized()
    derecha = Vector((mira.y, -mira.x, 0))
    xs, ys = [], []
    for p in vertices:
        d = p - ojo
        z = d.dot(mira)
        if z > 1.0:
            xs.append(d.dot(derecha) / z)
            ys.append(d.z / z)
    if not xs:
        return None
    # Se gira hacia el centro de lo proyectado para que el encuadre quede centrado.
    giro = math.atan((min(xs) + max(xs)) / 2.0)
    mira = (mira * math.cos(giro) + derecha * math.sin(giro)).normalized()
    derecha = Vector((mira.y, -mira.x, 0))
    xs, ys = [], []
    for p in vertices:
        d = p - ojo
        z = d.dot(mira)
        if z > 1.0:
            xs.append(d.dot(derecha) / z)
            ys.append(d.z / z)
    semi_x = max(abs(min(xs)), abs(max(xs))) * MARGEN
    abajo, arriba = -ALTURA_OJOS / 8.0, max(ys)
    alto = (arriba - abajo) * MARGEN
    focal_justa = min(SENSOR / (2 * semi_x), SENSOR * ALTO / ANCHO / alto)
    focal = min(FOCAL_MAX, max(FOCAL_MIN, focal_justa))
    desplazamiento = (arriba + abajo) / 2.0 * focal / SENSOR
    return mira, focal, desplazamiento, focal_justa


sol = bpy.data.objects.get("Sol_base")
vistas, elegidas = {}, []
for nombre, acimut in OCTANTES.items():
    if SOLO and nombre not in SOLO:
        continue
    candidatas = []
    for desvio in range(-20, 21, 5):
        a = math.radians(acimut + desvio)
        r = 10.0
        while r <= 70.0:
            ojo = posicion_valida(centro.x + r * math.sin(a), centro.y + r * math.cos(a))
            r += 1.5
            if ojo is None or any((ojo - otra).length < SEPARACION for otra in elegidas):
                continue
            e = encuadre(ojo)
            if e is None:
                continue
            ve = visibles(ojo)
            # Se penaliza que la iglesia no quepa ni con la focal mas corta.
            cabe = min(1.0, e[3] / FOCAL_MIN)
            candidatas.append((ve * cabe ** 6 * cielo(ojo) ** 2, ve, ojo, e))
    if not candidatas:
        vistas[nombre] = {"sin_posicion": True}
        print("SIN_POSICION", nombre)
        continue
    _, ve, ojo, (mira, focal, desplazamiento, focal_justa) = max(candidatas, key=lambda c: c[0])
    vistas[nombre] = {
        "posicion": [round(v, 3) for v in ojo],
        "rumbo_grados": round(math.degrees(math.atan2(mira.x, mira.y)) % 360, 1),
        "focal_mm": round(focal, 1),
        "desplazamiento_y": round(desplazamiento, 4),
        "iglesia_a_la_vista": round(ve, 3),
        "cabe_entera": focal_justa >= FOCAL_MIN,
    }
    vistas[nombre]["cielo_libre"] = round(cielo(ojo), 3)
    elegidas.append(ojo)
    print("VISTA", nombre, vistas[nombre])
    # Sol a espaldas de la camara (35 grados a un lado, 45 de altura) para que
    # la fachada fotografiada se lea; no es la posicion real del sol.
    rumbo = math.atan2(-mira.x, -mira.y) + math.radians(35)
    desde = Vector((math.sin(rumbo), math.cos(rumbo), 1.0)).normalized()
    sol.rotation_euler = desde.to_track_quat("Z", "Y").to_euler()

    datos = bpy.data.cameras.new(f"CAM_calle_{nombre}")
    datos.lens, datos.sensor_width, datos.sensor_fit = focal, SENSOR, "HORIZONTAL"
    datos.shift_y = desplazamiento
    datos.clip_end = 1000.0
    cam = bpy.data.objects.new(datos.name, datos)
    escena.collection.objects.link(cam)
    cam.location = ojo
    cam.rotation_euler = mira.to_track_quat("-Z", "Y").to_euler()
    escena.camera = cam
    escena.render.resolution_x, escena.render.resolution_y = ANCHO, ALTO
    escena.render.resolution_percentage = 100
    escena.cycles.samples = MUESTRAS
    escena.render.filepath = str(SALIDA / f"{datos.name}.png")
    SALIDA.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print("RENDER", escena.render.filepath)

registro = SALIDA / "registro.json"
if registro.exists():
    vistas = {**json.loads(registro.read_text(encoding="utf-8"))["vistas"], **vistas}
registro.write_text(json.dumps({
    "blender": bpy.app.version_string,
    "origen": BLEND.relative_to(RAIZ).as_posix(),
    "altura_ojos_m": ALTURA_OJOS,
    "resolucion": [ANCHO, ALTO],
    "muestras": MUESTRAS,
    "sensor_mm": SENSOR,
    "vistas": vistas,
}, indent=2, ensure_ascii=False), encoding="utf-8")
