"""H4 (prueba): exporta el maestro a FBX para Unity, con texturas y manifiesto.

Abre blender/santa_maria.blend y NO lo guarda. Sale a exports/unity/:
santa_maria.fbx, Texturas/ y manifiesto.json. Solo en la exportacion, los
materiales por color de vertice de v0.3 se sustituyen por tres colores planos y
se vuelven hacia arriba las cubiertas de la concatedral que miran hacia abajo.
h4_probar_unity.ps1 genera despues SantaMaria.unitypackage.

Uso (desde la raiz del proyecto):
    blender -b --factory-startup -P herramientas/h4_exportar_unity.py
"""
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

RAIZ = Path(__file__).resolve().parents[1]
BLEND = RAIZ / "blender" / "santa_maria.blend"
SALIDA = RAIZ / "exports" / "unity"
FBX = SALIDA / "santa_maria.fbx"
CONTROLES = ("Terreno_interpolado", "Concatedral_torre_pinaculo_2", "Concatedral_portada_peldanos",
             "Concatedral_ventana_W4_vidrio", "Concatedral_cuerpo_portada")
CUBIERTAS_V03 = ("Concatedral_nave", "Concatedral_ala_norte", "Concatedral_ala_sur",
                 "Concatedral_abside")
CAMARAS = ("CAM_foto", "CAM_peaton_noroeste", "CAM_portada", "CAM_torre", "CAM_general")


def sha(ruta):
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def redondo(v, n=4):
    return [round(float(x), n) for x in v]


bpy.ops.wm.open_mainfile(filepath=str(BLEND))
escena = bpy.context.scene
assert escena.get("intervencion") == 12, "el maestro no es el de la intervencion 12"
SALIDA.mkdir(parents=True, exist_ok=True)

mallas = [o for o in escena.objects if o.type == "MESH" and not o.hide_render]
excluidos = sorted(o.name for o in escena.objects if o.type == "MESH" and o.hide_render)


# --- cubiertas v0.3 con la cara hacia abajo: Unity no las dibujaria desde arriba ---
volteadas = {}
for nombre in CUBIERTAS_V03:
    o = bpy.data.objects[nombre]
    normal_m = o.matrix_world.to_3x3().inverted_safe().transposed()
    abajo = [p for p in o.data.polygons if (normal_m @ p.normal).z < -1e-6]
    for p in abajo:
        p.flip()
    o.data.update()
    volteadas[nombre] = len(abajo)


# --- ranuras de material sin caras: Unity no las importa --------------------------
for o in mallas:
    usadas = {p.material_index for p in o.data.polygons}
    for i in reversed(range(len(o.data.materials))):
        if i not in usadas:
            o.data.materials.pop(index=i)


# --- materiales provisionales para lo que v0.3 pinta por vertice ---------------
def categoria(o, material):
    if o.name.startswith("Terreno"):
        return "Provisional_terreno"
    if material and not material.name.startswith("DefaultMaterial"):
        return None
    if any(c in o.name for c in ("cubierta", "nave", "ala_", "abside")):
        return "Provisional_cubierta"
    return "Provisional_fachada_v03"


sumas = {}
for o in mallas:
    cats = {categoria(o, m) for m in (o.data.materials or [None])} - {None}
    for cat in cats if o.data.color_attributes else ():
        capa = o.data.color_attributes[0]
        total = sumas.setdefault(cat, [Vector((0, 0, 0)), 0])
        for d in capa.data:
            total[0] += Vector(d.color[:3])
            total[1] += 1
planos = {}
for cat, (suma, n) in sumas.items():
    color = suma / n
    m = bpy.data.materials.new(cat)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = 0.9
    planos[cat] = m
for o in mallas:
    if not o.data.materials:
        o.data.materials.append(None)
    for i, m in enumerate(o.data.materials):   # ranura a ranura: conserva la teja
        cat = categoria(o, m)
        if cat:
            o.data.materials[i] = planos[cat]

