"""H1: coloca una camara como la de una foto real y compara el modelo con ella.

La camara se ajusta SOLO con tres puntos de la torre (dos arriba, uno abajo), mas
la altura de una persona y el horizonte casi nivelado. Todo lo demas que se dibuja
es prediccion del modelo y sirve para comprobarlo. No guarda el .blend.

Desde la intervencion 3 usa la camara de referencias/medidas_portada.json (torre y
cuatro remates), no la ajustada solo a la torre.

Foto: "Santa Maria, Caceres.JPG", Jesusccastillo, CC BY-SA 3.0 ES (ver fuentes.md).
La imagen superpuesta es obra derivada y lleva la misma licencia.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/h1_comparar_foto.py
"""
import json
import struct
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix

RAIZ = Path(__file__).resolve().parents[1]
BLEND = RAIZ / "blender" / "santa_maria.blend"
FOTO = RAIZ / "referencias" / "fotos" / "Santa María, Cáceres.JPG"
ANCHO, ALTO = 2000, 1328

# (nombre, punto 3D del modelo, pixel marcado a ojo en la foto reducida a 2000 px)
AJUSTE = [
    ("torre, esquina oeste arriba", (5.11, -7.17, 27.77), (1627, 117)),
    ("torre, esquina norte arriba", (10.33, -2.19, 27.77), (1362, 108)),
    ("torre, esquina oeste al pie", (5.11, -7.32, 1.74), (1748, 1270)),
]


def focal_35mm(ruta):
    """Lee la focal equivalente de la cabecera EXIF."""
    d = ruta.read_bytes()[:200000]
    base = d.index(b"Exif\x00\x00") + 6
    orden = "<" if d[base:base + 2] == b"II" else ">"

    def ifd(desp):
        n = struct.unpack_from(orden + "H", d, base + desp)[0]
        for i in range(n):
            pos = base + desp + 2 + 12 * i
            etiqueta, tipo, _ = struct.unpack_from(orden + "HHI", d, pos)
            yield etiqueta, tipo, pos + 8

    primero = struct.unpack_from(orden + "I", d, base + 4)[0]
    for etiqueta, _, pos in ifd(primero):
        if etiqueta == 0x8769:
            sub = struct.unpack_from(orden + "I", d, pos)[0]
            valores = {}
            for e2, _, p2 in ifd(sub):
                if e2 == 0xA405:
                    valores["eq"] = struct.unpack_from(orden + "H", d, p2)[0]
                if e2 == 0x920A:
                    off = struct.unpack_from(orden + "I", d, p2)[0]
                    a, b = struct.unpack_from(orden + "II", d, base + off)
                    valores["real"] = a / b
            return valores
    raise ValueError("sin EXIF")


def ejes(giro, cabeceo, alabeo):
    f = np.array([np.cos(cabeceo) * np.cos(giro), np.cos(cabeceo) * np.sin(giro), np.sin(cabeceo)])
    r0 = np.cross(f, [0, 0, 1.0])
    r0 /= np.linalg.norm(r0)
    u0 = np.cross(r0, f)
    r = np.cos(alabeo) * r0 + np.sin(alabeo) * u0
    u = -np.sin(alabeo) * r0 + np.cos(alabeo) * u0
    return r, u, f


def proyectar(par, puntos, fpx):
    r, u, f = ejes(*par[3:6])
    v = np.asarray(puntos, float) - par[:3]
    z = v @ f
    return np.stack([ANCHO / 2 + fpx * (v @ r) / z, ALTO / 2 - fpx * (v @ u) / z], axis=1), z


def residuos(par, fpx):
    px, _ = proyectar(par, [a[1] for a in AJUSTE], fpx)
    r = (px - np.array([a[2] for a in AJUSTE])).ravel() / 8.0     # sigma 8 px
    ojos = (par[2] - 3.05) / 0.5                                   # suelo 1,4 + 1,65
    nivel = par[5] / np.radians(2.0)
    return np.concatenate([r, [ojos, nivel]])


