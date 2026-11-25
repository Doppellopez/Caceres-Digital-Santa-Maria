# CLAUDE.md — Cáceres Digital / Santa María

## Misión y límites

Construir una recreación exterior, editable y de alta fidelidad de la plaza de Santa María de Cáceres tal como existe actualmente. El entregable maestro será `blender/santa_maria.blend`, con texturas y scripts reproducibles cuando proceda. Jorge dirige las decisiones visuales y creativas. Trabaja con él, no a sus espaldas.

Qazrix es el videojuego Unity inspirado en la leyenda de la Mansaborá. Este repositorio es una dependencia de arte, no el juego: no introducir personajes, misiones, NPC, lógica de juego, medievalización ni cambios en su repositorio. El juego consumirá exportaciones versionadas; no editar el maestro desde Unity. No ampliar el ámbito a otras plazas hasta que Jorge acepte la primera.

## Material entregado

- `modelos/v0.3/`: GLB (importación preferida) y OBJ/MTL alternativos. 84 geometrías en el GLB. Concatedral aproximada en componentes `Concatedral_*`.
- `modelos/v0.2/`: comparación previa al refinamiento, 69 geometrías; conservar intacta.
- `datos/locales/santa_maria_dxf_local.json`: extracción local de entidades 3D, fuente directa del modelo. Diccionario por archivo; cada registro contiene tipo, capa, lista de puntos XYZ, indicador de cierre y texto. XY locales, Z absoluta.
- `datos/locales/santa_maria_cartografia.json` y `santa_maria_planta.obj`: extracción anterior KMZ, bidimensional; no usar para alturas.
- `datos/originales/`: DXF convertido por el usuario desde DWG municipal y archivos DGN/DWG/KMZ originales. No es necesario descomprimirlos para empezar. Los DXF juntos pesan unos 371 MB sin comprimir.
- `herramientas/`: generadores Python históricos v0.1 y v0.2; no hay generador completo v0.3 conservado. Para regenerar v0.2, copia su script y el JSON DXF a una carpeta de trabajo y ejecuta allí `python generate_santa_maria_v0_2.py`. Dependencias numpy, scipy, shapely, trimesh (matplotlib para v0.1). No sobrescribir modelos de referencia.
- `referencias/`: planos y capturas de las versiones previas; son visualizaciones del modelo o cartografía, NO fotografías reales ni renders Blender.
- `historico/`: paquete v0.1 y notas originales.

## Contrato espacial

Unidades en metros. Origen del sistema local documentado en v0.1: ETRS89 / UTM zona 29N, EPSG:25829, E=726189.9868201963, N=4372743.045037453, referencia vertical 440 m (no se ha verificado el datum vertical). En el OBJ y datos locales: X este, Y norte, Z arriba (restar 440 a Z absoluta del JSON). El GLB usa la transformación (x,z,-y) con Y arriba; Blender convierte al importar. No aplicar una segunda rotación a ciegas. No recentrar los edificios individualmente perdiendo su posición. Mantener origen común en exportaciones. Recorte nominal de 150 m por lado; la malla de terreno v0.2/v0.3 alcanza aproximadamente ±80 m debido a puntos de apoyo. No asumir una frontera exacta.

## Estado y limitaciones iniciales

La malla no es una restitución arquitectónica validada. Hay picos en terreno, interpolación aproximada, cubiertas con huecos, alturas inferidas, fachadas planas, ausencia de texturas, colisiones y LOD. Los datos de cubierta contienen puntos y líneas, no superficies acabadas. La identificación de la concatedral (polígono de ~993 m², punto interior local ~28,-2) se hizo por forma y posición; confirmar con cartografía y fotografías. En v0.3 se conservaron plantas como base, pero se impusieron formas aproximadas de nave, ábside, torre y contrafuertes. No considerar la torre ni sus dimensiones verdaderas: verificar y sustituir si procede. La descripción oficial menciona torre occidental de tres cuerpos, contrafuertes y portadas góticas. No hay fotos incluidas ni prueba previa de importación real en Blender/Unity. Los GLB v0.2/v0.3 se han leído con trimesh. OBJ dispone de UV planas provisionales; no asumir que GLB trae UV útiles para texturizar.

## Protocolo de trabajo

