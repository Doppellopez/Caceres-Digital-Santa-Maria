# Fachada noroeste de la concatedral: medidas

Fuente: `datos/locales/santa_maria_dxf_local.json`, archivo `trama urbana_2012_3D.dxf`, registro 1688 (POLYLINE, capa `Edificio singular`, 101 puntos). Reproducir: `blender -b --factory-startup -P herramientas/h1_medicion_noroeste.py`. Planta comparativa: `renders/h1_medicion/planta_torre.png` (rojo: torre del levantamiento; azul: torre v0.3; negro: contorno; gris: resto de v0.3).

Distancias en planta desde la esquina exterior de la torre (5,3 ; -7,3) hacia la cabecera. Alturas = cota del contorno menos terreno interpolado a 1 m de la fachada (el terreno es provisional).

## Del levantamiento

| Elemento | Posición | Cota local (Z) | Altura aprox. |
|---|---|---|---|
| Torre, cornisa o remate registrado | esquina; lados de unos 7 m (NO) y 8 m (SO) | 27,77 | 26,0 m |
| Alero junto a la torre | 11 m | 15,05 | 13,4 m |
| Tramo bajo | 11,4 a 16,8 m (unos 5,4 m) | 12,54 | 10,9 m |
| Alero, resto de la fachada | 18 a 36 m | 14,7 a 15,6 (con puntos sueltos en 10,22 y 17,37) | 13,2 a 14,6 m |

## Comparación con v0.3

- Torre v0.3: centro (15,7 ; -14,1), cubierta en Z 25,63. Está a unos 8 m de la posición del levantamiento, apartada de la fachada noroeste, y es unos 2,1 m más baja.
- Aleros v0.3: todos a Z 14,125.

## Interpretación (provisional)

- El tramo bajo coincide en posición y proporción con el cuerpo de la portada que se ve en las fotos. Es una correspondencia visual, no un dato del DXF.
- La posición de la torre en la esquina coincide con las fotos de `fuentes.md`.
- El contorno no incluye la esquina interior de la torre, ni pináculos, huecos de campanas o portada.

## Intervención 1 aplicada (2026-11-25)

Script: `herramientas/h1_i1_torre_alturas.py` (parte siempre de `blender/copias/santa_maria_h0.blend`). Informe: `renders/h1_i1_despues/informe.json`.

Provisional o interpretado:
- Muro tras los cuerpos salientes: recta entre los puntos 59 y 67 del contorno.
- Esquina interior de la torre: cierre en paralelogramo.
- Tapas planas del contrafuerte de la torre y del cuerpo escalonado.
- Cubierta de cierre junto a la torre: no representa la cubierta real.
- No se aplican las cotas de los puntos 49 y 50 (17,37; generaban una aguja) ni la del 67 (15,88; inclinaba el muro 1 m; se usa 15,04).
- Ocultos, no borrados: `Concatedral_contrafuerte_2`, `_3` y `_4` de v0.3, que chocaban con la torre o la portada.

## Contraste con la foto

`herramientas/h1_comparar_foto.py` ajusta la cámara a *Santa María, Cáceres.JPG* con focal EXIF (27 mm equivalentes) y tres puntos de la torre (error 5 a 15 px sobre 2000). La torre, por tanto, no queda verificada por esta prueba. Diferencias en lo demás, estimadas a ojo (unos 55 px por metro):

| Elemento | Diferencia |
|---|---|
| Altura del cuerpo de la portada y del escalón | unos 0,4 m o menos |
| Pretil, centro y derecha | unos 0,4 m o menos |
| Pretil, extremo izquierdo | hasta unos 1,2 m alto en el modelo |
| Lado derecho del cuerpo de la portada | unos 2 m corto en el modelo |
| Lado izquierdo del escalón | alrededor de 1 m más ancho en el modelo |
| Contrafuertes v0.3 restantes (0 y 1) | desplazados unos 2 a 3 m; falta el que flanquea la portada por la izquierda |

## Intervención 2: contrafuertes y remates (2026-11-25)

Scripts: `h1_medir_contrafuertes.py` (retroproyección sobre la foto), `h1_i2_contrafuertes.py` (parte de `blender/copias/santa_maria_i1.blend`). `s` es la distancia a lo largo del muro desde el punto 67 hacia la cabecera.

| Contrafuerte | s (m) | Origen de la posición | Añadido |
|---|---|---|---|
| B1 | 22,3 a 23,4 | DXF 51-54 (ya estaba en los muros) | remate |
| B2 | 18,0 a 19,2 | DXF 55-58 (ya estaba en los muros) | cuerpo bajo, repisa a Z 5,7 y remate |
| B3 | 12,1 a 13,0 | extremo del escalón, DXF 59-60, y foto | tramo entre escalón y pretil, repisa a Z 11,9 y remate |
| B4 | 6,2 a 7,1 | DXF 62 y foto | tramo sobre la portada y remate |
| B5 | 0,0 a 0,8 | DXF 65-66 (intervención 1) | remate |