def ajustar(fpx):
    mejor = None
    for dist in (18.0, 25.0, 35.0):
        c = np.array([15.9 - 0.69 * dist, 3.0 + 0.72 * dist, 3.05])
        m = np.array([13.0, 0.0, 11.0]) - c
        par = np.array([*c, np.arctan2(m[1], m[0]), np.arctan2(m[2], np.hypot(*m[:2])), 0.0])
        lam = 1.0
        for _ in range(300):
            r = residuos(par, fpx)
            J = np.stack([(residuos(par + e, fpx) - r) / 1e-6 for e in np.eye(6) * 1e-6], axis=1)
            paso = np.linalg.solve(J.T @ J + lam * np.eye(6), -J.T @ r)
            if np.sum(residuos(par + paso, fpx) ** 2) < np.sum(r ** 2):
                par, lam = par + paso, lam / 3
            else:
                lam *= 5
        coste = np.sum(residuos(par, fpx) ** 2)
        if mejor is None or coste < mejor[0]:
            mejor = (coste, par)
    return mejor[1]


def trazo(lienzo, a, b, color, grosor=2):
    n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) + 1
    for t in np.linspace(0, 1, n * 2):
        x, y = a + (b - a) * t
        x, y = int(x), int(y)
        if -grosor <= x < ANCHO + grosor and -grosor <= y < ALTO + grosor:
            lienzo[max(y - grosor, 0):max(y + grosor, 0), max(x - grosor, 0):max(x + grosor, 0), :3] = color


exif = focal_35mm(FOTO)
fpx = exif["eq"] / 36.0 * ANCHO
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
escena = bpy.context.scene
# Una carpeta por intervencion, para conservar las comparaciones anteriores.
SALIDA = RAIZ / "renders" / f"h1_i{escena['intervencion']}_comparacion"
par = ajustar(fpx)
if escena["intervencion"] >= 3:
    # Desde la portada se usa la camara ajustada con torre y remates (ningun punto de
    # la portada), la misma con la que se midio.
    par = np.array(json.loads((RAIZ / "referencias" / "medidas_portada.json")
                              .read_text(encoding="utf-8"))["camara_par"])
r, u, f = ejes(*par[3:6])
print("EXIF", exif, "CAMARA", np.round(par[:3], 2).tolist(),
      "giro/cabeceo/alabeo", np.round(np.degrees(par[3:]), 2).tolist())
px, _ = proyectar(par, [a[1] for a in AJUSTE], fpx)
errores = {a[0]: round(float(np.linalg.norm(p - a[2])), 1) for p, a in zip(px, AJUSTE)}
print("ERROR_PX", errores)

datos = bpy.data.cameras.new("CAM_foto")
datos.lens, datos.sensor_width, datos.sensor_fit = exif["eq"], 36.0, "HORIZONTAL"
cam = bpy.data.objects.new("CAM_foto", datos)
escena.collection.objects.link(cam)
cam.matrix_world = Matrix([[r[0], u[0], -f[0], par[0]], [r[1], u[1], -f[1], par[1]],
                           [r[2], u[2], -f[2], par[2]], [0, 0, 0, 1]])
escena.camera = cam
escena.render.resolution_x, escena.render.resolution_y = ANCHO, ALTO
SALIDA.mkdir(parents=True, exist_ok=True)
escena.render.filepath = str(SALIDA / "modelo_misma_camara.png")
bpy.ops.render.render(write_still=True)

# Superposicion: cantos superiores del modelo sobre la foto.
img = bpy.data.images.load(str(FOTO))
img.scale(ANCHO, ALTO)
buf = np.empty(ANCHO * ALTO * 4, np.float32)
img.pixels.foreach_get(buf)
lienzo = buf.reshape(ALTO, ANCHO, 4)[::-1].copy()       # fila 0 arriba

COLORES = {"torre": (1.0, 0.1, 0.05), "cuerpo": (0.1, 1.0, 0.2),
           "contrafuerte": (1.0, 0.85, 0.0), "remate": (1.0, 0.2, 1.0),
           "portada": (0.1, 1.0, 0.2), "ventana": (1.0, 1.0, 1.0), "fachadas": (0.0, 0.85, 1.0)}
