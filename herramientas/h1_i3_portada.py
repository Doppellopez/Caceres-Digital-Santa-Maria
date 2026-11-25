"""H1, intervencion 3: portada de la fachada noroeste.

Parte del .blend de la intervencion 2: lo copia a blender/copias/santa_maria_i2.blend
y siempre trabaja desde esa copia. Medidas en referencias/medidas_portada.json
(h1_medir_portada.py).

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/h1_i3_portada.py
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
COPIA = RAIZ / "blender" / "copias" / "santa_maria_i2.blend"
ANTES = RAIZ / "renders" / "h1_i3_antes"
DESPUES = RAIZ / "renders" / "h1_i3_despues"
SIN_RENDER = "--sin-render" in sys.argv

M = json.loads((RAIZ / "referencias" / "medidas_portada.json").read_text(encoding="utf-8"))
registro = json.loads((RAIZ / "datos" / "locales" / "santa_maria_dxf_local.json")
                      .read_text(encoding="utf-8"))["/mnt/data/work/trama urbana_2012_3D.dxf"][1688]
P = [Vector((p[0], p[1], p[2] - 440.0)) for p in registro[2]]

if not COPIA.exists():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    assert bpy.context.scene.get("intervencion") == 2, "el maestro no es el de la intervencion 2"
    shutil.copy2(BLEND, COPIA)
bpy.ops.wm.open_mainfile(filepath=str(COPIA))
escena = bpy.context.scene

A = P[67].xy
T = (P[58].xy - A).normalized()
N = Vector((-T.y, T.x))
if N.dot(Vector((-0.69, 0.72))) < 0:
    N = -N
EJE_S, EJE_D, ARRIBA = Vector((T.x, T.y, 0)), Vector((N.x, N.y, 0)), Vector((0, 0, 1))


def en_mundo(s, d, z):
    q = A + T * s + N * d
    return Vector((q.x, q.y, z))


terreno = bpy.data.objects["Terreno_interpolado"]


def suelo(s, d):
    inv = terreno.matrix_world.inverted()
    abajo = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
    ok, golpe, *_ = terreno.ray_cast(inv @ en_mundo(s, d, 200.0), abajo)
    assert ok, (s, d)
    return (terreno.matrix_world @ golpe).z


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


# --- medidas -----------------------------------------------------------------
DF = M["frente_d"]                      # plano del frente (DXF 62-64)
PROF = M["profundidad_usada"]           # abocinado: supuesto
DB = DF - PROF                          # plano de timpano y puertas
S0, S1 = M["s_derecha"], M["s_izquierda"]
CORNISA = M["cornisa_z"]
ext, inte = M["arco_exterior"], M["arco_interior"]
SC = M["eje_escalera"]
A_EXT = (ext["s_izq"] - ext["s_der"]) / 2.0
A_INT = (inte["s_izq"] - inte["s_der"]) / 2.0
ARRANQUE = (inte["z_arranque"] + M["puertas"]["z_dintel"]) / 2.0
R_EXT = (A_EXT ** 2 + (ext["z_clave"] - ARRANQUE) ** 2) / (2 * A_EXT)
CENTRO = R_EXT - A_EXT                  # arquivoltas concentricas
ORDENES = 6
# Escaleras del DXF: tres lineas (umbral, peldano intermedio y arranque).
ESC = M["escalera_dxf"]


def linea(d_min, d_max):
    pts = [e for e in ESC if d_min <= e[1] < d_max]
    return (min(e[0] for e in pts), max(e[0] for e in pts),
            sum(e[1] for e in pts) / len(pts), sum(e[2] for e in pts) / len(pts))


ALTA, MEDIA, PIE = linea(0.5, 1.0), linea(1.0, 1.5), linea(1.5, 2.0)
UMBRAL = ALTA[3]
BASE = min(min(suelo(s, DF + 0.2) for s in (S0, 0.0, 2.0, 4.0, 6.0, S1)), PIE[3]) - 0.25
assert S0 < SC - A_EXT and SC + A_EXT < S1 and DB > 0.15
clave_interior = ARRANQUE + math.sqrt((A_INT + CENTRO) ** 2 - CENTRO ** 2)


def perfil(k, n=16):
    """Contorno (s, z) del orden k: jamba, dos arcos y jamba."""
    a = A_EXT - (A_EXT - A_INT) * k / ORDENES
    r = a + CENTRO
    fin = math.acos(CENTRO / r)
    lado = [(CENTRO - r * math.cos(fin * i / n), ARRANQUE + r * math.sin(fin * i / n))
            for i in range(n + 1)]
    pts = [(-a, BASE)] + lado + [(-x, z) for x, z in reversed(lado[:-1])] + [(a, BASE)]
    return [(SC + x, z) for x, z in pts]


class Malla:
    def __init__(self):
        self.v, self.f = [], []

    def poligono(self, puntos, mira):
        """Triangula un poligono plano y orienta sus caras hacia el vector mira."""
        eje = max((EJE_S, EJE_D, ARRIBA), key=lambda e: abs(e.dot(mira)))
        otros = [e for e in (EJE_S, EJE_D, ARRIBA) if e != eje]
        plano = [Vector((p.dot(otros[0]), p.dot(otros[1]), 0)) for p in puntos]
        for tri in tessellate_polygon([plano]):
            a, b, c = (puntos[i] for i in tri)
            if (b - a).cross(c - a).length < 1e-7:
                continue
            if (b - a).cross(c - a).dot(mira) < 0:
                b, c = c, b
            n = len(self.v)
            self.v.extend([a, b, c])
            self.f.append([n, n + 1, n + 2])

    def cara(self, sdz, mira):
        self.poligono([en_mundo(*p) for p in sdz], mira)

    def caja(self, s0, s1, d0, d1, z0, z1):
        self.cara([(s0, d1, z0), (s1, d1, z0), (s1, d1, z1), (s0, d1, z1)], EJE_D)
        self.cara([(s0, d0, z0), (s1, d0, z0), (s1, d0, z1), (s0, d0, z1)], -EJE_D)
        self.cara([(s0, d0, z0), (s0, d1, z0), (s0, d1, z1), (s0, d0, z1)], -EJE_S)
        self.cara([(s1, d0, z0), (s1, d1, z0), (s1, d1, z1), (s1, d0, z1)], EJE_S)
        self.cara([(s0, d0, z1), (s1, d0, z1), (s1, d1, z1), (s0, d1, z1)], ARRIBA)
        self.cara([(s0, d0, z0), (s1, d0, z0), (s1, d1, z0), (s0, d1, z0)], -ARRIBA)


col = bpy.data.collections["Concatedral"]
muro = bpy.data.objects["Concatedral_fachadas"]
piedra = muro.data.materials[0]
nombre_capa = muro.data.color_attributes[0].name
color = tuple(muro.data.color_attributes[0].data[0].color)


def volcar(nombre, malla, material, tono, origen, supuesto):
    """Crea o sustituye Concatedral_<nombre> conservando el nombre del objeto."""
    completo = "Concatedral_" + nombre
    o = bpy.data.objects.get(completo)
    if o is not None:
        o.data.name = completo + "_anterior"
    me = bpy.data.meshes.new(completo)
    if o is None:
        o = bpy.data.objects.new(completo, me)
        col.objects.link(o)
    else:
        viejo, o.data = o.data, me
        bpy.data.meshes.remove(viejo)
    inv = o.matrix_world.inverted()
    me.from_pydata([inv @ v for v in malla.v], [], malla.f)
    me.update()
    capa = me.color_attributes.new(nombre_capa, "BYTE_COLOR", "POINT")
    for dato in capa.data:
        dato.color = tono
    me.materials.append(material)
    o["origen"] = "H1 intervencion 3; " + origen
    o["provisional"] = supuesto
    o["dibujar_aristas"] = True
    return o


camara("CAM_portada", en_mundo(SC + 2.5, 13.5, suelo(SC + 2.5, 13.5) + 1.65),
       en_mundo(SC, 0.5, 6.4), 24.0)
if not SIN_RENDER:
    renderizar(ANTES, ["CAM_portada"])

# --- 1. Cuerpo de la portada con arco abocinado ------------------------------
cuerpo = Malla()
frente = [(S0, BASE)] + perfil(0) + [(S1, BASE), (S1, CORNISA), (S0, CORNISA)]
cuerpo.cara([(s, DF, z) for s, z in frente], EJE_D)
cuerpo.cara([(S0, 0, BASE), (S0, DF, BASE), (S0, DF, CORNISA), (S0, 0, CORNISA)], -EJE_S)
cuerpo.cara([(S1, 0, BASE), (S1, DF, BASE), (S1, DF, CORNISA), (S1, 0, CORNISA)], EJE_S)
# Cubierta del cuerpo: no tapa el hueco del abocinado, que queda bajo ella.
cuerpo.cara([(S0, 0, CORNISA), (S1, 0, CORNISA), (S1, DF, CORNISA), (S0, DF, CORNISA)], ARRIBA)

paso = PROF / ORDENES
for k in range(ORDENES):
    d_fuera, d_dentro = DF - paso * k, DF - paso * (k + 1)
    p, q = perfil(k), perfil(k + 1)
    for i in range(len(p) - 1):
        (s_a, z_a), (s_b, z_b) = p[i], p[i + 1]
        medio = en_mundo((s_a + s_b) / 2, 0, (z_a + z_b) / 2)
        foco = en_mundo(SC, 0, min((z_a + z_b) / 2, ARRANQUE))
        # intrados de este orden: mira hacia el eje del hueco
        cuerpo.cara([(s_a, d_fuera, z_a), (s_b, d_fuera, z_b),
                     (s_b, d_dentro, z_b), (s_a, d_dentro, z_a)], foco - medio)
        # corona plana entre este orden y el siguiente: mira a la plaza
        cuerpo.cara([(s_a, d_dentro, z_a), (s_b, d_dentro, z_b),
                     (q[i + 1][0], d_dentro, q[i + 1][1]), (q[i][0], d_dentro, q[i][1])], EJE_D)

# Timpano sobre las puertas y parteluz, en el plano del fondo.
interior = perfil(ORDENES)
arco = [(s, z) for s, z in interior if z >= ARRANQUE - 1e-6]
cuerpo.cara([(s, DB, z) for s, z in arco], EJE_D)
p4 = M["puertas"]["s"]
medio_parteluz = abs(p4[1] - p4[2]) / 2.0
cuerpo.caja(SC - medio_parteluz, SC + medio_parteluz, DB - 0.12, DB + 0.06, UMBRAL, ARRANQUE)
volcar("cuerpo_portada", cuerpo, piedra, color,
       "frente y cornisa del DXF; anchos y arco de la foto",
       "profundidad del abocinado y numero y reparto de arquivoltas supuestos")

# --- 2. Puertas --------------------------------------------------------------
madera = bpy.data.materials.new("Madera_provisional")
madera.use_nodes = True
tono_madera = (0.045, 0.024, 0.013, 1.0)
principled = madera.node_tree.nodes["Principled BSDF"]
principled.inputs["Base Color"].default_value = tono_madera
principled.inputs["Roughness"].default_value = 0.75
puertas = Malla()
hoja = DB - 0.12
for lado in (-1, 1):
    s_a, s_b = sorted((SC + lado * medio_parteluz, SC + lado * A_INT))
    puertas.cara([(s_a, hoja, UMBRAL), (s_b, hoja, UMBRAL),
                  (s_b, hoja, ARRANQUE), (s_a, hoja, ARRANQUE)], EJE_D)
volcar("portada_puertas", puertas, madera, tono_madera, "huecos medidos en la foto",
       "hojas lisas, sin clavos ni herrajes ni postigo")
# Cierres del rebaje de las puertas.
rebaje = Malla()
for lado in (-1, 1):
    s_j = SC + lado * A_INT
    rebaje.cara([(s_j, hoja, UMBRAL), (s_j, DB, UMBRAL), (s_j, DB, ARRANQUE),
                 (s_j, hoja, ARRANQUE)], EJE_S * -lado)
    s_a, s_b = sorted((SC + lado * medio_parteluz, s_j))
    rebaje.cara([(s_a, hoja, ARRANQUE), (s_b, hoja, ARRANQUE), (s_b, DB, ARRANQUE),
                 (s_a, DB, ARRANQUE)], -ARRIBA)
    rebaje.cara([(s_a, hoja, UMBRAL), (s_b, hoja, UMBRAL), (s_b, DB, UMBRAL),
                 (s_a, DB, UMBRAL)], ARRIBA)
volcar("portada_rebaje", rebaje, piedra, color, "foto", "fondo del rebaje 0,12 m a ojo")

# --- 3. Cornisa y canecillos --------------------------------------------------
GRUESO, VUELO = 0.20, 0.24
cornisa = Malla()
cornisa.caja(S0 - 0.14, S1 + 0.10, DF - 0.05, DF + VUELO, CORNISA - GRUESO, CORNISA + 0.02)
cornisa.caja(S0 - 0.14, S0 + 0.05, 0.0, DF - 0.05, CORNISA - GRUESO, CORNISA + 0.02)
volcar("portada_cornisa", cornisa, piedra, color, "cota del DXF; grueso de la foto",
       "perfil moldurado reducido a un prisma; vuelo a ojo")
canes = Malla()
for s in M["canecillos_s"]:
    s = min(max(s, S0 + 0.14), S1 - 0.14)
    canes.caja(s - 0.12, s + 0.12, DF - 0.02, DF + 0.17,
               CORNISA - GRUESO - 0.30, CORNISA - GRUESO)
volcar("portada_canecillos", canes, piedra, color, "once posiciones de la foto",
       "bloques lisos en lugar de cabezas talladas")

# --- 4. Peldanos -------------------------------------------------------------
peldanos = Malla()
peldanos.caja(ALTA[0], ALTA[1], DB - 0.12, ALTA[2], BASE, UMBRAL)
peldanos.caja(MEDIA[0], MEDIA[1], DB - 0.14, MEDIA[2], BASE, MEDIA[3])
volcar("portada_peldanos", peldanos, piedra, color, "capa Escalera del DXF",
       "extremos achaflanados reducidos a rectangulos")

# El terreno de v0.3 pasaba por encima de los peldanos (rampa interpolada). Se baja
# solo delante de la portada, hasta la cota del arranque de la escalera y el bordillo.
inv_t = terreno.matrix_world.inverted()
bajados, mayor = 0, 0.0
for v in terreno.data.vertices:
    w = terreno.matrix_world @ v.co
    r = w.xy - A
    s, d = r.dot(T), r.dot(N)
    if not (-0.2 <= s <= 7.3 and -0.5 <= d <= 3.4):
        continue
    tope = PIE[3] - 0.01 - max(d - PIE[2], 0.0) * 0.06
    if w.z > tope:
        mayor = max(mayor, w.z - tope)
        v.co = inv_t @ Vector((w.x, w.y, tope))
        bajados += 1
terreno.data.update()
bpy.context.view_layer.update()

# --- 5. B5: ahora solo sobre la cornisa --------------------------------------
b5 = Malla()
s_65, d_65 = (P[65].xy - A).dot(T), (P[65].xy - A).dot(N)
b5.caja(0.0, s_65, 0.0, d_65, CORNISA - 0.05, P[65].z)
volcar("contrafuerte_portada", b5, piedra, color, "DXF 65-66",
       "bajo la cornisa lo sustituye el cuerpo de la portada")

# --- 6. Triangulo de cubierta de v0.3 que asomaba entre B1 y B2 ---------------
ala = bpy.data.objects["Concatedral_ala_sur"]
inv = ala.matrix_world.inverted()
movidos = 0
for v in ala.data.vertices:
    w = ala.matrix_world @ v.co
    if (w.xy - P[52].xy).length < 0.05:
        v.co = inv @ Vector((P[54].x, P[54].y, w.z))
        movidos += 1
ala.data.update()
assert movidos >= 1

escena["intervencion"] = 3
escena.camera = bpy.data.objects["CAM_general"]
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)

# Comprobacion: rayos rasantes desde la plaza al pie de la portada. Ninguno debe
# colarse por detras del muro principal (d < -0,05).
dg = bpy.context.evaluated_depsgraph_get()
rayos = colados = 0
for i_s in range(-30, 91):
    s = i_s / 10.0
    pie = suelo(s, 1.8)
    for alto in (0.02, 0.1, 0.2, 0.35, 0.5, 1.0, 3.0):
        origen = en_mundo(s, 3.5, pie + alto)
        ok, golpe, *_ = escena.ray_cast(dg, origen, -EJE_D, distance=12.0)
        rayos += 1
        colados += not ok or (golpe.xy - A).dot(N) < -0.05
huecos = {"rayos": rayos, "colados": colados}

nuevos = [o for o in escena.objects if o.type == "MESH" and o.get("dibujar_aristas")]
informe = {
    "cuerpo_s": [round(S0, 2), round(S1, 2)], "frente_d": round(DF, 2),
    "arco_exterior": {"ancho": round(2 * A_EXT, 2), "clave_z": round(ext["z_clave"], 2)},
    "arco_interior": {"ancho": round(2 * A_INT, 2), "clave_z_modelo": round(clave_interior, 2),
                      "clave_z_foto": round(inte["z_clave"], 2)},
    "arranque_z": round(ARRANQUE, 2), "umbral_z": round(UMBRAL, 2),
    "profundidad_supuesta": PROF, "vertices_de_cubierta_movidos": movidos,
    "terreno": {"vertices_bajados": bajados, "descenso_maximo_m": round(mayor, 2)},
    "escalera": {"alta": ALTA, "media": MEDIA, "pie": PIE},
    "rayos_al_pie": huecos,
    "objetos": [o.name for o in nuevos],
    "caras_degeneradas": [o.name for o in nuevos if any(f.area < 1e-6 for f in o.data.polygons)],
}
DESPUES.mkdir(parents=True, exist_ok=True)
(DESPUES / "informe.json").write_text(json.dumps(informe, indent=2), encoding="utf-8")
print("INFORME", json.dumps(informe))
if not SIN_RENDER:
    renderizar(DESPUES, ["CAM_portada", "CAM_general", "CAM_peaton_noroeste",
                         "CAM_inspeccion_suroeste"])