# --- texturas y manifiesto de materiales ----------------------------------------
carpeta_tex = SALIDA / "Texturas"
carpeta_tex.mkdir(exist_ok=True)
for antigua in carpeta_tex.glob("*.png"):
    antigua.unlink()
materiales = {}
for m in (m for o in mallas for m in o.data.materials):
    if m.name in materiales:
        continue
    b = m.node_tree.nodes["Principled BSDF"]
    datos = {"color_lineal": redondo(b.inputs["Base Color"].default_value[:3], 5),
             "rugosidad": round(b.inputs["Roughness"].default_value, 3),
             "metalico": round(b.inputs["Metallic"].default_value, 3)}
    for nodo in m.node_tree.nodes:
        if nodo.type == "TEX_IMAGE":
            origen = Path(bpy.path.abspath(nodo.image.filepath))
            shutil.copy2(origen, carpeta_tex / origen.name)
            clave = "textura_normal" if "normal" in origen.name else "textura_color"
            datos[clave] = origen.name
            datos["sin_repetir"] = nodo.extension == "EXTEND"
    materiales[m.name] = datos

# --- controles de escala y ejes, camaras y sol ----------------------------------
controles = {}
for nombre in CONTROLES:
    o = bpy.data.objects[nombre]
    pts = [o.matrix_world @ v.co for v in o.data.vertices]
    controles[nombre] = {"min": redondo([min(p[i] for p in pts) for i in range(3)]),
                         "max": redondo([max(p[i] for p in pts) for i in range(3)])}
camaras = []
for nombre in CAMARAS:
    o = bpy.data.objects[nombre]
    giro = o.matrix_world.to_3x3()
    camaras.append({"nombre": nombre, "posicion": redondo(o.matrix_world.translation),
                    "frente": redondo(giro @ Vector((0, 0, -1)), 6),
                    "arriba": redondo(giro @ Vector((0, 1, 0)), 6),
                    "focal_mm": o.data.lens, "sensor_horizontal_mm": o.data.sensor_width,
                    "ancho": 2000 if nombre == "CAM_foto" else 1600,
                    "alto": 1328 if nombre == "CAM_foto" else 1000})
sol = bpy.data.objects["Sol_base"].matrix_world.to_3x3() @ Vector((0, 0, -1))

# --- recorridos de prueba (eje de la portada, ver intervencion 3) ----------------
dxf = json.loads((RAIZ / "datos" / "locales" / "santa_maria_dxf_local.json")
                 .read_text(encoding="utf-8"))["/mnt/data/work/trama urbana_2012_3D.dxf"][1688][2]
A, B = Vector(dxf[67][:2]), Vector(dxf[58][:2])
T = (B - A).normalized()
N = Vector((-T.y, T.x))
if N.dot(Vector((-0.69, 0.72))) < 0:
    N = -N
eje = json.loads((RAIZ / "referencias" / "medidas_portada.json")
                 .read_text(encoding="utf-8"))["eje_escalera"]
terreno = bpy.data.objects["Terreno_interpolado"]


def en_suelo(s, d):
    q = A + T * s + N * d
    inv = terreno.matrix_world.inverted()
    abajo = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
    ok, golpe, *_ = terreno.ray_cast(inv @ Vector((q.x, q.y, 200.0)), abajo)
    assert ok, (s, d)
    return redondo((q.x, q.y, (terreno.matrix_world @ golpe).z))


umbral = bpy.data.objects["Concatedral_portada_peldanos"]
cota_umbral = max((umbral.matrix_world @ v.co).z for v in umbral.data.vertices)
puerta = A + T * (eje + 1.0) + N * 0.55      # ante una hoja, sin chocar con el parteluz
recorridos = [
    {"nombre": "plaza_a_puerta", "meta_cota": round(cota_umbral, 3),
     "puntos": [{"p": en_suelo(eje + 1.0, 9.0)}, {"p": en_suelo(eje + 1.0, 3.0)},
                {"p": redondo((puerta.x, puerta.y, cota_umbral))}]},
    {"nombre": "a_lo_largo_de_la_fachada", "meta_cota": -999,
     "puntos": [{"p": en_suelo(-2.0, 6.0)}, {"p": en_suelo(9.0, 6.0)},
                {"p": en_suelo(21.0, 6.0)}]},
]