dg = bpy.context.evaluated_depsgraph_get()
ojo = cam.matrix_world.translation


def visible(punto):
    d = punto - ojo
    # Se arranca 1 m por delante: el ajuste puede dejar la camara pegada a un muro vecino.
    u = d.normalized()
    ok, golpe, *_ = escena.ray_cast(dg, ojo + u, u, distance=d.length)
    return not ok or (golpe - ojo).length > d.length - 0.12


for o in escena.objects:
    if o.type != "MESH" or o.hide_render or not o.name.startswith("Concatedral"):
        continue
    clave = next((c for c in COLORES if c in o.name), None)
    if clave is None or "interior" in o.name or o.name.endswith("cubierta"):
        continue
    if "contrafuerte_torre" in o.name:
        clave = "torre"
    # Los panos con huecos tienen muchas diagonales: tambien van por aristas vivas.
    if o.get("dibujar_aristas") or (escena["intervencion"] >= 4 and "fachadas" in o.name):
        # Aristas vivas: las que separan caras con mas de 30 grados entre si.
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.transform(o.matrix_world)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
        bm.normal_update()
        for arista in bm.edges:
            if len(arista.link_faces) == 2 and arista.calc_face_angle(0.0) < 0.52:
                continue
            a, b = (v.co.copy() for v in arista.verts)
            tramos = max(int((b - a).length / 0.1), 1)
            for k in range(tramos):
                s, e = a.lerp(b, k / tramos), a.lerp(b, (k + 1) / tramos)
                q, z = proyectar(par, [s, e], fpx)
                if (z > 1).all() and visible((s + e) / 2):
                    trazo(lienzo, q[0], q[1], COLORES[clave], 1)
        bm.free()
        continue
    for cara in o.data.polygons:
        v = [o.matrix_world @ o.data.vertices[i].co for i in cara.vertices]
        n = (v[1] - v[0]).cross(v[2] - v[0]).normalized()
        if abs(n.z) > 0.5 or n.dot(cam.matrix_world.translation - v[0]) <= 0:
            continue                                   # solo caras vistas desde la foto
        for i in range(3):
            a, b = v[i], v[(i + 1) % 3]
            horizontal_alto = min(a.z, b.z) > 6 and (a.xy - b.xy).length > 0.15
            vertical = (a.xy - b.xy).length < 0.01 and clave in ("cuerpo", "contrafuerte", "remate")
            if not (horizontal_alto or vertical):
                continue
            tramos = max(int((b - a).length / 0.1), 1)
            for k in range(tramos):                    # se omite lo tapado por otra pieza
                s, e = a.lerp(b, k / tramos), a.lerp(b, (k + 1) / tramos)
                if not visible((s + e) / 2):
                    continue
                q, z = proyectar(par, [s, e], fpx)
                if (z > 1).all():
                    trazo(lienzo, q[0], q[1], COLORES[clave])
for _, _, (x, y) in AJUSTE:
    for d in (np.array([14.0, 0]), np.array([0, 14.0])):
        trazo(lienzo, np.array([x, y]) - d, np.array([x, y]) + d, (1.0, 0.0, 1.0), 2)

salida = bpy.data.images.new("superpuesta", ANCHO, ALTO, alpha=True)
salida.pixels.foreach_set(np.ascontiguousarray(lienzo[::-1]).ravel())
salida.filepath_raw = str(SALIDA / "foto_con_lineas.png")
salida.file_format = "PNG"
salida.save()
(SALIDA / "ajuste.json").write_text(json.dumps({
    "foto": FOTO.name, "autor": "Jesusccastillo", "licencia": "CC BY-SA 3.0 ES",
    "exif_focal": exif, "camara_xyz": np.round(par[:3], 3).tolist(),
    "giro_cabeceo_alabeo_grados": np.round(np.degrees(par[3:]), 3).tolist(),
    "puntos_de_ajuste_error_px": errores, "imagen_px": [ANCHO, ALTO],
    "matriz_camara": [list(fila) for fila in cam.matrix_world],
}, indent=2, ensure_ascii=False), encoding="utf-8")
print("HECHO", SALIDA)
