"""Extrae a CSV los vertices de la red topografica municipal (RedPol 2009) y compara su cota con el MDT02.

Entrada: datos/originales/redpol_2009/RedPol_2009_WEB.dxf (convertido del DWG con LibreDWG 0.14).

Las coordenadas del DWG estan en ED50 / UTM 29N (EPSG:23029): se anaden convertidas a ETRS89 (25829).
Se comprobo con la red poligonal en el casco: convertidas, el 15 % cae sobre edificio; sin convertir, el 57 %.

Uso (con el Python de QGIS, desde la raiz del proyecto):
    "C:\\Program Files\\QGIS 3.44.15\\bin\\python-qgis-ltr.bat" herramientas\\redpol_estaciones.py
"""
import csv
import math
from pathlib import Path

import numpy as np
from osgeo import gdal, ogr, osr

gdal.UseExceptions()
osr.UseExceptions()
ed50, etrs89 = osr.SpatialReference(), osr.SpatialReference()
for ref, codigo in ((ed50, 23029), (etrs89, 25829)):
    ref.ImportFromEPSG(codigo)
    ref.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
A_ETRS89 = osr.CoordinateTransformation(ed50, etrs89)
RAIZ = Path(__file__).resolve().parents[1]
CARPETA = RAIZ / "datos" / "originales" / "redpol_2009"
MDT = RAIZ.parents[1] / "Research" / "Source" / "CNIG" / "MDT02-ETRS89-HU29-0704-1-COB2.tif"
CAPAS = ("Red Poligonal 2009", "Red GPS2009")
CASCO = (726000.0, 4372420.0, 726512.0, 4372996.0)

fuente = ogr.Open(str(CARPETA / "RedPol_2009_WEB.dxf"))
circulos, textos = [], []
for f in fuente.GetLayer(0):
    capa = f.GetField("Layer")
    g = f.GetGeometryRef()
    if capa not in CAPAS or g is None:
        continue
    x0, x1, y0, y1, z0, z1 = g.GetEnvelope3D()
    clase = f.GetField("SubClasses") or ""
    if clase.endswith("AcDbCircle"):
        circulos.append((capa, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    elif clase.endswith("AcDbText") and f.GetField("Text"):
        textos.append((capa, x0, y0, f.GetField("Text").strip()))

ds = gdal.Open(str(MDT))
gt, relieve = ds.GetGeoTransform(), ds.GetRasterBand(1)


def cota_mdt(e, n):
    c, f = int((e - gt[0]) / gt[1]), int((n - gt[3]) / gt[5])
    if not (0 <= c < ds.RasterXSize and 0 <= f < ds.RasterYSize):
        return None
    v = float(relieve.ReadAsArray(c, f, 1, 1)[0, 0])
    return v if v > 0 else None


filas, vistos, dif = [], set(), []
for capa, e, n, z in circulos:
    clave = (capa, round(e, 1), round(n, 1))
    if clave in vistos:
        continue
    vistos.add(clave)
    cerca = min((t for t in textos if t[0] == capa),
                key=lambda t: math.hypot(t[1] - e, t[2] - n), default=None)
    nombre = cerca[3] if cerca and math.hypot(cerca[1] - e, cerca[2] - n) < 15 else ""
    et, nt = A_ETRS89.TransformPoint(e, n)[:2]
    en_casco = CASCO[0] <= et <= CASCO[2] and CASCO[1] <= nt <= CASCO[3]
    m = cota_mdt(et, nt)
    if z > 0 and m is not None:
        dif.append(z - m)
    filas.append((capa, nombre, f"{e:.3f}", f"{n:.3f}", f"{et:.2f}", f"{nt:.2f}", f"{z:.3f}",
                  "si" if en_casco else "no"))

with open(CARPETA / "estaciones.csv", "w", newline="", encoding="utf-8") as salida:
    w = csv.writer(salida)
    w.writerow(("capa", "etiqueta_cercana", "este_ed50", "norte_ed50", "este_etrs89", "norte_etrs89",
                "cota", "en_casco"))
    w.writerows(sorted(filas))
print("ESTACIONES", len(filas), "EN_CASCO", sum(r[-1] == "si" for r in filas))
if dif:
    d = np.array(dif)
    print("COTA_RED_MENOS_MDT02 n=%d mediana=%.2f p10=%.2f p90=%.2f"
          % (d.size, np.median(d), np.percentile(d, 10), np.percentile(d, 90)))
