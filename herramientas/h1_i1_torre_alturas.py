"""H1, intervencion 1: torre y alturas de la fachada noroeste segun el levantamiento.

Parte del .blend de H0. Antes de tocarlo lo copia a blender/copias/santa_maria_h0.blend
y siempre trabaja desde esa copia, asi que se puede repetir sin acumular cambios.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/h1_i1_torre_alturas.py
    ... -- --sin-render    aplica y guarda sin renderizar
"""
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.geometry import intersect_line_line_2d, tessellate_polygon

RAIZ = Path(__file__).resolve().parents[1]
BLEND = RAIZ / "blender" / "santa_maria.blend"
COPIA = RAIZ / "blender" / "copias" / "santa_maria_h0.blend"
DXF = RAIZ / "datos" / "locales" / "santa_maria_dxf_local.json"
ANTES = RAIZ / "renders" / "h1_i1_antes"
DESPUES = RAIZ / "renders" / "h1_i1_despues"
SIN_RENDER = "--sin-render" in sys.argv

registro = json.loads(DXF.read_text(encoding="utf-8"))[
    "/mnt/data/work/trama urbana_2012_3D.dxf"][1688]
P = [Vector((p[0], p[1], p[2] - 440.0)) for p in registro[2]]

if not COPIA.exists():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    assert "intervencion" not in bpy.context.scene, "el maestro ya no es el de H0"
    COPIA.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BLEND, COPIA)
bpy.ops.wm.open_mainfile(filepath=str(COPIA))
escena = bpy.context.scene


def obj(nombre):
    return bpy.data.objects["Concatedral_" + nombre]


def mundo(o):
    return [o.matrix_world @ v.co for v in o.data.vertices]


def cubierta_descubierta():
    """Porcentaje de la planta municipal sin nada de la concatedral por encima de z=9."""
    quien = [o for o in escena.objects if o.type == "MESH" and o.visible_get()
             and o.name.startswith("Concatedral")]
    poligono = [(p.x, p.y) for p in P]

    def dentro(x, y):
        n = False
        for (x1, y1), (x2, y2) in zip(poligono, poligono[1:] + poligono[:1]):
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) / (y2 - y1) * (x2 - x1):
                n = not n
        return n

    total = libres = 0
    x = 5.0
    while x < 47.5:
        y = -25.0
        while y < 21.5:
            if dentro(x, y):
                total += 1
                tocado = False
                for o in quien:
                    inv = o.matrix_world.inverted()
                    d = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
                    ok, p, _, _ = o.ray_cast(inv @ Vector((x, y, 60.0)), d)
                    if ok and (o.matrix_world @ p).z > 9.0:
                        tocado = True
                        break
                libres += not tocado
            y += 0.25
        x += 0.25
    return round(100.0 * libres / total, 2)


def camara_inspeccion():
    datos = bpy.data.cameras.new("CAM_inspeccion_suroeste")
    datos.lens = 45.0
    c = bpy.data.objects.new("CAM_inspeccion_suroeste", datos)
    bpy.data.collections["Camaras_y_luz"].objects.link(c)
    c.location = (-38.0, -55.0, 62.0)
    c.rotation_euler = (Vector((17.0, -8.0, 11.0)) - c.location).to_track_quat("-Z", "Y").to_euler()


def renderizar(carpeta, camaras):
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre in camaras:
        escena.camera = bpy.data.objects[nombre]
        escena.render.filepath = str(carpeta / f"{nombre}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", escena.render.filepath)


camara_inspeccion()
descubierta_antes = cubierta_descubierta()
if not SIN_RENDER:
    renderizar(ANTES, ["CAM_inspeccion_suroeste"])

# --- datos de partida -------------------------------------------------------
fach = obj("fachadas")
V = mundo(fach)
material_muro = fach.data.materials[0]
capa = fach.data.color_attributes[0]
nombre_capa = capa.name
color_muro = tuple(capa.data[0].color)
cubierta_ref = obj("nave")
material_cubierta = cubierta_ref.data.materials[0]
color_cubierta = tuple(cubierta_ref.data.color_attributes[0].data[0].color)

