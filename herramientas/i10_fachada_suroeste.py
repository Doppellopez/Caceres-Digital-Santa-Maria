"""Intervencion 10: fachada suroeste de la concatedral (portada, roseton y torre).

Parte del .blend de la intervencion 9: lo copia a blender/copias/santa_maria_i9.blend
y siempre trabaja desde esa copia. Planta y alturas de los muros: contorno municipal.
Posiciones de huecos y molduras: referencias/medidas_suroeste.json (fotos propias
184905, 184908 y 184911, ver i10_medir_suroeste.py). Las tres fotos se tomaron casi
desde el mismo punto, asi que NO miden profundidades: los vuelos son estimados.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/i10_fachada_suroeste.py
    ... -- --prueba        renders pequenos en renders/i10_prueba, sin guardar el maestro
    ... -- --sin-render
"""
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.geometry import tessellate_polygon

RAIZ = Path(__file__).resolve().parents[1]
BLEND = RAIZ / "blender" / "santa_maria.blend"
COPIA = RAIZ / "blender" / "copias" / "santa_maria_i9.blend"
PRUEBA = "--prueba" in sys.argv
SIN_RENDER = "--sin-render" in sys.argv
TEXTURAS = (RAIZ / "renders" / "i10_prueba") if PRUEBA else (RAIZ / "texturas" / "concatedral")
ANTES = RAIZ / "renders" / "i10_antes"
DESPUES = RAIZ / "renders" / ("i10_prueba" if PRUEBA else "i10_despues")
ANCHO_M, ALTO_M = 6.4, 3.2              # repeticion de la silleria
TEJA_UV = (3.84, 3.6)                   # repeticion de la teja (intervencion 9)

J = json.loads((RAIZ / "referencias" / "medidas_suroeste.json").read_text(encoding="utf-8"))
P = [Vector((p[0], p[1], p[2] - 440.0)) for p in json.loads(
    (RAIZ / "datos" / "locales" / "santa_maria_dxf_local.json").read_text(encoding="utf-8"))
    ["/mnt/data/work/trama urbana_2012_3D.dxf"][1688][2]]
ORIGEN = P[82].xy
T2 = (P[83].xy - P[82].xy).normalized()
N2 = Vector((T2.y, -T2.x))
if N2.dot(Vector((-0.7, -0.7))) < 0:
    N2 = -N2
T, N, Z = Vector((T2.x, T2.y, 0)), Vector((N2.x, N2.y, 0)), Vector((0, 0, 1))


def W(s, d, z):
    """Coordenadas de fachada (a lo largo, hacia fuera, cota) -> mundo."""
    q = ORIGEN + T2 * s + N2 * d
    return Vector((q.x, q.y, z))


def sdz(p):
    r = p.xy - ORIGEN
    return r.dot(T2), r.dot(N2), p.z


def d_muro(s):
    """Paramento principal entre la torre (DXF 87) y el segundo contrafuerte (DXF 88)."""
    return -0.41 + (s - 8.02) * (0.14 / 8.22)


# --- medidas (m). s y z salen de las fotos o del contorno; d, ver cabecera -------
ALERO = 18.50                                            # DXF 88: 18,48
ROS_C, ROS_Z = 11.68, 13.02
ROS_R = (1.26, 1.07, 0.88, 0.70)
CUERPO = (9.20, 14.66)
D_CUERPO, D_PUERTA = 0.10, -1.00                         # puerta: por simetria del arco
Z_CORNISA = (9.74, 10.00)
S_CORNISA, D_CORNISA = (8.82, 14.90), 0.45
CANECILLOS = [9.09, 9.32, 10.16, 11.08, 12.00, 12.82, 13.61, 14.43]
ARCO_EXT = dict(c=12.02, w=2.52, arr=5.65, clave=8.22)
ARCO_INT = dict(c=11.98, w=1.10, arr=5.45, clave=6.86)
B1 = dict(s=(6.52, 7.56), repisa=14.22, alto=17.90, d_bajo=0.75, d_alto=0.60)
B2 = dict(s=(16.23, 17.60), repisa=14.30, alto=18.22, d_bajo=0.50, d_alto=0.43)
# muro inclinado a la derecha: (s, cota de coronacion, cota del pie)
PENDIENTE = [(17.60, 18.35, 2.40), (23.62, 15.94, 2.66), (24.42, 15.67, 2.60), (25.21, 15.41, 2.54)]
TORRE_EJE = 3.63
MEDALLON = dict(s=3.28, z=19.85, r=0.78)

if not COPIA.exists():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    assert bpy.context.scene.get("intervencion") == 9, "el maestro no es el de la intervencion 9"
    shutil.copy2(BLEND, COPIA)


# --- camaras de las fotos y renders ----------------------------------------------
def camaras_foto():
    for foto, c in J["camaras"].items():
        s, d, z, giro, cab, alabeo = c
        f = Vector((math.sin(giro) * math.cos(cab), -math.cos(giro) * math.cos(cab), math.sin(cab)))
        r0 = Vector((math.cos(giro), math.sin(giro), 0))
        u0 = Vector((-math.sin(giro) * math.sin(cab), math.cos(giro) * math.sin(cab), math.cos(cab)))
        r = r0 * math.cos(alabeo) + u0 * math.sin(alabeo)
        u = u0 * math.cos(alabeo) - r0 * math.sin(alabeo)

        def mundo(v):
            return T * v.x + N * v.y + Z * v.z

        nombre = f"CAM_SO_{foto}"
        cam = bpy.data.objects.get(nombre)
        if cam is None:
            datos = bpy.data.cameras.new(nombre)
            cam = bpy.data.objects.new(nombre, datos)
            bpy.data.collections["Camaras_y_luz"].objects.link(cam)
        cam.data.sensor_fit, cam.data.sensor_height = "VERTICAL", 36.0
        cam.data.lens = J["focal_px"] * 36.0 / 2000.0
        rot = Matrix((mundo(r), mundo(u), -mundo(f))).transposed()
        cam.matrix_world = Matrix.Translation(W(s, d, z)) @ rot.to_4x4()