# --- exportacion -----------------------------------------------------------------
bpy.ops.object.select_all(action="DESELECT")
for o in mallas:
    o.hide_set(False)
    o.select_set(True)
bpy.context.view_layer.objects.active = mallas[0]
# Medido en Unity 6000.3: sin esto el modelo entra girado 180 grados (cambiar
# axis_forward no lo corrige, porque Unity deshace los ejes declarados en el FBX).
# Se gira solo la copia en memoria y se aplican las transformaciones.
media_vuelta = Matrix.Rotation(math.pi, 4, "Z")
for o in mallas:
    o.matrix_world = media_vuelta @ o.matrix_world
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.export_scene.fbx(
    filepath=str(FBX), use_selection=True, object_types={"MESH"},
    apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", global_scale=1.0,
    axis_forward="-Z", axis_up="Y", use_space_transform=True, bake_space_transform=True,
    mesh_smooth_type="FACE", use_tspace=False, path_mode="STRIP", embed_textures=False,
    add_leaf_bones=False, bake_anim=False, use_custom_props=False)

commit = subprocess.run(["git", "-C", str(RAIZ), "log", "-1", "--format=%h"],
                        capture_output=True, text=True).stdout.strip()
manifiesto = {
    "version": "H1-i12-prueba-1",
    "origen": {"archivo": "blender/santa_maria.blend", "sha256": sha(BLEND),
               "commit_al_exportar": commit, "blender": bpy.app.version_string},
    "unidades": "metros",
    "sistema_local": {"crs": "ETRS89 / UTM 29N (EPSG:25829)", "E": 726189.9868201963,
                      "N": 4372743.045037453, "cota_referencia_m": 440.0,
                      "nota": "datum vertical sin verificar"},
    "ejes": {"blender": "X este, Y norte, Z arriba", "unity_esperado": "X este, Y arriba, Z norte"},
    "archivos": [{"ruta": "santa_maria.fbx", "sha256": sha(FBX)}]
    + [{"ruta": f"Texturas/{p.name}", "sha256": sha(p)} for p in sorted(carpeta_tex.iterdir())],
    "mallas": len(mallas),
    "triangulos": sum(len(p.vertices) - 2 for o in mallas for p in o.data.polygons),
    "excluidos_ocultos": excluidos,
    "caras_volteadas_solo_en_exportacion": volteadas,
    "materiales": [{"nombre": n, **d} for n, d in sorted(materiales.items())],
    "material_por_objeto": [{"objeto": o.name,
                             "materiales": [m.name for m in o.data.materials]}
                            for o in mallas],
    "controles": [{"objeto": n, **d} for n, d in controles.items()],
    "recorridos": recorridos,
    "camaras": camaras,
    "sol_direccion": redondo(sol, 6),
    "dependencias": "Unity 6000.3.6f1 con URP 17.3.0; sin paquetes de terceros",
    "avisos": ["geometria provisional fuera de la fachada noroeste",
               "colisiones sin simplificar y sin LOD",
               "silleria: despiece generado con grano de fotos propias; intervenciones 7 y 8 sin revisar",
               "teja arabe (intervencion 9) generada por codigo, sin revisar; solo textura",
               "fachada suroeste (intervencion 10) sin revisar; vuelos y profundidades estimados",
               "licencia de la cartografia municipal sin comprobar"],
}
(SALIDA / "manifiesto.json").write_text(json.dumps(manifiesto, indent=1, ensure_ascii=False),
                                        encoding="utf-8")
print("EXPORTADO mallas", len(mallas), "triangulos", manifiesto["triangulos"],
      "excluidos", len(excluidos), "MB", round(FBX.stat().st_size / 1e6, 2))
print("MATERIALES", sorted(materiales))
print("VOLTEADAS", volteadas)