suelo = {}   # cota del pie de muro en cada punto del contorno
cuadros = {}  # (i, j) -> primer vertice del pano que va del punto i al j
for k in range(0, len(V), 4):
    ids = [min(range(len(P)), key=lambda i: (P[i].xy - v.xy).length) for v in V[k:k + 4]]
    assert ids[0] == ids[3] and ids[1] == ids[2]
    cuadros[(ids[0], ids[1])] = k
    suelo[ids[0]], suelo[ids[1]] = V[k].z, V[k + 1].z

# Sentido del contorno: decide hacia donde mira cada pano.
area = sum(a.x * b.y - b.x * a.y for a, b in zip(P, P[1:] + P[:1])) / 2.0
CCW = area > 0


class Malla:
    def __init__(self):
        self.v, self.f = [], []

    def cara(self, puntos):
        n = len(self.v)
        self.v.extend(Vector(p) for p in puntos)
        self.f.append(list(range(n, n + len(puntos))))

    def muro(self, a, b, za, zb, base_a, base_b):
        """Pano vertical del punto a al b, recorrido en el sentido del contorno."""
        q = [(a.x, a.y, base_a), (b.x, b.y, base_b), (b.x, b.y, zb), (a.x, a.y, za)]
        if not CCW:
            q.reverse()
        self.cara([q[0], q[1], q[2]])
        self.cara([q[0], q[2], q[3]])

    def tapa(self, puntos):
        """Superficie superior, siempre con la normal hacia arriba."""
        for tri in tessellate_polygon([[Vector((p[0], p[1], 0)) for p in puntos]]):
            a, b, c = (Vector(puntos[i]) for i in tri)
            if (b - a).cross(c - a).z < 0:
                b, c = c, b
            self.cara([a, b, c])

    def aplicar(self, o, color):
        """Sustituye la geometria de o (coordenadas de mundo) conservando nombre."""
        inv = o.matrix_world.inverted()
        viejo = o.data
        nombre, material = viejo.name, viejo.materials[0] if viejo.materials else None
        viejo.name = nombre + "_h0"
        me = bpy.data.meshes.new(nombre)
        me.from_pydata([inv @ v for v in self.v], [], self.f)
        me.update()
        capa_color = me.color_attributes.new(nombre_capa, "BYTE_COLOR", "POINT")
        for d in capa_color.data:
            d.color = color
        if material:
            me.materials.append(material)
        o.data = me
        bpy.data.meshes.remove(viejo)

    def crear(self, nombre, coleccion, material, color, provisional):
        me = bpy.data.meshes.new("Concatedral_" + nombre)
        me.materials.append(material)
        o = bpy.data.objects.new(me.name, me)
        coleccion.objects.link(o)
        self.aplicar(o, color)
        o["provisional"] = provisional
        o["origen"] = "H1 intervencion 1; contorno DXF registro 1688"
        return o


def en_planta(x, y, puntos):
    n = False
    for a, b in zip(puntos, puntos[1:] + puntos[:1]):
        if (a.y > y) != (b.y > y) and x < a.x + (y - a.y) / (b.y - a.y) * (b.x - a.x):
            n = not n
    return n


def prisma(puntos_exteriores, cierre, cota):
    """Volumen bajo: panos por los puntos exteriores y tapa hasta los puntos de cierre."""
    m = Malla()
    for (a, base_a), (b, base_b) in zip(puntos_exteriores, puntos_exteriores[1:]):
        m.muro(a, b, cota, cota, base_a, base_b)
    contorno = [p for p, _ in puntos_exteriores] + cierre
    # Comprobacion: todos los panos deben mirar hacia fuera de su planta.
    for cara in m.f:
        a, b, c = (m.v[i] for i in cara)
        n = (b - a).cross(c - a).normalized()
        fuera = (a + b + c) / 3.0 + n * 0.005
        assert not en_planta(fuera.x, fuera.y, contorno), "pano mirando hacia dentro"
    m.tapa([(p.x, p.y, cota) for p in contorno])
    return m


def pto(i):
    return (P[i], suelo[i])


def proyectar_en_muro(p):
    """Punto del muro principal (recta 59-67) mas cercano a p, con su cota de pie."""
    a, b = P[59].xy, P[67].xy
    t = (p.xy - a).dot(b - a) / (b - a).length_squared
    q = a + (b - a) * t
    return Vector((q.x, q.y, 0.0)), suelo[59] + (suelo[67] - suelo[59]) * t