def renderizar(carpeta):
    """Renderiza sin guardar despues el .blend."""
    escena = bpy.context.scene
    camaras_foto()
    carpeta.mkdir(parents=True, exist_ok=True)
    sol = escena.objects["Sol_base"]
    registro = json.loads((RAIZ / "renders" / "calle_i9" / "registro.json").read_text(encoding="utf-8"))
    vistas = [(f"CAM_SO_{f}", 1500, 2000) for f in J["camaras"]]
    for n in ("S", "SO"):
        v = registro["vistas"][n]
        datos = bpy.data.cameras.new(f"CAM_calle_{n}")
        datos.lens, datos.sensor_width = v["focal_mm"], registro["sensor_mm"]
        datos.sensor_fit, datos.shift_y = "HORIZONTAL", v["desplazamiento_y"]
        cam = bpy.data.objects.new(datos.name, datos)
        escena.collection.objects.link(cam)
        cam.location = v["posicion"]
        a = math.radians(v["rumbo_grados"])
        cam.rotation_euler = Vector((math.sin(a), math.cos(a), 0)).to_track_quat("-Z", "Y").to_euler()
        vistas.append((datos.name, 2000, 1500))
    for nombre, ancho, alto in vistas:
        cam = escena.objects[nombre]
        escena.camera = cam
        bpy.context.view_layer.update()
        mira = cam.matrix_world.to_3x3() @ Vector((0, 0, -1))
        # Sol a espaldas de la camara (no es el real), como en render_calle.py.
        rumbo = math.atan2(-mira.x, -mira.y) + math.radians(35)
        sol.rotation_euler = Vector((math.sin(rumbo), math.cos(rumbo), 1.0)).normalized() \
            .to_track_quat("Z", "Y").to_euler()
        escena.render.resolution_x, escena.render.resolution_y = ancho, alto
        escena.render.resolution_percentage = 40 if PRUEBA else 100
        escena.cycles.samples = 16 if PRUEBA else 48
        escena.render.filepath = str(carpeta / f"{nombre}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", escena.render.filepath)


if not (SIN_RENDER or ANTES.exists()):
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    assert bpy.context.scene.get("intervencion") == 9, "no se puede sacar el 'antes'"
    renderizar(ANTES)

bpy.ops.wm.open_mainfile(filepath=str(COPIA))
escena = bpy.context.scene
assert escena.get("intervencion") == 9
# La copia esta una carpeta mas abajo: se apuntan las texturas mientras se trabaja.
enlazadas = []
for img in bpy.data.images:
    if img.filepath.replace("\\", "/").startswith("//../"):
        relativa = img.filepath.replace("\\", "/")[5:]
        img.filepath = str(RAIZ / relativa)
        img.reload()
        enlazadas.append((img, relativa))


def geometria():
    return {o.name: ([tuple(v.co) for v in o.data.vertices], [tuple(p.vertices) for p in o.data.polygons])
            for o in escena.objects if o.type == "MESH"}


antes = geometria()
col = bpy.data.collections["Concatedral"]
granito = bpy.data.materials["Granito_silleria_concatedral"]
liso = bpy.data.materials["Granito_liso_concatedral"]
oscuro = bpy.data.materials["Hueco_oscuro_provisional"]
madera = bpy.data.materials["Madera_provisional"]
bronce = bpy.data.materials["Bronce_provisional"]
teja = bpy.data.materials["Teja_arabe_cubiertas"]


def plano_material(nombre, tono, rugoso, metal=0.0):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*tono, 1.0)
    b.inputs["Roughness"].default_value = rugoso
    b.inputs["Metallic"].default_value = metal
    return m


hierro = plano_material("Hierro_provisional", (0.012, 0.01, 0.008), 0.6, 0.6)


# --- texturas recortadas de las fotos --------------------------------------------
def rayo_pixel(foto, s, d, z):
    """Pixel (x, y) de la foto reducida a 1500 x 2000 donde se ve el punto."""
    cs, cd, cz, giro, cab, alabeo = J["camaras"][foto]
    f = np.array([math.sin(giro) * math.cos(cab), -math.cos(giro) * math.cos(cab), math.sin(cab)])
    r0 = np.array([math.cos(giro), math.sin(giro), 0.0])
    u0 = np.array([-math.sin(giro) * math.sin(cab), math.cos(giro) * math.sin(cab), math.cos(cab)])
    r = math.cos(alabeo) * r0 + math.sin(alabeo) * u0
    u = -math.sin(alabeo) * r0 + math.cos(alabeo) * u0
    v = np.stack([s - cs, np.full_like(s, d - cd), z - cz], axis=-1)
    w = v @ f
    return 750 + J["focal_px"] * (v @ r) / w, 1000 - J["focal_px"] * (v @ u) / w


def foto_en_pie(foto):
    img = bpy.data.images.load(str(RAIZ / "referencias" / "fotos_jorge" / f"20261125_{foto}.jpg"))
    ancho, alto = img.size
    px = np.empty(ancho * alto * 4, np.float32)
    img.pixels.foreach_get(px)
    a = px.reshape(alto, ancho, 4)[::-1, :, :3]          # fila 0 arriba
    bpy.data.images.remove(img)
    if a.shape[1] > a.shape[0]:                          # EXIF 6: girar 90 grados a la derecha
        a = np.rot90(a, -1)
    return a.copy()


