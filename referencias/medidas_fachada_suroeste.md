# Fachada suroeste de la concatedral (portada, rosetón y torre)

Intervención 10, 2026-11-26. Pedida por Jorge ("Sí, modélala"), pendiente de su revisión.

Reproducir: `python herramientas/i10_medir_suroeste.py` (escribe `medidas_suroeste.json`) y `i10_fachada_suroeste.py` en Blender (parte de `blender/copias/santa_maria_i9.blend`).

## Identificación

Las fotos propias 184905, 184908 y 184911 se atribuyen a esta cara porque su disposición coincide con el contorno municipal (torre, vano de 8,2 m, contrafuerte de 1,4 m y muro que baja hasta el edificio contiguo). Jorge confirmó que era la cara a modelar.

## Método

Ajuste conjunto de las tres cámaras (focal 1.699 px sobre 1500 × 2000; EXIF 1.676) con las cornisas de la torre del modelo y puntos del contorno. Error mediano 2,0 / 2,1 / 4,1 px; máximo 20 px. Los píxeles se marcaron a ojo.

**Las tres fotos se tomaron casi desde el mismo punto: miden posiciones y alturas sobre los planos, no profundidades.**

| Elemento | s (m) | Cota Z (m) | Origen |
|---|---|---|---|
| Coronación del muro | 8,0 a 16,2 | 18,5 | contorno (18,48) y fotos (18,47 a 18,64) |
| Muro que baja | 17,6 a 25,2 | 18,35 a 15,41 | contorno; fotos de acuerdo en 0,1 m |
| Rosetón | centro 11,68; diámetros 2,5 y 1,4 | 13,02 | fotos |
| Cuerpo de la portada | 9,2 a 14,66 | hasta 9,74 | fotos |
| Cornisa y ocho canecillos | 8,82 a 14,90 | 9,74 a 10,00 | fotos |
| Arco exterior / vano | 5,0 / 2,2 m de ancho | claves 8,22 / 6,86 | fotos |
| Contrafuerte junto a la torre | 6,52 a 7,56 | repisa 14,2; remate 17,9 | fotos |
| Contrafuerte de la derecha | 16,23 a 17,60 | repisa 14,3; remate 18,2 | contorno y fotos |
| Campanario | eje 3,63; 2,2 m | 23,1 a 26,3 | fotos (cara noroeste: 23,1 a 26,3) |
| Medallón | eje 3,28 | 19,85 | fotos |
| Dos ventanas con reja, cinco saeteras y moldura | ver JSON | 4,7 a 23,1 | fotos |

`s` se mide a lo largo de la fachada desde la esquina oeste de la torre (punto 82 del contorno).

## Estimado

- Profundidades: puerta 1,1 m detrás del frente (por la asimetría aparente del arco); cuerpo de la portada 0,5 m; cornisa 0,35 m; contrafuerte de la torre 0,75 m; derrames, escalones del rosetón y fondos de huecos.
- Grosor del muro levantado (0,55 m) y cubierta que lo une con la nave: no representan la cubierta real.
- Puerta, vidriera y medallón usan recortes de las fotos nocturnas.

## Sin modelar

Capiteles y basas (reducidos a bloques), cabezas de los canecillos, armas del escudo, herrajes, faroles, placa, gárgolas, discos de la torre, cruz del yugo.

## Discrepancias abiertas

- La torre del modelo sale en estas fotos unos 0,6 a 0,9 m más ancha por la derecha (lado sur) que en la realidad: el canto fotografiado cae en s ≈ 7,3 y el contorno municipal llega a 8,26. Concuerda con la cara noreste 0,8 m corta ya anotada. No se ha tocado.
- Junto al contrafuerte de la torre queda a la vista el resalte de esquina del contorno, que en las fotos no se aprecia.

## Comprobaciones

17.092 rayos por rosetón, portada y huecos de la torre, sin fugas. Solo cambian `Concatedral_fachadas`, `Concatedral_torre_fachadas` y `Concatedral_cubierta_cierre_provisional`. Renders desde las cámaras ajustadas en `renders/i10_antes` y `renders/i10_despues`.
