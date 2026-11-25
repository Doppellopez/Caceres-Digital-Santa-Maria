CÁCERES DIGITAL — SANTA MARÍA, PROTOTIPO 0.1

Fuente: Ayuntamiento de Cáceres, cartografía vuelo 2012, archivos
trama urbana_2012_3D.dxf y relieve_2012_3D.dxf aportados por el usuario.
Comprobar condiciones de reutilización antes de redistribuir.

Blender: File > Import > glTF 2.0 > santa_maria.glb.
Alternativa: importar santa_maria.obj (ejes Y forward, Z up; conservar .mtl al lado).
Guardar como .blend. GLB usa Y arriba, Blender convierte al importar.
Escala: metros. Origen local ETRS89 / UTM 29N (EPSG:25829):
E=726189.9868201963, N=4372743.045037453, cota=440 m.
Recorte de 150 x 150 m. Edificios divididos en sectores de cubierta y fachada.
OBJ tiene UV plana provisional en metros; GLB usa colores provisionales.

Geometría: terreno interpolado a partir de puntos de cota y trazados urbanos
(escaleras, bordillos, soportales y pilares). Cubiertas aproximadas triangulando
contornos cerrados y muestras de limatesas/limahoyas. Fachadas generadas entre
contorno superior y terreno. Se resuelven solapes por prioridad de polilíneas 3D.
No es una reconstrucción exacta: faltan curvas de nivel, restricciones de
triangulación, detalles de fachadas, patios, torres, texturas y comprobación
visual contra fotografías. Hay posibles picos, huecos y errores de cubierta.
No es malla cerrada ni lista para colisiones. No se ha probado en Blender/Unity.

Regeneración: Python 3 con numpy, scipy, shapely, trimesh, matplotlib.
Ejecutar python generate_santa_maria.py en la carpeta descomprimida.
El JSON contiene la extracción local de entidades DXF con cotas absolutas.
