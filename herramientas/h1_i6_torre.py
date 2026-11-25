"""H1, intervencion 6: torre (cornisas, huecos, campana y pinaculos).

Parte del .blend de la intervencion 5: lo copia a blender/copias/santa_maria_i5.blend
y siempre trabaja desde esa copia. Medidas en referencias/medidas_torre.json
(h1_medir_torre.py). Solo se detallan las caras noroeste y noreste, las que se ven
en las fotos de referencia descargadas.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/h1_i6_torre.py
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from silleria import ALTO_M, ANCHO_M  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
BLEND = RAIZ / "blender" / "santa_maria.blend"
COPIA = RAIZ / "blender" / "copias" / "santa_maria_i5.blend"
TEXTURAS = RAIZ / "texturas" / "concatedral"
ANTES = RAIZ / "renders" / "h1_i6_antes"
DESPUES = RAIZ / "renders" / "h1_i6_despues"
SIN_RENDER = "--sin-render" in sys.argv

M = json.loads((RAIZ / "referencias" / "medidas_torre.json").read_text(encoding="utf-8"))
P = [Vector((p[0], p[1], p[2] - 440.0)) for p in json.loads(
    (RAIZ / "datos" / "locales" / "santa_maria_dxf_local.json").read_text(encoding="utf-8"))
    ["/mnt/data/work/trama urbana_2012_3D.dxf"][1688][2]]
ARRIBA = Vector((0, 0, 1))
CIMA = P[79].z

if not COPIA.exists():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    assert bpy.context.scene.get("intervencion") == 5, "el maestro no es el de la intervencion 5"
    shutil.copy2(BLEND, COPIA)
bpy.ops.wm.open_mainfile(filepath=str(COPIA))
escena = bpy.context.scene
# La copia esta una carpeta mas abajo: se apuntan las texturas mientras se trabaja.
enlazadas = []
for img in bpy.data.images:
    if img.filepath.startswith("//"):
        nombre = Path(img.filepath.replace("\\", "/")).name
        img.filepath = str(TEXTURAS / nombre)
        img.reload()
        enlazadas.append((img, nombre))
assert len(enlazadas) == 2

rect = [P[70].xy, P[80].xy]                     # cara noroeste: norte -> oeste
fondo_torre = P[87].xy - P[79].xy
rect += [P[80].xy + fondo_torre, P[70].xy + fondo_torre]
centro_torre = sum(rect, Vector((0, 0))) / 4


class Cara:
    """Plano de una cara: u a lo largo, d hacia fuera."""

    def __init__(self, a, b):
        self.a, self.largo = a, (b - a).length
        self.t = (b - a).normalized()
        n = Vector((-self.t.y, self.t.x))
        if n.dot((a + b) / 2 - centro_torre) < 0:
            n = -n
        self.n = n
        self.T = Vector((self.t.x, self.t.y, 0))
        self.N = Vector((n.x, n.y, 0))

    def p(self, u, z, d=0.0):
        q = self.a + self.t * u + self.n * d
        return Vector((q.x, q.y, z))

    def uz(self, punto):
        r = punto.xy - self.a
        return r.dot(self.t), r.dot(self.n)


NO = Cara(P[74].xy, P[79].xy)                   # paramento real de la cara noroeste
NE = Cara(P[69].xy, P[87].xy + (P[69].xy - P[79].xy))


def u_noroeste(f):
    """Fraccion medida entre los cantos P70 y P80, pasada al paramento."""
    return NO.uz((P[70].xy.lerp(P[80].xy, f)).to_3d())[0]


col = bpy.data.collections["Concatedral"]
granito = bpy.data.materials["Granito_silleria_concatedral"]
madera = bpy.data.materials["Madera_provisional"]


def material(nombre, tono, rugoso, metal=0.0):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*tono, 1.0)
    b.inputs["Roughness"].default_value = rugoso
    b.inputs["Metallic"].default_value = metal
    return m


oscuro = material("Hueco_oscuro_provisional", (0.004, 0.003, 0.002), 1.0)
bronce = material("Bronce_provisional", (0.045, 0.06, 0.035), 0.5, 0.7)
# Piezas labradas: sin juntas de silleria. Tono medio de la textura (lineal).
liso = material("Granito_liso_provisional", (0.36, 0.25, 0.15), 0.92)


class Malla:
    def __init__(self):
        self.v, self.f = [], []

    def tri(self, a, b, c, mira):
        if (b - a).cross(c - a).length < 1e-7:
            return
        if (b - a).cross(c - a).dot(mira) < 0:
            b, c = c, b
        n = len(self.v)
        self.v.extend([a, b, c])
        self.f.append([n, n + 1, n + 2])

    def cuad(self, q, mira):
        self.tri(q[0], q[1], q[2], mira)
        self.tri(q[0], q[2], q[3], mira)


def uv_metros(me, mw):
    capa = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    capa = me.uv_layers["UVMap"]
    for cara in me.polygons:
        pts = [mw @ me.vertices[me.loops[i].vertex_index].co for i in cara.loop_indices]
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0]).normalized()
        t = Vector((-n.y, n.x, 0.0))
        for li, p in zip(cara.loop_indices, pts):
            if t.length > 0.3:
                u, v = p.dot(t.normalized()), p.z
            else:
                u, v = p.x, p.y
            capa.data[li].uv = (u / ANCHO_M, v / ALTO_M)


nuevos = []


def volcar(nombre, malla, mat, origen=None, supuesto=None):
    completo = "Concatedral_" + nombre
    o = bpy.data.objects.get(completo)
    if o is not None:
        o.data.name = completo + "_anterior"
    me = bpy.data.meshes.new(completo)
    if o is None:
        o = bpy.data.objects.new(completo, me)
        col.objects.link(o)
        o["origen"] = "H1 intervencion 6; " + origen
        o["provisional"] = supuesto
        o["dibujar_aristas"] = True
        nuevos.append(o)
    else:
        viejo, o.data = o.data, me
        bpy.data.meshes.remove(viejo)
    inv = o.matrix_world.inverted()
    me.from_pydata([inv @ v for v in malla.v], [], malla.f)
    me.update()
    me.materials.append(mat)
    uv_metros(me, o.matrix_world)
    return o


def arco(uc, ancho, z0, z1, n=12):
    """Lazo (u, z) de un hueco de medio punto."""
    r = ancho / 2
    arranque = z1 - r
    pts = [(uc - r, z0)]
    pts += [(uc - r * math.cos(math.pi * i / n), arranque + r * math.sin(math.pi * i / n))
            for i in range(n + 1)]
    return pts + [(uc + r, z0)]


def rectangulo(uc, ancho, z0, z1):
    return [(uc - ancho / 2, z0), (uc - ancho / 2, z1), (uc + ancho / 2, z1), (uc + ancho / 2, z0)]


def rebaje(nombre, cara, lazos, fondos, mat_fondo, supuesto):
    """Hueco escalonado: lazos[0] en el paramento; fondos[k] es el d de cada escalon."""
    piedra, fondo = Malla(), Malla()
    d0 = 0.0
    for k, d1 in enumerate(fondos):
        p = lazos[k]
        cu = sum(u for u, _ in p) / len(p)
        cz = sum(z for _, z in p) / len(p)
        for i in range(len(p)):
            (ua, za), (ub, zb) = p[i], p[(i + 1) % len(p)]
            nu, nz = -(zb - za), ub - ua
            if nu * (cu - (ua + ub) / 2) + nz * (cz - (za + zb) / 2) < 0:
                nu, nz = -nu, -nz
            mira = cara.T * nu + ARRIBA * nz
            piedra.cuad([cara.p(ua, za, d0), cara.p(ub, zb, d0),
                         cara.p(ub, zb, d1), cara.p(ua, za, d1)], mira)
            if k + 1 < len(lazos):
                q = lazos[k + 1]
                (va, wa), (vb, wb) = q[i], q[(i + 1) % len(p)]
                piedra.cuad([cara.p(ua, za, d1), cara.p(ub, zb, d1),
                             cara.p(vb, wb, d1), cara.p(va, wa, d1)], cara.N)
        d0 = d1
    ultimo = lazos[-1]
    for t in tessellate_polygon([[Vector((u, z, 0)) for u, z in ultimo]]):
        fondo.tri(*(cara.p(*ultimo[i], d=fondos[-1]) for i in t), cara.N)
    volcar(f"torre_{nombre}", piedra, granito, "foto", supuesto)
    volcar(f"torre_{nombre}_fondo", fondo, mat_fondo, "foto", supuesto)


def torno(malla, centro, perfil, lados=16):
    """Solido de revolucion cerrado; perfil = [(radio, z)] de abajo arriba."""
    anillos = [[centro + Vector((r * math.cos(2 * math.pi * i / lados),
                                 r * math.sin(2 * math.pi * i / lados), z - centro.z))
                for i in range(lados)] for r, z in perfil]
    for k in range(len(anillos) - 1):
        for i in range(lados):
            j = (i + 1) % lados
            q = [anillos[k][i], anillos[k][j], anillos[k + 1][j], anillos[k + 1][i]]
            medio = sum(q, Vector()) / 4
            radial = Vector((medio.x - centro.x, medio.y - centro.y, 0))
            dr = perfil[k + 1][0] - perfil[k][0]
            dz = perfil[k + 1][1] - perfil[k][1]
            mira = radial.normalized() * dz - ARRIBA * dr
            malla.cuad(q, mira)
    for anillo, mira in ((anillos[0], -ARRIBA), (anillos[-1], ARRIBA)):
        c = sum(anillo, Vector()) / lados
        for i in range(lados):
            malla.tri(c, anillo[i], anillo[(i + 1) % lados], mira)


# --- vistas ------------------------------------------------------------------
def camara(nombre, desde, hacia, focal):
    datos = bpy.data.cameras.new(nombre)
    datos.lens, datos.sensor_width = focal, 36.0
    c = bpy.data.objects.new(nombre, datos)
    bpy.data.collections["Camaras_y_luz"].objects.link(c)
    c.location = desde
    c.rotation_euler = (hacia - desde).to_track_quat("-Z", "Y").to_euler()


camara("CAM_torre", NO.p(NO.largo / 2 - 8.0, 31.0, 30.0), NO.p(NO.largo / 2, 20.5), 35.0)


def renderizar(carpeta, camaras):
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre in camaras:
        escena.camera = bpy.data.objects[nombre]
        escena.render.resolution_x, escena.render.resolution_y = (
            (2000, 1328) if nombre == "CAM_foto" else (1600, 1000))
        escena.render.filepath = str(carpeta / f"{nombre}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", escena.render.filepath)


if not SIN_RENDER:
    renderizar(ANTES, ["CAM_torre"])

# --- 1. Huecos -----------------------------------------------------------------
cam, bal, med = M["campanario"], M["balaustrada"], M["medallon"]
F_EJE = sum(M[k]["f"] for k in ("campanario", "balaustrada", "medallon",
                                 "ventanuco_alto", "ciega")) / 5.0
eje = u_noroeste(F_EJE)
huecos_no, huecos_ne = [], []


def abrir(nombre, cara, lista, lazos, fondos, mat_fondo, supuesto):
    lista.append(lazos[0])
    rebaje(nombre, cara, lazos, fondos, mat_fondo, supuesto)


abrir("campanario_NO", NO, huecos_no,
      [arco(eje, cam["ancho"], cam["z_bajo"], cam["z_alto"])], [-1.35], oscuro,
      "fondo 1,35 m supuesto")
c = M["ciega"]
abrir("ventana_ciega", NO, huecos_no,
      [arco(eje, c["ancho"], c["z_bajo"], c["z_alto"]),
       arco(eje, c["ancho"] * 0.62, c["z_bajo"] + 0.15, c["z_alto"] - 0.40),
       arco(eje, c["ancho"] * 0.30, c["z_bajo"] + 0.25, c["z_alto"] - 0.75)],
      [-0.22, -0.40, -0.48], granito, "escalones y fondos supuestos")
for nombre in ("ventanuco_alto", "ventanuco_medallon", "ventanuco_bajo"):
    v = M[nombre]
    uc = eje if nombre == "ventanuco_alto" else u_noroeste(v["f"])
    alto = v["z_alto"] - v["z_bajo"]
    abrir(nombre, NO, huecos_no,
          [rectangulo(uc, v["ancho"], v["z_bajo"], v["z_alto"]),
           rectangulo(uc, 0.22, v["z_bajo"] + 0.12 * alto, v["z_bajo"] + 0.70 * alto)],
          [-0.35, -0.60], oscuro, "fondos y saetera supuestos")
abrir("balaustrada_NO", NO, huecos_no,
      [rectangulo(eje, bal["ancho"], bal["z_bajo"], bal["z_alto"])], [-0.22], granito,
      "relieve reducido a rebaje con balaustres")
for n, fraccion in enumerate((0.36, 0.64), 1):
    uc = NE.largo * fraccion
    abrir(f"campanario_NE{n}", NE, huecos_ne,
          [arco(uc, 0.95, cam["z_bajo"], cam["z_alto"])], [-1.0], oscuro,
          "posicion y ancho estimados en J29 199; mismas cotas que la cara noroeste")
    abrir(f"balaustrada_NE{n}", NE, huecos_ne,
          [rectangulo(uc, 0.95, bal["z_bajo"], bal["z_alto"])], [-0.22], granito,
          "estimada en J29 199")


def perforar(nombre_obj, cara, lazos):
    """Sustituye los panos de una cara por uno solo con los huecos."""
    o = bpy.data.objects[nombre_obj]
    mundo = [o.matrix_world @ v.co for v in o.data.vertices]
    del_pano, resto = [], []
    for f in o.data.polygons:
        puntos = [mundo[i] for i in f.vertices]
        rel = [cara.uz(p) for p in puntos]
        if all(abs(d) < 0.03 and -0.03 <= u <= cara.largo + 0.03 for u, d in rel):
            del_pano.append(puntos)
        else:
            resto.append(puntos)
    assert del_pano, nombre_obj
    todos = [p for tri in del_pano for p in tri]
    orilla = [[p for p in todos if cara.uz(p)[0] < cara.largo / 2],
              [p for p in todos if cara.uz(p)[0] >= cara.largo / 2]]
    u_min = min(cara.uz(p)[0] for p in orilla[0])
    u_max = max(cara.uz(p)[0] for p in orilla[1])
    izq = [p for p in orilla[0] if cara.uz(p)[0] < u_min + 0.05]
    der = [p for p in orilla[1] if cara.uz(p)[0] > u_max - 0.05]
    extremos = [min(izq, key=lambda p: p.z), min(der, key=lambda p: p.z),
                max(der, key=lambda p: p.z), max(izq, key=lambda p: p.z)]
    contorno = [(cara.uz(p)[0], p.z) for p in extremos]
    malla = Malla()
    for puntos in resto:
        n = len(malla.v)
        malla.v.extend(puntos)
        malla.f.append(list(range(n, n + len(puntos))))
    listas = [contorno] + lazos
    for lazo in lazos:
        assert all(u_min < u < u_max and max(contorno[0][1], contorno[1][1]) < z
                   < min(contorno[2][1], contorno[3][1]) for u, z in lazo), (nombre_obj, lazo[:2])
    plano = [p for lazo in listas for p in lazo]
    for t in tessellate_polygon([[Vector((u, z, 0)) for u, z in lazo] for lazo in listas]):
        malla.tri(*(cara.p(*plano[i]) for i in t), cara.N)
    volcar(nombre_obj.removeprefix("Concatedral_"), malla, granito)


perforar("Concatedral_torre_fachadas", NO, huecos_no)
perforar("Concatedral_torre_interior_provisional", NE, huecos_ne)

# --- 2. Balaustres, medallon, campana ------------------------------------------
balaustres = Malla()
alto = bal["z_alto"] - bal["z_bajo"]
for cara, centros, paso in ((NO, [eje], bal["ancho"] / 5),
                            (NE, [NE.largo * 0.36, NE.largo * 0.64], 0.95 / 3)):
    cuantos = 5 if cara is NO else 3
    for uc in centros:
        for i in range(cuantos):
            u = uc + (i - (cuantos - 1) / 2) * paso
            z = bal["z_bajo"]
            torno(balaustres, cara.p(u, z, -0.11),
                  [(0.09, z), (0.09, z + 0.10), (0.05, z + 0.22), (0.105, z + 0.45 * alto),
                   (0.045, z + 0.80 * alto), (0.085, z + alto - 0.08), (0.085, z + alto)], 8)
volcar("torre_balaustres", balaustres, liso, "foto", "perfil y numero en la cara noreste a ojo")

medallon = Malla()
zc = (med["z_alto"] + med["z_bajo"]) / 2
radio = (med["z_alto"] - med["z_bajo"]) / 2
for r_ext, r_int, saliente in ((radio, radio * 0.82, 0.14), (radio * 0.82, 0.0, 0.07)):
    n = 32
    for i in range(n):
        a, b = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n

        def q(r, ang, d):
            return NO.p(eje + r * math.cos(ang), zc + r * math.sin(ang), d)

        radial = NO.T * math.cos((a + b) / 2) + ARRIBA * math.sin((a + b) / 2)
        medallon.cuad([q(r_ext, a, 0), q(r_ext, b, 0), q(r_ext, b, saliente),
                       q(r_ext, a, saliente)], radial)
        if r_int:
            medallon.cuad([q(r_ext, a, saliente), q(r_ext, b, saliente),
                           q(r_int, b, saliente), q(r_int, a, saliente)], NO.N)
            medallon.cuad([q(r_int, a, 0.07), q(r_int, b, 0.07), q(r_int, b, saliente),
                           q(r_int, a, saliente)], -radial)
        else:
            medallon.tri(q(0, 0, saliente), q(r_ext, a, saliente), q(r_ext, b, saliente), NO.N)
volcar("torre_medallon", medallon, liso, "foto", "disco con orla; sin el escudo tallado")

campana = Malla()
z0, z1 = M["campana"]["z_bajo"], M["campana"]["z_alto"]
h, r = z1 - z0, M["campana"]["ancho"] / 2
centro_c = NO.p(eje, z0, -0.65)
torno(campana, centro_c, [(r, z0), (r * 0.86, z0 + 0.10 * h), (r * 0.64, z0 + 0.40 * h),
                          (r * 0.56, z0 + 0.74 * h), (r * 0.38, z0 + 0.90 * h),
                          (r * 0.12, z1)], 24)
volcar("torre_campana", campana, bronce, "foto", "perfil a ojo")


def bloque(malla, cara, u0, u1, d0, d1, za, zb):
    q = [cara.p(u, z, d) for z in (za, zb) for u, d in ((u0, d0), (u1, d0), (u1, d1), (u0, d1))]
    c = sum(q, Vector()) / 8
    for f in ([0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]):
        malla.cuad([q[i] for i in f], sum((q[i] for i in f), Vector()) / 4 - c)


yugo = Malla()
ancho_hueco = cam["ancho"] / 2
bloque(yugo, NO, eje - ancho_hueco, eje + ancho_hueco, -0.78, -0.52, z1, z1 + 0.22)
bloque(yugo, NO, eje - 0.30, eje + 0.30, -0.76, -0.54, z1 + 0.22, z1 + 0.70)
volcar("torre_yugo", yugo, madera, "foto", "yugo reducido a dos prismas; sin la cruz")

# --- 3. Cornisas ----------------------------------------------------------------
def desplazado(d):
    salida = []
    for i, q in enumerate(rect):
        a, b = rect[i - 1], rect[(i + 1) % 4]
        salida.append(q + ((q - a).normalized() + (q - b).normalized()) * d)
    return salida


for n, (cota, vuelo) in enumerate(((M["cornisas_z"][1], 0.17), (M["cornisas_z"][0], 0.17),
                                   (CIMA + 0.03, 0.28)), 1):
    cornisa = Malla()
    z0, z1 = cota - 0.28, cota
    fuera, dentro = desplazado(vuelo), desplazado(-0.06)
    for i in range(4):
        j = (i + 1) % 4
        lado = ((fuera[i] + fuera[j]) / 2 - centro_torre).to_3d()
        cornisa.cuad([fuera[i].to_3d() + ARRIBA * z0, fuera[j].to_3d() + ARRIBA * z0,
                      fuera[j].to_3d() + ARRIBA * z1, fuera[i].to_3d() + ARRIBA * z1], lado)
        for z, mira in ((z0, -ARRIBA), (z1, ARRIBA)):
            cornisa.cuad([fuera[i].to_3d() + ARRIBA * z, fuera[j].to_3d() + ARRIBA * z,
                          dentro[j].to_3d() + ARRIBA * z, dentro[i].to_3d() + ARRIBA * z], mira)
    volcar(f"torre_cornisa_{n}", cornisa, granito, "cota de la foto o del DXF",
           "perfil liso; en las caras no vistas se supone continua")

# --- 4. Pinaculos ----------------------------------------------------------------
p = M["pinaculo"]
for n, esquina in enumerate(range(4), 1):
    q = rect[esquina]
    a, b = rect[esquina - 1], rect[(esquina + 1) % 4]
    ea, eb = (a - q).normalized(), (b - q).normalized()
    c2 = q + (ea + eb) * 0.45
    base = Vector((c2.x, c2.y, CIMA))
    pin = Malla()
    esquinas = [q, q + ea * 0.9, q + ea * 0.9 + eb * 0.9, q + eb * 0.9]
    z0, z1 = CIMA, CIMA + p["pedestal"]
    caja = [Vector((e.x, e.y, z)) for z in (z0, z1) for e in esquinas]
    cc = sum(caja, Vector()) / 8
    for f in ([0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]):
        pin.cuad([caja[i] for i in f], sum((caja[i] for i in f), Vector()) / 4 - cc)
    za, zb, zr = CIMA + p["plato_bajo"], CIMA + p["plato_alto"], CIMA + p["remate"]
    torno(pin, base, [(0.22, z1), (0.20, z1 + 0.2), (0.12, za - 0.08), (0.15, za),
                      (0.50, za + 0.55 * (zb - za)), (0.52, za + 0.75 * (zb - za)),
                      (0.20, zb), (0.12, zb + 0.15), (0.15, zr - 0.12), (0.02, zr)])
    volcar(f"torre_pinaculo_{n}", pin, liso, "alturas de la foto",
           "torneado a ojo; sin la figura" + ("" if esquina != 2 else
                                             "; esquina sur no visible, supuesta igual"))
bpy.context.view_layer.update()

# --- comprobaciones --------------------------------------------------------------
dg = bpy.context.evaluated_depsgraph_get()
rayos = fugas = 0
for cara, lazos, limite in ((NO, huecos_no, -1.37), (NE, huecos_ne, -1.02)):
    for lazo in lazos:
        us, zs = [u for u, _ in lazo], [z for _, z in lazo]
        u = min(us) + 0.017
        while u < max(us):
            z = min(zs) + 0.019
            while z < max(zs):
                dentro = False
                for (x1, y1), (x2, y2) in zip(lazo, lazo[1:] + lazo[:1]):
                    if (y1 > z) != (y2 > z) and u < x1 + (z - y1) / (y2 - y1) * (x2 - x1):
                        dentro = not dentro
                if dentro:
                    ok, golpe, *_ = escena.ray_cast(dg, cara.p(u, z, 3.0), -cara.N, distance=9.0)
                    rayos += 1
                    fugas += not ok or cara.uz(golpe)[1] < limite
                z += 0.06
            u += 0.06

for img, nombre in enlazadas:
    img.filepath = f"//../texturas/concatedral/{nombre}"
escena["intervencion"] = 6
escena.camera = bpy.data.objects["CAM_general"]
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True, relative_remap=False)
informe = {"rayos_por_huecos": rayos, "fugas": fugas, "eje_u": round(eje, 3),
           "cornisas_z": [M["cornisas_z"][1], M["cornisas_z"][0], round(CIMA + 0.03, 2)],
           "coronacion_pinaculos_z": round(CIMA + M["pinaculo"]["remate"], 2),
           "objetos_nuevos": sorted(o.name for o in nuevos),
           "caras_degeneradas": [o.name for o in nuevos
                                 if any(f.area < 1e-7 for f in o.data.polygons)]}
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
escena = bpy.context.scene
assert all(Path(bpy.path.abspath(i.filepath)).exists() for i in bpy.data.images
           if i.filepath.startswith("//"))
DESPUES.mkdir(parents=True, exist_ok=True)
(DESPUES / "informe.json").write_text(json.dumps(informe, indent=2), encoding="utf-8")
print("INFORME", json.dumps(informe))
if not SIN_RENDER:
    renderizar(DESPUES, ["CAM_torre", "CAM_foto", "CAM_peaton_oeste_torre", "CAM_general"])