col = bpy.data.collections["Concatedral"]

# --- 1. Muros: alturas medidas en el noroeste -------------------------------
cota_muro = {i: P[i].z for i in range(47, 69)}
# Puntos 49 y 50 (17,37): remate de 0,2 m que como muro quedaba en aguja. Se omite.
cota_muro[49] = P[48].z + (P[51].z - P[48].z) / 3.0
cota_muro[50] = P[48].z + (P[51].z - P[48].z) * 2.0 / 3.0
# Punto 67 (15,88): inclinaba 1 m el muro; en las fotos el pretil es horizontal.
cota_muro[67] = P[66].z
muros = Malla()
cambiados = {(i, i + 1) for i in range(47, 59)}
proyecciones = {(i, i + 1) for i in range(59, 67)}
torre_ids = {k for k in cuadros if 68 <= k[0] and k[1] <= 87}
for (i, j), k in sorted(cuadros.items(), key=lambda kv: kv[1]):
    if (i, j) in proyecciones or (i, j) in torre_ids:
        continue
    q = [v.copy() for v in V[k:k + 4]]
    if (i, j) in cambiados:
        q[2].z, q[3].z = cota_muro[j], cota_muro[i]
    elif (i, j) == (67, 68):
        q[2].z = q[3].z = cota_muro[67]  # la cota 23,0 del punto 68 es de la torre
    muros.cara([q[0], q[1], q[2]])
    muros.cara([q[0], q[2], q[3]])
assert cambiados <= set(cuadros) and (67, 68) in cuadros
muros.muro(P[59], P[67], cota_muro[59], cota_muro[67], suelo[59], suelo[67])
muros.aplicar(fach, color_muro)

# --- 2. Cuerpos salientes de la portada -------------------------------------
cota_portada, cota_escalon = P[63].z, P[60].z
q_der, base_q = proyectar_en_muro(P[65])
q_izq, base_r = proyectar_en_muro(P[62])
nota_fondo = "frente medido; fondo apoyado en la recta 59-67 (interpolada)"
prisma([(q_der, base_q), pto(65), pto(66), pto(67)], [], P[65].z).crear(
    "contrafuerte_portada", col, material_muro, color_muro, nota_fondo)
prisma([(q_izq, base_r), pto(62), pto(63), pto(64), (q_der, base_q)], [], cota_portada).crear(
    "cuerpo_portada", col, material_muro, color_muro, nota_fondo)
prisma([pto(59), pto(60), pto(61), pto(62), (q_izq, base_r)], [], cota_escalon).crear(
    "cuerpo_escalonado", col, material_muro, color_muro,
    nota_fondo + "; el remate real parece inclinado")

# --- 3. Torre ----------------------------------------------------------------
cima = P[79].z
esquina_interior = P[87] + (P[69] - P[79])
esquina_interior.z = cima
base_interior = min(suelo[69], suelo[87])
torre = Malla()
recorrido = [68, 69, 70, 71, 72, 73, 74, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87]
for a, b in zip(recorrido, recorrido[1:]):
    torre.muro(P[a], P[b], cima, cima, suelo[a], suelo[b])
torre.aplicar(obj("torre_fachadas"), color_muro)

tapa = Malla()
contorno_torre = [P[i] for i in recorrido[1:]] + [esquina_interior]
tapa.tapa([(p.x, p.y, cima) for p in contorno_torre])
tapa.aplicar(obj("torre_cubierta"), color_cubierta)
obj("torre_cubierta")["provisional"] = "incluye la esquina interior supuesta"

interior = Malla()
interior.muro(P[87], esquina_interior, cima, cima, suelo[87], base_interior)
interior.muro(esquina_interior, P[69], cima, cima, base_interior, suelo[69])
interior.crear("torre_interior_provisional", col, material_muro, color_muro,
               "esquina interior supuesta como paralelogramo; no esta en el DXF")

prisma([pto(74), pto(75), pto(76), pto(77), pto(78)], [], P[75].z).crear(
    "contrafuerte_torre", col, material_muro, color_muro, "tapa plana supuesta")