def recorte(nombre, foto, s0, s1, z0, z1, d, ancho, alto, tono=None, ganancia=1.0):
    a = foto_en_pie(foto)
    escala = a.shape[1] / 1500.0
    s = s0 + (np.arange(ancho) + 0.5) / ancho * (s1 - s0)
    z = z0 + (np.arange(alto) + 0.5) / alto * (z1 - z0)   # fila 0 abajo
    S, Zm = np.meshgrid(s, z)
    x, y = rayo_pixel(foto, S, d, Zm)
    x = np.clip(x * escala - 0.5, 0, a.shape[1] - 1.001)
    y = np.clip(y * escala - 0.5, 0, a.shape[0] - 1.001)
    i, j = x.astype(int), y.astype(int)
    fx, fy = (x - i)[..., None], (y - j)[..., None]
    c = ((a[j, i] * (1 - fx) + a[j, i + 1] * fx) * (1 - fy)
         + (a[j + 1, i] * (1 - fx) + a[j + 1, i + 1] * fx) * fy)
    if tono is not None:
        c = c * (np.array(tono) / np.maximum(c.reshape(-1, 3).mean(0), 1e-3))
    c = np.clip(c * ganancia, 0, 1)
    img = bpy.data.images.new(nombre, ancho, alto, alpha=False)
    rgba = np.ones((alto, ancho, 4), np.float32)
    rgba[..., :3] = c
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = str(TEXTURAS / f"{nombre}.png")
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    img = bpy.data.images.load(str(TEXTURAS / f"{nombre}.png"))
    img.name = nombre
    if not PRUEBA:
        enlazadas.append((img, f"texturas/concatedral/{nombre}.png"))
    return img


def con_foto(nombre, imagen, rugoso, origen):
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    arbol = mat.node_tree
    bsdf = arbol.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rugoso
    uv = arbol.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    tex = arbol.nodes.new("ShaderNodeTexImage")
    tex.image, tex.extension = imagen, "EXTEND"
    arbol.links.new(uv.outputs[0], tex.inputs[0])
    arbol.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    mat["textura"] = origen
    return mat


TEXTURAS.mkdir(parents=True, exist_ok=True)
ref = bpy.data.images["granito_foto_color"]
px = np.empty(ref.size[0] * ref.size[1] * 4, np.float32)
ref.pixels.foreach_get(px)
tono_piedra = px.reshape(-1, 4)[:, :3].mean(0)
# Rectangulos tal como se ven (plano en el que se midieron).
PUERTA_VISTA = (10.65, 12.72, 2.40, 6.76, -0.20)
mat_puerta = con_foto("Puerta_foto_SO", recorte(
    "puerta_SO_foto", "184908", *PUERTA_VISTA[:4], PUERTA_VISTA[4], 512, 1024, ganancia=2.0),
    0.75, "foto propia 20261125_184908")
mat_vidrio = con_foto("Roseton_foto_SO", recorte(
    "roseton_SO_foto", "184908", ROS_C - 0.70, ROS_C + 0.70, ROS_Z - 0.69, ROS_Z + 0.69, -0.40,
    512, 512, ganancia=1.15), 0.5, "foto propia 20261125_184908")
mat_medallon = con_foto("Medallon_foto_SO", recorte(
    "medallon_SO_foto", "184905", MEDALLON["s"] - MEDALLON["r"], MEDALLON["s"] + MEDALLON["r"],
    MEDALLON["z"] - MEDALLON["r"], MEDALLON["z"] + MEDALLON["r"], 0.0, 384, 384, tono=tono_piedra),
    0.9, "foto propia 20261125_184905")


# --- constructores -----------------------------------------------------------------
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

    def panel(self, lazos, d, mira=None):
        """Poligono (s, z) con huecos; d puede ser funcion de s."""
        f = d if callable(d) else (lambda s, v=d: v)
        plano = [p for lazo in lazos for p in lazo]
        for t in tessellate_polygon([[Vector((s, z, 0)) for s, z in lazo] for lazo in lazos]):
            self.tri(*(W(plano[i][0], f(plano[i][0]), plano[i][1]) for i in t), N if mira is None else mira)

    def prisma(self, lazo, d0, d1, frente=True, fondo=False):
        """Extrusion de un poligono (s, z) entre los planos d0 (atras) y d1 (delante)."""
        f0 = d0 if callable(d0) else (lambda s, v=d0: v)
        f1 = d1 if callable(d1) else (lambda s, v=d1: v)
        area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(lazo, lazo[1:] + lazo[:1]))
        giro = 1 if area > 0 else -1
        for (sa, za), (sb, zb) in zip(lazo, lazo[1:] + lazo[:1]):
            mira = T * ((zb - za) * giro) + Z * (-(sb - sa) * giro)
            self.cuad([W(sa, f0(sa), za), W(sb, f0(sb), zb), W(sb, f1(sb), zb), W(sa, f1(sa), za)], mira)
        if frente:
            self.panel([lazo], f1)
        if fondo:
            self.panel([lazo], f0, -N)

    def caja(self, s0, s1, d0, d1, z0, z1):
        self.prisma([(s0, z0), (s1, z0), (s1, z1), (s0, z1)], d0, d1, fondo=True)

    def tubo(self, puntos, radio, lados=8):
        """Baquetón a lo largo de una polilinea de puntos del mundo."""
        anillos = []
        for k, p in enumerate(puntos):
            t = (puntos[min(k + 1, len(puntos) - 1)] - puntos[max(k - 1, 0)]).normalized()
            a = t.cross(N).normalized()
            b = t.cross(a).normalized()
            anillos.append([p + a * (radio * math.cos(2 * math.pi * i / lados))
                            + b * (radio * math.sin(2 * math.pi * i / lados)) for i in range(lados)])
        for k in range(len(anillos) - 1):
            eje = (puntos[k] + puntos[k + 1]) / 2
            for i in range(lados):
                j = (i + 1) % lados
                q = [anillos[k][i], anillos[k][j], anillos[k + 1][j], anillos[k + 1][i]]
                self.cuad(q, sum(q, Vector()) / 4 - eje)
        for anillo, mira in ((anillos[0], puntos[0] - puntos[1]), (anillos[-1], puntos[-1] - puntos[-2])):
            c = sum(anillo, Vector()) / lados
            for i in range(lados):
                self.tri(c, anillo[i], anillo[(i + 1) % lados], mira)

    def torno(self, centro, perfil, lados=16):
        anillos = [[centro + Vector((r * math.cos(2 * math.pi * i / lados),
                                     r * math.sin(2 * math.pi * i / lados), z - centro.z))
                    for i in range(lados)] for r, z in perfil]
        for k in range(len(anillos) - 1):
            for i in range(lados):
                j = (i + 1) % lados
                q = [anillos[k][i], anillos[k][j], anillos[k + 1][j], anillos[k + 1][i]]
                medio = sum(q, Vector()) / 4
                radial = Vector((medio.x - centro.x, medio.y - centro.y, 0))
                mira = radial.normalized() * (perfil[k + 1][1] - perfil[k][1]) \
                    - Z * (perfil[k + 1][0] - perfil[k][0])
                self.cuad(q, mira)
        for anillo, mira in ((anillos[0], -Z), (anillos[-1], Z)):
            c = sum(anillo, Vector()) / lados
            for i in range(lados):
                self.tri(c, anillo[i], anillo[(i + 1) % lados], mira)


