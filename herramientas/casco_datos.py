"""Casco antiguo: prepara las rejillas de relieve y cubiertas para ampliar la maqueta.

Fuentes (solo lectura), CNIG/IGN, en ../../Research/Source/CNIG:
  - LiDAR PNOA 2018, cuadro 726-4374, clase 6 (edificios)
  - MDT02 2a cobertura, hoja 0704-1, ETRS89 HU29
Ventana (EPSG:25829): E 726000..726512, N 4372420..4372996. El borde oeste es el del cuadro LiDAR.

Uso (con el Python de QGIS, desde la raiz del proyecto; no descarga nada):
    "C:\\Program Files\\QGIS 3.44.15\\bin\\python-qgis-ltr.bat" herramientas\\casco_datos.py
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from osgeo import gdal
from scipy import ndimage

gdal.UseExceptions()

RAIZ = Path(__file__).resolve().parents[1]
FUENTES = RAIZ.parents[1] / "Research" / "Source" / "CNIG"
LAZ = FUENTES / "PNOA_2018_EXT_N_726-4374_ORT-CLA-IRC.laz"
MDT = FUENTES / "MDT02-ETRS89-HU29-0704-1-COB2.tif"
SALIDA = RAIZ / "datos" / "locales" / "casco_lidar.npz"
PDAL = r"C:\Program Files\QGIS 3.44.15\bin\pdal.exe"

E0, N0, ANCHO, ALTO = 726000.0, 4372420.0, 512, 576
CELDA_CUBIERTA, CELDA_SUELO = 1.0, 2.0
COTA_REF = 440.0
ALTURA_MIN = 2.0      # m sobre el terreno para contar una celda como edificio
AREA_MIN = 8          # celdas: menos es ruido

with tempfile.TemporaryDirectory() as tmp:
    tif = os.path.join(tmp, "cubiertas.tif")
    tuberia = [
        {"type": "readers.las", "filename": str(LAZ), "override_srs": "EPSG:25829"},
        {"type": "filters.crop",
         "bounds": "([%f,%f],[%f,%f])" % (E0, E0 + ANCHO, N0, N0 + ALTO)},
        {"type": "filters.range", "limits": "Classification[6:6]"},
        {"type": "writers.gdal", "filename": tif, "gdaldriver": "GTiff", "data_type": "float32",
         "output_type": "max", "resolution": CELDA_CUBIERTA, "radius": 0.6, "window_size": 0,
         "nodata": -9999.0, "origin_x": E0, "origin_y": N0, "width": ANCHO, "height": ALTO},
    ]
    ruta = os.path.join(tmp, "tuberia.json")
    Path(ruta).write_text(json.dumps(tuberia), encoding="utf-8")
    subprocess.run([PDAL, "pipeline", ruta], check=True)
    ds = gdal.Open(tif)
    cubierta = ds.ReadAsArray().astype(np.float32)   # fila 0 = norte
    ds = None


def relieve(celda):
    ds = gdal.Warp("", str(MDT), format="MEM", dstSRS="EPSG:25829",
                   outputBounds=(E0, N0, E0 + ANCHO, N0 + ALTO), xRes=celda, yRes=celda,
                   resampleAlg="bilinear")
    return ds.ReadAsArray().astype(np.float32)


suelo_1m = relieve(CELDA_CUBIERTA)
assert cubierta.shape == suelo_1m.shape == (ALTO, ANCHO)
hay = (cubierta > -9000) & (cubierta - suelo_1m >= ALTURA_MIN)

# Huecos de una celda dentro de los tejados (densidad de puntos del LiDAR).
for _ in range(2):
    vecinos = ndimage.convolve(hay.astype(int), np.ones((3, 3), int), mode="constant")
    nuevos = ~hay & (vecinos >= 5)
    mediana = ndimage.generic_filter(np.where(hay, cubierta, np.nan), np.nanmedian, size=3,
                                     mode="nearest") if nuevos.any() else cubierta
    cubierta[nuevos] = mediana[nuevos]
    hay |= nuevos

etiquetas, n = ndimage.label(hay)
tam = np.bincount(etiquetas.ravel())
hay &= tam[etiquetas] >= AREA_MIN

# Vertices del terreno cada CELDA_SUELO, incluidos los dos bordes.
fino = relieve(0.5)
filas = np.minimum((np.arange(0, ALTO + 1, CELDA_SUELO) / 0.5).astype(int), fino.shape[0] - 1)
cols = np.minimum((np.arange(0, ANCHO + 1, CELDA_SUELO) / 0.5).astype(int), fino.shape[1] - 1)
suelo = fino[np.ix_(filas, cols)]
assert np.isfinite(suelo).all() and suelo.min() > 300, "celdas sin relieve"

SALIDA.parent.mkdir(parents=True, exist_ok=True)
np.savez_compressed(
    SALIDA,
    cubierta=np.where(hay, cubierta - COTA_REF, np.nan).astype(np.float32),
    suelo=(suelo - COTA_REF).astype(np.float32),
    ventana=np.array([E0, N0, ANCHO, ALTO], np.float64),
    celdas=np.array([CELDA_CUBIERTA, CELDA_SUELO], np.float64),
)
print("CELDAS_EDIFICADAS", int(hay.sum()), "SUELO", suelo.shape,
      "COTAS", round(float(suelo.min()), 1), round(float(suelo.max()), 1), "->", SALIDA)