Medidas en la foto: ancho 0,84 a 0,99 m (se usa 0,90); remate sobre el pretil 1,58 a 1,70 m (se usa 1,65). Las posiciones de la foto salen unos 0,6 a 0,75 m desplazadas respecto al DXF en B2 y B5, de forma constante; B3 y B4 coinciden con el DXF al corregirlo.

Provisional: planta cuadrada y profundidad de los remates; vuelo extra del pie de B2 (0,12 m); retranqueo de B3. Sin modelar: figuras talladas sobre los remates, gárgolas, cabezas bajo la repisa de B2, repisa baja de B1 y remates de la torre. B1 no se ve en la foto medida (sí en *Concatedral 02*).

### Correcciones al contraste anterior

- El escalón **no** estaba 1 m ancho: lo que parecía exceso es el pie de B3.
- El pretil del extremo izquierdo no está demostrado que esté 1,2 m alto: con la cámara ajustada solo a la torre el pie del remate B2 se desvía 68 px; ajustándola con torre y remates (`h1_diagnostico_camara.py`) los siete puntos quedan entre 8 y 28 px (unos 0,15 a 0,5 m). Es una prueba de coherencia, no independiente.

### Pendiente visto en los renders

- Un triángulo de cubierta de v0.3 asoma por delante del muro entre B1 y B2.
- El cuerpo de la portada sigue corto por la derecha (unos 2 m).

## Intervención 3: portada (2026-11-25)

Scripts: `h1_medir_portada.py` (escribe `medidas_portada.json`) y `h1_i3_portada.py` (parte de `blender/copias/santa_maria_i2.blend`).

| Elemento | Medida | Origen |
|---|---|---|
| Frente del cuerpo | 1,32 m delante del muro principal; cornisa Z 12,54 | DXF 62-64 |
| Ancho del cuerpo | s -0,90 a 7,69 (8,6 m) | foto |
| Arco exterior | 7,57 m de ancho; clave Z 10,37; arranque Z 6,08 | foto |
| Arco interior | 3,73 m; clave Z 8,42 (en la foto 8,43) | foto |
| Puertas | dos hojas de unos 1,6 m, parteluz de unos 0,5 m, del umbral a Z 6,08 | foto |
| Escaleras | umbral Z 1,98, peldaño Z 1,80, arranque Z 1,57 | DXF, capa `Escalera` |
| Cornisa y canecillos | 0,20 m de grueso, once canecillos | foto |

Posición a lo largo del muro: eje de las escaleras del DXF (s 3,59). El primer intento ancló el canto izquierdo del cuerpo al punto 62; las escaleras mostraron que ese punto no es el canto del cuerpo.

Provisional: abocinado de 1,0 m (la foto sugiere 0,6 ± 0,5, no concluyente), seis arquivoltas lisas de reparto uniforme, vuelo de la cornisa, rebaje de las puertas.

Sin modelar: molduras, capiteles, basas, imagen de la Virgen en el parteluz, clavos, herrajes y postigo, cabezas de los canecillos, faroles.

Cambios fuera de la portada:
- Terreno: 45 vértices bajados (máximo 0,46 m) solo delante de la portada, porque la rampa interpolada de v0.3 tapaba los peldaños.
- Cubierta: un vértice del ala sur movido para quitar el triángulo que asomaba entre B1 y B2.
- `Concatedral_contrafuerte_portada` (B5) queda solo sobre la cornisa.

### Contraste con la foto (`renders/h1_i3_comparacion`)

Cámara ajustada con torre y cuatro remates. Estimado a ojo:
- Cornisa: coincide a la izquierda; a la derecha unos 20 px (0,35 m).
- Clave del arco: altura dentro de unos 5 px; unos 20 px desplazada en horizontal.
- Pie (puertas y peldaños): las líneas quedan unos 50 a 60 px por encima (cerca de 1 m aparente). Causa sin determinar: el ajuste no modela la distorsión de la lente y no se ha separado de un posible error de cota del suelo. El modelo sigue las cotas del DXF.
- Rayos al pie de la portada: 847, ninguno pasa detrás del muro.

## Intervención 4: ventanas (2026-11-25)

Scripts: `h1_medir_ventanas.py` (escribe `medidas_ventanas.json`) y `h1_i4_ventanas.py` (parte de `blender/copias/santa_maria_i3.blend`).