def uv_metros(me):
    capa = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    capa = me.uv_layers["UVMap"]
    for cara in me.polygons:
        pts = [me.vertices[me.loops[i].vertex_index].co for i in cara.loop_indices]
        n = cara.normal
        t = Vector((-n.y, n.x, 0.0))
        for li, p in zip(cara.loop_indices, pts):
            u, v = (p.dot(t.normalized()), p.z) if t.length > 0.3 else (p.x, p.y)
            capa.data[li].uv = (u / ANCHO_M, v / ALTO_M)


nuevos = []


def volcar(nombre, malla, mat, supuesto, uv=None):
    completo = "Concatedral_" + nombre
    assert completo not in bpy.data.objects, completo
    me = bpy.data.meshes.new(completo)
    me.from_pydata(malla.v, [], malla.f)
    me.update()
    o = bpy.data.objects.new(completo, me)
    col.objects.link(o)
    me.materials.append(mat)
    if uv is None:
        uv_metros(me)
    else:
        capa = me.uv_layers.new(name="UVMap")
        for cara in me.polygons:
            for li in cara.loop_indices:
                capa.data[li].uv = uv(me.vertices[me.loops[li].vertex_index].co)
    o["origen"] = "intervencion 10; contorno municipal y fotos propias 184905-184911"
    o["provisional"] = supuesto
    o["dibujar_aristas"] = True
    nuevos.append(o)
    return o


def uv_foto(s0, s1, z0, z1):
    def f(p):
        s, _, z = sdz(p)
        return ((s - s0) / (s1 - s0), (z - z0) / (z1 - z0))
    return f


def circulo(sc, zc, r, n=40):
    return [(sc + r * math.cos(2 * math.pi * i / n), zc + r * math.sin(2 * math.pi * i / n))
            for i in range(n)]


def apuntado(a, zpie, n=14):
    """Lazo (s, z) de un vano apuntado abierto por abajo, de izquierda a derecha."""
    w, h = a["w"], a["clave"] - a["arr"]
    c = (h * h - w * w) / (2 * w)                        # centros sobre la linea de arranque
    R = w + c
    ang = math.atan2(h, -c)                              # angulo de la clave
    pts = [(a["c"] - w, zpie)]
    for i in range(n + 1):                               # lado izquierdo: centro a la derecha
        t = math.pi + (ang - math.pi) * i / n
        pts.append((a["c"] + c + R * math.cos(t), a["arr"] + R * math.sin(t)))
    der = [(2 * a["c"] - s, z) for s, z in pts[1:-1]]
    return pts + der[::-1] + [(a["c"] + w, zpie)]


def teja_en(o, mat_otro):
    """Reparte teja y UV por faldones en un objeto de cubierta (como en la intervencion 9)."""
    me = o.data
    normal_m = o.matrix_world.to_3x3().inverted_safe().transposed()
    me.update()
    capa = me.uv_layers["UVMap"]
    me.materials.clear()
    me.materials.append(mat_otro)
    me.materials.append(teja)
    for p in me.polygons:
        if (normal_m @ p.normal).z < 0:
            p.flip()
    me.update()
    for p in me.polygons:
        n = (normal_m @ p.normal).normalized()
        inclinada = math.degrees(math.acos(min(1.0, n.z))) >= 5.0
        p.material_index = 1 if inclinada else 0
        if inclinada:
            u = Z.cross(n).normalized()
            v = n.cross(u).normalized()
            for li in p.loop_indices:
                q = o.matrix_world @ me.vertices[me.loops[li].vertex_index].co
                capa.data[li].uv = (q.dot(u) / TEJA_UV[0], q.dot(v) / TEJA_UV[1])


# --- 1. Retirar lo anterior de la cara suroeste ------------------------------------
fach = bpy.data.objects["Concatedral_fachadas"]
mw = fach.matrix_world


def en_zona(p):
    s, d, z = sdz(p)
    return 7.95 <= s <= 25.3 and -0.5 <= d <= 0.5 and z < 14.2


fuera = [f.index for f in fach.data.polygons
         if all(en_zona(mw @ fach.data.vertices[i].co) for i in f.vertices)]
assert fuera == list(range(254, 268)), fuera