# --- 4. Cubiertas ------------------------------------------------------------
ala = obj("ala_sur")
va = mundo(ala)
fuera = {i for i, v in enumerate(va)
         if min((v.xy - P[61].xy).length, (v.xy - P[64].xy).length) < 0.05}
caras = [list(f.vertices) for f in ala.data.polygons if not fuera & set(f.vertices)]
print("ALA_SUR caras retiradas sobre la portada:", len(ala.data.polygons) - len(caras))
assert len(ala.data.polygons) - len(caras) == 2
# Un triangulo del ala asomaba unos 6 cm por la cara noroeste de la torre.
asoman = {i for i, v in enumerate(va) if (v.xy - Vector((8.39, -4.0))).length < 0.05}
antes_torre = len(caras)
caras = [f for f in caras if not asoman & set(f)]
assert antes_torre - len(caras) >= 1
recorte = Malla()
for f in caras:
    recorte.cara([va[i] for i in f])
color_ala = tuple(ala.data.color_attributes[0].data[0].color)
recorte.aplicar(ala, color_ala)

nave = mundo(obj("nave"))
alan = mundo(obj("ala_norte"))


def cerca(lista, x, y):
    v = min(lista, key=lambda v: (v.x - x) ** 2 + (v.y - y) ** 2)
    assert math.hypot(v.x - x, v.y - y) < 0.05, (x, y)
    return v


n1, n2 = cerca(nave, 13.79, -9.13), cerca(nave, 20.75, -15.75)
a1 = cerca(alan, 26.83, -21.53)
corte = intersect_line_line_2d(n1.xy, n2.xy, P[87].xy, esquina_interior.xy)
assert corte is not None
x_punto = Vector((corte.x, corte.y, n2.z))
borde = max(v.z for v in V)                 # alero v0.3 del lado suroeste
cierre = [x_punto, n2, a1] + [Vector((P[i].x, P[i].y, borde)) for i in range(96, 86, -1)]
panel = Malla()
panel.tapa([tuple(p) for p in cierre])
panel.crear("cubierta_cierre_provisional", col, material_cubierta, color_cubierta,
            "cierra el hueco junto a la torre; no representa la cubierta real")

# --- 5. Elementos v0.3 que chocan con la geometria nueva ----------------------
ocultos = bpy.data.collections.new("Concatedral_v03_ocultos")
escena.collection.children.link(ocultos)
for n in (2, 3, 4):
    o = obj(f"contrafuerte_{n}")
    for c in list(o.users_collection):
        c.objects.unlink(o)
    ocultos.objects.link(o)
    o.hide_viewport = o.hide_render = True
    o["motivo_oculto"] = "invade la torre o los cuerpos de la portada del levantamiento"
bpy.context.view_layer.update()

escena["intervencion"] = 1
descubierta_despues = cubierta_descubierta()
escena.camera = bpy.data.objects["CAM_general"]
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)

degeneradas = [o.name for o in escena.objects if o.type == "MESH"
               and o.name.startswith("Concatedral")
               and any(f.area < 1e-6 for f in o.data.polygons)]
informe = {
    "planta_sin_cubrir_pct": {"antes": descubierta_antes, "despues": descubierta_despues},
    "contorno_antihorario": CCW,
    "torre": {"cota": round(cima, 2), "esquina_interior_supuesta":
              [round(c, 2) for c in esquina_interior]},
    "cota_cuerpo_portada": round(cota_portada, 2),
    "cota_cuerpo_escalonado": round(cota_escalon, 2),
    "cotas_no_aplicadas": {"49-50": round(P[49].z, 2), "67": round(P[67].z, 2)},
    "ocultos": [f"Concatedral_contrafuerte_{n}" for n in (2, 3, 4)],
    "objetos_con_caras_degeneradas": degeneradas,
}
DESPUES.mkdir(parents=True, exist_ok=True)
(DESPUES / "informe.json").write_text(json.dumps(informe, indent=2), encoding="utf-8")
print("INFORME", json.dumps(informe))
if not SIN_RENDER:
    renderizar(DESPUES, ["CAM_general", "CAM_peaton_noroeste", "CAM_peaton_oeste_torre",
                         "CAM_inspeccion_suroeste"])