| Ventana | Tipo | s (m) | Ancho exterior / vidrio | Antepecho a clave (Z) |
|---|---|---|---|---|
| W1 (entre B3 y B4) | medio punto | 9,9 | 1,79 / 0,51 | 11,7 a 14,2 |
| W2 (sobre la portada) | medio punto | 3,6 | 1,79 / 0,51 | 11,7 a 14,2 (la cornisa tapa el pie) |
| W3 (entre B5 y la torre) | medio punto | -2,0 | 1,79 / 0,51 | 12,0 a 14,5 |
| W4 (entre B1 y B2) | apuntada | 20,7 | 2,37 / 0,44 | 6,1 a 10,9 |

Medidas sobre *Santa María, Cáceres.JPG*, corrigiendo la cámara con los pies de los remates; son relativas a los contrafuertes. W1 a W3 comparten tamaño. W4 sale de su clave y su canto derecho, porque la foto la tapa a medias; su forma se contrastó a la vista con *Concatedral 02*.

Provisional: fondo del vidrio (0,45 m), tres órdenes lisos por ventana, arco apuntado equilátero (la clave del vidrio medida coincide con él), antepechos escalonados en lugar del derrame inclinado de W4.

Sin modelar: molduras y guardapolvo, plomos del vidrio, reja de W4, la saetera cegada del cuerpo escalonado y los huecos de la torre.

Comprobaciones: 8.984 rayos de frente por los cuatro huecos sin ninguna fuga; el borde de cada hueco coincide con el abocinado (se corrigió una rendija que se veía en oblicuo).

Contraste (`renders/h1_i4_comparacion`, a ojo): W1 dentro de unos 15 px; W2 y W3 unos 15 a 20 px a la izquierda, igual que la portada y los remates de esa zona con esta cámara; el canto visible de W4, unos 10 px.

## Intervención 5: piedra (2026-11-25)

Jorge eligió la sillería generada. Script: `h1_i5_piedra.py` (parte de `blender/copias/santa_maria_i4.blend`); generador común en `silleria.py`.

- Texturas en `texturas/concatedral/` (color y normales OpenGL, 2048×1024, 6,4×3,2 m por repetición, hiladas de 0,40 m), con ruta relativa.
- Material `Granito_silleria_concatedral` en 35 piezas de piedra de la concatedral, **incluidas las otras fachadas**, que comparten objeto con la noroeste y no se han revisado.
- UV nuevas (`UVMap`) en metros; juntas radiales en arquivoltas.
- Vidrios más mates: el reflejo del sol parecía un hueco.
- Ningún vértice movido (comprobado por el script).

Limitaciones: no es la piedra real; sin verdín, manchas ni desgaste; los sillares no se ajustan a esquinas ni dovelas reales; se ven saltos de junta entre paños y una franja estrecha donde se solapan el cuerpo de la portada y el escalonado. Sin probar en Unity.

## Intervención 6: torre (2026-11-25)

Scripts: `h1_medir_torre.py` (escribe `medidas_torre.json`) y `h1_i6_torre.py` (parte de `blender/copias/santa_maria_i5.blend`).

| Elemento | Cota Z / medida | Origen |
|---|---|---|
| Cornisas | 17,9 / 21,6 / 27,8 | foto; la última, DXF |
| Campanario noroeste | 23,1 a 26,3; 1,9 m de ancho | foto |
| Balaustrada | 21,9 a 23,0 | foto |
| Medallón | 19,3 a 21,0 | foto |
| Ventana ciega | 11,9 a 14,7 | foto |
| Ventanucos | 6,4-7,5; 15,8-17,1; 19,3-20,2 | foto |
| Pináculos | hasta 30,5 | foto |
| Dos huecos de campanas noreste | posición y ancho estimados | *J29 199* |

Posiciones horizontales medidas desde la esquina oeste. Comprobación: 6.471 rayos por los huecos, sin fugas.

Provisional o sin modelar: fondos; perfil de campana, yugo, balaustres y pináculos; medallón sin escudo; sin cruz del yugo, gárgolas ni discos de las esquinas. El cuarto pináculo (sur) no se ve y se supone igual. Las caras suroeste y sureste no tienen huecos: faltan fotos descargadas.

Contraste (`renders/h1_i6_comparacion`, a ojo): cornisas y campanario dentro de unos 10 px; ventanucos y ventana ciega 15 a 30 px a la izquierda (unos 0,4 a 0,7 m).

Discrepancias abiertas:
- La cara noreste parece unos 0,8 m más corta en la foto: la esquina interior de la torre es un supuesto desde la intervención 1.
- El contrafuerte de la torre (DXF 74-77) sale en la foto unos 0,6 m más hacia el oeste.