def rehacer(o, quitar, mover):
    """Quita caras y cambia la cota de vertices, conservando UV."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in quitar], context="FACES")
    inv = o.matrix_world.inverted()
    movidos = 0
    for v in bm.verts:
        q = o.matrix_world @ v.co
        z = mover(*sdz(q))
        if z is not None:
            v.co = inv @ Vector((q.x, q.y, z))
            movidos += 1
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    return movidos


def cerca(s, d, a, b):
    return abs(s - a) < 0.08 and abs(d - b) < 0.08


def mover_esquina(s, d, z):
    for a, b, cota in ((25.21, -0.44, 15.41), (25.19, -0.88, 15.41), (25.19, -1.45, 15.41),
                       (25.10, -6.07, 15.42)):
        if cerca(s, d, a, b) and 14.0 < z < 14.2:
            return cota
    return None


movidos_muro = rehacer(fach, fuera, mover_esquina)
fach.data.update()
uv_metros_local = fach.data.uv_layers.get("UVMap")
if uv_metros_local:                                      # los paneles estirados: UV en metros
    uv_metros(fach.data)

cierre = bpy.data.objects["Concatedral_cubierta_cierre_provisional"]
mat_cierre = cierre.data.materials[0]
BORDE = ((8.02, -0.41, 18.38), (16.24, -0.27, 18.38), (17.61, -0.44, 18.22), (23.62, -0.44, 15.82),
         (24.42, -0.44, 15.55), (25.21, -0.44, 15.30), (25.19, -0.88, 15.30), (25.19, -1.45, 15.30))


def mover_borde(s, d, z):
    for a, b, cota in BORDE:
        if cerca(s, d, a, b) and z < 14.2:
            return cota
    return None


tapas_b2 = [f.index for f in cierre.data.polygons
            if any(sdz(cierre.matrix_world @ cierre.data.vertices[i].co)[1] > 0.3 for i in f.vertices)]
assert len(tapas_b2) == 2, tapas_b2
movidos_cierre = rehacer(cierre, tapas_b2, mover_borde)
teja_en(cierre, mat_cierre)

# --- 2. Muro principal, con roseton y hueco de la portada --------------------------
arco_ext = apuntado(ARCO_EXT, 2.05)
muro = Malla()
contorno = [(8.02, 2.08)] + arco_ext + [(16.24, 2.42), (16.24, ALERO), (8.02, ALERO)]
muro.panel([contorno, circulo(ROS_C, ROS_Z, ROS_R[0])], d_muro)
atras = lambda s: d_muro(s) - 0.55
muro.panel([[(8.02, 13.9), (16.24, 13.9), (16.24, ALERO), (8.02, ALERO)]], atras, -N)
muro.cuad([W(8.02, atras(8.02), ALERO), W(16.24, atras(16.24), ALERO),
           W(16.24, d_muro(16.24), ALERO), W(8.02, d_muro(8.02), ALERO)], Z)
for s, hacia in ((8.02, -T), (16.24, T)):
    muro.cuad([W(s, atras(s), 13.9), W(s, d_muro(s), 13.9),
               W(s, d_muro(s), ALERO), W(s, atras(s), ALERO)], hacia)
volcar("SO_muro", muro, granito, "grosor 0,55 m supuesto")

pend = Malla()
alto_p = [(s, z) for s, z, _ in PENDIENTE]
lazo = [(s, pie) for s, _, pie in PENDIENTE] + alto_p[::-1]
pend.prisma(lazo, -0.99, -0.44, fondo=True)
volcar("SO_muro_inclinado", pend, granito, "grosor 0,55 m supuesto")

# Alero: moldura de piedra y boquillas de teja.
moldura, bocas = Malla(), Malla()
tramos = [((8.02, ALERO), (16.23, ALERO), d_muro)]
tramos += [(alto_p[i], alto_p[i + 1], lambda s: -0.44) for i in range(3)]
for (sa, za), (sb, zb), d in tramos:
    moldura.prisma([(sa, za - 0.34), (sb, zb - 0.34), (sb, zb - 0.17), (sa, za - 0.17)],
                   lambda s, d=d: d(s) - 0.02, lambda s, d=d: d(s) + 0.10)
    s = sa + 0.12
    while s < sb - 0.08:
        z = za + (zb - za) * (s - sa) / (sb - sa) + 0.02
        bocas.tubo([W(s, d(s) - 0.25, z + 0.03), W(s, d(s) + 0.15, z - 0.01)], 0.085, 8)
        s += 0.24
volcar("SO_alero_moldura", moldura, liso, "perfil liso")
volcar("SO_alero_tejas", bocas, teja, "boquillas de teja cada 24 cm",
       uv=lambda p: (sdz(p)[0] / TEJA_UV[0], (p.z * 0.5) / TEJA_UV[1]))

# --- 3. Roseton ----------------------------------------------------------------------
d_r = d_muro(ROS_C)
piedra, aros = Malla(), Malla()
lazos = [circulo(ROS_C, ROS_Z, r) for r in ROS_R]
fondos = [-0.10, -0.20, -0.30, -0.38]
d0 = None
for k, hondo in enumerate(fondos):
    p = lazos[k]
    for i in range(len(p)):
        (sa, za), (sb, zb) = p[i], p[(i + 1) % len(p)]
        mira = T * (ROS_C - (sa + sb) / 2) + Z * (ROS_Z - (za + zb) / 2)
        ini = (lambda s: d_muro(s)) if k == 0 else (lambda s, v=d_r + fondos[k - 1]: v)
        piedra.cuad([W(sa, ini(sa), za), W(sb, ini(sb), zb), W(sb, d_r + hondo, zb),
                     W(sa, d_r + hondo, za)], mira)
        if k + 1 < len(lazos):
            (va, wa), (vb, wb) = lazos[k + 1][i], lazos[k + 1][(i + 1) % len(p)]
            piedra.cuad([W(sa, d_r + hondo, za), W(sb, d_r + hondo, zb), W(vb, d_r + hondo, wb),
                         W(va, d_r + hondo, wa)], N)
for r, hondo, grueso in ((ROS_R[0] + 0.05, 0.02, 0.075), (ROS_R[1], -0.10, 0.055),
                         (ROS_R[2], -0.20, 0.05), (ROS_R[3] + 0.02, -0.30, 0.04)):
    aro = [W(s, d_r + hondo, z) for s, z in circulo(ROS_C, ROS_Z, r)]
    aros.tubo(aro + aro[:2], grueso)
volcar("SO_roseton", piedra, liso, "escalones y fondos supuestos")
volcar("SO_roseton_molduras", aros, liso, "cuatro boceles lisos")
vidrio = Malla()
vidrio.panel([lazos[-1]], d_r + fondos[-1])
volcar("SO_roseton_vidrio", vidrio, mat_vidrio, "imagen de la foto nocturna",
       uv=uv_foto(ROS_C - 0.70, ROS_C + 0.70, ROS_Z - 0.70, ROS_Z + 0.70))

# --- 4. Portada ------------------------------------------------------------------------
cuerpo = Malla()
frente = [(CUERPO[0], 2.05)] + arco_ext + [(CUERPO[1], 2.22), (CUERPO[1], Z_CORNISA[0]),
                                           (CUERPO[0], Z_CORNISA[0])]
cuerpo.panel([frente], D_CUERPO)
for s, hacia, pie in ((CUERPO[0], -T, 2.05), (CUERPO[1], T, 2.22)):
    cuerpo.cuad([W(s, d_muro(s), pie), W(s, D_CUERPO, pie), W(s, D_CUERPO, Z_CORNISA[0]),
                 W(s, d_muro(s), Z_CORNISA[0])], hacia)
volcar("SO_portada_cuerpo", cuerpo, granito, "vuelo de unos 0,5 m estimado")

ORDENES = 6
arcos, boceles = Malla(), Malla()
pasos = []
for k in range(ORDENES + 1):
    f = k / ORDENES
    pasos.append((apuntado({c: ARCO_EXT[c] + (ARCO_INT[c] - ARCO_EXT[c]) * f for c in ARCO_EXT}, 2.05),
                  D_CUERPO + (D_PUERTA - D_CUERPO) * f))
for (la, da), (lb, db) in zip(pasos, pasos[1:]):
    centro = (ARCO_EXT["c"], 4.0)
    for i in range(len(la) - 1):                         # pared y escalon de cada orden
        (sa, za), (sb, zb) = la[i], la[i + 1]
        mira = T * (centro[0] - (sa + sb) / 2) + Z * (centro[1] - (za + zb) / 2)
        arcos.cuad([W(sa, da, za), W(sb, da, zb), W(sb, db, zb), W(sa, db, za)], mira)
        (va, wa), (vb, wb) = lb[i], lb[i + 1]
        arcos.cuad([W(sa, db, za), W(sb, db, zb), W(vb, db, wb), W(va, db, wa)], N)
for lazo_k, d in pasos[:-1]:
    boceles.tubo([W(s, d, max(z, 3.30)) if i in (0, len(lazo_k) - 1) else W(s, d, z)
                  for i, (s, z) in enumerate(lazo_k)], 0.055)
volcar("SO_portada_arquivoltas", arcos, liso, "seis ordenes y 1,1 m de abocinado estimados")
volcar("SO_portada_boceles", boceles, liso, "un bocel liso por orden")
herrajes = Malla()
for lado in (-1, 1):                                     # basas escalonadas y capiteles corridos
    for k, (lazo_k, d) in enumerate(pasos[:-1]):
        s = lazo_k[0][0] if lado < 0 else lazo_k[-1][0]
        herrajes.caja(s - 0.11, s + 0.11, d - 0.12, d + 0.07, 2.05, 3.30)
        herrajes.caja(s - 0.09, s + 0.09, d - 0.10, d + 0.09, ARCO_EXT["arr"] - 0.30, ARCO_EXT["arr"] - 0.08)
volcar("SO_portada_basas_capiteles", herrajes, liso, "reducidos a bloques")

puerta = Malla()
hoja = apuntado(ARCO_INT, 2.05)
puerta.panel([hoja], D_PUERTA + 0.001)
volcar("SO_portada_puerta", puerta, mat_puerta, "imagen de la foto nocturna",
       uv=uv_foto(ARCO_INT["c"] - ARCO_INT["w"], ARCO_INT["c"] + ARCO_INT["w"], 2.29, ARCO_INT["clave"]))

cornisa, canes, escudo = Malla(), Malla(), Malla()
cornisa.caja(*S_CORNISA, -0.42, D_CORNISA, Z_CORNISA[0] + 0.08, Z_CORNISA[1])
cornisa.caja(S_CORNISA[0] + 0.05, S_CORNISA[1] - 0.05, -0.42, D_CORNISA - 0.07,
             Z_CORNISA[0], Z_CORNISA[0] + 0.08)
for s in CANECILLOS:
    z1, z0 = Z_CORNISA[0], Z_CORNISA[0] - 0.30
    cabeza = [(s - 0.10, z0 + 0.08), (s - 0.05, z0), (s + 0.05, z0), (s + 0.10, z0 + 0.08),
              (s + 0.10, z1), (s - 0.10, z1)]
    canes.prisma(cabeza, D_CUERPO - 0.02, D_CUERPO + 0.24)
volcar("SO_portada_cornisa", cornisa, granito, "vuelo estimado")
volcar("SO_portada_canecillos", canes, liso, "ocho, sin las cabezas talladas")
escudo.prisma([(11.84, 9.22), (11.84, 8.95), (11.93, 8.82), (12.06, 8.76), (12.19, 8.82),
               (12.28, 8.95), (12.28, 9.22)], D_CUERPO - 0.01, D_CUERPO + 0.05)
volcar("SO_portada_escudo", escudo, liso, "silueta sin las armas")

# --- 5. Contrafuertes --------------------------------------------------------------------
for nombre, c, atras_b, pie, nota in (("SO_contrafuerte_torre", B1, -0.05, 1.95, "vuelo estimado"),
                                      ("SO_contrafuerte_portada", B2, -0.60, 2.25, "planta del contorno")):
    m = Malla()
    s0, s1 = c["s"]
    m.caja(s0 - 0.02, s1 + 0.02, atras_b, c["d_bajo"], pie, c["repisa"] - 0.10)
    m.caja(s0 - 0.08, s1 + 0.08, atras_b, c["d_bajo"] + 0.09, c["repisa"] - 0.10, c["repisa"] + 0.06)
    m.caja(s0, s1, atras_b, c["d_alto"], c["repisa"] + 0.06, c["alto"] - 0.16)
    m.caja(s0 - 0.08, s1 + 0.08, atras_b, c["d_alto"] + 0.09, c["alto"] - 0.16, c["alto"])
    volcar(nombre, m, granito, nota)

# --- 6. Torre: huecos de la cara suroeste -------------------------------------------------
def arco_medio(sc, ancho, z0, z1, n=14):
    r = ancho / 2
    arr = z1 - r
    return [(sc - r, z0)] + [(sc - r * math.cos(math.pi * i / n), arr + r * math.sin(math.pi * i / n))
                             for i in range(n + 1)] + [(sc + r, z0)]


def rect(s0, s1, z0, z1):
    return [(s0, z0), (s0, z1), (s1, z1), (s1, z0)]


huecos, honduras = [], []


def hueco(nombre, lazos, tramos, mat_fondo, supuesto):
    """lazos[0] en el paramento; tramos = [(lazo_destino, d)] hacia dentro."""
    lados, fondo = Malla(), Malla()
    anterior, d0 = lazos, 0.0
    for lazo, d1 in tramos:
        cs = sum(s for s, _ in anterior) / len(anterior)
        cz = sum(z for _, z in anterior) / len(anterior)
        for i in range(len(anterior)):
            j = (i + 1) % len(anterior)
            (sa, za), (sb, zb) = anterior[i], anterior[j]
            (ta, ya), (tb, yb) = lazo[i], lazo[j]
            mira = T * (cs - (sa + sb) / 2) + Z * (cz - (za + zb) / 2) + N * 0.01
            lados.cuad([W(sa, d0, za), W(sb, d0, zb), W(tb, d1, yb), W(ta, d1, ya)], mira)
        anterior, d0 = lazo, d1
    fondo.panel([anterior], d0)
    huecos.append(lazos)
    honduras.append((anterior, d0))
    volcar(f"torre_SO_{nombre}", lados, granito, supuesto)
    volcar(f"torre_SO_{nombre}_fondo", fondo, mat_fondo, supuesto)


M = J["medidas"]["torre"]
c = M["campanario"]
ancho_c = c["s1"] - c["s0"]
vano_c = arco_medio(TORRE_EJE, ancho_c, c["z0"], c["z1"])
hueco("campanario", vano_c, [(vano_c, -1.35)], oscuro, "fondo 1,35 m supuesto")
b = M["balaustrada"]
vano_b = rect(TORRE_EJE - (b["s1"] - b["s0"]) / 2, TORRE_EJE + (b["s1"] - b["s0"]) / 2, b["z0"], b["z1"])
hueco("balaustrada", vano_b, [(vano_b, -0.22)], granito, "relieve reducido a rebaje con balaustres")
for nombre, clave in (("ventana_alta", "ventana_alta"), ("ventana_baja", "ventana_baja")):
    m_, v_ = M[clave + "_marco"], M[clave + "_vano"]
    marco = rect(m_["s0"], m_["s1"], m_["z0"], m_["z1"])
    vano = rect(v_["s0"], v_["s1"], v_["z0"], v_["z1"])
    hueco(nombre, marco, [(vano, -0.35), (vano, -0.50)], oscuro, "derrame de 0,35 m estimado")
    reja = Malla()
    for i in (1, 2, 3):
        s = v_["s0"] + (v_["s1"] - v_["s0"]) * i / 4
        reja.caja(s - 0.012, s + 0.012, -0.37, -0.345, v_["z0"], v_["z1"])
    zm = (v_["z0"] + v_["z1"]) / 2
    reja.caja(v_["s0"], v_["s1"], -0.372, -0.343, zm - 0.012, zm + 0.012)
    volcar(f"torre_SO_{nombre}_reja", reja, hierro, "barrotes a ojo")
SAETERAS = [(M[f"saetera{i}"]) for i in range(1, 6)]
for i, v in enumerate(SAETERAS, 1):
    z0, z1 = v["z0"], v["z1"]
    if i == 5:                                           # queda justo sobre la cornisa baja
        z0, z1 = 17.96, 18.24
    marco = rect(v["s0"], v["s1"], z0, z1)
    luz = rect(v["s0"] + 0.04, v["s1"] - 0.04, z0 + 0.03, z1 - 0.03)
    hueco(f"saetera_{i}", marco, [(luz, -0.10), (luz, -0.40)], oscuro, "fondo supuesto")

torre = bpy.data.objects["Concatedral_torre_fachadas"]
del_pano = [f.index for f in torre.data.polygons
            if all(abs(sdz(torre.matrix_world @ torre.data.vertices[i].co)[1]) < 0.03
                   and -0.03 <= sdz(torre.matrix_world @ torre.data.vertices[i].co)[0] <= 7.70
                   for i in f.vertices)]
assert del_pano == [18, 19], del_pano
rehacer(torre, del_pano, lambda s, d, z: None)
pano = Malla()
pano.panel([[(0.0, 1.69), (7.67, 2.06), (7.67, 27.77), (0.0, 27.77)]] + huecos, 0.0)
volcar("torre_SO_pano", pano, granito, "paramento con los huecos de la cara suroeste")

balaustres = Malla()
alto = b["z1"] - b["z0"]
ancho_b = b["s1"] - b["s0"]
for i in range(4):
    s = TORRE_EJE + (i - 1.5) * ancho_b / 4
    z = b["z0"]
    balaustres.torno(W(s, -0.11, z), [(0.09, z), (0.09, z + 0.09), (0.05, z + 0.20),
                                      (0.105, z + 0.45 * alto), (0.045, z + 0.80 * alto),
                                      (0.085, z + alto - 0.07), (0.085, z + alto)], 8)
volcar("torre_SO_balaustres", balaustres, liso, "perfil a ojo")

medallon = Malla()
sc, zc, radio = MEDALLON["s"], MEDALLON["z"], MEDALLON["r"]
for r_ext, r_int, sale in ((radio, radio * 0.84, 0.14), (radio * 0.84, 0.0, 0.07)):
    n = 32
    for i in range(n):
        a1, a2 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n

        def q(r, ang, d):
            return W(sc + r * math.cos(ang), d, zc + r * math.sin(ang))

        radial = T * math.cos((a1 + a2) / 2) + Z * math.sin((a1 + a2) / 2)
        medallon.cuad([q(r_ext, a1, 0), q(r_ext, a2, 0), q(r_ext, a2, sale), q(r_ext, a1, sale)], radial)
        if r_int:
            medallon.cuad([q(r_ext, a1, sale), q(r_ext, a2, sale), q(r_int, a2, sale),
                           q(r_int, a1, sale)], N)
            medallon.cuad([q(r_int, a1, 0.07), q(r_int, a2, 0.07), q(r_int, a2, sale),
                           q(r_int, a1, sale)], -radial)
        else:
            medallon.tri(q(0, 0, sale), q(r_ext, a1, sale), q(r_ext, a2, sale), N)
volcar("torre_SO_medallon", medallon, mat_medallon, "relieve plano con la imagen de la foto",
       uv=uv_foto(sc - radio, sc + radio, zc - radio, zc + radio))

campana, yugo = Malla(), Malla()
z0, z1 = c["z0"] + 0.25, c["z0"] + 1.55
r = 0.62
campana.torno(W(TORRE_EJE, -0.65, z0), [(r, z0), (r * 0.86, z0 + 0.13), (r * 0.64, z0 + 0.52),
                                        (r * 0.56, z0 + 0.96), (r * 0.38, z0 + 1.17),
                                        (r * 0.12, z1)], 24)
yugo.caja(TORRE_EJE - ancho_c / 2, TORRE_EJE + ancho_c / 2, -0.78, -0.52, z1, z1 + 0.22)
yugo.caja(TORRE_EJE - 0.30, TORRE_EJE + 0.30, -0.76, -0.54, z1 + 0.22, z1 + 0.70)
volcar("torre_SO_campana", campana, bronce, "perfil a ojo")
volcar("torre_SO_yugo", yugo, madera, "yugo reducido a dos prismas; sin la cruz")

zocalo = Malla()
zm = J["medidas"]["torre"]["moldura_zocalo"][1]
zocalo.caja(-0.05, B1["s"][0], -0.02, 0.09, zm - 0.09, zm + 0.09)
volcar("torre_SO_moldura", zocalo, liso, "perfil liso")

camaras_foto()
bpy.context.view_layer.update()

# --- comprobaciones ------------------------------------------------------------------------
dg = bpy.context.evaluated_depsgraph_get()


def dentro_de(s, z, lazo):
    d = False
    for (x1, y1), (x2, y2) in zip(lazo, lazo[1:] + lazo[:1]):
        if (y1 > z) != (y2 > z) and s < x1 + (z - y1) / (y2 - y1) * (x2 - x1):
            d = not d
    return d


def sondear(lazo, limite, paso):
    """Rayos de frente por un vano: deben dar en algo antes del limite de profundidad."""
    ss, zs = [s for s, _ in lazo], [z for _, z in lazo]
    rayos = fugas = 0
    s = min(ss) + paso * 0.37
    while s < max(ss):
        z = max(min(zs), 2.55) + paso * 0.41
        while z < max(zs):
            if dentro_de(s, z, lazo):
                ok, golpe, *_ = escena.ray_cast(dg, W(s, 4.0, z), -N, distance=8.0)
                rayos += 1
                fugas += not ok or sdz(golpe)[1] < limite
            z += paso
        s += paso
    return rayos, fugas


rayos = fugas = 0
for lazo, hondo in [(arco_ext, D_PUERTA - 0.02), (circulo(ROS_C, ROS_Z, ROS_R[0] - 0.01), d_r - 0.40)] \
        + [(h, d - 0.02) for h, (_, d) in zip(huecos, honduras)]:
    a, f = sondear(lazo, hondo, 0.05)
    rayos, fugas = rayos + a, fugas + f
despues = geometria()
cambiados = sorted(k for k in antes if antes[k] != despues.get(k))
assert cambiados == ["Concatedral_cubierta_cierre_provisional", "Concatedral_fachadas",
                     "Concatedral_torre_fachadas"], cambiados
informe = {"rayos_por_vanos": rayos, "fugas": fugas, "objetos_modificados": cambiados,
           "vertices_subidos": {"muros": movidos_muro, "cubierta_cierre": movidos_cierre},
           "objetos_nuevos": sorted(o.name for o in nuevos),
           "triangulos_nuevos": sum(len(o.data.polygons) for o in nuevos),
           "caras_degeneradas": [o.name for o in nuevos if any(f.area < 1e-7 for f in o.data.polygons)]}
print("INFORME", json.dumps({k: v for k, v in informe.items() if k != "objetos_nuevos"}))

escena["intervencion"] = 10
if not PRUEBA:
    for img, relativa in enlazadas:
        img.filepath = f"//../{relativa}"
    escena.camera = bpy.data.objects["CAM_general"]
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True, relative_remap=False)
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    escena = bpy.context.scene
    for img in bpy.data.images:
        if img.filepath.startswith("//"):
            assert Path(bpy.path.abspath(img.filepath)).exists(), img.filepath
DESPUES.mkdir(parents=True, exist_ok=True)
(DESPUES / "informe.json").write_text(json.dumps(informe, indent=2), encoding="utf-8")
if not SIN_RENDER:
    renderizar(DESPUES)