1. Comprueba herramientas reales: versión de Blender, ruta al ejecutable y posibilidad de renderizar. Si existe CLI, usa Python/bpy y Blender en background (`blender -b archivo.blend -P script.py`). Si no existe, pide a Jorge que lo instale o localice; no simules resultados. Antes de tocar geometría, guarda el .blend inicial y un render general y otro a ~1,65 m sobre el suelo, en la plaza mirando al edificio elegido. Registra cámara, focal, resolución y versión.
2. Jorge elige UN edificio y UNA intervención. Localiza objetos por geometría y coordenadas, comprueba identificación contra referencias. No modificar el resto de la ciudad. Formula un cambio pequeño con criterio observable; pide decisión a Jorge cuando haya alternativas creativas importantes o falten referencias que cambien el resultado.
3. Obtén fotografías reales con licencia compatible o proporcionadas por Jorge. Guarda URL, autor, licencia y elemento representado en `referencias/fuentes.md`; guarda imágenes autorizadas en una carpeta aparte. No extraer texturas de Street View sin permiso ni dar por libre una imagen por estar en Internet. Si no hay referencias suficientes, marcar la pieza como provisional. No inventar puertas ni ventanas para aparentar fidelidad.
4. Rectifica fotografías por planos de fachada cuando sea viable. Ajusta UV, materiales y escala; evita iluminación horneada excesiva. Modela en 3D los elementos con impacto en silueta o paralaje (contrafuertes, jambas, arcos, cornisas); usa textura para detalle superficial. No necesitas reproducir piedra a piedra. Mantén materiales y objetos editables, nombres estables y texturas relativas.
5. Renderiza desde la misma cámara, compara antes/después y con fotos reales. Inspecciona en otra vista para detectar huecos, normales invertidas, superficies duplicadas, penetraciones y elementos flotantes. Si empeora, revierte. No eliminar triángulos sin resolver los huecos resultantes. Verifica dimensiones contra datos medidos, no solo por apariencia.
6. Presenta a Jorge captura, cambios, incertidumbres y siguiente decisión. Guarda scripts reproducibles en `herramientas/` y avances en `CHANGELOG.md`. No sustituir el archivo maestro sin copia o commit. No generar una ilustración con IA y presentarla como render de la geometría.

## Hitos y aceptación

- H0: importar v0.3, comprobar escala/orientación y producir renders reales. Guardar baseline.
- H1: una fachada reconocible desde la plaza. Comparación fotográfica, geometría y materiales revisados por Jorge.
- H2: completar exteriores de la concatedral (incluida torre verificada), o el edificio que Jorge haya elegido. Mantener componentes separables.
- H3: resto de fachadas de la plaza, una por una; terreno, escaleras y pavimento transitables. No extender el área sin aprobación.
- H4: exportar a Unity y probar recorrido en proyecto vacío o escena de integración, sin tocar la lógica de Qazrix.

No considerar un hito terminado por haber escrito código: debe existir un modelo y una captura real, revisados. Las referencias, medidas y aproximaciones deben distinguirse claramente. La fidelidad a un edificio real tiene prioridad frente al número de edificios completados.

## Entrega a Qazrix (cuando corresponda)

Acordar versión Unity y render pipeline (URP/HDRP/Built-in) con Jorge. Exportar GLB como formato portable o FBX probado para Unity, texturas separadas y manifiesto de versión, origen, escala, ejes y dependencias. Unity no necesariamente importa GLB de fábrica: usar importador compatible o FBX. Probar orientación, escala con personaje estándar, materiales, normales, colisiones simplificadas y acceso a escaleras. Mantener identificadores y .meta estables cuando se cree un paquete Unity; nunca imponer reimportaciones que rompan referencias. El paquete no incluirá código de juego. LOD y optimización se decidirán tras medir, no ahora.

## Fuentes y derechos

Cartografía municipal, vuelo 2012: https://sig.caceres.es/cartografia/vuelo-2012/ . Datos originales proporcionados por Joaquín; comprobar licencia específica y atribución antes de publicar o redistribuir. No asumir que el acceso público equivale a licencia comercial. Descripción patrimonial: https://cacereshistorica.caceres.es/patrimonio-historico/edificios-historicos/arquitectura-religiosa/concatedral-de-santa-maria/ ; https://concatedralcaceres.com/la-catedral/ . Son referencias descriptivas, no una fuente de texturas automáticamente autorizadas. Buscar fotos de Wikimedia Commons con licencia individual compatible o fotografías propias. No se incluyen imágenes de terceros.
